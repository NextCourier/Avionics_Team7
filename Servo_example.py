##########################################
# Servo control example python script for AVDASI 2 AVIONICS
##########################################

from pymavlink import mavutil
import time

SERVO_PINS = {
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 5,
    6: 6,
    7: 7,
    8: 8
}

def angle_to_pwm(angle):
    return (20/3) * angle + 950

def mav_bytes(string):
    # Convert string to MAVLink byte format
    return bytes(string, 'utf-8')

class Servo:
    def __init__(self, pin, min_pwm=950, max_pwm=2150, trim_pwm=1550, reversed=False, surface_type="port flap"):
        self.pin = pin 
        self.min = min_pwm
        self.max = max_pwm
        self.trim = trim_pwm
        self.reversed = reversed
        self.surface_type = surface_type 
    def angle_to_pwm(self, angle):
        
        if self.surface_type == "port flap":  #we could change this bit, im not sure if this is the best way to do this but u have to define each control surface
            pwm = -7.19* angle + 1607 
            
        elif self.surface_type == "+45 elevator":
            pwm=10.78*angle + 1417
            
        elif self.surface_type == "starboard":
            pwm = 1205 + 31.3*angle

        else:
            #Default formula
            pwm = (20/3) * angle + 950
            
        return max(self.min, min(self.max, int(pwm)))

class Servo:
    def __init__(self, pin, min_pwm=950, max_pwm=2150, trim_pwm=1550, reversed=False):
        self.pin = pin
        self.min = min_pwm
        self.max = max_pwm
        self.trim = trim_pwm
        self.reversed = reversed

    def angle_to_pwm(self, angle):
        pwm = angle_to_pwm(angle)
        return max(self.min, min(self.max, pwm))

    def reverse_angle(self, angle):
        # calculate the angle for servo2 to inverse
        reversed_angle = 180 - angle
        return max(0, min(180, reversed_angle))

class ServoController:
    def __init__(self, mav, servo_number):
        if not 1 <= servo_number <= 8:
            raise ValueError("Servo number must be between 1 and 8")
        self.mav = mav
        self.servo_number = servo_number
        self.pin = SERVO_PINS[servo_number]
        self.servo = Servo(self.pin)

    def write_servo_params(self):
        print(f"Setting parameters for Servo {self.servo_number}...")
        param_map = {
            "MAX": self.servo.max,
            "MIN": self.servo.min,
            "TRIM": self.servo.trim,
            "REVERSED": int(self.servo.reversed)
        }
        for key, value in param_map.items():
            self.mav.mav.param_set_send(
                self.mav.target_system,
                self.mav.target_component,
                mav_bytes(f"SERVO{self.pin}_{key}"),
                value,
                mavutil.mavlink.MAV_PARAM_TYPE_REAL32
            )
        time.sleep(0.05)
        print(f"Parameters set for Servo {self.servo_number} successfully")

    def send_angle(self, angle, method="servo"):
        if not 0 <= angle <= 180:
            raise ValueError("Angle must be between 0 and 180 degrees")
        pwm = self.servo.angle_to_pwm(angle)
        print(f"Servo {self.servo_number}: {angle}° → PWM {pwm}")

        if method == "servo":
            self.mav.mav.command_long_send(
                self.mav.target_system,
                self.mav.target_component,
                mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
                0,  # Confirmation
                self.pin,  # Servo pin
                pwm,  # PWM value
                0, 0, 0, 0, 0  # Unused parameters
            )

    def send_batch_angles(self, servo_angle_map):
        channels = [65535] * 8

        # logic of how servo1 and servo2 move inversely
        if 1 in servo_angle_map and 2 in servo_angle_map:
            base_angle = servo_angle_map[1]
            servo_angle_map[1] = base_angle
            servo_angle_map[2] = self.servo.reverse_angle(base_angle)
        for servo_num, angle in servo_angle_map.items():
            if not 1 <= servo_num <= 8:
                raise ValueError(f"servo{servo_num}out of range（1-8）")
            if not 0 <= angle <= 180:
                raise ValueError(f"servo{servo_num}angle{angle}out of range（0-180）")

            sub_servo = ServoController(self.mav, servo_num)
            pwm = sub_servo.servo.angle_to_pwm(angle)
            channels[servo_num - 1] = int(pwm)

        # send all channel data at the same time
        self.mav.mav.rc_channels_override_send(
            self.mav.target_system,
            self.mav.target_component,
            *channels
        )

        print("send batch angles：")
        for servo_num, angle in servo_angle_map.items():
            pwm = ServoController(self.mav, servo_num).servo.angle_to_pwm(angle)
            print(f"servo{servo_num}: {angle}° → PWM {pwm}")

def setup_mav():
    mav = mavutil.mavlink_connection('udp:0.0.0.0:15110')
    print("Waiting for heartbeat from flight controller...")
    mav.wait_heartbeat()
    print(f"Heartbeat received - System ID: {mav.target_system}, Component ID: {mav.target_component}")
    servo_number = 1  # Can be modified to any servo number from 1-8 as needed
    servo_controller = ServoController(mav, servo_number)
    servo_controller.write_servo_params()
    return servo_controller, mav

def main():
    try:
        # 1: Initialize single servo
        servo_config, mav = setup_mav()
        servo_config.send_angle(90)  # Send 90 degree command
        time.sleep(1)

        # test batch sending
        servo_config.send_batch_angles({1: 90, 2: 90, 3: 45})
        time.sleep(1)

        # 2: Initialize all 8 servos
        servo_controllers = [ServoController(mav, i) for i in range(1, 9)]
        for controller in servo_controllers:
            controller.write_servo_params()
            time.sleep(0.05)

        # Send test angles
        test_angles = [0, 10, 20, 30, 40, 50, 60, 70]
        for controller, angle in zip(servo_controllers, test_angles):
            controller.send_angle(angle)
            time.sleep(0.5)

        print("All servo commands sent successfully")
    except Exception as e:
        print(f"Error: {str(e)}")

# Test code
if __name__ == "__main__":
    main()