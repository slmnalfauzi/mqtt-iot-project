# utils/exporter.py - Export data ke CSV
import csv
from datetime import datetime
import json

class DataExporter:
    """Export MQTT data ke berbagai format"""

    @staticmethod
    def export_to_csv(logs, filename=None):
        """Export logs ke CSV file"""
        if filename is None:
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        try:
            with open(filename, 'w', newline='') as csvfile:
                # Get headers dari first entry
                if not logs:
                    print("No logs to export")
                    return False

                first_entry = logs[0]

                # Flatten data structure
                fieldnames = ['timestamp', 'topic']
                if isinstance(first_entry.get('data'), dict):
                    fieldnames.extend(first_entry['data'].keys())
                else:
                    fieldnames.append('value')

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                # Write rows
                for entry in logs:
                    row = {
                        'timestamp': entry['timestamp'],
                        'topic': entry['topic']
                    }

                    if isinstance(entry['data'], dict):
                        row.update(entry['data'])
                    else:
                        row['value'] = entry['data']

                    writer.writerow(row)

            print(f"[Exporter] Exported {len(logs)} records to {filename}")
            return True

        except Exception as e:
            print(f"[Exporter] Export failed: {e}")
            return False