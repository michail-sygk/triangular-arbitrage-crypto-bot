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
from signalr_aio import Connection # https://github.com/slazarov/python-signalr-client
from base64 import b64decode
from zlib import decompress, MAX_WBITS
import hashlib
import hmac
import json
import asyncio
import time
import uuid
 
  

class CryptoEngineTriArbitrage(object):
    def __init__(self, exchange, mock=False):
        self.exchange = exchange
        self.mock = mock
        self.minProfitUSDT = 0.00013
        self.openOrderCheckCount = 0
        self.engine = EngineLoader.getEngine(self.exchange['exchange'], self.exchange['keyFile'])
        self.initial_df_with_all_tickers  =   pd.DataFrame(columns = ['Pair' , 'AskAmount' , 'AskRate', 'BidAmount', 'BidRate'])
        self.initial_df_with_all_tickers.set_index ('Pair' , inplace = True)
        self.dataframe_object_opportunities = Dataframe(
            'data/bittrex/triangular_arbitrage_data.csv')
        self.dataframe_all_arbitrage_combinations = Dataframe(
            'data/bittrex/triangular_arbitrage_all_combinations.csv')
        self.all_combinations = self.get_all_combinations()
        self.session = self.dataframe_object_opportunities.return_dataframe()['Session'].iloc[-1] + 1
        self.should_I_do_trade   = True
        self.round_number = 0
       
        tickers = ['USDT', 'EUR' , 'USD']
        rs =  [self.engine.get_balance( tickers) ] 
        responses = self.send_request(rs)
        self.engine.balance = responses[0].parsed
        print( 'Skata')
       
    def get_all_combinations(self):
        all_combinations = []
        df = self.dataframe_all_arbitrage_combinations.return_dataframe()
        for ind in df.index:
            all_combinations.append([df['TickerPairA'][ind],
                                     df['TickerPairB'][ind],
                                     df['TickerPairC'][ind],
                                     df['Route'][ind]])
        return all_combinations
        
 
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
    
   #Here we check the balance for each coin that we want to make Arbitrage
    def check_balance(self  , tickers):
        rs =  self.engine.get_balance( tickers)

        responses = self.send_request([rs])
 
        self.engine.balance = responses[0].parsed
 
        return True
    
    def get_maxAmount_in_a_specific_currency_and_USDT(self, bid_ask_amount , bid_ask_price , lastTradeRate , balance,status ):
            if status == 1: 
                maxBalance_without_fees = min(bid_ask_amount, balance )  
                USDT  = maxBalance_without_fees * lastTradeRate  
                max_balance_with_fees = maxBalance_without_fees * (1-self.engine.feeRatio)
            else: 
                maxBalance_without_fees = min(bid_ask_amount , (balance / bid_ask_price) )  
                USDT  = maxBalance_without_fees * lastTradeRate 
                max_balance_with_fees =  maxBalance_without_fees * (1-self.engine.feeRatio)

            return [maxBalance_without_fees , USDT , max_balance_with_fees]

   #Check different opportunities which can give us arbitrage opportunities 
    def place_orders_to_arbitrages(self):
       #Load all  the necessary csv and getting the combinations
       while True:
        try:
            for pairs in self.all_combinations:                
       
                # Getting the bidRate and the askRate from the json to calculate if it exists arbitrage opportunity. 
                #If for some pairs will not find pairs at all       
                try:             
                    bidRates =  [
                                 self.initial_df_with_all_tickers.at[pairs[0] , 'BidRate'],
                                 self.initial_df_with_all_tickers.at[pairs[1] , 'BidRate'],
                                 self.initial_df_with_all_tickers.at[pairs[2] , 'BidRate']
                                 ]
                    bidAmounts  = [
                        self.initial_df_with_all_tickers.at[pairs[0] , 'BidAmount'],
                        self.initial_df_with_all_tickers.at[pairs[1] , 'BidAmount'],
                        self.initial_df_with_all_tickers.at[pairs[2] , 'BidAmount']
                        ] 
                    
                    askRates  =  [
                        self.initial_df_with_all_tickers.at[pairs[0] , 'AskRate'],
                        self.initial_df_with_all_tickers.at[pairs[1] , 'AskRate'],
                        self.initial_df_with_all_tickers.at[pairs[2] , 'AskRate']]  
                    askAmounts =  [
                        self.initial_df_with_all_tickers.at[pairs[0] , 'AskAmount'],
                        self.initial_df_with_all_tickers.at[pairs[1] , 'AskAmount'],
                        self.initial_df_with_all_tickers.at[pairs[2] , 'AskAmount']]
                except: 
                    pass  
                    continue
          
 
                bidRates = list(map(float, bidRates     ))
                askRates =list(map(float, askRates      ))
                askAmounts = list(map(float ,askAmounts ))
                bidAmounts = list(map(float , bidAmounts))

                if len(askRates)<3 or len(bidRates) < 3:
                   continue
                if 0.0 in askRates or 0.0 in bidRates: 
                    continue
                if 0.0 in askAmounts or 0.0 in bidAmounts: 
                    continue
   
              # Ready to check for the arbitrage

               # if the askRoute_result is greater than 1  there is a chance to exist Arbitrage.. 
                bidRoute_result = (1 / askRates [0]) / askRates[1]  * bidRates[2]
                       
                  
              # Here We aee starting to execute the arbitrage
              #1st Step check if the profit will be more than the fees + trades
                if bidRoute_result  >  1  :
                    print ('BidRoute result' + str(bidRoute_result))
                    self.place_the_order_of_the_bidRoute(pairs ,askRates,bidRates,askAmounts , bidAmounts )
                    


                        
        except Exception as e : 
            print(e)
            time.sleep(5)
            pass
 
    def place_the_order_of_the_bidRoute(self , pairs ,askRates,bidRates , askAmounts , bidAmounts ):
        max_Amount_1  =   ( self.engine.balance[pairs[0].split('-')[1]] / askRates[0] )  / askRates[1]
        if max_Amount_1 >askAmounts[0] / askRates[1] : 
            max_Amount_1 =  askAmounts[0] / askRates[1]
            
        max_Amount_2  =askAmounts[1]
        max_Amount_3  = bidAmounts[2]
                        
        minimum_Amount = min( max_Amount_1 , max_Amount_2  , max_Amount_3 )

        maxAmounts =  [0, 0  ,0 ]

        maxAmounts[0] =   minimum_Amount*0.99  * askRates[1]  
        maxAmounts[1] = minimum_Amount*0.99  * (1 - self.engine.feeRatio)    
        maxAmounts[2] =  minimum_Amount*0.99  * (1 - self.engine.feeRatio)  * (1 - self.engine.feeRatio) 
                        
        final_result =  (maxAmounts[2] * bidRates[2]*0.99)  * (1 - self.engine.feeRatio)  * (1 - self.engine.feeRatio)
        profit = final_result -( maxAmounts[0]*0.99  * askRates[0])
        minimum_Amount = (minimum_Amount*0.99 * askRates[1]) * askRates[0]
                       
        if minimum_Amount >  22 and profit > 0.1 and self.should_I_do_trade == True:
            print('Profit:' + str(profit))
            print(pairs)
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
            t1 = threading.Thread(target = self.place_order, args = [orderInfo_1[0]  ])
            t2 = threading.Thread(target = self.place_order, args = [orderInfo_2[0] , 0.001 ])
            t3 = threading.Thread(target = self.place_order, args = [orderInfo_3[0] , 0.002])

                                
 
            t1.start()
            t2.start()
            t3.start()
            t1.join()
            t2.join()
            t3.join()
            time.sleep(10000)
                                
            while self.check_openOrder():
                try:
                    print('There are still open orders..Process can not continue..')
                    time.sleep(1)
                except: pass 

        if minimum_Amount >  22 and profit > 0  and 1 >2: 
            print(pairs)
            net_pecentage_profit =  (profit  / minimum_Amount) * 100
            new_arbi_opp = Arbitrage_opportunity(  pairs[0]
                                                  ,pairs[1]
                                                  ,pairs[2]
                                                  ,0
                                                  ,"{:.2f}".format(net_pecentage_profit) + '%' 
                                                  ,  profit
                                                  ,minimum_Amount
                                                  ,'BidRoute'
                                                  ,1
                                                  ,'Blocked'
                                                  , self.round_number
                                                  , self.session
                                                  )
            self.dataframe_object_opportunities.parse_data_to_dataframe(new_arbi_opp,'fullfilled_triangular_arbitrage.csv')
                                
    def get_data_from_the_whole_orderbook(self):
        while True:
            try:
                for pairs in self.all_combinations:                
                    try:             
                        bidRates =  [
                                     self.initial_df_with_all_tickers.at[pairs[0] , 'BidRate'],
                                     self.initial_df_with_all_tickers.at[pairs[1] , 'BidRate'],
                                     self.initial_df_with_all_tickers.at[pairs[2] , 'BidRate']
                                     ]
                        bidAmounts  = [
                            self.initial_df_with_all_tickers.at[pairs[0] , 'BidAmount'],
                            self.initial_df_with_all_tickers.at[pairs[1] , 'BidAmount'],
                            self.initial_df_with_all_tickers.at[pairs[2] , 'BidAmount']
                            ] 

                        askRates  =  [
                            self.initial_df_with_all_tickers.at[pairs[0] , 'AskRate'],
                            self.initial_df_with_all_tickers.at[pairs[1] , 'AskRate'],
                            self.initial_df_with_all_tickers.at[pairs[2] , 'AskRate']]  
                        askAmounts =  [
                            self.initial_df_with_all_tickers.at[pairs[0] , 'AskAmount'],
                            self.initial_df_with_all_tickers.at[pairs[1] , 'AskAmount'],
                            self.initial_df_with_all_tickers.at[pairs[2] , 'AskAmount']]
                    except: 
                        pass  
                        continue
                    
                    
                    bidRates = list(map(float, bidRates     ))
                    askRates =list(map(float, askRates      ))
                    askAmounts = list(map(float ,askAmounts ))
                    bidAmounts = list(map(float , bidAmounts))

                    if len(askRates)<3 or len(bidRates) < 3:
                       continue
                    if 0.0 in askRates or 0.0 in bidRates: 
                        continue
                    if 0.0 in askAmounts or 0.0 in bidAmounts: 
                        continue
                    
                  # Ready to check for the arbitrage

                   # if the askRoute_result is greater than 1  there is a chance to exist Arbitrage.. 
                    bidRoute_result = (1 / askRates [0]) / askRates[1]  * bidRates[2]
                    askRoute_result =  (1 * bidRates[0])  / askRates[2] * bidRates[1]       

                  # Here We aee starting to execute the arbitrage
                  #1st Step check if the profit will be more than the fees + trades
                    if bidRoute_result  >  1  :
                        self.parse_to_dataframe_bidRoute(pairs ,askRates,bidRates,askAmounts , bidAmounts )
                    
                    if askRoute_result  >  1  :
                        self.parse_to_dataframe_askRoute(pairs ,askRates,bidRates,askAmounts , bidAmounts )
                        
                    


                self.round_number =self.round_number + 1         
            except Exception as e : 
               print(e)
               time.sleep(5)
               pass
  
    def parse_to_dataframe_bidRoute(self , pairs ,  askRates,bidRates,askAmounts, bidAmounts):
                        
        max_Amount_1  =     askAmounts[0] / askRates[1]
        max_Amount_2  =askAmounts[1]
        max_Amount_3  = bidAmounts[2]
 
        final_max_Amount = min( max_Amount_1 , max_Amount_2  , max_Amount_3 )
                        

        maxAmounts =  [0, 0  ,0 ]
        maxAmounts[0] =   final_max_Amount * askRates[1] *0.99   
        maxAmounts[1] = final_max_Amount  * (1 - self.engine.feeRatio)  *0.99   
        maxAmounts[2] =  final_max_Amount  * (1 - self.engine.feeRatio)  * (1 - self.engine.feeRatio)*0.99 

        starting_Amount =  maxAmounts[0]*askRates[0]*0.99  
        
                        
        final_result =  (maxAmounts[2] * bidRates[2]*0.99)  * (1 - self.engine.feeRatio)   
        profit = final_result - starting_Amount
        percentage_profit =  ( profit  /  starting_Amount) *100
        
        if  profit > 0  :
            percentage_profit = "{:.3f}".format(percentage_profit)  + '%'
            profit =  "{:.3f}".format(profit) 
            starting_Amount =  "{:.3f}".format(starting_Amount)  + ' ' + pairs[0].split('-')[1]
            
            print(pairs)
            print('BidRoute Percentage Profit: '+  percentage_profit )
            print('BidRoute Profit:'+   profit  )
            print ('Max Amount:'+  starting_Amount  )
            new_arbi_opp = Arbitrage_opportunity(  
                                                   pairs[0]
                                                 , pairs[1]
                                                 , pairs[2]
                                                 , percentage_profit
                                                 , profit
                                                 , starting_Amount
                                                 , pairs[0].split('-')[1]
                                                 ,'BidRoute'
                                                 , self.round_number
                                                 , self.session
                                                 )
            self.dataframe_object_opportunities.parse_data_to_dataframe(new_arbi_opp,'triangular_arbitrage_data.csv')
            
    def parse_to_dataframe_askRoute(self , pairs ,askRates, bidRates, askAmounts , bidAmounts): 
                        
        max_Amount_1  =     bidAmounts[0] / bidRates[1]
        max_Amount_2  = askAmounts[2]
        max_Amount_3  = bidAmounts[1]
 
        final_max_Amount = min( max_Amount_1 , max_Amount_2  , max_Amount_3 )
                        

        maxAmounts =  [0, 0  ,0 ]
        maxAmounts[0] =   final_max_Amount * bidRates[1] *0.99   
        maxAmounts[1] = final_max_Amount  * (1 - self.engine.feeRatio)  *0.99   
        maxAmounts[2] =  final_max_Amount  * (1 - self.engine.feeRatio)  * (1 - self.engine.feeRatio)*0.99 

        starting_Amount =  maxAmounts[0]*0.99  
        
                        
        final_result =  (maxAmounts[2] * bidRates[1]*0.99)  * (1 - self.engine.feeRatio)   
        profit = final_result - starting_Amount
        percentage_profit =  ( profit  /  starting_Amount) *100
        
        if  profit > 0  :
            percentage_profit = "{:.3f}".format(percentage_profit)  + '%'
            profit =  "{:.3f}".format(profit) 
            starting_Amount =  "{:.3f}".format(starting_Amount)  + ' ' + pairs[0].split('-')[1]
            
            print(pairs)
            print('AskRoute Percentage Profit: '+  percentage_profit )
            print('AskRoute Profit:'+   profit  )
            print ('Max Amount:'+  starting_Amount  )
            new_arbi_opp = Arbitrage_opportunity(  
                                                   pairs[0]
                                                 , pairs[1]
                                                 , pairs[2]
                                                 , percentage_profit
                                                 , profit
                                                 , starting_Amount
                                                 , pairs[0].split('-')[1]
                                                 ,'AskRoute'
                                                 , self.round_number
                                                 , self.session
                                                 )
            self.dataframe_object_opportunities.parse_data_to_dataframe(new_arbi_opp,'triangular_arbitrage_data.csv')
        
    
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

 
    
     #This is the function which is responsible to send the requests and it returns us the response from the API
    
    def send_request(self, rs):
        responses = grequests.map( rs )
        for res in responses:
            if res.status_code == 409 :
                print('Skata')
                return False
            if not res:
                print (responses)
                raise Exception
        return responses
 