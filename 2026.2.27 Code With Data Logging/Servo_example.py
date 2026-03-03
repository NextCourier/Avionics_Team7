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

DEFAULT_SERVO_CONFIG = {
    "min_pwm": 950,
    "max_pwm": 2150,
    "trim_pwm": 1550,
    "reversed": False
}

def mav_bytes(string):
    return bytes(string, 'utf-8')

# --- Specialized Surface Classes ---

class Servo:
    def __init__(self, pin, min_pwm=950, max_pwm=2150, mirrored=False):
        self.pin = pin
        self.min = min_pwm
        self.max = max_pwm
        self.mirrored = mirrored

    def _prepare_angle(self, angle):
        if self.mirrored:
            return max(0, min(180, 180 - angle))
        return angle

    def _clamp(self, pwm):
        return max(self.min, min(self.max, int(pwm)))

    def angle_to_pwm(self, angle):
        a = self._prepare_angle(angle)
        return self._clamp((20/3) * a + 950)

class PortFlapServo(Servo):
    def angle_to_pwm(self, angle):
        a = self._prepare_angle(angle)
        return self._clamp(-7.19 * a + 1607)

class StarboardFlapServo(Servo):
    def angle_to_pwm(self, angle):
        a = self._prepare_angle(angle)
        return self._clamp(31.3 * a + 1205)

class ElevatorServo(Servo):
    def angle_to_pwm(self, angle):
        a = self._prepare_angle(angle)
        return self._clamp(10.78 * a + 1417)

class PortAileronServo(Servo):
    def angle_to_pwm(self, angle):
        a = self._prepare_angle(angle)
        # Add specific aileron math here
        return self._clamp((20/3) * a + 950)

class StarboardAileronServo(Servo):
    def angle_to_pwm(self, angle):
        a = self._prepare_angle(angle)
        return self._clamp((20/3) * a + 950)

class RudderServo(Servo):
    def angle_to_pwm(self, angle):
        a = self._prepare_angle(angle)
        return self._clamp((20/3) * a + 950)



class ServoController:
    def __init__(self, mav, servo_number, surface_type="default", mirrored=False):
        self.mav = mav
        self.servo_number = servo_number
        self.pin = SERVO_PINS[servo_number]
        
        surface_map = {
            "port_flap": PortFlapServo,
            "starboard_flap": StarboardFlapServo,
            "elevator": ElevatorServo,
            "port_aileron": PortAileronServo,
            "starboard_aileron": StarboardAileronServo,
            "rudder": RudderServo,
            "default": Servo
        }
        
        servo_class = surface_map.get(surface_type, Servo)
        self.servo = servo_class(self.pin, mirrored=mirrored)

    def get_pwm(self, angle):
        """Calculates PWM using the specialized class logic."""
        return self.servo.angle_to_pwm(angle)

    def write_servo_params(self):
        """Restored: Tells the Flight Controller the Min/Max PWM limits."""
        print(f"Setting parameters for Servo {self.servo_number}...")
        param_map = {
            "MAX": self.servo.max,
            "MIN": self.servo.min,
            "TRIM": 1500,
            "REVERSED": 0  # 0 because we handle 'mirrored' in Python now
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

    def send_angle(self, angle):
        """Sends a single servo move command."""
        pwm = self.get_pwm(angle)
        self.mav.mav.command_long_send(
            self.mav.target_system,
            self.mav.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
            0, self.pin, pwm, 0, 0, 0, 0, 0
        )
        return pwm

    def send_batch_angles(self, servo_angle_map):
        """Restored: Updates multiple servos at once (used in your main test loop)."""
        channels = [65535] * 8
        for servo_num, angle in servo_angle_map.items():
            # Note: This uses default math for the test loop. 
            # The UI uses the specialized controllers initialized in _init_controllers.
            temp_servo = Servo(SERVO_PINS[servo_num])
            channels[servo_num - 1] = int(temp_servo.angle_to_pwm(angle))

        self.mav.mav.rc_channels_override_send(
            self.mav.target_system,
            self.mav.target_component,
            *channels
        )  


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
