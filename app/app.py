import time 
import sqlite3
from io import BytesIO
import datetime
import pandas as pd
import numpy as np
import prophet
from scipy.signal import butter, filtfilt
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MultipleLocator
from aiohttp import web
import jinja2
import aiohttp_jinja2

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

def fix_glitches(df):
    def replace_glitch(window):
        """    This function replaces glitches within a rolling window with np.nan  """  
        return np.nan if window.nunique() == 1 else window.iloc[0]
    window_size=6 # 6 equal samples in 6 x (120 seconds = 12min)
    # Apply rolling window function with custom function
    df['temp_out'] = df['temp_out'].rolling(window=window_size).apply(replace_glitch)
    df['temp_in'] = df['temp_in'].rolling(window=window_size).apply(replace_glitch)
    # since they are failing alternately and are measuring the same we can fill nans 
    # when one of those are not failing
    df['temp_out'] = df['temp_out'].fillna(df['temp_in'])
    df['temp_in'] = df['temp_in'].fillna(df['temp_out'])
    return df 

def filter_and_forecast(df):
    # Forecast based on filtered data
    # since external and internal sensors are measuring the same 
    
    # 1. Merge the two temper sensors data
    #  Standardize std and mean by scaling by std
    std_in, std_out = df['temp_in'].std(), df['temp_out'].std()
    std_scaler = std_out/std_in
    df.loc[:, 'temp_in'] = df['temp_in']*std_scaler
    # 3. removing mean difference between internal and external
    mean_diff = (df['temp_out'].mean() - df['temp_in'].mean())
    df.loc[:, 'temp_in'] = df['temp_in'] + mean_diff
    # 4. Finally we minmax adjust [0, 1] to perform the averaging of the two sensors
    def minmax(x):
        return (x - x.min()) / (x.max() - x.min())
    outmax, outmin = df['temp_out'].max(), df['temp_out'].min()
    df.temp = np.nan 
    # average two sensors 
    df.loc[:, 'temp'] = 0.5*((minmax(df['temp_out'])+minmax(df['temp_in']))*(outmax-outmin)) + outmin
    # interpolate data series for regular time-sample
    temp = df['temp'].interpolate('slinear').resample('2min').mean()

    # 2. Filter data using a low pass 4th order Butterworth filter
    # define low pass and filter it
    order = 4  # Filter order - Design the Butterworth filter
    b, a = butter(order, 0.025, btype='low', analog=False)
    # Apply the low-pass filter using filtfilt to preserve phase
    temp_filt = filtfilt(b, a, temp.bfill())
    temp_raw = df['temp_out']

    # 3. forecast next 5 hours using 5 min samples
    df['y'] = temp_filt
    df.drop(columns=['temp_in', 'temp_out'], inplace=True)
    df['ds'] = df.index

    model = prophet.Prophet() # Create a Prophet model
    model.fit(df) # Fit the model to the data
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
    return forecast_df, temp_raw, temp_filt


app = web.Application()
# Setup jinja2 template loader
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('/home/andre/tempcheck/app'))


async def plot_image(request):

    df, dfz = read_data()
    lambda_mask = lambda df : df.index > datetime.datetime.now() - datetime.timedelta(days=7)

    df = df.loc[lambda_mask(df)]
    dfz = dfz.loc[lambda_mask(dfz)]

    df = fix_glitches(df)

    # Filter and forecast data
    forecast, temp_raw, temp_filt = filter_and_forecast(df)

    fig, ax = plt.subplots(figsize=(15, 4))
    ax.set_title(f"Temperature at {datetime.datetime.now().time().isoformat(timespec='seconds')}")
    ax.plot(df.index, temp_raw, 'bx-', markersize=0.7, linewidth=0., label='raw')
    ax.plot(df.index, temp_filt, '-k', markersize=0., label='temp', linewidth=0.8)    
    ax.plot(dfz.index, dfz['temp_zb'], 'g+', markersize=0.7, alpha=0.4, label='temp_zb', linewidth=0.8)
    ax.plot(forecast.index, forecast.temp, 'y-', linewidth=0.8, markersize=0., label='forecast')

    ax.set_ylim([21, 33])
    ax.yaxis.grid(True, linestyle='-', linewidth=0.9, color='gray')

    ax3 = ax.twinx()
    ax3.set_ylim(ax.get_ylim())
    ax3.yaxis.grid(True)

    day_xtick_locator_ = mdates.DayLocator()
    hour_xtick_locator_ = mdates.HourLocator(byhour=range(0, 24, 6))
    ax.xaxis.set_major_locator(hour_xtick_locator_)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H'))
    ax.xaxis.set_minor_locator(MultipleLocator(0.125))
    ax.xaxis.set_minor_formatter(mdates.DateFormatter('%H'))
    ax.grid(True, which='minor', axis='both', linestyle='-', linewidth=0.25)
    ax.grid(True, which='major', axis='both', linestyle='-', linewidth=0.9, color='gray')

    ax2 = ax.twiny()
    ax2.set_xlim(ax.get_xlim())
    ax2.xaxis.set_major_locator(day_xtick_locator_)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    ax2.xaxis.set_minor_locator(MultipleLocator(12 / 24))
    ax2.xaxis.set_minor_formatter(mdates.DateFormatter('%H:00'))
    ax2.grid(True, which='minor', axis='both', linestyle='-', linewidth=0.25)
    ax2.grid(True, which='major', axis='both', linestyle='-', linewidth=0.9, color='gray')

    ax.legend()

    # Save plot to a BytesIO object
    img_io = BytesIO()
    fig.savefig(img_io, format='png', dpi=200)
    img_io.seek(0)

    return web.Response(body=img_io.read(), content_type='image/png')


@aiohttp_jinja2.template('index.html')  # Render 'index.html' with the time
async def index(request):
    return {'time': time.time() }  # Pass the current time to avoid caching
    
# Define routes for the app
app.router.add_get('/', index)
app.router.add_get('/plot', plot_image)

# Run the app on port 500
if __name__ == '__main__':
    web.run_app(app, port=5000)


