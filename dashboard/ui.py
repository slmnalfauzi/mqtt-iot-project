import tkinter as tk
from tkinter import ttk
import json
from datetime import datetime
import threading
from collections import deque
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

class DashboardUI:
    """
    Dashboard UI untuk monitoring data real-time
    """

    def __init__(self, mqtt_client, config_file='config.json'):
        """
        Inisialisasi dashboard
        """
        # Load konfigurasi
        with open(config_file, 'r') as f:
            config = json.load(f)

        self.config = config
        self.mqtt_client = mqtt_client

        # Root window
        self.root = tk.Tk()
        self.root.title(config['dashboard']['title'])
        self.root.geometry(f"{config['dashboard']['width']}x{config['dashboard']['height']}")
        self.root.resizable(True, True)

        # Data storage (untuk grafik)
        self.data_history = {
            'temperature': deque(maxlen=60),
            'humidity': deque(maxlen=60),
            'pressure': deque(maxlen=60)
        }
        self.graph_update_interval = 1000  # ms
        # Queue and counters for thread-safe communication
        self.msg_queue = deque()
        self.message_count = 0
        self.time_history = deque(maxlen=60)
        self._connection_flag = False

        # Current values
        self.current_values = {
            'temperature': 0.0,
            'humidity': 0.0,
            'pressure': 0.0,
            'led_status': 'OFF',
            'last_update': None
        }

        # Status tracking
        self.is_running = True
        self.connection_status = False
        # IDs for scheduled tkinter after callbacks (so we can cancel them on close)
        self._ui_after_id = None
        self._graph_after_id = None

        # Setup UI
        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.start_message_processor()
        self._ui_after_id = self.root.after(500, self.update_ui)

    # UI initialized

    def setup_ui(self):
        """
        Setup user interface
        """
    # Configure style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TFrame', background='#f7f7f7')
        self.style.configure('TLabel', background='#f7f7f7', foreground='#222831', font=("Segoe UI", 11))
        self.style.configure('TButton', font=("Segoe UI", 11, "bold"), background='#ffffff', foreground='#0078d7')
        self.style.configure('Led.TButton', font=("Segoe UI", 11, "bold"), background='#ffffff', foreground='#0078d7')
        self.style.configure('TLabelframe', background='#f7f7f7', foreground='#0078d7', font=("Segoe UI", 12, "bold"))
        self.style.configure('TLabelframe.Label', background='#f7f7f7', foreground='#0078d7', font=("Segoe UI", 12, "bold"))
        self.style.configure('Card.TFrame', background='#ffffff', relief='raised', borderwidth=2)
        self.style.configure('Card.TLabelframe', background='#ffffff', foreground='#0078d7', font=("Segoe UI", 12, "bold"), relief='raised', borderwidth=2)
        self.style.configure('Card.TLabelframe.Label', background='#ffffff', foreground='#0078d7', font=("Segoe UI", 12, "bold"))
       
        # 'background' controls the bar fill color in the 'clam' theme
        self.style.configure('Temp.Horizontal.TProgressbar', troughcolor='#e0e0e0', background='#43a047')
        self.style.configure('Hum.Horizontal.TProgressbar', troughcolor='#e0e0e0', background='#43a047')
        self.style.configure('Pres.Horizontal.TProgressbar', troughcolor='#e0e0e0', background='#1976d2')

        # Header frame
        header_frame = ttk.Frame(self.root, padding=10, style='Card.TFrame')
        header_frame.pack(fill=tk.X, padx=10, pady=(10,0))

        # Title (judul utama)
        title_label = ttk.Label(
            header_frame,
            text="ESP32 DHT11 Monitoring Dashboard",
            font=("Segoe UI", 22, "bold"),
            foreground="#1976d2",
            background="#ffffff"
        )
        title_label.pack(fill=tk.X, pady=(0,2))

        # Subjudul (nama dan NIM)
        sub_label = ttk.Label(
            header_frame,
            text="Salman Alfauzi Asngari | NIM: 2316050013",
            font=("Segoe UI", 12),
            foreground="#1976d2",
            background="#ffffff"
        )
        sub_label.pack(fill=tk.X, pady=(0,8))

        # Connection status bar (di bawah header)
        status_bar = ttk.Frame(self.root, padding=(10,2), style='Card.TFrame')
        status_bar.pack(fill=tk.X, padx=10, pady=(0,10))
        self.status_label = ttk.Label(
            status_bar,
            text="● Disconnected",
            font=("Segoe UI", 11),
            foreground="#ff3b3f",
            background="#ffffff"
        )
        self.status_label.pack(side=tk.LEFT)
        self.header_last_update_label = ttk.Label(
            status_bar,
            text="Last Update: --",
            font=("Segoe UI", 11),
            foreground="#222831",
            background="#ffffff"
        )
        self.header_last_update_label.pack(side=tk.LEFT, padx=20)

        # Main content frame
        self.main_frame = ttk.Frame(self.root, padding=0)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        self.main_frame.columnconfigure(0, weight=2)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        # Grafik suhu & kelembapan (kiri)
        self.graph_frame = ttk.Frame(self.main_frame, style='Card.TFrame', padding=20)
        self.graph_frame.grid(row=0, column=0, sticky="nsew", padx=(30,15), pady=30)
        self.graph_frame.columnconfigure(0, weight=1)
        self.graph_frame.rowconfigure(0, weight=1)

        self.fig = Figure(figsize=(8, 5), dpi=100)
        self.ax_temp = self.fig.add_subplot(211)
        self.ax_hum = self.fig.add_subplot(212)
        self.fig.subplots_adjust(hspace=0.6) 
        self.ax_temp.set_title("Grafik Suhu Real-time", fontsize=16, color="#ffffff", backgroundcolor="#1976d2", pad=20)
        self.ax_hum.set_title("Grafik Kelembaban Real-time", fontsize=16, color="#ffffff", backgroundcolor="#1976d2")
        self.ax_temp.set_facecolor('#f7f7f7')
        self.ax_hum.set_facecolor('#f7f7f7')
        self.ax_temp.tick_params(axis='x', colors='#1976d2')
        self.ax_temp.tick_params(axis='y', colors='#1976d2')
        self.ax_hum.tick_params(axis='x', colors='#1976d2')
        self.ax_hum.tick_params(axis='y', colors='#1976d2')
        self.ax_temp.set_ylabel("Suhu (°C)", fontsize=12, color="#1976d2")
        self.ax_hum.set_ylabel("Kelembaban (%)", fontsize=12, color="#1976d2")
        self.ax_temp.set_xlabel("Data Point", fontsize=12, color="#1976d2")
        self.ax_hum.set_xlabel("Time", fontsize=12, color="#1976d2")

        self.temp_line, = self.ax_temp.plot([], [], color="#ffa000", linewidth=2)
        self.temp_scatter = self.ax_temp.scatter([], [], c=[], cmap="RdYlGn", s=60)
        self.hum_line, = self.ax_hum.plot([], [], color="#1976d2", linewidth=2, marker='o')

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # Panel kanan: sensor, kontrol, status
        right_panel = ttk.Frame(self.main_frame, style='Card.TFrame', padding=20)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(15,30), pady=30)
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)
        right_panel.rowconfigure(1, weight=1)
        right_panel.rowconfigure(2, weight=1)

        # Sensor Data - Modern Card Style
        sensor_frame = ttk.Frame(right_panel, style='Card.TFrame', padding=0)
        sensor_frame.grid(row=0, column=0, sticky="ew", pady=(0,15))
        sensor_frame.columnconfigure(0, weight=1)

        # Temperature Card
        temp_card = ttk.Frame(sensor_frame, style='Card.TFrame', padding=15)
        temp_card.grid(row=0, column=0, sticky="ew", pady=5)
        temp_card.columnconfigure(0, weight=1)
        ttk.Label(temp_card, text="🌡️ Suhu", font=("Segoe UI", 14, "bold"), foreground="#ffa000", background="#ffffff").pack(anchor=tk.W)
        self.temp_value_label = ttk.Label(temp_card, text="--°C", font=("Segoe UI", 24, "bold"), foreground="#ffa000", background="#ffffff")
        self.temp_value_label.pack(anchor=tk.W, pady=(5,0))
        self.temp_status_label = ttk.Label(temp_card, text="", font=("Segoe UI", 11), foreground="#43a047", background="#ffffff")
        self.temp_status_label.pack(anchor=tk.W, pady=(2,0))

        # Optional progress bar for temperature
        self.temp_progress = ttk.Progressbar(temp_card, orient='horizontal', length=200, mode='determinate', maximum=50, style='Temp.Horizontal.TProgressbar')
        self.temp_progress.pack(anchor=tk.W, pady=(6,0), fill='x')

        # Humidity Card
        hum_card = ttk.Frame(sensor_frame, style='Card.TFrame', padding=15)
        hum_card.grid(row=1, column=0, sticky="ew", pady=5)
        hum_card.columnconfigure(0, weight=1)
        ttk.Label(hum_card, text="💧 Kelembapan", font=("Segoe UI", 14, "bold"), foreground="#1976d2", background="#ffffff").pack(anchor=tk.W)
        self.humidity_value_label = ttk.Label(hum_card, text="--%", font=("Segoe UI", 24, "bold"), foreground="#1976d2", background="#ffffff")
        self.humidity_value_label.pack(anchor=tk.W, pady=(5,0))
        self.humidity_status_label = ttk.Label(hum_card, text="", font=("Segoe UI", 11), foreground="#43a047", background="#ffffff")
        self.humidity_status_label.pack(anchor=tk.W, pady=(2,0))

        # Optional progress for humidity
        self.humidity_progress = ttk.Progressbar(hum_card, orient='horizontal', length=200, mode='determinate', maximum=100, style='Hum.Horizontal.TProgressbar')
        self.humidity_progress.pack(anchor=tk.W, pady=(6,0), fill='x')

        # Pressure Card
        pressure_card = ttk.Frame(sensor_frame, style='Card.TFrame', padding=15)
        pressure_card.grid(row=2, column=0, sticky="ew", pady=5)
        pressure_card.columnconfigure(0, weight=1)
        ttk.Label(pressure_card, text="🧭 Tekanan", font=("Segoe UI", 14, "bold"), foreground="#0078d7", background="#ffffff").pack(anchor=tk.W)
        self.pressure_value_label = ttk.Label(pressure_card, text="-- hPa", font=("Segoe UI", 24, "bold"), foreground="#0078d7", background="#ffffff")
        self.pressure_value_label.pack(anchor=tk.W, pady=(5,0))
        self.pressure_status_label = ttk.Label(pressure_card, text="", font=("Segoe UI", 11), foreground="#43a047", background="#ffffff")
        self.pressure_status_label.pack(anchor=tk.W, pady=(2,0))

        # Optional progress for pressure (scaled)
        self.pressure_progress = ttk.Progressbar(pressure_card, orient='horizontal', length=200, mode='determinate', maximum=1100, style='Pres.Horizontal.TProgressbar')
        self.pressure_progress.pack(anchor=tk.W, pady=(6,0), fill='x')

        # Device Control - Modern Card Style
        control_card = ttk.Frame(right_panel, style='Card.TFrame', padding=15)
        control_card.grid(row=1, column=0, sticky="ew", pady=(0,15))
        control_card.columnconfigure(0, weight=1)

        ttk.Label(control_card, text="💡 Kontrol Indikator LED", font=("Segoe UI", 14, "bold"), foreground="#c77dff", background="#ffffff").pack(anchor=tk.W)
        self.led_status_label = ttk.Label(control_card, text="Status: DISABLED", font=("Segoe UI", 12, "bold"), foreground="#ff3b3f", background="#ffffff")
        self.led_status_label.pack(anchor=tk.W, pady=(8,0))
        self.led_toggle_button = ttk.Button(control_card, text="ENABLE", command=self.toggle_led_indicator, style='Led.TButton')
        self.led_toggle_button.pack(anchor=tk.W, pady=(12,0), ipadx=20, ipady=8)

        # LED indicator status (color hint based on temperature)
        self.led_indicator_status = ttk.Label(control_card, text="Indikator: -", font=("Segoe UI", 11, "bold"), foreground="#888888", background="#ffffff")
        self.led_indicator_status.pack(anchor=tk.W, pady=(8,0))

        # Indikator LED info
        info_frame = ttk.Frame(control_card, style='Card.TFrame', padding=0)
        info_frame.pack(anchor=tk.W, pady=(15,0))
        ttk.Label(info_frame, text="Indikator LED:", font=("Segoe UI", 11, "bold"), foreground="#888888", background="#ffffff").pack(anchor=tk.W)
        ttk.Label(info_frame, text="RED: Suhu > 30°C", font=("Segoe UI", 10), foreground="#ff3b3f", background="#ffffff").pack(anchor=tk.W)
        ttk.Label(info_frame, text="YELLOW: Suhu 25-30°C", font=("Segoe UI", 10), foreground="#ffc107", background="#ffffff").pack(anchor=tk.W)
        ttk.Label(info_frame, text="GREEN: Suhu < 25°C", font=("Segoe UI", 10), foreground="#43a047", background="#ffffff").pack(anchor=tk.W)

        # System Status
        status_frame = ttk.LabelFrame(right_panel, text="System Status", padding=15, style='Card.TLabelframe')
        status_frame.grid(row=2, column=0, sticky="ew", pady=(0,0))
        self.last_update_label = ttk.Label(
            status_frame,
            text="Last update: --",
            font=("Segoe UI", 11)
        )
        self.last_update_label.pack(anchor=tk.W, padx=5)
        self.message_count_label = ttk.Label(
            status_frame,
            text="Messages received: 0",
            font=("Segoe UI", 11)
        )
        self.message_count_label.pack(anchor=tk.W, padx=5)
        self.broker_info_label = ttk.Label(
            status_frame,
            text=f"Broker: {self.config['broker']['host']}:{self.config['broker']['port']}",
            font=("Segoe UI", 11)
        )
        self.broker_info_label.pack(anchor=tk.W, padx=5)

        # Mulai update grafik (store id so we can cancel on close)
        self._graph_after_id = self.root.after(self.graph_update_interval, self.update_graph)
        # ensure matplotlib uses a non-interactive backend appropriate for embedding
        plt.tight_layout()

    def toggle_led_indicator(self):
        """
        Toggle LED indikator (enable/disable)
        """
        if self.current_values['led_status'] == 'OFF':
            self.mqtt_client.publish('led_indicator', {'action': 'enable'})
            self.current_values['led_status'] = 'ON'
            self.led_status_label.config(text="ON", foreground="#43a047")
            self.led_toggle_button.config(text="Disable LED Indikator", style='Led.TButton')
        else:
            self.mqtt_client.publish('led_indicator', {'action': 'disable'})
            self.current_values['led_status'] = 'OFF'
            self.led_status_label.config(text="OFF", foreground="#ff3b3f")
            self.led_toggle_button.config(text="Enable LED Indikator", style='Led.TButton')

    # Hapus tombol ON/OFF LED

    def update_sensor_display(self, topic, data):
        """
        Update display sensor data
        """
        try:
            # Temperature
            if 'temperature' in data:
                temp = float(data['temperature'])
                self.current_values['temperature'] = temp
                self.data_history['temperature'].append(temp)
                self.temp_value_label.config(text=f"{temp:.1f}°C")
                try:
                    self.temp_progress['value'] = temp
                    try:
                        if temp > 30:
                            self.style.configure('Temp.Horizontal.TProgressbar', background='#ff3b3f')
                        elif 25 <= temp <= 30:
                            self.style.configure('Temp.Horizontal.TProgressbar', background='#ffc107')
                        else:
                            self.style.configure('Temp.Horizontal.TProgressbar', background='#43a047')
                    except Exception:
                        pass
                except Exception:
                    pass

                # LED indicator based on temperature
                if temp > 30:
                    self.led_indicator_status.config(text="Indikator: Merah", foreground="#ff3b3f")
                elif temp >= 25:
                    self.led_indicator_status.config(text="Indikator: Kuning", foreground="#ffc107")
                else:
                    self.led_indicator_status.config(text="Indikator: Hijau", foreground="#43a047")

                # Enhanced interactive temperature message
                try:
                    if temp < 18:
                        self.temp_status_label.config(text="🥶 Sangat Dingin — Risiko embun/kerusakan; isolasi atau hangatkan area", foreground="#0d47a1")
                        self.temp_value_label.config(foreground="#0d47a1")
                    elif 18 <= temp < 25:
                        self.temp_status_label.config(text="❄️ Dingin — nyaman untuk penyimpanan, tapi perhatikan kenyamanan manusia", foreground="#2196f3")
                        self.temp_value_label.config(foreground="#2196f3")
                    elif 25 <= temp <= 30:
                        self.temp_status_label.config(text="🙂 Ideal — Suhu optimal untuk kenyamanan dan perangkat", foreground="#43a047")
                        self.temp_value_label.config(foreground="#43a047")
                    elif 30 < temp <= 33:
                        self.temp_status_label.config(text="🌤️ Hangat — Pastikan ventilasi dan sirkulasi udara", foreground="#ffb300")
                        self.temp_value_label.config(foreground="#ffb300")
                    else:
                        self.temp_status_label.config(text="🔥 Panas — Risiko overheat, aktifkan pendingin/kipas segera", foreground="#d32f2f")
                        self.temp_value_label.config(foreground="#d32f2f")
                except Exception:
                    pass

            # Humidity
            if 'humidity' in data:
                humidity = float(data['humidity'])
                self.current_values['humidity'] = humidity
                self.data_history['humidity'].append(humidity)
                self.humidity_value_label.config(text=f"{humidity:.0f}%")
                try:
                    self.humidity_progress['value'] = humidity
                    try:
                        if humidity < 30:
                            self.style.configure('Hum.Horizontal.TProgressbar', background='#2196f3')
                        elif 30 <= humidity < 60:
                            self.style.configure('Hum.Horizontal.TProgressbar', background='#43a047')
                        elif 60 <= humidity < 80:
                            self.style.configure('Hum.Horizontal.TProgressbar', background='#ff9800')
                        else:
                            self.style.configure('Hum.Horizontal.TProgressbar', background='#d32f2f')
                    except Exception:
                        pass
                except Exception:
                    pass

                try:
                    if humidity < 30:
                        self.humidity_status_label.config(text="Kelembapan: Kering — jaga kelembapan tanaman/udara", foreground="#2196f3")
                    elif 30 <= humidity < 60:
                        self.humidity_status_label.config(text="Kelembapan: Normal — kondisi nyaman", foreground="#43a047")
                    elif 60 <= humidity < 80:
                        self.humidity_status_label.config(text="Kelembapan: Lembap — waspadai kondensasi", foreground="#ff9800")
                    else:
                        self.humidity_status_label.config(text="Kelembapan: Sangat Lembap — risiko jamur/korosi", foreground="#d32f2f")
                except Exception:
                    pass

            # Pressure
            if 'pressure' in data:
                pressure = float(data['pressure'])
                self.current_values['pressure'] = pressure
                self.data_history['pressure'].append(pressure)
                self.pressure_value_label.config(text=f"{pressure:.1f} hPa")
                try:
                    self.pressure_progress['value'] = pressure
                    try:
                        if pressure < 1000:
                            self.style.configure('Pres.Horizontal.TProgressbar', background='#1976d2')
                        elif 1000 <= pressure < 1020:
                            self.style.configure('Pres.Horizontal.TProgressbar', background='#4caf50')
                        elif 1020 <= pressure < 1040:
                            self.style.configure('Pres.Horizontal.TProgressbar', background='#ffb300')
                        else:
                            self.style.configure('Pres.Horizontal.TProgressbar', background='#d32f2f')
                    except Exception:
                        pass
                except Exception:
                    pass

                try:
                    if pressure < 1000:
                        self.pressure_status_label.config(text="Tekanan: Rendah — kemungkinan cuaca buruk/berawan", foreground="#1976d2")
                    elif 1000 <= pressure < 1020:
                        self.pressure_status_label.config(text="Tekanan: Sedikit Rendah — awan/berubah-ubah", foreground="#4caf50")
                    elif 1020 <= pressure < 1040:
                        self.pressure_status_label.config(text="Tekanan: Normal/Tinggi — cenderung cerah", foreground="#ffb300")
                    else:
                        self.pressure_status_label.config(text="Tekanan: Sangat Tinggi — kondisi sangat stabil/cerah", foreground="#d32f2f")
                except Exception:
                    pass

            # Update last update time
            now = datetime.now().strftime("%H:%M:%S")
            self.current_values['last_update'] = now
            self.last_update_label.config(text=f"Last update: {now}")
            # append timestamp for plotting
            self.time_history.append(now)

            # Update LED button and status
            if 'led_status' in data:
                self.current_values['led_status'] = data['led_status']
                if data['led_status'] == 'ON':
                    self.led_status_label.config(text="ON", foreground="#43a047")
                    self.led_toggle_button.config(text="Disable LED Indikator", style='Led.TButton')
                else:
                    self.led_status_label.config(text="OFF", foreground="#ff3b3f")
                    self.led_toggle_button.config(text="Enable LED Indikator", style='Led.TButton')

        except Exception as e:
            print(f"[Dashboard] Error updating display: {e}")

    def update_graph(self):
        """
        Update grafik suhu dan kelembapan secara realtime
        """
        temp_data = list(self.data_history['temperature'])
        hum_data = list(self.data_history['humidity'])
        times = list(self.time_history)
        x = list(range(len(temp_data)))

        # Suhu: scatter warna
        colors = []
        for t in temp_data:
            if t > 30:
                colors.append('#ff3b3f') # merah
            elif t >= 25:
                colors.append('#ffc107') # kuning
            else:
                colors.append('#43a047') # hijau

        self.temp_line.set_data(x, temp_data)
        try:
            self.temp_scatter.remove()
        except Exception:
            pass
        self.temp_scatter = self.ax_temp.scatter(x, temp_data, c=colors, s=60, zorder=3)

        self.ax_temp.set_xlim(0, max(10, len(temp_data)))
        # autoscale y slightly around data
        if temp_data:
            ymin = min(temp_data) - 2
            ymax = max(temp_data) + 2
            self.ax_temp.set_ylim(ymin, ymax)
        else:
            self.ax_temp.set_ylim(15, 45)
        self.ax_temp.set_title("Grafik Suhu Real-time", fontsize=16, color="#ffffff", backgroundcolor="#1976d2")

        # Kelembaban: sumbu X berupa waktu
        if len(hum_data) > 0:
            # Ambil waktu dari last_update untuk setiap data
            time_labels = []
            # use available time_history labels (may be shorter than hum_data)
            for i in range(len(hum_data)):
                if i < len(times):
                    time_labels.append(times[i])
                else:
                    time_labels.append(str(i))
            self.hum_line.set_data(range(len(hum_data)), hum_data)
            self.ax_hum.set_xlim(-0.5, len(hum_data)-0.5)
            # reduce number of x-ticks for readability
            step = max(1, len(time_labels)//6)
            ticks = list(range(0, len(time_labels), step))
            if (len(time_labels)-1) not in ticks:
                ticks.append(len(time_labels)-1)
            self.ax_hum.set_xticks(ticks)
            self.ax_hum.set_xticklabels([time_labels[i] for i in ticks], rotation=45, fontsize=8)
        else:
            self.hum_line.set_data([], [])
            self.ax_hum.set_xlim(0, 1)
        self.ax_hum.set_ylim(40, 100)
        self.ax_hum.set_title("Grafik Kelembaban Real-time", fontsize=16, color="#ffffff", backgroundcolor="#1976d2")

        self.canvas.draw_idle()
        # keep updating graphs periodically (only if still running)
        if self.is_running and hasattr(self, 'root'):
            try:
                self._graph_after_id = self.root.after(self.graph_update_interval, self.update_graph)
            except Exception:
                # If scheduling fails because root was destroyed, just stop
                self._graph_after_id = None

    def process_messages(self):
        """
        Process incoming MQTT messages
        """
        # Background thread: read messages and put them into a thread-safe queue.
        while self.is_running:
            try:
                # check connection but don't touch GUI here
                try:
                    conn = self.mqtt_client.check_connection()
                except Exception:
                    conn = False
                self._connection_flag = conn

                msg = self.mqtt_client.get_message(timeout=0.5)
                if msg:
                    # enqueue for main thread to process
                    self.msg_queue.append(msg)
            except Exception as e:
                print(f"[Dashboard] Error reading messages: {e}")

        # end while

    def start_message_processor(self):
        """
        Mulai thread untuk process MQTT messages
        """
        thread = threading.Thread(target=self.process_messages, daemon=True)
        thread.start()

    def update_ui(self):
        """Main-thread UI updater: process queued messages and refresh status/labels."""
        try:
            # Connection status
            if self._connection_flag and not self.connection_status:
                self.connection_status = True
                self.status_label.config(text="● Connected", foreground="green")
            elif not self._connection_flag and self.connection_status:
                self.connection_status = False
                self.status_label.config(text="● Disconnected", foreground="#ff3b3f")

            # Process all queued messages
            while self.msg_queue:
                msg = self.msg_queue.popleft()
                self.message_count += 1
                topic = msg.get('topic', '')
                data = msg.get('data', {})
                # Update sensor display (this will append data_history and timestamps)
                self.update_sensor_display(topic, data)

            # Update message count label
            self.message_count_label.config(text=f"Messages received: {self.message_count}")

        except Exception as e:
            print(f"[Dashboard] Error in update_ui: {e}")
        finally:
            # Reschedule only if still running and root exists
            if self.is_running and hasattr(self, 'root'):
                try:
                    self._ui_after_id = self.root.after(500, self.update_ui)
                except Exception:
                    self._ui_after_id = None

    def on_close(self):
        """
        Cleanup when window is closed: cancel scheduled callbacks and stop background threads.
        """
        # Stop background loop
        self.is_running = False

        # Cancel scheduled after callbacks if present
        try:
            if getattr(self, '_ui_after_id', None):
                self.root.after_cancel(self._ui_after_id)
        except Exception:
            pass
        try:
            if getattr(self, '_graph_after_id', None):
                self.root.after_cancel(self._graph_after_id)
        except Exception:
            pass

        # Try to disconnect mqtt client gracefully
        try:
            self.mqtt_client.disconnect()
        except Exception:
            pass

        # Destroy the window
        try:
            self.root.destroy()
        except Exception:
            pass

    def get_data_history(self):
        """Return a copy of buffered data history for tests or external access."""
        return {k: list(v) for k, v in self.data_history.items()}

    def run(self):
        """Run the Tk main loop (blocking)."""
        try:
            self.root.mainloop()
        finally:
            # Ensure background loop is stopped
            self.is_running = False
            try:
                self.mqtt_client.disconnect()
            except Exception:
                pass
