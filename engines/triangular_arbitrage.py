import time
from time import strftime
import grequests
import os 
import sys
from engines.exchanges.loader import EngineLoader
import json

class CryptoEngineTriArbitrage(object):
    def __init__(self, exchange, mock=False):
        self.exchange = exchange
        self.mock = mock
        self.minProfitUSDT = 0.00013
        self.hasOpenOrder = True # always assume there are open orders first
        self.openOrderCheckCount = 0
      
        self.engine = EngineLoader.getEngine(self.exchange['exchange'], self.exchange['keyFile'])

    def start_engine(self):
        print (strftime('%Y%m%d%H%M%S') + ' starting Triangular Arbitrage Engine...')
        while True:
            try:
                if not self.mock and self.hasOpenOrder:
                    self.check_openOrder()
                elif self.check_balance():           
                    bookStatus = self.check_orderBook()
                    if bookStatus['status']:
                        self.place_order(bookStatus['orderInfo'])
            except Exception as e :
               print (e)
            time.sleep(1)
    
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
   
    def check_balance(self):
        rs = [self.engine.get_balance([
            self.exchange['tickerA'],
            self.exchange['tickerB'],
            self.exchange['tickerC']
            ])]

        responses = self.send_request(rs)
 
        self.engine.balance = responses[0].parsed

        ''' Not needed? '''
        # if not self.mock:
        #     for res in responses:
        #         for ticker in res.parsed:
        #             if res.parsed[ticker] < 0.05:
        #                 print ticker, res.parsed[ticker], '- Not Enough'
        #                 return False
        return True
    
    def check_the_whole_order_book(self):
        all_combinations = [
            ['ETH-BTC' , 'LTC-ETH', 'LTC-BTC'],
            ['ETH-BTC' , 'DOT-ETH', 'DOT-BTC'],
            ['ETH-BTC' , 'ATOM-ETH', 'ATOM-BTC'],
            ['ETH-BTC' , 'AAVE-ETH', 'AAVE-BTC'],
            ['ETH-BTC' , 'BCH-ETH', 'BCH-BTC'],
            ['ETH-BTC' , 'DOGE-ETH', 'DOGE-BTC'],
            ['ETH-BTC' , 'DASH-ETH', 'DASH-BTC'],
            ['ETH-BTC' , 'XLM-ETH', 'XLM-BTC'],
            ['ETH-BTC' , 'XMR-ETH', 'XMR-BTC'],
           
            ['ETH-USD' , 'LTC-ETH', 'LTC-USD'], 
            
            ['USDT-EUR', 'DOT-USDT', 'DOT-EUR'],
            
            ['BTC-USDT', 'DOT-BTC', 'DOT-USDT'],
            ['BTC-USDT', 'ALGO-BTC', 'ALGO-USDT'],
            ['BTC-USDT', 'LUNA-BTC', 'LUNA-USDT'],
            ['BTC-USDT', 'XMR-BTC', 'XMR-USDT'],
            ['BTC-USDT', 'LTC-BTC', 'LTC-USDT'],
            ['BTC-USDT', 'XLM-BTC', 'XLM-USDT'],
            
            ]
         
        while True:
            rs  = self.engine.get_all_tickers_of_bittrex()
            response = self.send_request([rs])
            json = response[0].json()
        
            for pairs in all_combinations:
                lastPrices = []
                bidRates = []
                askRates =  []
                
                tickerA = pairs[0].replace('-', ' ').split()[1] + '-USDT'
                tickerB = pairs[1].replace('-', ' ').split()[1] + '-USDT'
                tickerC = pairs[2].replace('-', ' ').split()[0] + '-USDT'
                
                tickers = [tickerA , tickerB , tickerC ]
                
                for ticker in tickers:
                    for value in json: 
                        if ticker == value['symbol']: 
                            lastPrices.append(value['lastTradeRate'])              

                    
                
                
                for pair in pairs:
                    for value in json:
                        if pair ==  value['symbol'] :
                            bidRates.append(value['bidRate'])
                            askRates.append(value['askRate']) 
                
           
                lastPrices =  list(map(float, lastPrices))
                bidRates = list(map(float, bidRates))
                askRates =list(map(float, askRates))
           
                
                askRoute_result = (1 *  bidRates[0]) / askRates[2] *   bidRates[1] 
                bidRoute_result = (1 /  askRates[0]) / askRates[1] *   bidRates[2]
 
                if askRoute_result > 1 :
                    
                    percentage_profit =( (askRoute_result - 1 ) / 1 ) * 100
                    print(pairs)
                    print('Percentage Profit:'+ str(percentage_profit) + '%')
                    
                     
                    
                if bidRoute_result > 1 :
                    percentage_profit =( (bidRoute_result - 1 ) / 1 ) * 100
                    print(pairs)
                    print('Percentage Profit:'+ str(percentage_profit) + '%')
                    
                         
                        
                
            time.sleep(2)
        



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
        
        # if self.mock:
          #  print(self.exchange['tickerPairA']  + '-' + self.exchange['tickerPairB'] + '-'  + self.exchange['tickerPairC'])
            #print ('{0} - {1}; {2} - {3}; {4} - {5}'.format(
            #    self.exchange['tickerPairA'],
            #    responses[0].parsed,
            #    self.exchange['tickerPairB'],
            #    responses[1].parsed,
            #    self.exchange['tickerPairC'],
            #    responses[2].parsed
            #    ))
        
        # bid route BTC->ETH->LTC->BTC
        bidRoute_result = (1 / responses[0].parsed['ask']['price']) / responses[1].parsed['ask']['price'] * responses[2].parsed['bid']['price']  
        if bidRoute_result > 1:
            print('Bidroute :'+ str(bidRoute_result) )
            percentage_profit =( (bidRoute_result - 1 ) / 1 ) * 100
            print('Percentage Profit:' + str(percentage_profit))
                    
        # ask route ETH->BTC->LTC->ETH
        askRoute_result = (1 * responses[0].parsed['bid']['price']) / responses[2].parsed['ask']['price']   * responses[1].parsed['bid']['price']
        if askRoute_result > 1 :
            print('Askroute :'+ str(askRoute_result) )
            percentage_profit =( (askRoute_result - 1 ) / 1 ) * 100
            print('Percentage Profit:' + str(percentage_profit))


        
        # Max amount for bid route & ask routes can be different and so less profit
        if bidRoute_result > 1 or \
        (bidRoute_result > 1 and askRoute_result > 1 and (bidRoute_result - 1) * lastPrices[0] > (askRoute_result - 1) * lastPrices[1]):
            status = 1 # bid route
        elif askRoute_result > 1:
            status = 2 # ask route
        else:
            status = 0 # do nothing
 
        # print('Bidroute :'+ str(bidRoute_result) )
        # print('Askroute :'+ str(askRoute_result) )
        #if status   == 0:
        if status   >0  :
    
            maxAmounts = self.getMaxAmount(lastPrices, responses, status)
            fee = 0
            for index, amount in enumerate(maxAmounts):
                fee += amount * float(lastPrices[index])
            fee *= self.engine.feeRatio
            
            bidRoute_profit = (bidRoute_result - 1) * float(lastPrices[0]) * maxAmounts[0]
            askRoute_profit = (askRoute_result - 1) * float(lastPrices[1]) * maxAmounts[1]
            print ('bidRoute_profit - {0} askRoute_profit - {1} fee - {2}'.format( bidRoute_profit, askRoute_profit, fee))
            print('Profit-'+ str( bidRoute_profit - fee ))
            print('Profit-'+ str( askRoute_profit - fee ))
            if status == 1 and bidRoute_profit - fee > self.minProfitUSDT:
                orderInfo = [
                    {
                        "tickerPair": self.exchange['tickerPairA'],
                        "action": "bid",
                        "price": responses[0].parsed['ask']['price'],
                        "amount":  maxAmounts[1]   
                    },
                    {
                        "tickerPair": self.exchange['tickerPairB'],
                        "action": "bid",
                        "price": responses[1].parsed['ask']['price'],
                        "amount": maxAmounts[2]   
                    },
                    {
                        "tickerPair": self.exchange['tickerPairC'],
                        "action": "ask",
                        "price": responses[2].parsed['bid']['price'],
                        "amount": maxAmounts[2]  
                    }                                        
                ]
                return {'status': 1, "orderInfo": orderInfo}
            elif status == 2 and askRoute_profit - fee > self.minProfitUSDT:
                print (strftime('%Y%m%d%H%M%S') + ' Ask Route: Result - {0} Profit - {1} Fee - {2}'.format(askRoute_result, askRoute_profit, fee))
                orderInfo = [
                    {
                        "tickerPair": self.exchange['tickerPairA'],
                        "action": "ask",
                        "price": responses[0].parsed['bid']['price'],
                        "amount": maxAmounts[1]  
                    },
                    {
                        "tickerPair": self.exchange['tickerPairB'],
                        "action": "ask",
                        "price": responses[1].parsed['bid']['price'],
                        "amount": maxAmounts[2]   
                    },
                    {
                        "tickerPair": self.exchange['tickerPairC'],
                        "action": "bid",
                        "price": responses[2].parsed['ask']['price'],
                        "amount":maxAmounts[2]   
                    }                                        
                ]               
                return {'status': 2, 'orderInfo': orderInfo}
        return {'status': 0}
    # Using USDT may not be accurate
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
            #print ('{0} orderBookAmount - {1} ownAmount - {2}'.format(
            #     self.exchange[tickerIndex], 
            #     orderBookRes[index].parsed[bid_ask]['amount'], 
            #     self.engine.balance[self.exchange[tickerIndex]]
            # ))
            USDT = maxBalance * float(lastPrices[index]) * (1 - self.engine.feeRatio)
            if not maxUSDT or USDT < maxUSDT: 
                maxUSDT = USDT       

        maxAmounts = []
        for index, tickerIndex in enumerate(['tickerA', 'tickerB', 'tickerC']):
            # May need to handle scientific notation
            maxAmounts.append(maxUSDT / float(lastPrices[index]))

        return maxAmounts

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
        time.sleep(360)
        self.hasOpenOrder = True
        self.openOrderCheckCount = 0

    def send_request(self, rs):
        responses = grequests.map( rs )
        for res in responses:
            if not res:
                print (responses)
                raise Exception
        return responses

    def run(self):
        
     # self.check_the_whole_order_book()
      self.start_engine()
 