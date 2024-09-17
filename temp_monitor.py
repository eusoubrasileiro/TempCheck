"""
Reads temperature and humidity from 2 sensors

1. A usb metal probe only for temperature (2 readings internal and external temperature)
    TEMPer2 sensor from https://pcsensor.com/manuals-detail?article_id=474 

2. A tuya Zigbee Sensor WSD500A type C power supplied (2 readings: temperature and relative humidity)    
    Connects and publishes on mosquitto mqtt broker from zigbee2mqtt and usb wireless zigbee 3.0 gateway adapter.
       
To monitor temperature at our house. Writes on a database sqlite internal 
 1. Temper internal temperature
 2. Temper external temperature (probe on the end of black wire)
 3. Zigbee temperature
 4. Zigbee relative humidity
"""
# Temper installation
# this fork supports my version at branch TEMPer 4.1 install from it
# pip install git+https://github.com/greg-kodama/temper@TEMPer2_V4.1
# pip install pyserial pandas
import sys 
from datetime import datetime
import sqlite3
#zigbee
import paho.mqtt.client as mqtt # paho-mqtt-2.1.0
import json 
from datetime import datetime 
#temper
import temper 
# in case no permissions
# sudo chmod o+rw /dev/hidraw*
# or use .rules and reboot
dbfile = '/home/andre/home_temperature.db'
temper_reader = temper.Temper()

#zigbee
# Define the MQTT broker address and port
broker_address = "localhost"  # Or use "orangepi5"
broker_port = 1883  # Default MQTT port
mqtt_username = "andre" 
mqtt_password = "gig1684"
# Define the topic to publish/subscribe
topic = "zigbee2mqtt/temper_humidity"

# Define callback functions
def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print("Connected to MQTT Broker!")
        # Subscribe to a topic
        client.subscribe(topic)
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    """on message from mqtt broker take the oportunity to read
    temper sensor as well and store everything on sqlite database"""
    msg = msg.payload.decode()    
    msg = json.loads(msg)        
    # fetch temper sensor data as well
    results = temper_reader.read()[0] 
    temp_in, temp_out = float(results['internal temperature']), float(results['external temperature'])
    temp_zb, hum_zb = float(msg['temperature']), float(msg['humidity'])
    print(f"temp_in {temp_in:2.2f} temp_out {temp_out:2.2f} "
        f"temp_zb {temp_zb:2.2f} hum_zb {hum_zb:2.2f}", file=sys.stderr)                
    with sqlite3.connect(dbfile) as conn:
        cursor = conn.cursor()
        cursor.execute(f"INSERT INTO home (time, temp_in, temp_out, temp_zb, hum_zb) " 
                       "VALUES (?, ?, ?, ?, ?)", (datetime.now(), temp_in, temp_out, temp_zb, hum_zb))
        conn.commit()        

# Create an MQTT client instance
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
# Set the username and password for broker authentication
client.username_pw_set(mqtt_username, mqtt_password)
# Assign the callback functions
client.on_connect = on_connect
client.on_message = on_message

# Connect to the broker
try:
    client.connect(broker_address, broker_port)
except ConnectionRefusedError as e:
    print(f"Connection refused: {e}")
    exit(1)

client.loop_forever()
# Keep the script running
try:
    while True:
        pass
except KeyboardInterrupt:
    print("Exiting...")

# Stop the loop and disconnect
client.loop_stop()
client.disconnect()