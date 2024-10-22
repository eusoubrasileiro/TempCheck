import sqlite3
import datetime
import pandas as pd
import numpy as np
from prophet import Prophet
from scipy.signal import butter, filtfilt
from aiohttp import web
import os 
import sys 

def read_data():
    # Function to read and resample data
    def read_resample(file, resample='2min', label_offset={}):
        with sqlite3.connect(file) as conn:
            df = pd.read_sql_query("SELECT * FROM home", conn)
            df.index = pd.to_datetime(df.time)
            df.sort_index(inplace=True)
            df.drop(columns=['time'], inplace=True)
            df.dropna(inplace=True)
            df = df.interpolate('slinear').resample(resample).mean()
            if label_offset:
                for label, offset in label_offset.items():
                    df.loc[:, label] = df.loc[:, label] + offset
            return df
        return df.dropna()

    dfz = read_resample('zigbee.db')  # Data from zigbee.db
    df = read_resample('temper.db', label_offset={'temp_out': +2., 'temp_in': +0.75})  # Data from temper.db

    return df, dfz 

def process_data(df):
    def replace_glitch(window):
        """    This function replaces glitches within a rolling window with np.nan  """  
        return np.nan if window.nunique() == 1 else window.iloc[0]
    window_size=6 # 6 equal samples in 6 x (120 seconds = 12min)
    # Apply rolling window function with custom function
    df['temp_out'] = df['temp_out'].rolling(window=window_size).apply(replace_glitch)
    df['temp_in'] = df['temp_in'].rolling(window=window_size).apply(replace_glitch)    
    # since they are failing alternately and are measuring the same we can fill nans 
    # when one of those are not failing
    # since they are failing alternately and are measuring the same we can fill nans
    df['temp_out'] = df['temp_out'].fillna(df['temp_in'])
    df['temp_in'] = df['temp_in'].fillna(df['temp_out'])
    df['raw'] = (df['temp_in'] + df['temp_out'])/ 2 # Merge the two temper sensors data
    df['temp'] = df['raw'].interpolate('slinear').resample('2min').mean()
    df['temp'] = df['temp'].bfill() # some nan samples in the begin
    order = 4  # Filter order - Design the Butterworth filter
    b, a = butter(order, 0.025, btype='low', analog=False)
    # Apply the low-pass filter using filtfilt to preserve phase
    df['temp'] = filtfilt(b, a, df['temp'])
    return df 

def make_forecast(df):
    # 3. forecast next 5 hours using 5 min samples
    # Forecast based on filtered data
    dfor = df.drop(columns=['temp_in', 'temp_out', 'temp'])
    dfor['y'] = df['temp']
    dfor['ds'] = df.index

    model = Prophet() # Create a Prophet model
    model.fit(dfor) # Fit the model to the data
    # Specify the number of periods to forecast
    future_periods = 60  # Number of 5-minute intervals in a day - 300 minutes - 5 hours
    # Generate future dates for forecasting
    future = model.make_future_dataframe(periods=future_periods, freq='5T')  # '5T' for 5-minute resolution
    # Perform the forecastdf
    forecast = model.predict(future[-60:])
    # Retrieve the forecasted values
    forecasted_values = forecast.tail(future_periods)['yhat']
    forecast_df = pd.DataFrame(forecasted_values.values, columns=['temp'], 
                                index=future.ds.iloc[-60:].values)                                
    return forecast_df


async def get_data(request):
    df, dfz = read_data()
    lambda_mask = lambda df : df.index > datetime.datetime.now() - datetime.timedelta(days=7)
    # NaN must be None for javascript json 
    replace_nan_with_none = lambda data_list: [None if np.isnan(x) else x for x in data_list]

    df = df.loc[lambda_mask(df)]
    dfz = dfz.loc[lambda_mask(dfz)]

    df = process_data(df)
    temp_raw, temp_filt = df['raw'], df['temp']
    forecast = make_forecast(df)
    # Convert data to JSON-compatible format
    data = {
        'raw': {
            'x': df.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),  # Convert index to strings
            'y': replace_nan_with_none(temp_raw.tolist())  # Replace NaN with None
        },
        'temp_filt': {
            'x': df.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
            'y': replace_nan_with_none(temp_filt.tolist())  # Replace NaN with None
        },
        'temp_zb': {
            'x': dfz.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
            'y': replace_nan_with_none(dfz['temp_zb'].tolist())  # Replace NaN with None
        },
        'forecast': {
            'x': forecast.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
            'y': replace_nan_with_none(forecast['temp'].tolist())  # Replace NaN with None
        }
    }

    return web.json_response(data)
    
    
# Define the path to your build folder (where index.html and _app are located)
BUILD_DIR = '/home/andre/tempcheck/app'  # Adjust this path if necessary

# Serve the main index.html
async def handle_index(request):
    return web.FileResponse(os.path.join(BUILD_DIR, 'index.html'))

# Serve the favicon.png
async def handle_favicon(request):
    return web.FileResponse(os.path.join(BUILD_DIR, 'favicon.png'))

# Serve static files from the _app folder
async def handle_app_files(request):
    # Get the full requested path under /_app
    full_path = request.match_info.get('tail')
    file_path = os.path.join(BUILD_DIR, '_app', full_path)    
    # Ensure the file exists before returning it, otherwise return a 404
    if os.path.exists(file_path):
        return web.FileResponse(file_path)
    else:
        return web.Response(status=404, text=f"File not found {file_path}")        

app = web.Application()
app.router.add_get('/', handle_index)
app.router.add_get('/favicon.png', handle_favicon)
app.router.add_get('/_app/{tail:.*}', handle_app_files)
app.router.add_get('/data', get_data)  # Your API route
    
if __name__ == '__main__':
    web.run_app(app, port=5005)

