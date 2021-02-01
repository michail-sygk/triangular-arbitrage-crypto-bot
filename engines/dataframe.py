import pandas as pd 
import time
import datetime
from datetime import datetime,date
from datetime import date
import uuid

class Dataframe(object): 
 
    def  __init__(self , dataframe_name ) :
        self.initial_df = pd.read_csv(dataframe_name)
        self.columns =  self.initial_df.columns
               
    def parse_data_to_dataframe (self  ,obj, csv_name ): 
        unique_id =  uuid.uuid4()
        row = [unique_id.hex]
        
        for column in self.columns : 
            if column in obj.__dict__.keys():
                row.append(obj.__dict__[column])
        buffer_df        = pd.DataFrame(columns = self.columns)
        
        buffer_df.loc[0]  =  self.calculate_how_long_lasts_an_arbitrage(row)
        self.initial_df = self.initial_df.append(buffer_df)   
        self.initial_df.to_csv('data/bittrex/'+ csv_name , index = False)
 
    def calculate_how_long_lasts_an_arbitrage(self , row ):
        filter_1  = self.initial_df['Session']  == row[13]
        filter_2  = self.initial_df['TickerPairA']  == row[2]
        filter_3  = self.initial_df['TickerPairB']  == row[3]
        filter_4  = self.initial_df['TickerPairC']  == row[4]
        filter_5  = self.initial_df['Round']  == row[12] - 1
        filter_6  = self.initial_df['Route']  ==  row[8]
        temp_dataframe   = self.initial_df[filter_1 & filter_2 & filter_3 & filter_4 & filter_5 ]

        if len(temp_dataframe) > 0 : 
              
            print('123')
            old_alive_seconds =   datetime.strptime( temp_dataframe['Alive_time'][0] ,'%H:%M:%S.%f')
            old_datetime_object  = datetime.strptime( temp_dataframe['Time'][0] ,'%H:%M:%S.%f')
            new_date_time_object = datetime.strptime( row[11]  ,'%H:%M:%S.%f')
 
            total_new_alive_time = new_date_time_object - old_datetime_object 
               
            total_new_alive_time =total_new_alive_time + old_alive_seconds
            row[9]  =  		total_new_alive_time.strftime('%H:%M:%S.%f')
            filter_1  =  self.initial_df['Unique_id'] != temp_dataframe['Unique_id'][0]

            self.initial_df = self.initial_df[filter_1]
            return row
        return row
                         
    def return_dataframe(self): 
        return self.initial_df    
