##########################################
# Flight Data Logging & CSV Export
# Author: Ethan Sheehan
##########################################
from pymavlink import mavutil
import threading
import time
import math
import csv
import os
from datetime import datetime

# Global data buffer
data_buffer = []
buffer_lock = threading.Lock()


class FlightDataMonitor:
    def __init__(self, conn_str):
        self.mav = None
        self.conn_str = conn_str
        self.running = False
        self.thread = None
        self.init_mav_connection()

    def init_mav_connection(self):
        """Initialize MAVLink connection"""
        try:
            self.mav = mavutil.mavlink_connection(
                self.conn_str,
                source_system=1,
                source_component=1,
                mavlink20=True,
                autoreconnect=True
            )
            self.mav.wait_heartbeat(timeout=10)
            print(f"Data monitoring connected - System ID: {self.mav.target_system}, Component ID: {self.mav.target_component}")
        except Exception as e:
            raise ConnectionError(f"Flight controller connection failed: {str(e)}")

    def start_monitoring(self):
        """Start data monitoring"""
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print("Started recording flight controller data...")

    def stop_monitoring(self):
        """Stop data monitoring"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("Data recording stopped")

    def _monitor_loop(self):
        """Data monitoring loop"""
        while self.running:
            try:
                record = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    "roll": 0.0,
                    "pitch": 0.0,
                    "yaw": 0.0,
                    "rc_channels": {},
                    "servo_pwm": {}
                }

                # Read attitude data
                att_msg = self.mav.recv_match(type='ATTITUDE', blocking=False, timeout=0.05)
                if att_msg:
                    record["roll"] = round(att_msg.roll * 180 / math.pi, 2)
                    record["pitch"] = round(att_msg.pitch * 180 / math.pi, 2)
                    record["yaw"] = round(att_msg.yaw * 180 / math.pi, 2)

                # Read RC channels
                rc_msg = self.mav.recv_match(type='RC_CHANNELS', blocking=False, timeout=0.05)
                if rc_msg:
                    for ch in range(1, 11):
                        ch_val = getattr(rc_msg, f"chan{ch}_raw", 0)
                        if ch_val != 0:
                            record["rc_channels"][f"CH{ch}"] = ch_val

                # Read servo PWM values
                servo_msg = self.mav.recv_match(type='SERVO_OUTPUT_RAW', blocking=False, timeout=0.05)
                if servo_msg:
                    for servo_num in range(1, 9):
                        pwm_val = getattr(servo_msg, f"servo{servo_num}_raw", 0)
                        if pwm_val != 0:
                            record["servo_pwm"][f"servo_{servo_num}"] = pwm_val

                # Write to buffer
                with buffer_lock:
                    data_buffer.append(record)

                time.sleep(0.1)
            except Exception as e:
                print(f"Data recording exception: {str(e)}")
                time.sleep(0.5)


def generate_csv_file():
    """Generate CSV log file"""
    # Create log directory
    save_dir = "flight_data_logs"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # Generate file name
    file_name = f"flight_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    file_path = os.path.join(save_dir, file_name)

    # Check data
    with buffer_lock:
        if not data_buffer:
            print("No data to export")
            return

    # Write to CSV
    try:
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            # Build header
            header = ["timestamp", "roll", "pitch", "yaw"]
            all_rc = set()
            all_servo = set()

            with buffer_lock:
                for record in data_buffer:
                    all_rc.update(record["rc_channels"].keys())
                    all_servo.update(record["servo_pwm"].keys())

            header.extend(sorted(all_rc))
            header.extend(sorted(all_servo))
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()

            # Write data rows
            with buffer_lock:
                for record in data_buffer:
                    row = {
                        "timestamp": record["timestamp"],
                        "roll": record["roll"],
                        "pitch": record["pitch"],
                        "yaw": record["yaw"]
                    }
                    for ch in all_rc:
                        row[ch] = record["rc_channels"].get(ch, "")
                    for servo in all_servo:
                        row[servo] = record["servo_pwm"].get(servo, "")
                    writer.writerow(row)

        print(f"CSV log saved: {os.path.abspath(file_path)}")
    except Exception as e:
        print(f"CSV generation failed: {str(e)}")


if __name__ == "__main__":
    try:
        monitor = FlightDataMonitor('udpin:0.0.0.0:14550')
        monitor.start_monitoring()
        print("Press Ctrl+C to stop recording...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop_monitoring()
        generate_csv_file()
    except Exception as e:
        print(f"Program exception: {str(e)}")
