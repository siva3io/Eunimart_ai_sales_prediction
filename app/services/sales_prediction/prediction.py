import pandas as pd
from datetime import datetime
from sklearn.preprocessing import StandardScaler
import pickle
import os
import warnings
import logging
from app.utils import catch_exceptions,download_from_s3
from constants import account_category
import math
warnings.filterwarnings("ignore")

logger = logging.getLogger(name=__name__)

class Prediction():

    def __init__(self):
        pass
    @catch_exceptions
    def preprocess_data(self,df):
        try:
            df['Weekday'] = df.Date.dt.weekday
            df['Year'] = df.Date.dt.year
            df['Month'] = df.Date.dt.month
            df['Day'] = df.Date.dt.day
            return df
        except Exception as e:
            logger.error(e,exc_info=True)

    @catch_exceptions
    def scaling(self,X):
        try:
            X = X.iloc[:,1:].values 
            sc_X = StandardScaler()
            X_scaled = sc_X.fit_transform(X)
            return X_scaled
        except Exception as e:
            logger.error(e,exc_info=True)
    
    @catch_exceptions
    def check_if_file_exists(self,abs_file_path):
        try:
            s3_path = 'sales'
        except Exception as e:
            logger.error(e,exc_info=True)
            return False
    
    @catch_exceptions
    def forecast_sales(self,abs_file_path,df,scaled_df):
        pickle_model = pickle.load(open(abs_file_path,'rb')) #Place the saved model path in open command 
        #Use the loaded pickled model to make predictionsted_quantity
        total_sales = 0
        forecasted_results = dict()
        for ind in df.index:
            forecasted_results[str(df['Date'][ind])] = df['PredictedQuantity'][ind]
            total_sales += df['PredictedQuantity'][ind]
        return math.ceil(total_sales)
        # return forecasted_results

    @catch_exceptions
    def forecasting(self,request_data):
        try:
            df = pd.date_range(start = request_data["start_date"],end = request_data["end_date"])
            df = df.to_frame()
            df = df.rename(columns={0:'Date'})
            df = self.preprocess_data(df)
            scaled_df = self.scaling(df) 
            if request_data["account_id"] in account_category and request_data["category_id"] in account_category[request_data["account_id"]]:
                abs_file_path = "models/Client-{0}/Category-{1}/model.pkl".format(request_data["account_id"],request_data["category_id"])
                if self.check_if_file_exists(abs_file_path):
                    total_sales = self.forecast_sales(abs_file_path,df,scaled_df)
            return total_sales
        except Exception as e:
            logger.error(e,exc_info=True)
    
    def get_sales(self,request_data):
        try:
            response_data = {}
            mandatory_fields = ["account_id","category_id","start_date","end_date"]
            for field in mandatory_fields:
                if not field in request_data["data"]:
                    response_data = {
                        "status":False,
                        "message":"Required field is missing",
                        "error_obj":{
                            "description":"{} is missing".format(field),
                            "error_code":"REQUIRED_FIELD_IS_MISSING"
                        }
                    }
            if not response_data:
                sales = self.forecasting(request_data["data"])
                response_data = {
                    "status":True,
                    "data":sales,
                    "columns": [
                        {
                            "column_key": "date",
                            "column_name": "Date",
                            "column_position": 1,
                        }
                    ]
                }

            return response_data
        except Exception as e:
            logger.error(e,exc_info=True)

prediction = Prediction()
