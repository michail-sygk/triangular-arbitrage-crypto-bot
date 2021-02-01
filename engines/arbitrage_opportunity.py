import pandas as pd 
import time
import datetime
from datetime import datetime,date
from datetime import date

class Arbitrage_opportunity(object): 
     
    def __init__(self 
                 , tickerPairA 
                 , tickerPairB 
                 , tickerPairC 
                 , Percentage_Profit
                 , Profit
                 , maxAmount
                 , start_ticker
                 , route
                 , round_number
                 , session
                 ): 
     
        self.Start_ticker = start_ticker
        self.TickerPairA = tickerPairA
        self.TickerPairB = tickerPairB
        self.TickerPairC = tickerPairC
        
        self.Percentage_Profit = Percentage_Profit
        self.Profit = Profit
        self.maxAmount = maxAmount
        self.Route = route
        self.Alive_time ='0:00:00.000000'
         
        now = datetime.now()
        self.Time = now.strftime("%H:%M:%S.%f")
        today = date.today()
        self.Date = today.strftime("%d/%m/%Y")
        self.Round = round_number
        self.Session = session
    


 