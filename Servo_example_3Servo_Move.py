##########################################
# Servo control example python script for AVDASI 2 AVIONICS
# Defines which servo you want to move
# Converts given angle to PWM output servo needs that translates to that angle
# Sets maximum and minimum PWMs as well as the trim (0 angle PWM)
# Writes the new servo parameters
# Sends the wanted angle to the cube
# Author: Ethan Sheehan & Lucas Dick

# This file should be able to run independently
# Potential upgrades:
# Allow multiple servo movement simultaneously
# Calibrate to your own servos and mechanisms
# Checks/confirmation that servos did indeed move
##########################################

##########################################
# Servo Control Module
# Author: Ethan Sheehan & Lucas Dick
##########################################
from pymavlink import mavutil
import time

# Servo pin definitions (8 servos total)
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

# Default servo calibration parameters (adjust for your servos)
DEFAULT_SERVO_CONFIG = {
    "min_pwm": 950,
    "max_pwm": 2150,
    "trim_pwm": 1550,
    "reversed": False
}


def angle_to_pwm(angle):
    """Convert angle to PWM (calibrated for specific servos)"""
    return -19 * angle + 1550


def mav_bytes(string):
    """Convert string to MAVLink byte format"""
    return bytes(string, 'utf-8')


class Servo:
    """Servo configuration class"""

    def __init__(self, pin, min_pwm=DEFAULT_SERVO_CONFIG["min_pwm"],
                 max_pwm=DEFAULT_SERVO_CONFIG["max_pwm"],
                 trim_pwm=DEFAULT_SERVO_CONFIG["trim_pwm"], reversed=False):
        self.pin = pin
        self.min = min_pwm
        self.max = max_pwm
        self.trim = trim_pwm
        self.reversed = reversed

    def angle_to_pwm(self, angle):
        """Convert target angle to PWM value (with bounds checking)"""
        pwm = angle_to_pwm(angle)
        return max(self.min, min(self.max, pwm))


class ServoController:
    """Unified servo controller for 8 servos"""

    def __init__(self, mav, servo_number):
        """
        Initialize servo controller
        :param mav: MAVLink connection instance
        :param servo_number: Servo number (1-8)
        """
        if not 1 <= servo_number <= 8:
            raise ValueError("Servo number must be between 1 and 8")

        self.mav = mav
        self.servo_number = servo_number
        self.pin = SERVO_PINS[servo_number]
        self.servo = Servo(self.pin)

    def write_servo_params(self):
        """Write servo configuration parameters to flight controller"""
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

        time.sleep(0.1)
        print(f"Parameters set for Servo {self.servo_number} successfully")

    def send_angle(self, angle):
        """
        Send target angle to servo
        :param angle: Target angle (0-180 degrees)
        """
        if not 0 <= angle <= 180:
            raise ValueError("Angle must be between 0 and 180 degrees")

        pwm = self.servo.angle_to_pwm(angle)
        print(f"Servo {self.servo_number}: {angle}° → PWM {pwm}")

        self.mav.mav.command_long_send(
            self.mav.target_system,
            self.mav.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
            0,  # Confirmation
            self.pin,  # Servo pin
            pwm,  # PWM value
            0, 0, 0, 0, 0  # Unused parameters
        )


# Test code
if __name__ == "__main__":
    # Initialize MAVLink connection
    try:
        mav = mavutil.mavlink_connection('udp:0.0.0.0:14550')
        print("Waiting for heartbeat from flight controller...")
        mav.wait_heartbeat()
        print(f"Heartbeat received - System ID: {mav.target_system}, Component ID: {mav.target_component}")

        # Initialize controllers for all 8 servos
        servo_controllers = [ServoController(mav, i) for i in range(1, 9)]

        # Set parameters for all servos
        for controller in servo_controllers:
            controller.write_servo_params()
            time.sleep(0.2)  # Small delay between parameter writes

        # Send test angles to each servo (customize as needed)
        test_angles = [0, 10, 20, 30, 40, 50, 60, 70]  # Angles for servo 1-8
        for i, (controller, angle) in enumerate(zip(servo_controllers, test_angles)):
            controller.send_angle(angle)
            time.sleep(0.5)  # Delay between servo movements

        print("All servo commands sent successfully")

    except Exception as e:
        print(f"Error: {str(e)}")