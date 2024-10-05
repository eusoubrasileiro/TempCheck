import time 
import sqlite3
from io import BytesIO
import datetime
import pandas as pd
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

app = web.Application()
# Setup jinja2 template loader
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('/home/andre/tempcheck/app'))


async def plot_image(request):

    df, dfz = read_data()
    lambda_mask = lambda df : df.index > datetime.datetime.now() - datetime.timedelta(days=7)

    fig, ax = plt.subplots(figsize=(15, 4))
    ax.plot(df.loc[lambda_mask(df)].index, df.loc[lambda_mask(df)]['temp_in'], 'x-', markersize=1.0, label='temp_in', linewidth=0.5)
    ax.plot(df.loc[lambda_mask(df)].index, df.loc[lambda_mask(df)]['temp_out'], '>-', markersize=1.0, label='temp_out', linewidth=0.5)
    ax.plot(dfz.loc[lambda_mask(dfz)].index, dfz.loc[lambda_mask(dfz)]['temp_zb'], '+-', markersize=1.0, label='temp_zb', linewidth=0.5)

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
    return {'time': time.time(), 'dtime' : datetime.datetime.now().time().isoformat(timespec='seconds')}  # Pass the current time to avoid caching
    
# Define routes for the app
app.router.add_get('/', index)
app.router.add_get('/plot', plot_image)

# Run the app on port 500
if __name__ == '__main__':
    web.run_app(app, port=5000)


