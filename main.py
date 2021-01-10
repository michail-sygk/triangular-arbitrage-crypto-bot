import argparse
import json
from engines.triangular_arbitrage import CryptoEngineTriArbitrage


configFile = 'arbitrage_config.json'

f = open(configFile)    
config = json.load(f)
f.close()

parser = argparse.ArgumentParser(description='Crypto Arbitrage')
parser.add_argument('-m', '--mode', help='Arbitrage mode: triangular or exchange', required=True)
parser.add_argument('-p', '--production', help='Production mode', action='store_true')

engine = None
isMockMode = True  



engine_2 = CryptoEngineTriArbitrage(config['triangular'], isMockMode)
#engine_1 = CryptoEngineTriArbitrage(config['triangular_ETH_USD_LTC'], isMockMode)



if engine_2:
    engine_2.run()
