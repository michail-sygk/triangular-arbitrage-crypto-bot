from mod_imports import *
from datetime import datetime
import urllib.parse

 

class ExchangeEngine(ExchangeEngineBase):
    def __init__(self):
        self.API_URL = 'https://api.bittrex.com/'
        self.apiVersion = 'v3'
        self.sleepTime = 2
        self.feeRatio = 0.0020 #Trades of Bittrex have 0.0035 % of fees
        self.sync = True
       
    def _create_request(self, command, httpMethod, params={}, hook=None):          
        command = '{0}/{1}'.format(self.apiVersion, command)
        command = command.replace('EUR-USDT', 'USDT-EUR')
        command = command.replace('USD-USDT', 'USDT-USD')
        url = self.API_URL + command
            
        if httpMethod == "GET":
            R = grequests.get
        elif httpMethod == "POST":
            R = grequests.post       
        
        headers = {}

        api_key =   '5f05fce4803a4d8cbc4707fc30310fc3'
        #    api_key =   self.key['public']  
    
        # secret = self.key['private']
        secret =  'ae149cf3144c45c891e1cc7092c5d331'
        secret = bytes(secret.encode("utf-8"))
    
        timestamp = format(int(time.time() * 1000))
        query = url
       
        if len(params) ==0:
            contentHash = hashlib.sha512("".encode()).hexdigest()
        else:
            content = json.dumps(params)
            contentHash = hashlib.sha512(content.encode()).hexdigest()

        presign =  timestamp  + url + httpMethod + contentHash 
        signature = hmac.new(secret, presign.encode(), hashlib.sha512).hexdigest()
        
        
        #Bittrex demand these kind of headers in order to make a proper request/post call
        headers = {
             'Api-Key' : api_key 
            ,'Api-Timestamp':timestamp
            ,'Api-Content-Hash': contentHash
            ,'Api-Signature' :signature
            ,'Content-Type': 'application/json'

         
        }    
        
        if len(params )  == 0:  
            args = {'data': params, 'headers': headers}
        else:
            args = {'json': params, 'headers': headers}
                

        
        if hook:
            args['hooks'] = dict(response=hook)
            
        req = R(url, **args)
        
        if self.sync:
            return req
        else:
            response = grequests.map(req)[0].json()
            
            if 'error' in response:
                print (response)
            return response
  
    def get_balance(self, tickers=[]):
        return self._create_request('balances', 'GET', {}, [self.hook_getBalance(tickers=tickers)])
    
    def hook_getBalance(self, *factory_args, **factory_kwargs):
        def res_hook(r, *r_args, **r_kwargs):
            def filter_currencySymbols(row):
                if row['currencySymbol'] in  factory_kwargs['tickers'] :
                    return True
                return False
            
            json = r.json()
            r.parsed = {}

            if factory_kwargs['tickers']:
                new_json = filter(filter_currencySymbols, json)
                        
            for ticker in new_json:
                r.parsed[ticker['currencySymbol'].upper()] = float(ticker['available'])
             
        return res_hook    
      
    def get_ticker_lastPrice(self, ticker):
         return self._create_request('markets/'+ticker+'-USDT/ticker', 'GET', {}, [self.hook_lastPrice(ticker=ticker)])

    def get_all_tickers_of_bittrex(self):
        return self._create_request('markets/tickers', 'GET', {}  )
    
    def get_all_markets_of_bittrex(self):
        return self._create_request('markets', 'GET', {})

    def hook_lastPrice(self, *factory_args, **factory_kwargs):
        def res_hook(r, *r_args, **r_kwargs):
            json = r.json()
            r.parsed = {}
            r.parsed[factory_kwargs['ticker']] = json['lastTradeRate']
                                  
        return res_hook    
    
    def get_ticker_orderBook_innermost(self, ticker):
        return self._create_request('markets/'+ticker+'/orderbook?depth='+str(1), 'GET', {}, self.hook_orderBook)
                                   
    def hook_orderBook(self, r, *r_args, **r_kwargs):
        json = r.json()
        #print json
        r.parsed = {
                    'bid':  {
                             'price': float(json['bid'][0]['rate']),
                             'amount': float(json['bid'][0]['quantity'])
                            },
                    'ask':  {
                             'price': float(json['ask'][0]['rate']),
                             'amount': float(json['ask'][0]['quantity'])
                            }
                    }    
        
    def get_open_order(self):
        return self._create_request('orders/open', 'GET', {}, self.hook_openOrder)
    
    def hook_openOrder(self, r, *r_args, **r_kwargs):                                                                                                                           
        json = r.json()
        r.parsed = []
        for order in json:
            r.parsed.append({'orderId': str(order['id']), 'created': order['createdAt']})
 
    def place_order(self, ticker, action, amount, price):
        action = 'buy' if action == 'bid' else 'sell'
        if action == 'buy':
            payload = {
                 'marketSymbol':ticker
                ,'direction': 'BUY'
                ,'type':'LIMIT'
                ,'quantity': amount
                ,'limit': price
                ,'timeInForce': 'GOOD_TIL_CANCELLED'
            }
            cmd =  'orders'
        else:
            payload = {
                 'marketSymbol':ticker
                ,'direction': 'SELL'
                ,'type':'LIMIT'
                ,'quantity':amount
                ,'limit': price
                ,'timeInForce': 'GOOD_TIL_CANCELLED'
            }
            cmd = 'orders'
        return self._create_request(cmd, 'POST',payload)    
    
    def cancel_order(self, orderID):
        return self._create_request('market/cancel?uuid={0}'.format(orderID), 'GET')
    
 