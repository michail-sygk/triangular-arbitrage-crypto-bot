from abc import ABCMeta, abstractmethod
import json

class ExchangeEngineBase:
    __metaclass__ = ABCMeta
    @abstractmethod
    def __init__(self):
        pass
    
    def load_key(self, filename):
        with open(filename) as f:    
            self.key = json.load(f)
            
  
 