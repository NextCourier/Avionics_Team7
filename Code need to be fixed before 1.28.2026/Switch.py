##########################################
# Switch Monitor Module
# Author: Ethan Sheehan
##########################################
from pymavlink import mavutil
import time
import threading

# Switch configuration
SWITCH_CHANNEL = 3
SWITCH_THRESHOLD = 1450
CONTROL_FREQUENCY = 0.05


class SwitchController:
    def __init__(self, mav=None, servo_controllers=None):
        self.mav = mav
        self.servo_controllers = servo_controllers or {}
        self.running = False
        self.thread = None

    def start(self):
        """Start switch monitoring thread"""
        if not self.mav or not self.servo_controllers:
            print("MAVLink not initialized - cannot start switch monitoring")
            return
        self.running = True
        self.thread = threading.Thread(target=self._monitor_switch, daemon=True)
        self.thread.start()
        print("Switch monitoring thread started successfully")

    def stop(self):
        """Stop switch monitoring thread"""
        self.running = False
        if self.thread:
            self.thread.join()
        print("Switch monitoring thread stopped successfully")

    def _monitor_switch(self):
        """Main loop for switch position monitoring"""
        while self.running:
            try:
                switch_pos = self._get_switch_position()
                print(f"Current CH{SWITCH_CHANNEL} value: {switch_pos}")

                if switch_pos > SWITCH_THRESHOLD:
                    print("→ Python control mode active")
                    self.servo_controllers[1].send_angle(0)
                    self.servo_controllers[2].send_angle_servo1(20)
                    self.servo_controllers[3].send_angle_servo2(30)
                else:
                    print("→ RC controller mode active")

                time.sleep(CONTROL_FREQUENCY)
            except Exception as e:
                print(f"Switch detection error: {e}")
                time.sleep(CONTROL_FREQUENCY)

    def _get_switch_position(self):
        """Retrieve current switch position from RC channel"""
        if not self.mav:
            return 0

        # Request RC channel data stream from flight controller
        self.mav.mav.request_data_stream_send(
            self.mav.target_system,
            self.mav.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_RC_CHANNELS,
            10, 1
        )

        msg = self.mav.recv_match(type='RC_CHANNELS', blocking=True, timeout=2)
        if msg:
            valid_ch = {f"CH{i}": getattr(msg, f"chan{i}_raw", 0) for i in range(1, 11) if
                        getattr(msg, f"chan{i}_raw", 0) != 0}
            print(f"Valid RC channels: {valid_ch}")
            return getattr(msg, f"chan{SWITCH_CHANNEL}_raw", 0) if 1 <= SWITCH_CHANNEL <= 10 else 0
        else:
            print("No RC channel data received")
            return 0

    def send_manual_control(self, roll=1500, pitch=1500, throttle=1000, yaw=1500):
        """Send manual RC control commands to flight controller"""
        if not self.mav:
            return

        # Limit PWM values to valid range (1000-2000)
        roll = max(1000, min(2000, roll))
        pitch = max(1000, min(2000, pitch))
        throttle = max(1000, min(2000, throttle))
        yaw = max(1000, min(2000, yaw))

        self.mav.mav.manual_control_send(
            self.mav.target_system,
            roll,
            pitch,
            throttle,
            yaw,
            0
        )