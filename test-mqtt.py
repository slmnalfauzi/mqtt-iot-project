# test_mqtt.py - Test MQTT client connection
import json
from mqtt.client import MqttClient
import time

def test_mqtt_connection():
    """Test koneksi MQTT"""
    print("=== MQTT Connection Test ===\n")

    # Inisialisasi client
    mqtt_client = MqttClient('config.json')

    # Test 1: Connection
    print("Test 1: Connecting to broker...")
    if mqtt_client.connect():
        print("✓ Connection successful\n")
    else:
        print("✗ Connection failed\n")
        return

    # Test 2: Check subscribed topics
    print("Test 2: Subscribed topics")
    topics = mqtt_client.get_subscribed_topics()
    for topic in topics:
        print(f"  ✓ {topic}")
    print()

    # Test 3: Publish test message
    print("Test 3: Publishing test message...")
    test_data = {
        'temperature': 25.5,
        'humidity': 60,
        'timestamp': int(time.time())
    }

    if mqtt_client.publish('sensor_temp', test_data):
        print("✓ Message published\n")
    else:
        print("✗ Publish failed\n")

    # Test 4: Receive messages
    print("Test 4: Listening for messages (10 seconds)...")
    start_time = time.time()
    message_count = 0

    while time.time() - start_time < 10:
        msg = mqtt_client.get_message(timeout=1.0)
        if msg:
            message_count += 1
            print(f"  Message {message_count}: {msg['topic']} = {msg['data']}")

    print(f"\n✓ Received {message_count} messages\n")

    # Test 5: Connection status
    print("Test 5: Connection status")
    if mqtt_client.check_connection():
        print("✓ Still connected\n")
    else:
        print("✗ Connection lost\n")

    # Cleanup
    mqtt_client.disconnect()
    print("=== Test Complete ===")

if __name__ == "__main__":
    test_mqtt_connection()