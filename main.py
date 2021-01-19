import argparse
import json
from engines.triangular_arbitrage import CryptoEngineTriArbitrage


'''
Over here you define from the arbitrage_config which market has to chose the program and what pairs 
to choose in order to fullfill arbitrage.
'''
configFile = 'arbitrage_config.json'

f = open(configFile)    
config = json.load(f)
f.close()
isMockMode = True  
engine = CryptoEngineTriArbitrage(config['triangular'], isMockMode)

#The program starts to run officially from this line

engine.run()

 


 




