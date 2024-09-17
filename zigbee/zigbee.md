#### Adapted and adjusted step-by-step on how to configure Zigbee Adapter, Broker and Temperature and Humidity Sensor. 

To set up the Zigbee device on your Orange Pi 5 running Ubuntu 22.04, you can use the open-source project **zigbee2mqtt**, which allows you to control Zigbee devices via MQTT.

Here’s a step-by-step guide:

### 1. **Install Prerequisites Node.js**
Zigbee2MQTT requires Node.js. You can install it by running:

```bash
sudo curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs git make g++ gcc libsystemd-dev
#Verify that the correct nodejs and npm (automatically installed with nodejs)
#version has been installed
node --version  # Should output V18.x, V20.x, V21.X
npm --version  # Should output 9.X or 10.X
```

```bash
curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
sudo apt install -y nodejs
```

### 3. **Install Zigbee2MQTT**
Clone the Zigbee2MQTT repository and navigate into the directory:

```bash
git clone --depth 1 https://github.com/Koenkk/zigbee2mqtt.git /opt/zigbee2mqtt
cd /opt/zigbee2mqtt
sudo chown -R ${USER}: /opt/zigbee2mqtt
```

Now install Zigbee2MQTT dependencies:

```bash
npm ci
```

### 4. **Configure Zigbee2MQTT**
To configure the Zigbee dongle, you'll need to modify the Zigbee2MQTT configuration.

Copy the default configuration file:

```bash
cp /opt/zigbee2mqtt/data/configuration.example.yaml /opt/zigbee2mqtt/data/configuration.yaml
nano /opt/zigbee2mqtt/data/configuration.yaml
```

Modify the following content, replacing the `serial` section with the correct path for your Zigbee USB stick (you can check the path using `ls -l /dev/serial/by-id`.

```yaml
permit_join: true
mqtt:
  base_topic: zigbee2mqtt
  server: 'mqtt://localhost'
  user: your_mqtt_user
  password: your_mqtt_password
serial:
  port: /dev/ttyUSB0
  adapter: ember
```

### 5. **Install and Configure MQTT Broker**
If you don’t already have an MQTT broker, you can install Mosquitto:

```bash
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

Create user and password  
```bash
sudo mosquitto_passwd -c /etc/mosquitto/passwd your_mqtt_user
sudo nano /etc/mosquitto/mosquitto.conf
```

Add these lines

```bash
allow_anonymous false
password_file /etc/mosquitto/passwd
listener 1883 0.0.0.0
```

Restart mosquitto
```bash
sudo systemctl restart mosquitto
```


### 6. **Start Zigbee2MQTT**
Now that everything is configured, you can start Zigbee2MQTT:

```bash
cd /opt/zigbee2mqtt
npm start
```

Zigbee2MQTT should now be running and communicating with your Zigbee devices via the USB stick.

### 7. **Running Zigbee2MQTT as a Service**
To ensure Zigbee2MQTT starts automatically, you can create a systemd service.

Create the service file:

```bash
sudo nano /etc/systemd/system/zigbee2mqtt.service
```

Add the following content:

```ini
[Unit]
Description=zigbee2mqtt
After=network.target

[Service]
ExecStart=/usr/bin/npm start --prefix /opt/zigbee2mqtt
WorkingDirectory=/opt/zigbee2mqtt
StandardOutput=inherit
StandardError=inherit
Restart=always
User=root

[Install]
WantedBy=multi-user.target
```

Save and close the file, then enable and start the service:

```bash
sudo systemctl enable zigbee2mqtt
sudo systemctl start zigbee2mqtt
```

### 8. **Accessing the Zigbee2MQTT Frontend (Optional)**

Installed by default use `http://your_orangepi5_ip`.

Let me know if you need further assistance with specific configurations!