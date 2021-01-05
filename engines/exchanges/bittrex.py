'''
    All trades have a 0.25% commission. -> real case it is 0.250626606% so use 0.26% for calculation instead

'''

from mod_imports import *
from datetime import datetime
import urllib.parse



class ExchangeEngine(ExchangeEngineBase):
    def __init__(self):
        self.API_URL = 'https://api.bittrex.com/'
        self.apiVersion = 'v3'
        self.sleepTime = 5
        self.feeRatio = 0.0026
        self.sync = True
                  
    def _send_request(self, command, httpMethod, params={}, hook=None):          
        command = '{0}/{1}'.format(self.apiVersion, command)
        command = command.replace('v3/markets/USD-USDT/ticker' ,'v3/markets/USDT-USD/ticker')
        
        url = self.API_URL + command
          
        if httpMethod == "GET":
            R = grequests.get
        elif httpMethod == "POST":
            R = grequests.post       
        
        headers = {}

        api_key =   '89b69e40a3464285b8905335c5c36b2d'
    #    api_key =   self.key['public']  
    
       # secret = self.key['private']
        secret =  'b7952007d413464998d6ab31e39a5243'
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
            args = {'data': content, 'headers': headers}
                

        
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
        return self._send_request('balances', 'GET', {}, [self.hook_getBalance(tickers=tickers)])
    
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
         return self._send_request('markets/'+ticker+'-USDT/ticker', 'GET', {}, [self.hook_lastPrice(ticker=ticker)])

    def get_all_tickers_of_bittrex(self):
        return self._send_request('markets/tickers', 'GET', {}  )
    
    def get_all_markets_of_bittrex(self):
        return self._send_request('markets', 'GET', {})

    def hook_lastPrice(self, *factory_args, **factory_kwargs):
        def res_hook(r, *r_args, **r_kwargs):
            json = r.json()
            r.parsed = {}
            r.parsed[factory_kwargs['ticker']] = json['lastTradeRate']
                                  
        return res_hook    

    '''
        return in r.parsed
        {
            'bid': {
                'price': 0.02202,
                'amount': 1103.5148
            },
            'ask': {
                'price': 0.02400,
                'amount': 103.2
            },           
        }
    '''       
    def get_ticker_orderBook_innermost(self, ticker):
        return self._send_request('markets/'+ticker+'/orderbook?depth='+str(25), 'GET', {}, self.hook_orderBook)
                                   
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
        
    '''
        return in r.parsed
        [
            {
                'orderId': 1242424
            }
        ]
    '''           
    def get_open_order(self):
        return self._send_request('market/getopenorders', 'GET', {}, self.hook_openOrder)
    
    def hook_openOrder(self, r, *r_args, **r_kwargs):
        json = r.json()
        r.parsed = []
        for order in json['result']:
            r.parsed.append({'orderId': str(order['OrderUuid']), 'created': order['Opened']})


        
    '''
        ticker: 'ETH-ETC'
        action: 'bid' or 'ask'
        amount: 700
        price: 0.2
    '''
    def place_order(self, ticker, action, amount, price):
        action = 'buy' if action == 'bid' else 'sell'
        if action == 'buy':
            payload = {
                 'marketSymbol':ticker
                ,'direction': 'BUY'
                ,'type':'LIMIT'
                ,'quantity':amount
                ,'limit': price
                ,'timeInForce': 'FILL_OR_KILL'
            }
            cmd =  'orders'
        else:
            payload = {
                 'marketSymbol':ticker
                ,'direction': 'SELL'
                ,'type':'LIMIT'
                ,'quantity':amount
                ,'limit': price
                ,'timeInForce': 'FILL_OR_KILL'
            }
            cmd = 'orders'
        return self._send_request(cmd, 'POST',payload)    
    
    def cancel_order(self, orderID):
        return self._send_request('market/cancel?uuid={0}'.format(orderID), 'GET')
    
 