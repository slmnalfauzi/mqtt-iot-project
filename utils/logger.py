# utils/logger.py - Logging MQTT messages
import json
from datetime import datetime
import os

class MessageLogger:
    """Logger untuk MQTT messages"""

    def __init__(self, log_dir='logs'):
        """Inisialisasi logger"""
        self.log_dir = log_dir

        # Create directory jika belum ada
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # File untuk setiap topic
        self.log_files = {}

        print(f"[Logger] Initialized - log directory: {log_dir}")

    def get_log_filename(self, topic):
        """Get filename untuk topic"""
        # Sanitize topic name
        safe_topic = topic.replace('/', '_')
        date = datetime.now().strftime("%Y%m%d")

        return os.path.join(self.log_dir, f"{safe_topic}_{date}.log")

    def log_message(self, topic, data, timestamp=None):
        """Log message ke file"""
        try:
            if timestamp is None:
                timestamp = datetime.now().isoformat()

            # Create log entry
            log_entry = {
                'timestamp': timestamp,
                'topic': topic,
                'data': data
            }

            # Get or create file handle
            filename = self.get_log_filename(topic)

            # Append ke file
            with open(filename, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')

        except Exception as e:
            print(f"[Logger] Error: {e}")

    def read_logs(self, topic, date=None):
        """Read logs untuk topic tertentu"""
        if date is None:
            date = datetime.now().strftime("%Y%m%d")

        safe_topic = topic.replace('/', '_')
        filename = os.path.join(self.log_dir, f"{safe_topic}_{date}.log")

        logs = []
        try:
            with open(filename, 'r') as f:
                for line in f:
                    logs.append(json.loads(line))
        except FileNotFoundError:
            print(f"[Logger] Log file not found: {filename}")

        return logs