# mqtt/client.py - MQTT Client untuk komunikasi
import json
import paho.mqtt.client as mqtt
from queue import Queue
from threading import Thread
import time

class MqttClient:
    """MQTT Client untuk komunikasi dengan broker"""

    def __init__(self, config_file='config.json'):
        """Inisialisasi MQTT Client"""
        # Load konfigurasi
        with open(config_file, 'r') as f:
            config = json.load(f)

        self.broker_config = config['broker']
        self.topics = config['topics']

        # Setup client
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        # Message queue untuk handling di thread terpisah
        self.message_queue = Queue()

        # Status tracking
        self.is_connected = False
        self.subscribed_topics = []

        print("[MQTT] Client initialized")

    def on_connect(self, client, userdata, flags, rc):
        """Callback saat client terhubung ke broker"""
        if rc == 0:
            print("[MQTT] Connected to broker successfully")
            self.is_connected = True

            # Subscribe ke semua topik sensor
            for topic_name, topic_path in self.topics.items():
                if topic_name.startswith('sensor_') or topic_name.startswith('button_'):
                    self.client.subscribe(topic_path)
                    self.subscribed_topics.append(topic_path)
                    print(f"[MQTT] Subscribed to: {topic_path}")
        else:
            print(f"[MQTT] Connection failed with code {rc}")
            self.is_connected = False

    def on_message(self, client, userdata, msg):
        """Callback saat menerima message"""
        topic = msg.topic
        payload = msg.payload.decode()

        try:
            # Coba parse sebagai JSON
            data = json.loads(payload)
            message = {
                'topic': topic,
                'data': data,
                'timestamp': time.time(),
                'raw_payload': payload
            }
        except json.JSONDecodeError:
            # Jika bukan JSON, simpan sebagai string
            message = {
                'topic': topic,
                'data': payload,
                'timestamp': time.time(),
                'raw_payload': payload
            }

        self.message_queue.put(message)
        print(f"[MQTT] Message received - Topic: {topic}, Payload: {payload}")

    def on_disconnect(self, client, userdata, rc):
        """Callback saat client disconnect"""
        if rc != 0:
            print(f"[MQTT] Unexpected disconnection: {rc}")
        else:
            print("[MQTT] Disconnected from broker")

        self.is_connected = False

    def connect(self):
        """Hubungkan ke broker MQTT"""
        try:
            print(f"[MQTT] Connecting to {self.broker_config['host']}:{self.broker_config['port']}")

            # Set username dan password jika ada
            if self.broker_config['username']:
                self.client.username_pw_set(
                    self.broker_config['username'],
                    self.broker_config['password']
                )

            # Connect ke broker
            self.client.connect(
                self.broker_config['host'],
                self.broker_config['port'],
                self.broker_config['keepalive']
            )

            # Start network loop di thread terpisah
            self.client.loop_start()

            # Tunggu sampai connected
            timeout = 10
            start_time = time.time()
            while not self.is_connected:
                if time.time() - start_time > timeout:
                    print("[MQTT] Connection timeout!")
                    return False
                time.sleep(0.1)

            return True

        except Exception as e:
            print(f"[MQTT] Connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect dari broker"""
        self.client.loop_stop()
        self.client.disconnect()
        print("[MQTT] Disconnected from broker")

    def publish(self, topic_key, data):
        """Publish data ke topik tertentu"""
        if not self.is_connected:
            print("[MQTT] Not connected to broker")
            return False

        try:
            # Get topic path dari konfigurasi
            topic_path = self.topics.get(topic_key)
            if not topic_path:
                print(f"[MQTT] Topic key '{topic_key}' not found in config")
                return False

            # Convert data ke JSON jika dictionary
            if isinstance(data, dict):
                payload = json.dumps(data)
            else:
                payload = str(data)

            # Publish message
            result = self.client.publish(topic_path, payload, qos=1)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"[MQTT] Published to {topic_path}: {payload}")
                return True
            else:
                print(f"[MQTT] Publish failed: {result.rc}")
                return False

        except Exception as e:
            print(f"[MQTT] Publish error: {e}")
            return False

    def get_message(self, timeout=1.0):
        """Ambil message dari queue"""
        try:
            return self.message_queue.get(timeout=timeout)
        except:
            return None

    def check_connection(self):
        """Cek status koneksi"""
        return self.is_connected

    def get_subscribed_topics(self):
        """Dapatkan list topik yang di-subscribe"""
        return self.subscribed_topics