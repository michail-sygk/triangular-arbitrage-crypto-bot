'''Alexandros Frangiadoulis 11/01/2021 '''


import pandas as pd
import itertools
from  itertools import permutations
import time



class all_combos(object):
    
    def __init__(self):
                 
        self.names               = ['ETH', 'XRP', 'LTC', 'USDT', 'BCH', 'LIBRA', 'XMR', 'EOS', 'BSV', 'BNB', 'BTC', 'USD', 'EUR', 'USDC', 'USDT']        
        self.all_triangles       = []
        self.unique_combinations = []
    
        #Run Functions 
        self.unique_triangles()
        self.fix_all_triangles()
        

    def unique_triangles(self):
             
        list_of_names = self.names
        
        list_final = list(itertools.combinations(list_of_names, 3))
        
        self.all_triangles = list_final

    def fix_all_triangles(self):
        
        for tr in self.all_triangles:
            
            comb = list(permutations([tr[0], tr[1], tr[2]], 3))
            
            for elem in comb:
                
                safe_coin = ['USD','EUR','USDT','USDC']
                
                if elem[1] in safe_coin:
                    if not(elem[2] in safe_coin):
                    
                        print(elem)
                
                        self.unique_combinations.append([elem[1]+'-'+elem[0], elem[2]+'-'+elem[1], elem[2]+'-'+elem[0], 0])
                

def return_all_triangles_list():

    a          = all_combos()
    res        = a.unique_combinations  
    
    return res




if __name__ == "__main__":
    
    
    print('\n"""""""""""""""""""""""""""""""""""""\n')
    
    res = return_all_triangles_list()
    
    for i in range (0,len(res)):
        print(str(i) + str(res[i]))
        
    print('\n"""""""""""""""""""""""""""""""""""""\n')






