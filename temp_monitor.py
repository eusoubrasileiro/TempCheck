"""
Uses TEMPer2 sensor from https://pcsensor.com/manuals-detail?article_id=474 
to monitor temperature at our house. Writes on a database sqlite internal 
(sensor temperature) and external temperature (probe on the end of black wire)

# this fork supports my version at branch TEMPer 4.1 install from it
pip install git+https://github.com/greg-kodama/temper@TEMPer2_V4.1
pip install pyserial pandas

"""

import sys 
import time
from datetime import datetime
import pandas as pd 
import sqlite3
import temper 

# in case no permissions
# sudo chmod o+rw /dev/hidraw*
# or use .rules and reboot

dbfile = '/home/andre/home_temperature.db'
temp = temper.Temper()

while True:    
    results = temp.read()[0]
    temp_in, temp_out = results['internal temperature'], results['external temperature']
    print('temp_in {} temp_out {}'.format(temp_in, temp_out), file=sys.stderr)
    now = datetime.now()
    with sqlite3.connect(dbfile) as conn:
        cursor = conn.cursor()
        cursor.execute(f"INSERT INTO home (time, temp_out, temp_in) VALUES (?, ?, ?)", (datetime.now(), float(temp_out), float(temp_in)))
        conn.commit()    
    time.sleep(30) # every 30 seconds