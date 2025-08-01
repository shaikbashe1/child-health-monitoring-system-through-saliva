import random
import time
import serial
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
from collections import deque
import sys

# Child-friendly pH classification
PH_LEVELS = {
    "Dragon Fire! 🔥": {
        "range": (0, 5.0),
        "advice": [
            "Drink water like a fish! 💧",
            "Crunch on veggies like a bunny! 🥕",
            "Say no to candy monsters! 🚫🍬"
        ],
        "color": "#FF0000",
        "emoji": "🔥",
        "face": "😫"
    },
    "Sour Lemon! 🍋": {
        "range": (5.0, 6.0),
        "advice": [
            "Banana power snacks! 🍌",
            "Cheese building blocks! 🧀",
            "Water adventures! 🚰"
        ],
        "color": "#FFA500",
        "emoji": "🍋",
        "face": "😖"
    },
    "Tangy Orange! 🍊": {
        "range": (6.0, 6.8),
        "advice": [
            "Apple crunch time! 🍎",
            "Milk magic potion! 🥛",
            "Super tooth brushing! 🪥"
        ],
        "color": "#FFD700",
        "emoji": "🍊",
        "face": "😕"
    },
    "Perfect Rainbow! 🌈": {
        "range": (6.8, 7.5),
        "advice": [
            "You're a health hero! 🦸",
            "Keep being awesome! 😎",
            "Water is your friend! 💧"
        ],
        "color": "#00FF00",
        "emoji": "🌈",
        "face": "😃"
    },
    "Bubble Trouble! 🫧": {
        "range": (7.5, 14),
        "advice": [
            "Nutty squirrel snacks! 🌰",
            "Water instead of juice! 💦",
            "Run and play outside! 🏃"
        ],
        "color": "#00BFFF",
        "emoji": "🫧",
        "face": "🤢"
    },
}

class RealSalivaMonitor:
    def __init__(self, serial_port='/dev/ttyUSB0', baud_rate=9600):
        # Initialize serial connection to sensor
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.ser = None
        self.connect_to_sensor()
        
        # Initialize data storage
        self.time_data = deque(maxlen=50)  # Store last 50 readings
        self.ph_data = deque(maxlen=50)
        self.start_time = time.time()
        self.last_reading_time = time.time()
        
        # Setup plot
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(10, 8))
        self.fig.suptitle("REAL-TIME SALIVA HEALTH MONITOR", fontsize=16, 
                         color='#FF6B8B', fontweight='bold')
        
        # Initialize plot elements
        self.line, = self.ax1.plot([], [], 'o-', color='royalblue', markersize=6)
        self.current_marker = self.ax1.scatter([], [], s=200)
        self.status_text = self.ax1.text(0.02, 0.95, '', transform=self.ax1.transAxes,
                                        fontsize=12, bbox=dict(facecolor='white', alpha=0.8))
        self.advice_text = self.ax2.text(0.5, 0.5, 'Initializing...', 
                                        ha='center', va='center', fontsize=14, wrap=True)
        
        # Configure plots
        self.configure_plots()
        
        # Initialize variables
        self.last_reading = None
        self.last_category = None
        self.consecutive_count = 0
        self.health_score = 100
        self.stars = 0
        self.sensor_errors = 0

    def connect_to_sensor(self):
        """Connect to pH sensor with error handling"""
        try:
            self.ser = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
            time.sleep(2)  # Allow connection to establish
            print(f"✅ Connected to sensor at {self.serial_port}")
            return True
        except (serial.SerialException, OSError) as e:
            print(f"❌ Sensor connection failed: {e}")
            print("⚠️ Using simulated data instead")
            self.ser = None
            return False

    def configure_plots(self):
        """Set up plot configurations"""
        # Main pH plot
        self.ax1.set_title("Real-time Saliva pH", fontsize=14)
        self.ax1.set_xlabel("Time (seconds)", fontsize=10)
        self.ax1.set_ylabel("pH Level", fontsize=10)
        self.ax1.set_ylim(4.0, 9.0)
        self.ax1.set_xlim(0, 60)  # Show last 60 seconds
        self.ax1.grid(True, linestyle='--', alpha=0.3)
        
        # Add healthy zone
        self.ax1.axhspan(6.8, 7.4, color='#98FB98', alpha=0.3, label='Healthy Zone')
        self.ax1.axhline(6.8, color='#2E8B57', linestyle='-', alpha=0.7)
        self.ax1.axhline(7.4, color='#2E8B57', linestyle='-', alpha=0.7)
        self.ax1.legend(loc='lower right', fontsize=9)
        
        # Configure advice panel
        self.ax2.axis('off')
        self.ax2.set_title("HEALTH ADVISOR", fontsize=14, color='purple')
        self.advice_box = plt.Rectangle((0.05, 0.05), 0.9, 0.9, 
                                       transform=self.ax2.transAxes,
                                       ec="green", fc="honeydew", 
                                       linewidth=2, alpha=0.8)
        self.ax2.add_patch(self.advice_box)
        
    def read_sensor(self):
        """Read actual pH value from hardware sensor"""
        # If we don't have a real sensor, use simulation
        if self.ser is None or not self.ser.is_open:
            return self.simulate_sensor_data()
        
        try:
            # Read from sensor
            self.ser.write(b'R')  # Send request for data
            response = self.ser.readline().decode('utf-8').strip()
            
            if response:
                return float(response)
            else:
                raise ValueError("Empty response from sensor")
                
        except (ValueError, serial.SerialException, UnicodeDecodeError) as e:
            self.sensor_errors += 1
            print(f"⚠️ Sensor error ({self.sensor_errors}/3): {e}")
            
            # After 3 errors, switch to simulation
            if self.sensor_errors >= 3:
                print("🔁 Switching to simulated data")
                self.ser = None
                
            return self.simulate_sensor_data()
    
    def simulate_sensor_data(self):
        """Generate simulated data when real sensor fails"""
        current_time = time.time()
        time_since_last = current_time - self.last_reading_time
        
        # Base value with slow drift
        base = 6.5 + 0.5 * np.sin(current_time / 30)
        
        # Add random fluctuations
        fluctuation = random.gauss(0, 0.2)
        
        # Simulate events based on time
        if time_since_last > 20 and random.random() < 0.1:
            # Simulate sugary drink (lowers pH)
            fluctuation -= random.uniform(1.0, 2.0)
        elif time_since_last > 40 and random.random() < 0.1:
            # Simulate healthy snack (raises pH)
            fluctuation += random.uniform(0.5, 1.0)
        
        ph = base + fluctuation
        
        # Ensure pH stays within reasonable bounds
        ph = max(4.0, min(9.0, ph))
        return round(ph, 2)

    def calibrate_sensor(self):
        """Perform sensor calibration sequence"""
        print("Starting calibration...")
        self.advice_text.set_text("Calibrating sensor... Please wait")
        
        # Only calibrate if we have a real sensor
        if self.ser and self.ser.is_open:
            try:
                # Send calibration command to sensor
                self.ser.write(b'CALIBRATE')
                
                # Wait for calibration to complete
                time.sleep(3)
                print("✅ Calibration complete!")
                self.advice_text.set_text("Calibration complete! Ready to monitor")
                return
            except serial.SerialException:
                print("⚠️ Calibration failed")
        
        # Simulate calibration
        print("🔁 Simulating calibration")
        time.sleep(2)
        print("✅ Simulated calibration complete")
        self.advice_text.set_text("Simulated calibration complete")

    def classify_ph(self, ph):
        """Categorize pH reading with child-friendly terms"""
        for name, data in PH_LEVELS.items():
            if data["range"][0] <= ph < data["range"][1]:
                return name, data
        return "Unknown", None
    
    def update_display(self, frame):
        """Update the display with new sensor data"""
        try:
            # Get sensor reading
            ph = self.read_sensor()
            current_time = time.time() - self.start_time
            
            # Add to data
            self.time_data.append(current_time)
            self.ph_data.append(ph)
            
            # Update plot
            self.line.set_data(self.time_data, self.ph_data)
            
            # Adjust x-axis to show most recent minute
            if current_time > 60:
                self.ax1.set_xlim(current_time - 60, current_time)
            
            # Classify pH
            category, data = self.classify_ph(ph)
            
            # Update health score
            if "Rainbow" in category:
                self.health_score = min(100, self.health_score + 1)
            else:
                self.health_score = max(0, self.health_score - 1)
                
            # Award stars for healthy readings
            if "Rainbow" in category and (time.time() - self.last_reading_time) > 5:
                self.stars += 1
                self.last_reading_time = time.time()
            
            # Check if category changed
            if category == self.last_category:
                self.consecutive_count += 1
            else:
                self.consecutive_count = 1
                self.last_category = category
            
            # Update status display
            status = (f"pH: {ph:.2f} {data['emoji']}\n"
                     f"Status: {category}\n"
                     f"Health Score: {self.health_score} | Stars: {'⭐' * min(5, self.stars)}")
            self.status_text.set_text(status)
            
            # Provide advice
            if self.consecutive_count >= 3:
                advice = random.choice(data['advice'])
                self.advice_text.set_text(advice)
                self.advice_text.set_color(data['color'])
            else:
                self.advice_text.set_text("Monitoring saliva health...")
                self.advice_text.set_color('black')
            
            # Update current marker
            if hasattr(self, 'current_marker'):
                self.current_marker.remove()
            self.current_marker = self.ax1.scatter(
                [current_time], [ph], s=200, c=data['color'], 
                edgecolors='black', zorder=3
            )
            
            # Add text annotation for significant changes (with None check)
            if (self.last_reading is not None and 
                abs(ph - self.last_reading) > 0.5 and 
                (current_time - self.last_reading_time) > 5):
                change = "↑↑" if ph > self.last_reading else "↓↓"
                self.ax1.text(
                    current_time, ph + 0.3, 
                    f"{change} {abs(ph - self.last_reading):.1f} change!",
                    fontsize=10, bbox=dict(facecolor='white', alpha=0.7)
                )
                self.last_reading = ph
            elif self.last_reading is None:
                self.last_reading = ph
                
            return self.line, self.status_text, self.advice_text, self.current_marker
        
        except Exception as e:
            print(f"⚠️ Critical error in update: {e}")
            # Return existing artists to keep animation alive
            return self.line, self.status_text, self.advice_text, self.current_marker
    
    def start_monitoring(self):
        """Start the real-time monitoring"""
        print("\n" + "="*60)
        print(" REAL-TIME SALIVA HEALTH MONITOR ".center(60, '❤️'))
        print("="*60)
        
        print("Hardware Status:")
        if self.ser and self.ser.is_open:
            print(f"- Connected to sensor at {self.ser.port}")
            print(f"- Baud rate: {self.ser.baudrate}")
        else:
            print("- Using simulated data")
        print("="*60)
        
        print("\nCalibrating sensor...")
        self.calibrate_sensor()
        time.sleep(2)
        
        print("\n✅ Monitoring started. Press Ctrl+C to stop\n")
        
        # Start animation
        self.ani = FuncAnimation(
            self.fig, 
            self.update_display, 
            interval=2000,  # Update every 2 seconds
            blit=False
        )
        
        plt.tight_layout()
        plt.subplots_adjust(top=0.9)
        plt.show()

    def __del__(self):
        """Clean up serial connection"""
        if hasattr(self, 'ser') and self.ser and self.ser.is_open:
            self.ser.close()
            print("✅ Serial connection closed")

# Start the monitoring system
if __name__ == "__main__":
    # Configure these based on your hardware setup
    SERIAL_PORT = '/dev/ttyUSB0'  # Change to your port (COM3 on Windows)
    BAUD_RATE = 9600
    
    print("\n" + "="*60)
    print(" CHILDREN'S SALIVA HEALTH MONITOR ".center(60, '⭐'))
    print("="*60)
    print("Designed for safe, non-invasive health monitoring")
    print("for children not eligible for injections")
    print("="*60)
    
    monitor = RealSalivaMonitor(serial_port=SERIAL_PORT, baud_rate=BAUD_RATE)
    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\n" + "="*60)
        print(" MONITORING STOPPED ".center(60, '❤️'))
        print("="*60)
        print(f"Final Health Score: {monitor.health_score}")
        print(f"Total Stars Earned: {monitor.stars}")
        print("\nKeep being a health hero every day! 👑")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        print("Please check your setup and try again")
        sys.exit(1)