# test_data_sender.py - Send test data untuk dashboard
import json
import random
import time
import os
from mqtt.client import MqttClient


class StableSensorSimulator:
    """Simulate stable indoor sensor readings using a small random-walk + attraction to baseline.

    The model keeps internal state and on each update moves the value slightly towards the
    configured baseline while adding small Gaussian noise so the output looks realistic
    and stable over time.
    """

    def __init__(self, baseline, sigma=0.2, inertia=0.05, clamp=None):
        # baseline: float
        self.baseline = float(baseline)
        self.value = float(baseline)
        self.sigma = float(sigma)
        # inertia controls how quickly the value drifts back to baseline (0..1)
        self.inertia = float(inertia)
        # clamp: (min, max) tuple or None
        self.clamp = clamp

    def step(self):
        # small pull towards baseline + gaussian noise
        pull = (self.baseline - self.value) * self.inertia
        noise = random.gauss(0, self.sigma)
        self.value += pull + noise
        if self.clamp:
            self.value = max(self.clamp[0], min(self.clamp[1], self.value))
        return self.value


def load_baselines(config_path='config.json'):
    # default comfortable indoor values
    defaults = {
        'temperature': 24.0,
        'humidity': 50.0,
        'pressure': 1013.25
    }
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                cfg = json.load(f)
            # allow user to override under key 'simulator' or top-level keys
            sim = cfg.get('simulator', {}) if isinstance(cfg, dict) else {}
            return {
                'temperature': sim.get('temperature', cfg.get('temperature', defaults['temperature'])),
                'humidity': sim.get('humidity', cfg.get('humidity', defaults['humidity'])),
                'pressure': sim.get('pressure', cfg.get('pressure', defaults['pressure'])),
            }
        except Exception:
            return defaults
    return defaults


def send_test_data(interval=2.0, config_path='config.json'):
    """Send simulated stable sensor data to the MQTT broker at a regular interval.

    interval: seconds between publishes (default 2)
    """
    print("=== Test Data Sender (stable simulator) ===\n")

    mqtt_client = MqttClient(config_path)

    print("Connecting to broker...")
    if not mqtt_client.connect():
        print("Connection failed!")
        return

    print(f"Connected! Sending simulated data every {interval} seconds...\n")
    print("Press Ctrl+C to stop\n")

    baselines = load_baselines(config_path)

    # Create simulators with small noise and mild inertia so values remain stable
    temp_sim = StableSensorSimulator(baselines['temperature'], sigma=0.15, inertia=0.08, clamp=(10.0, 40.0))
    hum_sim = StableSensorSimulator(baselines['humidity'], sigma=0.6, inertia=0.06, clamp=(10.0, 100.0))
    pres_sim = StableSensorSimulator(baselines['pressure'], sigma=0.4, inertia=0.02, clamp=(950.0, 1050.0))

    try:
        counter = 0
        while True:
            counter += 1

            temperature = temp_sim.step()
            humidity = hum_sim.step()
            pressure = pres_sim.step()

            data = {
                'temperature': round(temperature, 1),
                'humidity': round(humidity, 1),
                'pressure': round(pressure, 1),
                'timestamp': int(time.time())
            }

            # Publish
            mqtt_client.publish('sensor_temp', data)

            print(f"[{counter}] Temp: {data['temperature']:.1f}°C, "
                  f"Humidity: {data['humidity']:.0f}%, "
                  f"Pressure: {data['pressure']:.1f} hPa")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\nTest data sender stopped")

    finally:
        mqtt_client.disconnect()


if __name__ == "__main__":
    send_test_data()