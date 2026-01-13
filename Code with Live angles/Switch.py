from pymavlink import mavutil
import time
import threading
import GS_example
import Servo_example_3Servo_Move as servo_module

SWITCH_CHANNEL = 3
SWITCH_THRESHOLD = 1450
CONTROL_FREQUENCY = 0.1


class SwitchController:
    def __init__(self, mav=None, servo_controllers=None):
        self.mav = mav
        self.servo_controllers = servo_controllers  # 接收多舵机控制器字典
        self.running = False
        self.thread = None

    def start(self):
        if not self.mav or not self.servo_controllers:
            print("MAV Initialize failed")
            return
        self.running = True
        self.thread = threading.Thread(target=self._monitor_switch, daemon=True)
        self.thread.start()
        print("start the thread detect process")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        print("thread detect process stopping")

    def _monitor_switch(self):
        while self.running:
            try:
                switch_pos = self._get_switch_position()
                print(f"current CH{SWITCH_CHANNEL}value：{switch_pos}")

                if switch_pos > SWITCH_THRESHOLD:
                    print("→ python controlling")
                    self.servo_controllers[1].send_angle(0)
                    self.servo_controllers[2].send_angle_servo1(20)
                    self.servo_controllers[3].send_angle_servo2(30)
                else:
                    print("→ controller controlling")

                time.sleep(CONTROL_FREQUENCY)
            except Exception as e:
                print(f"switch detection fault：{e}")
                time.sleep(CONTROL_FREQUENCY)

    def _get_switch_position(self):
        if not self.mav:
            return 0
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
            print(f"TURNIGY X14 valid chanel：{valid_ch}")
            if 1 <= SWITCH_CHANNEL <= 10:
                return getattr(msg, f"chan{SWITCH_CHANNEL}_raw", 0)
            else:
                print(f"SWITCH_CHANNEL={SWITCH_CHANNEL} out of range")
                return 0
        else:
            print("not receive data from RC")
            return 0

    def send_manual_control(self, roll=1500, pitch=1500, throttle=1000, yaw=1500):
        if not self.mav:
            return
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