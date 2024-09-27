"""
Reads temperature and humidity from 2 sensors independently:

1. A usb metal probe only for temperature (2 readings internal and external temperature)
    TEMPer2 sensor from https://pcsensor.com/manuals-detail?article_id=474 
    The wire probe is now wrapped with cotton to avoid abrupt changes. 
    The internal sensor is now being used to monitor the temperature of the external probe.
    By setting both side by side and using a usb extension cable for that.

2. A tuya Zigbee Sensor WSD500A type C power supplied (2 readings: temperature and relative humidity)    
    Connects and publishes on mosquitto mqtt broker from zigbee2mqtt and usb wireless zigbee 3.0 gateway adapter.
       
To monitor temperature at our house. Writes on a database sqlite internal 
The readings from the Zigbee sensor are saved in zigbee.db, and the TEMPer2 readings in temper.db.

Requirements:
- pip install git+https://github.com/greg-kodama/temper@TEMPer2_V4.1
- pip install paho-mqtt sqlite3 pandas

Temper installation
this fork supports my version at branch TEMPer 4.1 install from it
pip install git+https://github.com/greg-kodama/temper@TEMPer2_V4.1
pip install pyserial pandas

"""

import sys
import time
import threading
from datetime import datetime, timedelta
import sqlite3
import json
import paho.mqtt.client as mqtt  # paho-mqtt-2.1.0
import temper  # TEMPer2 sensor library

# Define database files for each sensor
zigbee_dbfile = '/home/andre/zigbee.db'
temper_dbfile = '/home/andre/temper.db'

# Initialize TEMPer2 sensor
temper_reader = temper.Temper()

# MQTT settings for Zigbee
broker_address = "localhost"
broker_port = 1883
mqtt_username = "andre"
mqtt_password = "gig1684"
topic = "zigbee2mqtt/temper_humidity"
previous_time = datetime.now()

# Zigbee callback functions
def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print("Connected to MQTT Broker!")
        client.subscribe(topic)
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    """Handle MQTT message (Zigbee sensor data) and store it in zigbee.db"""
    try:
        global previous_time
        msg_payload = msg.payload.decode()
        data = json.loads(msg_payload)
        now = datetime.now()
        if now - previous_time < timedelta(minutes=1):
            previous_time = now 
            return 
        previous_time = now 
        temp_zb, hum_zb = float(data['temperature']), float(data['humidity'])

        # Save Zigbee data to zigbee.db
        with sqlite3.connect(zigbee_dbfile) as conn:
            cursor = conn.cursor()
            cursor.execute(f"INSERT INTO home (time, temp_zb, hum_zb) "
                           "VALUES (?, ?, ?)", (now, temp_zb, hum_zb))
            conn.commit()

        print(f"Zigbee - Temp: {temp_zb:.2f}°C, Humidity: {hum_zb:.2f}%", file=sys.stderr)

    except Exception as e:
        print(f"Error processing Zigbee message: {e}", file=sys.stderr)

# TEMPer2 sensor reading function (runs independently every 2 minutes)
def read_temper_sensors():
    while True:
        try:
            # Read TEMPer2 data
            results = temper_reader.read()[0]
            temp_in = float(results['internal temperature'])
            temp_out = float(results['external temperature'])
            now = datetime.now()

            # Save TEMPer2 data to temper.db
            with sqlite3.connect(temper_dbfile) as conn:
                cursor = conn.cursor()
                cursor.execute(f"INSERT INTO home (time, temp_in, temp_out) "
                               "VALUES (?, ?, ?)", (now, temp_in, temp_out))
                conn.commit()

            print(f"TEMPer2 - Internal: {temp_in:.2f}°C, External: {temp_out:.2f}°C", file=sys.stderr)

        except Exception as e:
            print(f"Error reading TEMPer2 sensor: {e}", file=sys.stderr)

        # Wait for 1 minutes before next reading
        time.sleep(60)

# Setup MQTT client for Zigbee sensor
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.username_pw_set(mqtt_username, mqtt_password)
mqtt_client.on_connect = on_connect # Assign the callback functions
mqtt_client.on_message = on_message


# Connect to the MQTT broker
try:
    mqtt_client.connect(broker_address, broker_port)
except Exception as e:
    print(f"Failed to connect to MQTT broker: {e}", file=sys.stderr)
    sys.exit(1)

# Start the MQTT loop in a separate thread
mqtt_thread = threading.Thread(target=mqtt_client.loop_forever)
mqtt_thread.start()

# Start the TEMPer2 sensor reading loop
read_temper_sensors()
