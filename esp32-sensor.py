import network
import utime
import ujson
from umqtt.simple import MQTTClient
import machine
import dht

class ESP32DHTMqtt:
    """ESP32 dengan sensor DHT dan MQTT publish"""

    def __init__(self, broker_host, client_id, topics_config):
        self.broker_host = broker_host
        self.client_id = client_id
        self.topics = topics_config

        self.wifi = network.WLAN(network.STA_IF)
        self.mqtt = None

        self.led_red = machine.Pin(18, machine.Pin.OUT)
        self.led_yellow = machine.Pin(19, machine.Pin.OUT)
        self.led_green = machine.Pin(20, machine.Pin.OUT)

        self.dht_sensor = dht.DHT11(machine.Pin(21))

        self.control_led = machine.Pin(22, machine.Pin.OUT)

        print(f"ESP32 DHT MQTT Sensor - Client ID: {client_id}")

    def connect_wifi(self, ssid, password, timeout=15):
        """Hubungkan ke WiFi"""
        print(f"WiFi Connecting to {ssid}...")
        self.wifi.active(True)
        self.wifi.connect(ssid, password)

        start = utime.time()
        while not self.wifi.isconnected():
            if utime.time() - start > timeout:
                print("WiFi Connection timeout!")
                return False
            print(".", end="")
            utime.sleep_ms(500)

        print(f"\nWiFi Connected. IP: {self.wifi.ifconfig()[0]}")
        return True

    def on_message(self, topic, msg):
        """Terima pesan dari GUI untuk kontrol LED"""
        topic = topic.decode()
        message = msg.decode()
        print(f"[MQTT] Pesan masuk dari {topic}: {message}")

        if topic == self.topics["sensor_led"]:
            if message == "on":
                self.control_led.on()
                print("[LED] LED manual dinyalakan")
            elif message == "off":
                self.control_led.off()
                print("[LED] LED manual dimatikan")

    def connect_mqtt(self):
        """Hubungkan ke broker MQTT"""
        try:
            print(f"[MQTT] Connecting to {self.broker_host}...")
            self.mqtt = MQTTClient(self.client_id, self.broker_host)
            self.mqtt.set_callback(self.on_message)
            self.mqtt.connect()
            self.mqtt.subscribe(self.topics["sensor_led"])
            print("[MQTT] Connected & subscribed to LED topic.")
            return True
        except Exception as e:
            print(f"[MQTT] Connection error: {e}")
            return False

    def read_dht_data(self):
        """Baca data dari sensor DHT"""
        try:
            self.dht_sensor.measure()
            temperature = self.dht_sensor.temperature()
            humidity = self.dht_sensor.humidity()
            print(f"[Sensor] Temperature: {temperature:.2f}°C, Humidity: {humidity:.2f}%")
            return temperature, humidity
        except Exception as e:
            print(f"[Sensor] Read error: {e}")
            return None, None

    def update_led_status(self, temperature):
        """Atur LED indikator suhu"""
        self.led_red.off()
        self.led_yellow.off()
        self.led_green.off()

        if temperature is None:
            return "OFF"

        if temperature > 30:
            self.led_red.on()
            return "RED"
        elif 25 <= temperature <= 30:
            self.led_yellow.on()
            return "YELLOW"
        else:
            self.led_green.on()
            return "GREEN"

    def publish_sensor_data(self):
        """Kirim data sensor ke broker"""
        temperature, humidity = self.read_dht_data()
        if temperature is None or humidity is None:
            print("[Publish] Skip (invalid data)")
            return

        led_status = self.update_led_status(temperature)

        payload_temp = ujson.dumps({"temperature": temperature, "timestamp": int(utime.time())})
        payload_hum = ujson.dumps({"humidity": humidity, "timestamp": int(utime.time())})
        payload_led = ujson.dumps({"led": led_status, "timestamp": int(utime.time())})

        self.mqtt.publish(self.topics["sensor_temp"], payload_temp)
        self.mqtt.publish(self.topics["sensor_humidity"], payload_hum)
        self.mqtt.publish("sensor/esp32/2/led", payload_led)

        print(f"[Publish] Temp={temperature:.2f}C, Hum={humidity:.2f}%, LED={led_status}")

    def run(self, publish_interval=5):
        """Loop utama"""
        print("[System] Starting main loop...")
        while True:
            try:
                self.mqtt.check_msg()
                self.publish_sensor_data()
                utime.sleep(publish_interval)
            except Exception as e:
                print(f"[Error] {e}")
                utime.sleep(2)

def run_esp32_dht():
    """Setup utama"""
    BROKER = "test.mosquitto.org"
    CLIENT_ID = "esp-sensor-suhu-2"
    SSID = "Salman@wifi.id"
    PASSWORD = "makan dulu"
    TOPICS = {
        "sensor_temp": "sensor/esp32/2/temperature",
        "sensor_humidity": "sensor/esp32/2/humidity",
        "sensor_led": "sensor/esp32/2/led"
    }

    esp = ESP32DHTMqtt(BROKER, CLIENT_ID, TOPICS)

    if not esp.connect_wifi(SSID, PASSWORD):
        print("[System] WiFi connection failed!")
        return

    if not esp.connect_mqtt():
        print("[System] MQTT connection failed!")
        return

    esp.run(publish_interval=5)


if __name__ == "__main__":
    run_esp32_dht()