# main.py - Main application launcher
import sys
import time
from mqtt.client import MqttClient
from dashboard.ui import DashboardUI

def main():
    """Main application function"""
    print("="*50)
    print("IoT MQTT Dashboard - Startup")
    print("="*50)

    try:
        # Step 1: Initialize MQTT Client
        print("\n[STARTUP] Initializing MQTT Client...")
        mqtt_client = MqttClient('config.json')

        # Step 2: Connect to MQTT Broker
        print("[STARTUP] Connecting to MQTT Broker...")
        if not mqtt_client.connect():
            print("[ERROR] Failed to connect to MQTT broker!")
            print("Make sure mosquitto broker is running on the configured host")
            print(f"Check config.json for broker settings")
            return False

        print("[SUCCESS] Connected to MQTT Broker")
        time.sleep(1)

        # Step 3: Initialize Dashboard
        print("[STARTUP] Initializing Dashboard UI...")
        dashboard = DashboardUI(mqtt_client, 'config.json')

        print("[SUCCESS] Dashboard initialized")
        print("\n" + "="*50)
        print("Dashboard running - waiting for sensor data...")
        print("="*50 + "\n")

        # Step 4: Run Dashboard
        dashboard.run()

    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Application interrupted by user")

    except Exception as e:
        print(f"\n[ERROR] Application error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("[SHUTDOWN] Cleaning up resources...")
        try:
            mqtt_client.disconnect()
        except:
            pass
        print("[SHUTDOWN] Application stopped")

if __name__ == "__main__":
    main()