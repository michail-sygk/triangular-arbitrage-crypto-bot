#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Last tested 2020/09/24 on Python 3.8.5
#
# Note: This file is intended solely for testing purposes and may only be used 
#   as an example to debug and compare with your code. The 3rd party libraries 
#   used in this example may not be suitable for your production use cases.
#   You should always independently verify the security and suitability of any 
#   3rd party library used in your code.

from signalr_aio import Connection # https://github.com/slazarov/python-signalr-client
from base64 import b64decode
from zlib import decompress, MAX_WBITS
import hashlib
import hmac
import json
import asyncio
import time
import uuid

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
  HUB.client.on('orderBook', on_Orderbook)
  
  
  channels = [
    'heartbeat',
       'orderbook_ETH-USDT_1',
      'orderbook_ADA-ETH_1',
      'orderbook_ADA-USDT_1',
      'orderbook_ATOM-ETH_1',
      'orderbook_ATOM-USDT_1',
      'orderbook_BAL-ETH_1',
      'orderbook_BAL-USDT_1',
      'orderbook_BAND-ETH_1',
      'orderbook_BAND-USDT_1',
      'orderbook_BAT-ETH_1',
      'orderbook_BAT-USDT_1',
      'orderbook_BCH-ETH_1',
      'orderbook_BCH-USDT_1',
      'orderbook_BSV-ETH_1',
      'orderbook_BSV-USDT_1',
      'orderbook_BTC-USDT_1',
      'orderbook_ETH-BTC_1',
      'orderbook_CELO-ETH_1',
      'orderbook_CELO-USDT_1',
      'orderbook_COMP-ETH_1',
      'orderbook_COMP-USDT_1',
      'orderbook_CRO-ETH_1',
      'orderbook_CRO-USDT_1',
      'orderbook_DAI-ETH_1',
      'orderbook_DAI-USDT_1',
      'orderbook_DGB-ETH_1',
      'orderbook_DGB-USDT_1',
      'orderbook_DOGE-ETH_1',
      'orderbook_DOGE-USDT_1',
      'orderbook_DOT-ETH_1',
      'orderbook_DOT-USDT_1',
      'orderbook_ENJ-ETH_1',
      'orderbook_ENJ-USDT_1',
      'orderbook_EOS-ETH_1',
      'orderbook_EOS-USDT_1',
      'orderbook_ETC-ETH_1',
      'orderbook_ETC-USDT_1',
      'orderbook_FIL-ETH_1',
      'orderbook_FIL-USDT_1',
      'orderbook_GRT-ETH_1',
      'orderbook_GRT-USDT_1',
      'orderbook_HBAR-ETH_1',
      'orderbook_HBAR-USDT_1',
      'orderbook_HNS-ETH_1',
      'orderbook_HNS-USDT_1',
      'orderbook_KNC-ETH_1',
      'orderbook_KNC-USDT_1',
      'orderbook_KSM-ETH_1',
      'orderbook_KSM-USDT_1',
      'orderbook_LINK-ETH_1',
      'orderbook_LINK-USDT_1',
      'orderbook_LTC-ETH_1',
      'orderbook_LTC-USDT_1',
      'orderbook_MKR-ETH_1',
      'orderbook_MKR-USDT_1',
      'orderbook_NEO-ETH_1',
      'orderbook_NEO-USDT_1',
      'orderbook_NMR-ETH_1',
      'orderbook_NMR-USDT_1',
      'orderbook_NPXS-ETH_1',
      'orderbook_NPXS-USDT_1',
      'orderbook_OMG-ETH_1',
      'orderbook_OMG-USDT_1',
      'orderbook_REN-ETH_1',
      'orderbook_REN-USDT_1',
      'orderbook_RENBTC-ETH_1',
      'orderbook_RENBTC-USDT_1',
      'orderbook_SC-ETH_1',
      'orderbook_SC-USDT_1',
      'orderbook_SOLVE-ETH_1',
      'orderbook_SOLVE-USDT_1',
      'orderbook_TRAC-ETH_1',
      'orderbook_TRAC-USDT_1',
      'orderbook_TRX-ETH_1',
      'orderbook_TRX-USDT_1',
      'orderbook_TUSD-ETH_1',
      'orderbook_TUSD-USDT_1',
      'orderbook_UMA-ETH_1',
      'orderbook_UMA-USDT_1',
      'orderbook_UNI-ETH_1',
      'orderbook_UNI-USDT_1',
      'orderbook_USDC-ETH_1',
      'orderbook_USDC-USDT_1',
      'orderbook_VDX-ETH_1',
      'orderbook_VDX-USDT_1',
      'orderbook_WAXP-ETH_1',
      'orderbook_WAXP-USDT_1',
      'orderbook_WBTC-ETH_1',
      'orderbook_WBTC-USDT_1',
      'orderbook_XLM-ETH_1',
      'orderbook_XLM-USDT_1',
      'orderbook_XMR-ETH_1',
      'orderbook_XMR-USDT_1',
      'orderbook_XRP-ETH_1',
      'orderbook_XRP-USDT_1',
      'orderbook_XTZ-ETH_1',
      'orderbook_XTZ-USDT_1',
      'orderbook_YFL-ETH_1',
      'orderbook_YFL-USDT_1',
      'orderbook_ZEC-ETH_1',
      'orderbook_ZEC-USDT_1',
      'orderbook_ZRX-ETH_1',
      'orderbook_ZRX-USDT_1',
      'orderbook_ADA-BTC_1',
      'orderbook_AKN-BTC_1',
      'orderbook_AKN-USDT_1',
      'orderbook_ALGO-BTC_1',
      'orderbook_ALGO-USDT_1',
      'orderbook_AMZN-BTC_1',
      'orderbook_AMZN-USDT_1',
      'orderbook_APM-BTC_1',
      'orderbook_APM-USDT_1',
      'orderbook_ATOM-BTC_1',
      'orderbook_BABA-BTC_1',
      'orderbook_BABA-USDT_1',
      'orderbook_BAL-BTC_1',
      'orderbook_BAND-BTC_1',
      'orderbook_BAT-BTC_1',
      'orderbook_BBC-BTC_1',
      'orderbook_BBC-USDT_1',
      'orderbook_BCH-BTC_1',
      'orderbook_BILI-BTC_1',
      'orderbook_BILI-USDT_1',
      'orderbook_BNTX-BTC_1',
      'orderbook_BNTX-USDT_1',
      'orderbook_BOA-BTC_1',
      'orderbook_BOA-USDT_1',
      'orderbook_BRZ-BTC_1',
      'orderbook_BRZ-USDT_1',
      'orderbook_BSV-BTC_1',
      'orderbook_BTCV-BTC_1',
      'orderbook_BTCV-USDT_1',
      'orderbook_BTE-BTC_1',
      'orderbook_BTE-USDT_1',
      'orderbook_BTT-BTC_1',
      'orderbook_BTT-USDT_1',
      'orderbook_BWF-BTC_1',
      'orderbook_BWF-USDT_1',
      'orderbook_BYND-BTC_1',
      'orderbook_BYND-USDT_1',
      'orderbook_CAMP-BTC_1',
      'orderbook_CAMP-USDT_1',
      'orderbook_CELO-BTC_1',
      'orderbook_CGT-BTC_1',
      'orderbook_CGT-USDT_1',
      'orderbook_CKB-BTC_1',
      'orderbook_CKB-USDT_1',
      'orderbook_CNS-BTC_1',
      'orderbook_CNS-USDT_1',
      'orderbook_CNTM-BTC_1',
      'orderbook_CNTM-USDT_1',
      'orderbook_COMP-BTC_1',
      'orderbook_CRO-BTC_1',
      'orderbook_CUSD-BTC_1',
      'orderbook_CUSD-USDT_1',
      'orderbook_DAI-BTC_1',
      'orderbook_DCR-BTC_1',
      'orderbook_DCR-USDT_1',
      'orderbook_DEP-BTC_1',
      'orderbook_DEP-USDT_1',
      'orderbook_DFI-BTC_1',
      'orderbook_DFI-USDT_1',
      'orderbook_DGB-BTC_1',
      'orderbook_DNA-BTC_1',
      'orderbook_DNA-USDT_1',
      'orderbook_DOGE-BTC_1',
      'orderbook_DOT-BTC_1',
      'orderbook_ECELL-BTC_1',
      'orderbook_ECELL-USDT_1',
      'orderbook_ECOC-BTC_1',
      'orderbook_ECOC-USDT_1',
      'orderbook_ELA-BTC_1',
      'orderbook_ELA-USDT_1',
      'orderbook_ENJ-BTC_1',
      'orderbook_EOS-BTC_1',
      'orderbook_ETC-BTC_1',
      'orderbook_EXE-BTC_1',
      'orderbook_EXE-USDT_1',
      'orderbook_FB-BTC_1',
      'orderbook_FB-USDT_1',
      'orderbook_FIL-BTC_1',
      'orderbook_FME-BTC_1',
      'orderbook_FME-USDT_1',
      'orderbook_GNC-BTC_1',
      'orderbook_GNC-USDT_1',
      'orderbook_GOOGL-BTC_1',
      'orderbook_GOOGL-USDT_1',
      'orderbook_GRIN-BTC_1',
      'orderbook_GRIN-USDT_1',
      'orderbook_GRT-BTC_1',
      'orderbook_GST-BTC_1',
      'orderbook_GST-USDT_1',
      'orderbook_GXC-BTC_1',
      'orderbook_GXC-USDT_1',
      'orderbook_HBAR-BTC_1',
      'orderbook_HDAO-BTC_1',
      'orderbook_HDAO-USDT_1',
      'orderbook_HIVE-BTC_1',
      'orderbook_HIVE-USDT_1',
      'orderbook_HNS-BTC_1',
      'orderbook_HXRO-BTC_1',
      'orderbook_HXRO-USDT_1',
      'orderbook_INX-BTC_1',
      'orderbook_INX-USDT_1',
      'orderbook_IRIS-BTC_1',
      'orderbook_IRIS-USDT_1',
      'orderbook_KAI-BTC_1',
      'orderbook_KAI-USDT_1',
      'orderbook_KDA-BTC_1',
      'orderbook_KDA-USDT_1',
      'orderbook_KDAG-BTC_1',
      'orderbook_KDAG-USDT_1',
      'orderbook_KLAY-BTC_1',
      'orderbook_KLAY-USDT_1',
      'orderbook_KLV-BTC_1',
      'orderbook_KLV-USDT_1',
      'orderbook_KNC-BTC_1',
      'orderbook_KOK-BTC_1',
      'orderbook_KOK-USDT_1',
      'orderbook_KRT-BTC_1',
      'orderbook_KRT-USDT_1',
      'orderbook_KSM-BTC_1',
      'orderbook_LBC-BTC_1',
      'orderbook_LBC-USDT_1',
      'orderbook_LCS-BTC_1',
      'orderbook_LCS-USDT_1',
      'orderbook_LINK-BTC_1',
      'orderbook_LMCH-BTC_1',
      'orderbook_LMCH-USDT_1',
      'orderbook_LOKI-BTC_1',
      'orderbook_LOKI-USDT_1',
      'orderbook_LOON-BTC_1',
      'orderbook_LOON-USDT_1',
      'orderbook_LTC-BTC_1',
      'orderbook_LUCY-BTC_1',
      'orderbook_LUCY-USDT_1',
      'orderbook_LUNA-BTC_1',
      'orderbook_LUNA-USDT_1',
      'orderbook_MATIC-BTC_1',
      'orderbook_MATIC-USDT_1',
      'orderbook_MDT-BTC_1',
      'orderbook_MDT-USDT_1',
      'orderbook_MFA-BTC_1',
      'orderbook_MFA-USDT_1',
      'orderbook_MKR-BTC_1',
      'orderbook_MOF-BTC_1',
      'orderbook_MOF-USDT_1',
      'orderbook_NEO-BTC_1',
      'orderbook_NFLX-BTC_1',
      'orderbook_NFLX-USDT_1',
      'orderbook_NMR-BTC_1',
      'orderbook_NPXS-BTC_1',
      'orderbook_NVT-BTC_1',
      'orderbook_NVT-USDT_1',
      'orderbook_OCEAN-BTC_1',
      'orderbook_OCEAN-USDT_1',
      'orderbook_OMG-BTC_1',
      'orderbook_ONT-BTC_1',
      'orderbook_ONT-USDT_1',
      'orderbook_OXT-BTC_1',
      'orderbook_OXT-USDT_1',
      'orderbook_PFE-BTC_1',
      'orderbook_PFE-USDT_1',
      'orderbook_PMA-BTC_1',
      'orderbook_PMA-USDT_1',
      'orderbook_QLC-BTC_1',
      'orderbook_QLC-USDT_1',
      'orderbook_REN-BTC_1',
      'orderbook_RENBTC-BTC_1',
      'orderbook_REV-BTC_1',
      'orderbook_REV-USDT_1',
      'orderbook_RVC-BTC_1',
      'orderbook_RVC-USDT_1',
      'orderbook_RVN-BTC_1',
      'orderbook_RVN-USDT_1',
      'orderbook_SC-BTC_1',
      'orderbook_SDT-BTC_1',
      'orderbook_SDT-USDT_1',
      'orderbook_SG-BTC_1',
      'orderbook_SG-USDT_1',
      'orderbook_SHR-BTC_1',
      'orderbook_SHR-USDT_1',
      'orderbook_SKM-BTC_1',
      'orderbook_SKM-USDT_1',
      'orderbook_SOLVE-BTC_1',
      'orderbook_SPY-BTC_1',
      'orderbook_SPY-USDT_1',
      'orderbook_SUKU-BTC_1',
      'orderbook_SUKU-USDT_1',
      'orderbook_SUTER-BTC_1',
      'orderbook_SUTER-USDT_1',
      'orderbook_TEA-BTC_1',
      'orderbook_TEA-USDT_1',
      'orderbook_TRAC-BTC_1',
      'orderbook_TRX-BTC_1',
      'orderbook_TRYB-BTC_1',
      'orderbook_TRYB-USDT_1',
      'orderbook_TSLA-BTC_1',
      'orderbook_TSLA-USDT_1',
      'orderbook_TUSD-BTC_1',
      'orderbook_UCT-BTC_1',
      'orderbook_UCT-USDT_1',
      'orderbook_UMA-BTC_1',
      'orderbook_UNI-BTC_1',
      'orderbook_UPUSD-BTC_1',
      'orderbook_UPUSD-USDT_1',
      'orderbook_UPXAU-BTC_1',
      'orderbook_UPXAU-USDT_1',
      'orderbook_UQC-BTC_1',
      'orderbook_UQC-USDT_1',
      'orderbook_USDC-BTC_1',
      'orderbook_USDN-BTC_1',
      'orderbook_USDN-USDT_1',
      'orderbook_UST-BTC_1',
      'orderbook_UST-USDT_1',
      'orderbook_VANY-BTC_1',
      'orderbook_VANY-USDT_1',
      'orderbook_VDX-BTC_1',
      'orderbook_VET-BTC_1',
      'orderbook_VET-USDT_1',
      'orderbook_VLX-BTC_1',
      'orderbook_VLX-USDT_1',
      'orderbook_WAXP-BTC_1',
      'orderbook_WBTC-BTC_1',
      'orderbook_WICC-BTC_1',
      'orderbook_WICC-USDT_1',
      'orderbook_XLM-BTC_1',
      'orderbook_XMR-BTC_1',
      'orderbook_XRP-BTC_1',
      'orderbook_XTZ-BTC_1',
      'orderbook_XUC-BTC_1',
      'orderbook_XUC-USDT_1',
      'orderbook_XVG-BTC_1',
      'orderbook_XVG-USDT_1',
      'orderbook_XWC-BTC_1',
      'orderbook_XWC-USDT_1',
      'orderbook_YFL-BTC_1',
      'orderbook_ZEC-BTC_1',
      'orderbook_ZRX-BTC_1',
      'orderbook_USDT-USD_1',
      'orderbook_AAPL-USDT_1',
      'orderbook_AAPL-USD_1',
      'orderbook_AAVE-USDT_1',
      'orderbook_AAVE-USD_1',
      'orderbook_ETH-USD_1',
      'orderbook_ADABEAR-USDT_1',
      'orderbook_ADABEAR-USD_1',
      'orderbook_ADA-USD_1',
      'orderbook_ADABULL-USDT_1',
      'orderbook_ADABULL-USD_1',
      'orderbook_ALGO-USD_1',
      'orderbook_AMZN-USD_1',
      'orderbook_ATOM-USD_1',
      'orderbook_BABA-USD_1',
      'orderbook_BAL-USD_1',
      'orderbook_BAND-USD_1',
      'orderbook_BAT-USD_1',
      'orderbook_BCH-USD_1',
      'orderbook_BEAR-USDT_1',
      'orderbook_BEAR-USD_1',
      'orderbook_BILI-USD_1',
      'orderbook_BNTX-USD_1',
      'orderbook_BSV-USD_1',
      'orderbook_BTC-USD_1',
      'orderbook_BULL-USDT_1',
      'orderbook_BULL-USD_1',
      'orderbook_BYND-USD_1',
      'orderbook_CELO-USD_1',
      'orderbook_COMP-USD_1',
      'orderbook_CRO-USD_1',
      'orderbook_DAI-USD_1',
      'orderbook_DCR-USD_1',
      'orderbook_DGB-USD_1',
      'orderbook_DOGE-USD_1',
      'orderbook_DOT-USD_1',
      'orderbook_ENJ-USD_1',
      'orderbook_EOS-USD_1',
      'orderbook_ETC-USD_1',
      'orderbook_ETHBEAR-USDT_1',
      'orderbook_ETHBEAR-USD_1',
      'orderbook_ETHBULL-USDT_1',
      'orderbook_ETHBULL-USD_1',
      'orderbook_FB-USD_1',
      'orderbook_FIL-USD_1',
      'orderbook_GOOGL-USD_1',
      'orderbook_GRT-USD_1',
      'orderbook_HBAR-USD_1',
      'orderbook_HIVE-USD_1',
      'orderbook_KNC-USD_1',
      'orderbook_LINK-USD_1',
      'orderbook_LTC-USD_1',
      'orderbook_NFLX-USD_1',
      'orderbook_PFE-USD_1',
      'orderbook_REN-USD_1',
      'orderbook_RENBTC-USD_1',
      'orderbook_RVN-USD_1',
      'orderbook_SC-USD_1',
      'orderbook_SOLVE-USD_1',
      'orderbook_SPY-USD_1',
      'orderbook_TRX-USD_1',
      'orderbook_TSLA-USD_1',
      'orderbook_TUSD-USD_1',
      'orderbook_UMA-USD_1',
      'orderbook_UNI-USD_1',
      'orderbook_USDC-USD_1',
      'orderbook_WAXP-USD_1',
      'orderbook_XLM-USD_1',
      'orderbook_XRP-USD_1',
      'orderbook_XTZ-USD_1',
      'orderbook_YFL-USD_1',
      'orderbook_ZEC-USD_1',
      'orderbook_ZRX-USD_1',
      'orderbook_AAPL-BTC_1',
      'orderbook_AAVE-ETH_1',
      'orderbook_AAVE-BTC_1',
      'orderbook_PAX-BTC_1',
      'orderbook_PAX-USD_1',
      'orderbook_USDS-BTC_1',
      'orderbook_USDS-USD_1',
      'orderbook_ZEN-BTC_1',
      'orderbook_ZEN-USD_1',
      'orderbook_ETH-EUR_1',
      'orderbook_AAVE-EUR_1',
      'orderbook_BTC-EUR_1',
      'orderbook_ADA-EUR_1',
      'orderbook_BAL-EUR_1',
      'orderbook_BAND-EUR_1',
      'orderbook_BCH-EUR_1',
      'orderbook_BSV-EUR_1',
      'orderbook_CRO-EUR_1',
      'orderbook_DOT-EUR_1',
      'orderbook_GRT-EUR_1',
      'orderbook_KNC-EUR_1',
      'orderbook_REN-EUR_1',
      'orderbook_RENBTC-EUR_1',
      'orderbook_TRX-EUR_1',
      'orderbook_UMA-EUR_1',
      'orderbook_XLM-EUR_1',
      'orderbook_XRP-EUR_1',
      'orderbook_YFL-EUR_1',
      'orderbook_USD-EUR_1',
      'orderbook_USDT-EUR_1'
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

async def on_balance(msg):
  await print_message('Tickers', msg)
  
async def on_Orderbook(msg):
  await 00('Orderbook', msg)

async def print_message(title, msg):
  decoded_msg = await process_message(msg[0])
  print(title + ': ' + json.dumps(decoded_msg, indent = 2))

async def process_message(message):
  try:
    decompressed_msg = decompress(b64decode(message, validate=True), -MAX_WBITS)
  except SyntaxError:
    decompressed_msg = decompress(b64decode(message, validate=True))
  return json.loads(decompressed_msg.decode()) 

if __name__ == "__main__":
  asyncio.run(main())
