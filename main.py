import argparse
import json
from engines.triangular_arbitrage import CryptoEngineTriArbitrage
from signalr_aio import Connection # https://github.com/slazarov/python-signalr-client
from base64 import b64decode
from zlib import decompress, MAX_WBITS
import hashlib
import hmac
import json
import asyncio
import time
import uuid



'''
Over here you define from the arbitrage_config which market has to chose the program and what pairs 
to choose in order to fullfill arbitrage.
'''

#Some important configurations.. 
configFile = 'arbitrage_config.json'

f = open(configFile)    
config = json.load(f)
f.close()
isMockMode = True  
engine = CryptoEngineTriArbitrage(config['triangular'], isMockMode)

#The program starts to run officially from this line


'''  Here I am setting up the Websocket and the program is ready to run .. ''' 

URL = 'https://socket-v3.bittrex.com/signalr'
API_KEY = '5f05fce4803a4d8cbc4707fc30310fc3'
API_SECRET = 'ae149cf3144c45c891e1cc7092c5d331'

HUB = None
LOCK = asyncio.Lock()
INVOCATION_EVENT = None
INVOCATION_RESPONSE = None

async def main():
  await connect()
  if(API_SECRET != ''):
    await authenticate()
  else:
    print('Authentication skipped because API key was not provided')
  await subscribe()
  forever = asyncio.Event()
  await forever.wait()

async def connect():
  global HUB
  connection = Connection(URL)
  HUB = connection.register_hub('c3')
  connection.received += on_message
  connection.error += on_error
  connection.start()
  print('Connected')
 
async def authenticate():
  timestamp = str(int(time.time()) * 1000)
  random_content = str(uuid.uuid4())
  content = timestamp + random_content
  signed_content = hmac.new(API_SECRET.encode(), content.encode(), hashlib.sha512).hexdigest()

  response = await invoke('Authenticate',
    API_KEY,
    timestamp,
    random_content,
    signed_content)

  if response['Success']:
    print('Authenticated')
    HUB.client.on('authenticationExpiring', on_auth_expiring)
  else:
    print('Authentication failed: ' + response['ErrorCode'])

async def subscribe():
  HUB.client.on('heartbeat', on_heartbeat)
  HUB.client.on('tickers', on_tickers)
  channels = [
    'heartbeat',
    'tickers'
  ]
  
  response = await invoke('Subscribe', channels)
  for i in range(len(channels)):
    if response[i]['Success']:
      print('Subscription to "' + channels[i] + '" successful')
    else:
      print('Subscription to "' + channels[i] + '" failed: ' + response[i]['ErrorCode'])
  
async def invoke(method, *args):
  async with LOCK:
    global INVOCATION_EVENT
    INVOCATION_EVENT = asyncio.Event()
    HUB.server.invoke(method, *args)
    await INVOCATION_EVENT.wait()
    return INVOCATION_RESPONSE

async def on_message(**msg):
  global INVOCATION_RESPONSE
  if 'R' in msg:
    INVOCATION_RESPONSE = msg['R']
    INVOCATION_EVENT.set()

async def on_error(msg):
  print(msg)

async def on_heartbeat(msg):
  print('\u2661')

async def on_auth_expiring(msg):
  print('Authentication expiring...')
  asyncio.create_task(authenticate())

async def on_trade(msg):
  await print_message('Trade', msg)

async def on_tickers( msg):
    await print_message('tickers', msg)

async def print_message(title, msg):
        decoded_msg = await process_message(msg[0])
            
        if title == 'tickers' : 
            for item in decoded_msg['deltas'] : 
                for item_two in engine.initial_json: 
                    if item['symbol'] == item_two['symbol'] : 
                         item_two['lastTradeRate'] =item['lastTradeRate']  
                         item_two['bidRate']  =  item['bidRate']
                         item_two['askRate'] =  item['askRate']
            engine.place_orders_to_arbitrages()
                         
        else:
            print(title + ': ' + json.dumps(decoded_msg, indent = 2))
                    
async def process_message(message):
  try:
    decompressed_msg = decompress(b64decode(message, validate=True), -MAX_WBITS)
  except SyntaxError:
    decompressed_msg = decompress(b64decode(message, validate=True))
  return json.loads(decompressed_msg.decode()) 

if __name__ == "__main__":
  asyncio.run(main())

 


 




