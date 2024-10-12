import time 
import sqlite3
from io import BytesIO
import datetime
import pandas as pd
import numpy as np
from prophet import Prophet
from scipy.signal import butter, filtfilt
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MultipleLocator
from aiohttp import web
import jinja2
import aiohttp_jinja2
import plotly.graph_objs as go
import plotly.io as pio


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


app = web.Application()
# Setup jinja2 template loader
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('/home/andre/tempcheck/app'))



@aiohttp_jinja2.template('index.html')
async def index(request):
    df, dfz = read_data()
    lambda_mask = lambda df : df.index > datetime.datetime.now() - datetime.timedelta(days=7)

    df = df.loc[lambda_mask(df)]
    dfz = dfz.loc[lambda_mask(dfz)]

    df = process_data(df)
    temp_raw, temp_filt = df['raw'], df['temp']
    forecast = make_forecast(df)

    # Create Plotly figure
    fig = go.Figure()
    # Add raw scatter points
    fig.add_trace(go.Scatter(x=df.index, y=temp_raw, mode='markers', 
                             marker=dict(color='blue', size=3), name='Raw'))    
    # Add filtered temperature line
    fig.add_trace(go.Scatter(x=df.index, y=temp_filt, mode='lines', 
                             line=dict(color='black', width=0.8), name='TempS'))
        # Add zigbee temperature points
    fig.add_trace(go.Scatter(x=dfz.index, y=dfz['temp_zb'], mode='markers', 
                             marker=dict(color='green', size=3, opacity=0.4), name='TempZb'))    
    # Add forecasted temperature line
    fig.add_trace(go.Scatter(x=forecast.index, y=forecast['temp'], mode='lines', 
                             line=dict(color='yellow', width=0.8), name='Forecast'))
                     
    # Layout for y-axis (left)
    fig.update_yaxes(title_text='Temperature', range=[21, 33], showgrid=True, gridwidth=0.9)
        
    fig.update_layout(
        title = 'Home Temperature Sensors',
        xaxis_tickformatstops = [
            dict(dtickrange=[1000, 60000], value="%H:%M:%S s"),
            dict(dtickrange=[60000, 3600000], value="%H:%M m"),
            dict(dtickrange=[3600000, 86400000], value="%H:%M <br>%d-%B")            
        ]
    )
                          
    # Convert the figure to HTML and serve it
    fig_html = fig.to_html(full_html=False)
    
    return {'plot': fig_html, 'time': datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}


    
# Define routes for the app
app.router.add_get('/', index)

# Run the app on port 500
if __name__ == '__main__':
    web.run_app(app, port=5000)

