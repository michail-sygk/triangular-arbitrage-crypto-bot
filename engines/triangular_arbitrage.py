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
import threading
 

class CryptoEngineTriArbitrage(object):
    def __init__(self, exchange, mock=False):
        self.exchange = exchange
        self.mock = mock
        self.minProfitUSDT = 0.00013
        self.openOrderCheckCount = 0
      
        self.engine = EngineLoader.getEngine(self.exchange['exchange'], self.exchange['keyFile'])
        self.should_I_do_trade = True
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
            rs = [self.engine.get_open_order()]
            responses = self.send_request(rs)

            if  responses[0].text != '[]':
                return True
            return False
 
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
            if status == 1: 
                maxBalance = min(bid_ask_amount, balance)  
                USDT  = maxBalance *(lastTradeRate * (1-self.engine.feeRatio))
            else: 
                maxBalance = min(bid_ask_amount , balance / bid_ask_price )  
                USDT  = maxBalance *(lastTradeRate * (1-self.engine.feeRatio))

            return [maxBalance , USDT]

   #Check different opportunities which can give us arbitrage opportunities 
    def place_orders_to_arbitrages(self):
       #Load all  the necessary csv and getting the combinations
        dataframe_object_opportunities = Dataframe('data/bittrex/fullfilled_triangular_arbitrage.csv')
        dataframe_all_arbitrage_combinations = Dataframe ('data/bittrex/triangular_arbitrage_selected_combinations.csv')       
        
        
        all_combinations = []
        df = dataframe_all_arbitrage_combinations.return_dataframe()
        for ind in df.index:
            all_combinations.append([df['TickerPairA'][ind],
                                     df['TickerPairB'][ind],
                                     df['TickerPairC'][ind],
                                     df['Route'][ind]])
        session =dataframe_object_opportunities.return_dataframe()['Session'].iloc[-1] + 1
        round_number = 0
       #
        while True :
            try:
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
                    tickerB = pairs[0].replace('-', ' ').split()[1] + '-USDT'
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
                    bidRoute_result = (1 / bidRates [0]) / askRates[1]  * bidRates[2]
                    askRoute_result = (1 * bidRates[0]) / askRates[2]  * bidRates[1]

                    percentage_profit_bidRoute =( (bidRoute_result - 1 ) / 1 ) * 100
                    percentage_profit_askRoute =( (askRoute_result - 1 ) / 1 ) * 100
                     
                  
              # Here We aee starting to execute the arbitrage
              #1st Step check if the profit will be more than the fees + trades
                    if bidRoute_result > 1 and percentage_profit_bidRoute > 0.86 :
                        print('Bidroute-result' + str(bidRoute_result))
 
                        tickers = [pairs[0].split('-')[1], pairs[1].split('-')[1],pairs[2].split('-')[0]]
                        rs = [self.engine.get_ticker_orderBook_innermost(pairs[0]),
                              self.engine.get_ticker_orderBook_innermost(pairs[1]),
                              self.engine.get_ticker_orderBook_innermost(pairs[2]),
                              self.engine.get_balance( tickers),
                              
                              ]
                        responses = self.send_request(rs)
                        self.engine.balance = responses[3].parsed
 

                        [maxAmount_Pair_1,USDT_1] =self.get_maxAmount_in_a_specific_currency_and_USDT( 
                                                                                                  responses[0].parsed['ask']['amount'] 
                                                                                                 ,responses[0].parsed['ask']['price'] 
                                                                                                 , lastPrices[0]
                                                                                                 ,self.engine.balance[pairs[0].split('-')[1]] , 0 )
                        [maxAmount_Pair_2,USDT_2] =self.get_maxAmount_in_a_specific_currency_and_USDT( 
                                                                                                      responses[1].parsed['ask']['amount']  
                                                                                                     ,responses[1].parsed['ask']['price'] 
                                                                                                     ,lastPrices[2]
                                                                                                     , maxAmount_Pair_1 ,0 )
                        [maxAmount_Pair_3,USDT_3] =self.get_maxAmount_in_a_specific_currency_and_USDT( 
                                                                                                  responses[2].parsed['bid']['amount']  
                                                                                                 ,responses[2].parsed['bid']['price'] 
                                                                                                 , lastPrices[2]
                                                                                                 , maxAmount_Pair_2  ,1 )

                        maxUSDT = min([USDT_1 , USDT_2 , USDT_3])
                        maxAmounts = [maxUSDT / lastPrices[0] , maxUSDT / lastPrices[2] , maxUSDT / lastPrices[2]]

                        fee = 0
                        for index, amount in enumerate(maxAmounts[0:3]):
                            fee += amount * float(lastPrices[index])
                        fee *= self.engine.feeRatio
                        bidRoute_profit = (bidRoute_result - 1) * lastPrices[0] * maxAmounts[0]
                        if bidRoute_profit > 0 : break
                        if maxUSDT >  21:
                            if self.should_I_do_trade:
                                orderInfo_1 = [
                                    {
                                        "tickerPair":pairs[0],
                                        "action": "bid",
                                        "price": askRates[0],
                                        "amount": maxAmounts[0]
                                    } ]           
                                orderInfo_2 = [
                                     {
                                        "tickerPair": pairs[1],
                                        "action": "bid",
                                        "price": askRates[1],
                                        "amount": maxAmounts[1]
                                    }
                                    ] 
                                orderInfo_3 = [ 
                                                {
                                        "tickerPair": pairs[2],
                                        "action": "ask",
                                        "price": bidRates[2],
                                        "amount": maxAmounts[2]
                                    }            
                                               ]

                                t1 = threading.Thread(target = self.place_order, args = [orderInfo_1[0] , 0])
                                t2 = threading.Thread(target = self.place_order, args = [orderInfo_2[0] , 0.001])
                                t3 = threading.Thread(target = self.place_order, args = [orderInfo_3[0] , 0.002])

                                
 
                                t1.start()
                                t2.start()
                                t3.start()
                                t1.join()
                                t2.join()
                                t3.join()
                                
                                
                                
                                
                                
                                
                                while self.check_openOrder():
                                    try:
                                        print('There are still open orders..Process can not continue..')
                                        time.sleep(1)
                                    except: pass 

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
                            dataframe_object_opportunities.parse_data_to_dataframe(new_arbi_opp,'fullfilled_triangular_arbitrage.csv')
                            print ('Profit:' + str(bidRoute_profit - fee))

                    


                round_number = round_number + 1         
            except Exception as e : 
                print(e)
                time.sleep(5)
                pass

            time.sleep(0.75)
 
    def get_data_from_the_whole_orderbook(self):
        # Load all  the necessary csv and getting the combinations
        dataframe_object_opportunities = Dataframe(
            'data/bittrex/triangular_arbitrage_data.csv')
        dataframe_all_arbitrage_combinations = Dataframe(
            'data/bittrex/triangular_arbitrage_all_combinations.csv')

        all_combinations = []
        df = dataframe_all_arbitrage_combinations.return_dataframe()
        for ind in df.index:
            all_combinations.append([df['TickerPairA'][ind],
                                     df['TickerPairB'][ind],
                                     df['TickerPairC'][ind],
                                     df['Route'][ind]])

        session = dataframe_object_opportunities.return_dataframe()['Session'].iloc[-1] + 1
        state = 1
        round_number = 0
        while state:
            try:
                rs = self.engine.get_all_tickers_of_bittrex()
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

                    tickers = [tickerA, tickerB, tickerC]

                    # Some minor changes in the string of pairs
                    for i in range(0, len(tickers)):
                        if tickers[i] == 'USDT-USDT':
                            tickers[i] = 'USDT-USD'
                            continue
                        if tickers[i] == 'USD-USDT':
                            tickers[i] = 'USDT-USD'
                            continue
                        if tickers[i] == 'EUR-USDT':
                            tickers[i] = 'USDT-EUR'
                            continue
                        if tickers[i] == 'KMD-USDT':
                            tickers[i] = 'KMD-USD'
                            continue

                    # Getting the differences with USDT/USD in order to calculate excactly the profit. Maybe it will
                    # be a little bit differ the final result
                    lastPrices = []
                    for ticker in tickers:
                        for value in json:
                            if ticker == value['symbol']:
                                lastPrices.append(value['lastTradeRate'])
                                break

                                # Getting the bidRate and the askRate from the json to calculate if it exists
                                # arbitrage opportunity.
                    # If for some pairs will not find pairs at all
                    bidRates = []
                    askRates = []
                    for pair in pairs:
                        for value in json:
                            if pair == value['symbol']:
                                bidRates.append(value['bidRate'])
                                askRates.append(value['askRate'])

                    lastPrices = list(map(float, lastPrices))
                    bidRates = list(map(float, bidRates))
                    askRates = list(map(float, askRates))

                    if len(lastPrices) < 3:
                        break
                    if 0.0 in askRates or 0.0 in bidRates:
                        continue

                    # Ready to check for the arbitrage

                    # if the askRoute_result is greater than 1  there is a chance to exist Arbitrage..
                    bidRoute_result = (1 / askRates[0]) / askRates[1] * bidRates[2]
                    askRoute_result = (1 * bidRates[0]) / askRates[2] * bidRates[1]
                    
                    percentage_profit_bidRoute = ((bidRoute_result - 1) / 1) * 100
                    percentage_profit_askRoute = ((askRoute_result - 1) / 1) * 100

                    # Here We aee starting to execute the arbitrage
                    # 1st Step check if the profit will be more than the fees + trades
                    if bidRoute_result > 1 and percentage_profit_bidRoute > 0.6:
                        tickers = [pairs[0].split('-')[1], pairs[1].split('-')[1],pairs[2].split('-')[0]]
                        rs = [self.engine.get_ticker_orderBook_innermost(pairs[0]),
                              self.engine.get_ticker_orderBook_innermost(pairs[1]),
                              self.engine.get_ticker_orderBook_innermost(pairs[2])
                              ]
                        responses = self.send_request(rs)
                        [maxAmount_Pair_1,USDT_1] =self.get_maxAmount_in_a_specific_currency_and_USDT( 
                                                                                                  responses[0].parsed['ask']['amount'] 
                                                                                                 ,responses[0].parsed['ask']['price'] 
                                                                                                 , lastPrices[0]
                                                                                                 , responses[0].parsed['ask']['amount'] , 0 )
                        [maxAmount_Pair_2,USDT_2] =self.get_maxAmount_in_a_specific_currency_and_USDT( 
                                                                                                      responses[1].parsed['ask']['amount']  
                                                                                                     ,responses[1].parsed['ask']['price'] 
                                                                                                     ,lastPrices[1]
                                                                                                     , responses[0].parsed['ask']['amount'] ,0 )
                        [maxAmount_Pair_3,USDT_3] =self.get_maxAmount_in_a_specific_currency_and_USDT( 
                                                                                                  responses[2].parsed['bid']['amount']  
                                                                                                 ,responses[2].parsed['bid']['price'] 
                                                                                                 , lastPrices[2]
                                                                                                 , responses[2].parsed['bid']['amount'] ,1 )

                        maxUSDT = min([USDT_1 , USDT_2 , USDT_3])
                        maxAmounts = []
                        for index in range(0,3): 
                                  maxAmounts.append(maxUSDT /  lastPrices[index] ) 

                        fee = 0
                        for index, amount in enumerate(maxAmounts[0:3]):
                            fee += amount * float(lastPrices[index])
                        fee *= self.engine.feeRatio
                        bidRoute_profit = (bidRoute_result - 1) * lastPrices[0] * maxAmounts[0]
                        if bidRoute_profit < 0 :break
                        if maxUSDT > 20:
                            print(pairs)
                            print('BidRoute Percentage Profit: %.2f' % percentage_profit_bidRoute + '%')
                            profit_fee = bidRoute_profit - fee
                            if profit_fee < 0 : break
                            net_pecentage_profit = (profit_fee / maxUSDT) * 100
                            new_arbi_opp = Arbitrage_opportunity(pairs[0]
                                                                 , pairs[1]
                                                                 , pairs[2]
                                                                 , "{:.2f}".format(percentage_profit_bidRoute) + '%'
                                                                 , "{:.2f}".format(net_pecentage_profit) + '%'
                                                                 , bidRoute_profit - fee
                                                                 , maxUSDT
                                                                 , 'BidRoute'
                                                                 , bidRoute_result
                                                                 , 'Blocked'
                                                                   , round_number
                                                                 , session
                                                                 )
                            dataframe_object_opportunities.parse_data_to_dataframe(new_arbi_opp,'triangular_arbitrage_data.csv')
                            print('Profit:' + str(bidRoute_profit - fee))

                    if askRoute_result > 1 and percentage_profit_askRoute > 0.6:


                            rs = [self.engine.get_ticker_orderBook_innermost(pairs[0]),
                                  self.engine.get_ticker_orderBook_innermost(pairs[1]),
                                  self.engine.get_ticker_orderBook_innermost(pairs[2])]
                            responses = self.send_request(rs)
                            
                                    
                            [maxAmount_Pair_1,USDT_1] =self.get_maxAmount_in_a_specific_currency_and_USDT( 
                                                                                                          responses[0].parsed['bid']['amount']  
                                                                                                         ,responses[0].parsed['bid']['price'] 
                                                                                                         , responses[0].parsed['bid']['price'] 
                                                                                                         ,responses[0].parsed['bid']['amount'] 
                                                                                                         , 1 )
                            [maxAmount_Pair_2,USDT_2] =self.get_maxAmount_in_a_specific_currency_and_USDT( 
                                                                                                          responses[1].parsed['bid']['amount']  
                                                                                                         ,responses[1].parsed['bid']['price'] 
                                                                                                         ,lastPrices[1]
                                                                                                         ,responses[1].parsed['bid']['amount'] ,1 )
                            [maxAmount_Pair_3,USDT_3] =self.get_maxAmount_in_a_specific_currency_and_USDT( 
                                                                                                          responses[2].parsed['ask']['amount']  
                                                                                                         ,responses[2].parsed['ask']['price'] 
                                                                                                         ,responses[2].parsed['ask']['price'] 
                                                                                                         ,responses[2].parsed['ask']['amount']  ,0 )
 
                            maxUSDT = min([USDT_1 , USDT_2 , USDT_3])
                            maxAmounts = []
                           
                            for index in range(0,3): 
                                      maxAmounts.append(maxUSDT /  lastPrices[index] ) 
                            
                            fee = 0 
                            for index, amount in enumerate(maxAmounts[0:3]):
                                fee += amount * lastPrices[index]
                            fee *= self.engine.feeRatio
                            askRoute_profit = (askRoute_result - 1) * lastPrices[1] * maxAmounts[0]

                            if maxUSDT > 9:
                                print(pairs)
                                print('AskRoute Percentage Profit: %.2f' % percentage_profit_askRoute + '%')
                                profit_fee = askRoute_profit - fee
                                if profit_fee < 0 : break
                                net_pecentage_profit = (profit_fee / maxUSDT) * 100
                                new_arbi_opp = Arbitrage_opportunity( pairs[0]
                                                                    , pairs[1]
                                                                    , pairs[2]
                                                                    , "{:.2f}".format(percentage_profit_askRoute) + '%'
                                                                    , "{:.2f}".format(net_pecentage_profit) + '%'
                                                                    , askRoute_profit - fee
                                                                    , maxUSDT
                                                                    , 'AskRoute'
                                                                    , askRoute_result
                                                                    , 'Blocked'
                                                                    , round_number
                                                                    , session
                                                                    )
                                dataframe_object_opportunities.parse_data_to_dataframe(new_arbi_opp,'triangular_arbitrage_data.csv')
                                print('Profit:' + str(askRoute_profit - fee))

                round_number = round_number + 1
            except Exception as e:
                print(e)
                time.sleep(5)
                pass

            time.sleep(3) 
    #This is the function for placing an order
    def place_order(self, orderInfo , waiting_time =0 ):
        responses = False
        time.sleep(waiting_time)
        while responses == False:     
            print('Order has been sent..')
            print (orderInfo)
            rs = []
 
            rs.append(self.engine.place_order(
                    orderInfo['tickerPair'],
                    orderInfo['action'],
                    orderInfo['amount'],
                    orderInfo['price'])
                )

            if  self.mock:
                responses = self.send_request(rs)

            self.hasOpenOrder = True
            self.openOrderCheckCount = 0
    
     #This is the function which is responsible to send the requests and it returns us the response from the API
    def send_request(self, rs):
        responses = grequests.map( rs )
        for res in responses:
            if res.status_code == 409 : return False
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
        self.place_orders_to_arbitrages()
      # self.start_engine()
        
 