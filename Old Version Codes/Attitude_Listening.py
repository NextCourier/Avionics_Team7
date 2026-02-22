##########################################
# Attitude Monitor for AVDASI 2 AVIONICS
# Real-time read roll/pitch/yaw from CubePilot
# Thread-safe data access
# Author: Modified based on Ethan Sheehan's code
##########################################

from pymavlink import mavutil
import threading
import time
import math


class AttitudeMonitor:
    def __init__(self, mav_connection):
        self.mav = mav_connection  # MAVLink连接实例
        self.running = False
        self.thread = None
        # initialise angles
        self._attitude = {
            "roll": 0.0,
            "pitch": 0.0,
            "yaw": 0.0,
            "timestamp": 0.0
        }
        self._lock = threading.Lock()

    def start(self):
        if not self.mav:
            raise ValueError("MAVLink connection not initialized")
        self.running = True
        self.thread = threading.Thread(target=self._monitor_attitude, daemon=True)
        self.thread.start()
        print("Attitude monitor started")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("Attitude monitor stopped")

    def _monitor_attitude(self):
        while self.running:
            try:
                # receive ATTITUDE message（100ms overtime）
                msg = self.mav.recv_match(type='ATTITUDE', blocking=True, timeout=0.1)
                if msg:
                    with self._lock:
                        # radius to angle（2 d.p.）
                        self._attitude['roll'] = round(msg.roll * 180 / math.pi, 2)
                        self._attitude['pitch'] = round(msg.pitch * 180 / math.pi, 2)
                        self._attitude['yaw'] = round(msg.yaw * 180 / math.pi, 2)
                        self._attitude['timestamp'] = msg.time_boot_ms
            except Exception as e:
                print(f"Attitude monitor error: {e}")
                time.sleep(0.1)

    def get_attitude(self):
        with self._lock:
            return self._attitude.copy()

    def get_attitude_str(self):
        att = self.get_attitude()
        return f"Roll: {att['roll']:.2f}°, Pitch: {att['pitch']:.2f}°, Yaw: {att['yaw']:.2f}°"


# for individual test
if __name__ == "__main__":
    mav = mavutil.mavlink_connection('udpin:0.0.0.0:14550')
    mav.wait_heartbeat()
    print(f"Heartbeat from system {mav.target_system}, component {mav.target_component}")

    monitor = AttitudeMonitor(mav)
    monitor.start()


    try:
        while True:
            print(monitor.get_attitude_str())
            time.sleep(0.5)
    except KeyboardInterrupt:
        monitor.stop()
        print("Test stopped")
