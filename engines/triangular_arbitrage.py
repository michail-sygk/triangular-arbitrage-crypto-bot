import time
from time import strftime
import grequests
import os 
import sys
from engines.exchanges.loader import EngineLoader
import json
import pandas as pd
from engines.arbitrage_opportunity import Arbitrage_opportunity
from engines.dataframe import Dataframe
 


class CryptoEngineTriArbitrage(object):
    def __init__(self, exchange, mock=False):
        self.exchange = exchange
        self.mock = mock
        self.minProfitUSDT = 0.00013
        self.hasOpenOrder = True # always assume there are open orders first
        self.openOrderCheckCount = 0
      
        self.engine = EngineLoader.getEngine(self.exchange['exchange'], self.exchange['keyFile'])

        self.frame_size = 20  # Number of entries in the dataframe
        self.logger_flag = True  # ON/OFF save Arbitrage oportunities to a dataframe

    # This loop starts the engine for the triangular Arbitrage..Since it will not appear an exception 
    '''In order to have a successful arbitrage they exist some steps which have to follow:
    1st : To check if exist open orders (This mean that an arbitrage still waits to fullfill)
    2nd : Check how much balance we have from each coin 
    3rd : Check the orderbook 
    4rth : Place orders since they exist arbitrage opporunity
    '''
    
    def start_engine(self):
        print ('starting Triangular Arbitrage Engine...')
        while True:
            try:
                if  self.hasOpenOrder: #We always assume in the start of the program that we have open orders
                    self.check_openOrder()
                    time.sleep(2)
                elif self.check_balance():           
                    bookStatus = self.check_orderBook()
                    if bookStatus['status']:
                        self.place_order(bookStatus['orderInfo'])
            except Exception as e :
               print (e)
            time.sleep(self.engine.sleepTime)
    
    def check_openOrder(self):
        if self.openOrderCheckCount >= 5:
            self.cancel_allOrders()
        else:
            print ('checking open orders...')
            rs = [self.engine.get_open_order()]
            responses = self.send_request(rs)

            if not responses[0]:
                print (responses)
                return False
            
            if responses[0].parsed:
                self.engine.openOrders = responses[0].parsed
                print (self.engine.openOrders)
                self.openOrderCheckCount += 1
            else:
                self.hasOpenOrder = False
                print ('no open orders')
                print ('starting to check order book...')
    
    def cancel_allOrders(self):
        print ('cancelling all open orders...')
        rs = []
        print (self.exchange['exchange'])
        for order in self.engine.openOrders:
            print (order)
            rs.append(self.engine.cancel_order(order['orderId']))

        responses = self.send_request(rs)
        
        self.engine.openOrders = []
        self.hasOpenOrder = False
    
   #Here we check the balance for each coin that we want to make Arbitrage
    def check_balance(self  , tickers):
        rs =  self.engine.get_balance( tickers)

        responses = self.send_request([rs])
 
        self.engine.balance = responses[0].parsed
 
        return True
    
    def get_maxAmount_in_a_specific_currency_and_USDT(self, bid_ask_amount , bid_ask_price , lastTradeRate , balance,status ):
        if status == 0:
                maxBalance = min(bid_ask_amount, (balance / bid_ask_price) /  (1 - self.engine.feeRatio) )
        else:
                maxBalance = min(bid_ask_amount, balance)
           
        USDT  = (maxBalance *lastTradeRate ) *  (1 - self.engine.feeRatio)
        return [maxBalance , USDT]

   #Check different opportunities which can give us arbitrage opportunities 
    def check_the_whole_order_book(self):
       #Load all  the necessary csv and getting the combinations
        dataframe_object_opportunities = Dataframe('data/bittrex/triangular_arbitrage_data.csv')
        dataframe_all_arbitrage_combinations = Dataframe ('data/bittrex/triangular_arbitrage_combinations.csv')       
        
        
        all_combinations = []
        df = dataframe_all_arbitrage_combinations.return_dataframe()
        for ind in df.index:
            all_combinations.append([df['TickerPairA'][ind],
                                     df['TickerPairB'][ind],
                                     df['TickerPairC'][ind],
                                     df['Route'][ind]])
       #

        
        session =dataframe_object_opportunities.return_dataframe()['Session'].iloc[-1] + 1
        state =  1
        round_number = 0
        while state :
            try:
                if state == 0 : break
                rs  = self.engine.get_all_tickers_of_bittrex()
                response = self.send_request([rs])
                json = response[0].json()


                for pairs in all_combinations:                
                
                    '''
                    It's necessary to calculate excactly how much is the profit for our arbitrage opportunities.This can happen only if 
                    we transfer the neccesary amounts in a stable currency.
                    Now I will take the necessary pairs and I will see kind of amount I have in USDT detecting their last prices.
                    '''
                    tickerA = pairs[0].replace('-', ' ').split()[0] + '-USDT'
                    tickerB = pairs[1].replace('-', ' ').split()[0] + '-USDT'
                    tickerC = pairs[1].replace('-', ' ').split()[0] + '-USDT'

                    tickers = [tickerA , tickerB , tickerC ]
                
                
              #Some minor changes in the string of pairs
                    for i in range(0,len(tickers)):
                        if tickers[i] == 'USDT-USDT' : 
                            tickers[i] = 'USDT-USD'
                            continue
                        if tickers[i] == 'USD-USDT' : 
                            tickers[i] = 'USDT-USD'
                            continue
                        if tickers[i] == 'EUR-USDT' : 
                            tickers[i] = 'USDT-EUR'
                            continue
                        if tickers[i] == 'KMD-USDT' : 
                            tickers[i] = 'KMD-USD'
                            continue
                
                # Getting the differences with USDT/USD in order to calculate excactly the profit. Maybe it will be a little bit differ the final result
                    lastPrices = []
                    for ticker in tickers:
                        for value in json: 
                            if ticker == value['symbol']: 
                                lastPrices.append(value['lastTradeRate'])          
                                break    
                            
                # Getting the bidRate and the askRate from the json to calculate if it exists arbitrage opportunity. 
                #If for some pairs will not find pairs at all                    
                    bidRates =  []
                    askRates  =  []   
                    for pair in pairs:
                        for value in json:
                            if pair ==  value['symbol'] :
                                bidRates.append(value['bidRate'])
                                askRates.append(value['askRate']) 
 
                    lastPrices =  list(map(float, lastPrices))
                    bidRates = list(map(float, bidRates))
                    askRates =list(map(float, askRates))

                    if len(lastPrices) <3 : 
                        break
                    if 0.0 in askRates or 0.0 in bidRates: 
                        continue
   
              # Ready to check for the arbitrage

               # if the askRoute_result is greater than 1  there is a chance to exist Arbitrage.. 
                    bidRoute_result = (1 / askRates[0]) / askRates[1]  * bidRates[2]
                    askRoute_result = (1 * bidRates[0]) / askRates[2]  * bidRates[1]

                    percentage_profit_bidRoute =( (bidRoute_result - 1 ) / 1 ) * 100
                    percentage_profit_askRoute =( (askRoute_result - 1 ) / 1 ) * 100
                
                 
              # Here We aee starting to execute the arbitrage
              #1st Step check if the profit will be more than the fees + trades
                    if bidRoute_result > 1 and percentage_profit_bidRoute > 0.6 :

                        if 'EUR'  == pairs[0].split('-')[1]: 
                            first_currency = 'EUR'
                            self.check_balance(['EUR'])
                        if 'USDT'  == pairs[0].split('-')[1]:
                            first_currency = 'USDT'
                            self.check_balance(['USDT'])
                        if 'USD'  == pairs[0].split('-')[1]:
                            first_currency = 'USD'
                            self.check_balance(['USD'])

                        rs = [self.engine.get_ticker_orderBook_innermost(pairs[0]),
                              self.engine.get_ticker_orderBook_innermost(pairs[1]),
                              self.engine.get_ticker_orderBook_innermost(pairs[2])
                              ]
                        responses = self.send_request(rs)

                        [maxAmount_Pair_1,USDT_1] =self.get_maxAmount_in_a_specific_currency_and_USDT( 
                                                                                                  responses[0].parsed['ask']['amount']  
                                                                                                 ,responses[0].parsed['ask']['price'] 
                                                                                                 , responses[0].parsed['ask']['price'] 
                                                                                                 ,self.engine.balance[first_currency] , 0 )
                        [maxAmount_Pair_2,USDT_2] =self.get_maxAmount_in_a_specific_currency_and_USDT( 
                                                                                                      responses[1].parsed['ask']['amount']  
                                                                                                     ,responses[1].parsed['ask']['price'] 
                                                                                                     ,lastPrices[1]
                                                                                                     , maxAmount_Pair_1 ,0 )
                        [maxAmount_Pair_3,USDT_3] =self.get_maxAmount_in_a_specific_currency_and_USDT( 
                                                                                                  responses[2].parsed['bid']['amount']  
                                                                                                 ,responses[2].parsed['bid']['price'] 
                                                                                                 ,responses[2].parsed['bid']['price'] 
                                                                                                 , maxAmount_Pair_2  ,1 )
                    
                        maxUSDT = min([USDT_1 , USDT_2 , USDT_3])
                        maxAmounts = []
                        maxAmounts.append(maxUSDT / responses[0].parsed['bid']['price'] )
                        for index in range(1,3): 
                                  maxAmounts.append(maxUSDT /  lastPrices[index] ) 

                        fee = 0
                        for index, amount in enumerate(maxAmounts):
                            fee += amount * float(lastPrices[index])
                        fee *= self.engine.feeRatio
                        bidRoute_profit = (bidRoute_result - 1) * float(lastPrices[0]) * maxAmounts[0]
 
                        if maxUSDT >  9:
                            print(pairs)
                            print('BidRoute Percentage Profit: %.2f' %  percentage_profit_bidRoute  + '%')
                            profit_fee = bidRoute_profit - fee
                            net_pecentage_profit =  (profit_fee  / maxUSDT) * 100
                            new_arbi_opp = Arbitrage_opportunity(  pairs[0]
                                                                  ,pairs[1]
                                                                  ,pairs[2]
                                                                  ,"{:.2f}".format(percentage_profit_bidRoute) +'%' 
                                                                  ,"{:.2f}".format(net_pecentage_profit) + '%' 
                                                                  ,bidRoute_profit - fee 
                                                                  ,maxUSDT
                                                                  ,'BidRoute'
                                                                  ,bidRoute_result
                                                                  ,'Blocked'
                                                                  , round_number
                                                                  , session
                                                                  )
                            dataframe_object_opportunities.parse_data_to_dataframe(new_arbi_opp)
                            print ('Profit:' + str(bidRoute_profit - fee))
    
                    if askRoute_result > 1 and percentage_profit_askRoute > 0.6 :
                        
                            if 'EUR'  == pairs[0].split('-')[1]: 
                                first_currency = 'EUR'
                                self.check_balance(['EUR'])
                            if 'USDT'  == pairs[0].split('-')[1]:
                                first_currency = 'USDT'
                                self.check_balance(['USDT'])
                            if 'USD'  == pairs[0].split('-')[1]:
                                first_currency = 'USD'
                                self.check_balance(['USD'])
                                
                            rs = [self.engine.get_ticker_orderBook_innermost(pairs[0]),
                                  self.engine.get_ticker_orderBook_innermost(pairs[1]),
                                  self.engine.get_ticker_orderBook_innermost(pairs[2])
                                  ]
                            responses = self.send_request(rs)
        
                            [maxAmount_Pair_1,USDT_1] =self.get_maxAmount_in_a_specific_currency_and_USDT( 
                                                                                                          responses[0].parsed['bid']['amount']  
                                                                                                         ,responses[0].parsed['bid']['price'] 
                                                                                                         , responses[0].parsed['bid']['price'] 
                                                                                                         ,self.engine.balance[first_currency] , 0 )
                            [maxAmount_Pair_2,USDT_2] =self.get_maxAmount_in_a_specific_currency_and_USDT( 
                                                                                                          responses[1].parsed['bid']['amount']  
                                                                                                         ,responses[1].parsed['bid']['price'] 
                                                                                                         ,lastPrices[1]
                                                                                                         , maxAmount_Pair_1 ,0 )
                            [maxAmount_Pair_3,USDT_3] =self.get_maxAmount_in_a_specific_currency_and_USDT( 
                                                                                                          responses[2].parsed['ask']['amount']  
                                                                                                         ,responses[2].parsed['ask']['price'] 
                                                                                                         ,responses[2].parsed['ask']['price'] 
                                                                                                         , maxAmount_Pair_2  ,1 )
                            
                            maxUSDT = min([USDT_1 , USDT_2 , USDT_3])
                            maxAmounts = []
                            maxAmounts.append(maxUSDT / responses[0].parsed['bid']['price'] )
                            for index in range(1,3): 
                                      maxAmounts.append(maxUSDT /  lastPrices[index] ) 
                             
                            fee = 0
                            for index, amount in enumerate(maxAmounts):
                                fee += amount * float(lastPrices[index])
                            fee *= self.engine.feeRatio
                            askRoute_profit = (askRoute_result - 1) * float(lastPrices[0]) * maxAmounts[0]
        
                            if maxUSDT >  9:
                                print(pairs)
                                print('AskRoute Percentage Profit: %.2f' %  percentage_profit_askRoute  + '%')
                                profit_fee = askRoute_profit - fee
                                net_pecentage_profit =  (profit_fee  / maxUSDT) * 100
                                new_arbi_opp = Arbitrage_opportunity(  pairs[0]
                                                                      ,pairs[1]
                                                                      ,pairs[2]
                                                                      ,"{:.2f}".format(percentage_profit_askRoute) +'%' 
                                                                      ,"{:.2f}".format(net_pecentage_profit) + '%' 
                                                                      ,askRoute_profit - fee 
                                                                      ,maxUSDT
                                                                      ,'AskRoute'
                                                                      ,askRoute_result
                                                                      ,'Blocked'
                                                                      , round_number
                                                                      , session
                                                                      )
                                dataframe_object_opportunities.parse_data_to_dataframe(new_arbi_opp)
                                print ('Profit:' + str(askRoute_profit - fee))
    

                round_number = round_number + 1         
            except Exception as e : 
                print(e)
                time.sleep(5)
                pass

            time.sleep(2)

                                
                            

                        
                        
            
 
 
                                
                    
                  
                
     
    #This Function is going_to check the orderbook for the pairs that we have defined to see if we arbitrage.    
    def check_orderBook(self):
        rs = [self.engine.get_ticker_lastPrice(self.exchange['tickerA']),
              self.engine.get_ticker_lastPrice(self.exchange['tickerB']),
              self.engine.get_ticker_lastPrice(self.exchange['tickerC']),
        ]
        lastPrices = []
        for res in self.send_request(rs):
            for value in res.parsed.values(): 
                lastPrices.append(value)
                
        rs = [self.engine.get_ticker_orderBook_innermost(self.exchange['tickerPairA']),
              self.engine.get_ticker_orderBook_innermost(self.exchange['tickerPairB']),
              self.engine.get_ticker_orderBook_innermost(self.exchange['tickerPairC']),
              ]
 
        responses = self.send_request(rs)
       
        '''It supposed that we have an arbitrage opportunity since the bidRoute_result is greater than 1 
        or askRoute_result is greater than 1 
        '''
       
        
        # bid route BTC->ETH->LTC->BTC for instance
        '''
        MORE EXPLANATION
        1st We buy ETH for BTC 
        2nd We buy LTC for ETH 
        3rd We sell LTC for BTC
        
        '''
        bidRoute_result = (1 / responses[0].parsed['ask']['price']) / responses[1].parsed['ask']['price'] * responses[2].parsed['bid']['price']  
    
        if bidRoute_result > 1:
            print('Bidroute :'+ str(bidRoute_result) )
            percentage_profit =( (bidRoute_result - 1 ) / 1 ) * 100
            print('Percentage Profit:' + str(percentage_profit))
                    
        # ask route ETH->BTC->LTC->ETH for instance 
        '''
        MORE EXPLANATION
        1st We buy ETH for BTC 
        2nd We buy LTC for BTC 
        3rd We sell LTC for ETH
        
        '''
                
        askRoute_result = (1 * responses[0].parsed['bid']['price']) / responses[2].parsed['ask']['price']   * responses[1].parsed['bid']['price']
        askRoute_result = -30 
        if askRoute_result > 1 :
         #   print('Askroute :'+ str(askRoute_result) )
            percentage_profit =( (askRoute_result - 1 ) / 1 ) * 100
           # print('Percentage Profit:' + str(percentage_profit))
        
        # Max amount for bid route & ask routes can be different and so less profit
        if bidRoute_result > 1 or \
        (bidRoute_result > 1 and askRoute_result > 1 and (bidRoute_result - 1) * lastPrices[0] > (askRoute_result - 1) * lastPrices[1]):
            status = 1 # bid route
        elif askRoute_result > 1:
            status = 2 # ask route
        else:
            status = 0 # do nothing
 
        if status   >  0  :
            #Since that now has appeared an arbitrage we have to check if with the fees we will have still a profit.
            maxAmounts = self.getMaxAmount(lastPrices, responses, status)
            fee = 0
            for index, amount in enumerate(maxAmounts):
                fee += amount * float(lastPrices[index])
            fee *= self.engine.feeRatio
            
            bidRoute_profit = (bidRoute_result - 1) * float(lastPrices[0]) * maxAmounts[0]
            askRoute_profit = (askRoute_result - 1) * float(lastPrices[1]) * maxAmounts[1]
            #print ('bidRoute_profit - {0} askRoute_profit - {1} fee - {2}'.format( bidRoute_profit, askRoute_profit, fee))
            #print('Profit-'+ str( bidRoute_profit - fee ))
            #print('Profit-'+ str( askRoute_profit - fee ))
            if status == 1 and bidRoute_profit - fee > self.minProfitUSDT:
                print (strftime('%Y%m%d%H%M%S') + ' Ask Route: Result - {0} Profit - {1} Fee - {2}'.format(askRoute_result, askRoute_profit, fee))

                orderInfo = [
                    {
                        "tickerPair": self.exchange['tickerPairA'],
                        "action": "ask",
                        "price": responses[0].parsed['ask']['price'],
                        "amount":  maxAmounts[1]   
                    },
                    {
                        "tickerPair": self.exchange['tickerPairB'],
                        "action": "ask",
                        "price": responses[1].parsed['ask']['price'],
                        "amount": maxAmounts[2]   
                    },
                    {
                        "tickerPair": self.exchange['tickerPairC'],
                        "action": "bid",
                        "price": responses[2].parsed['bid']['price'],
                        "amount": maxAmounts[2]  
                    }                                        
                ]
                return {'status': 1, "orderInfo": orderInfo}
            elif status == 10 and askRoute_profit - fee > self.minProfitUSDT:
                print (strftime('%Y%m%d%H%M%S') + ' Ask Route: Result - {0} Profit - {1} Fee - {2}'.format(askRoute_result, askRoute_profit, fee))
                orderInfo = [
                    {
                        "tickerPair": self.exchange['tickerPairA'],
                        "action": "bid",
                        "price": responses[0].parsed['bid']['price'],
                        "amount": maxAmounts[1]  
                    },
                    {
                        "tickerPair": self.exchange['tickerPairB'],
                        "action": "bid",
                        "price": responses[1].parsed['bid']['price'],
                        "amount": maxAmounts[2]   
                    },
                    {
                        "tickerPair": self.exchange['tickerPairC'],
                        "action": "ask",
                        "price": responses[2].parsed['ask']['price'],
                        "amount":maxAmounts[2]   
                    }                                        
                ]               
                return {'status': 2, 'orderInfo': orderInfo}
        return {'status': 0} # Using USDT may not be accurate
    # Here we calculate the max amounts that we can offer for the arbitrage
    def getMaxAmount(self, lastPrices, orderBookRes, status):
        maxUSDT = []
        for index, tickerIndex in enumerate(['tickerA', 'tickerB', 'tickerC']):
            # 1: 'bid', -1: 'ask'
            if index == 0: bid_ask = -1
            elif index == 1: bid_ask = -1
            else: bid_ask = 1
            # switch for ask route
            if status == 2: bid_ask *= -1
            
            bid_ask = 'bid' if bid_ask == 1 else 'ask'

            maxBalance = min(orderBookRes[index].parsed[bid_ask]['amount'], self.engine.balance[self.exchange[tickerIndex]])


            lastPrices =  list(map(float, lastPrices))
             
            USDT = maxBalance / ( lastPrices[index]  * (1 - self.engine.feeRatio))
            
            if not maxUSDT or USDT < maxUSDT: 
                maxUSDT = USDT       

        maxAmounts = []
        for index, tickerIndex in enumerate(['tickerA', 'tickerB', 'tickerC']):
            # May need to handle scientific notation
            if lastPrices[index] < 1 :
                maxAmounts.append(maxUSDT /  lastPrices[index] ) 
            else:
                maxAmounts.append(maxUSDT *  lastPrices[index] ) 


        return maxAmounts

 

  



    #This is the function for placing an order
    def place_order(self, orderInfo):
        print (orderInfo)
        rs = []
        for order in orderInfo:
            rs.append(self.engine.place_order(
                order['tickerPair'],
                order['action'],
                order['amount'],
                order['price'])
            )

        if  self.mock:
            responses = self.send_request(rs)

        self.hasOpenOrder = True
        self.openOrderCheckCount = 0

    #This is the function which is responsible to send the requests and it returns us the response from the API
    def send_request(self, rs):
        responses = grequests.map( rs )
        for res in responses:
            if not res:
                print (responses)
                raise Exception
        return responses


    ''' This function over here is responsible just to check all the pairs that I have defined inside to here
    to find in what percentages they exist arbitrage opportunities.
    
    For now you cannot choose both of them running.
    
    Choose the ckeck_the_whole_order_book or start_engine     
    '''
    def run(self):
        self.check_the_whole_order_book()
      # self.start_engine()
        
 