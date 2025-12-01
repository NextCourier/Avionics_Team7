from pymavlink import mavutil
import time
import threading
import GS_example
import Servo_example_3Servo_Move

SWITCH_CHANNEL = 5
SWITCH_THRESHOLD = 1450
CONTROL_FREQUENCY = 0.1  # 10Hz


class SwitchController:
    def __init__(self, mav=None, servo_config=None):
        self.mav = mav  # receive mav from main
        self.servo_config = servo_config
        self.running = False  # control thread start/stop
        self.thread = None

    def start(self):
        # start switch thread
        if not self.mav or not self.servo_config:
            print("initialise MAV and servo fail, can't enable switch")
            return
        self.running = True
        self.thread = threading.Thread(target=self._monitor_switch, daemon=True)
        self.thread.start()
        print("start Switch thread")

    def stop(self):
        # stop switch thread
        self.running = False
        if self.thread:
            self.thread.join()
        print("Switch thread stop")

    def _monitor_switch(self):
        while self.running:
            try:
                switch_pos = self._get_switch_position()

                if switch_pos > SWITCH_THRESHOLD:
                    print("switch  to python control")
                    # using existing servo_config
                    self.servo_config.send_angle(1, 30)  # example: turn servo into 30 degree
                    # add more servo here
                else:
                    print("Controller control")

                time.sleep(CONTROL_FREQUENCY)

            except Exception as e:
                print(f"detection fault: {e}")
                time.sleep(CONTROL_FREQUENCY)

    def _get_switch_position(self):
        # request for channel data
        self.mav.mav.request_data_stream_send(
            self.mav.target_system,
            self.mav.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_ALL,
            1, 1
        )
        # receive channel data
        msg = self.mav.recv_match(type='RC_CHANNELS', blocking=True, timeout=1)
        if msg:
            channels = [msg.chan1_raw, msg.chan2_raw, msg.chan3_raw,
                        msg.chan4_raw, msg.chan5_raw, msg.chan6_raw]
            return channels[SWITCH_CHANNEL - 1]  # 通道从1开始，列表从0开始
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
            0  # backup parameter(0 if no need)
        )