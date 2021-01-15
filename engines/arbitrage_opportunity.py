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
                 , percentage_profit_without_fees
                 , percentage_profit_with_fees
                 , amount_profit_USDT
                 , maxAmount_USDT
                 , route
                 , route_Result
                 , status
                 , round_number
                 , session
                 ):
         
        self.TickerPairA = tickerPairA
        self.TickerPairB = tickerPairB
        self.TickerPairC = tickerPairC
        self.Percentage_profit_without_fees =  percentage_profit_without_fees
        self.Percentage_profit_with_fees =  percentage_profit_with_fees
        self.Amount_profit_USDT = amount_profit_USDT
        self.maxAmount_USDT = maxAmount_USDT
        self.Route = route
        self.Alive_time = 0
         
        now = datetime.now()
        self.Time = now.strftime("%H:%M:%S")
    
        today = date.today()
        self.Date = today.strftime("%d/%m/%Y")
        self.Route_Result = route_Result
        self.Status = status   #Status : Completed, Inefficient Amount in market , Open  
        self.Round = round_number
        self.Session = session
    
