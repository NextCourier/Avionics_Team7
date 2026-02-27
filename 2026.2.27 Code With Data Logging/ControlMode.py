import time

class ControlModeManager:

    def __init__(self, mav, timeout=1.0):
        self.mav = mav
        self.current_mode = "RC"
        self.last_command_time = time.time()
        self.timeout = timeout

    # Switching mode
    def set_code_control(self):
        print("Switching to CODE control mode")
        self.current_mode = "CODE"
        self.last_command_time = time.time()

    def set_rc_control(self, reason="Manual"):
        print(f"Switching to RC control mode ({reason})")
        self.current_mode = "RC"

        # release override
        self.mav.mav.rc_channels_override_send(
            self.mav.target_system,
            self.mav.target_component,
            65535, 65535, 65535, 65535,
            65535, 65535, 65535, 65535
        )

    # Status detection
    def is_code_control(self):
        return self.current_mode == "CODE"

    def update_activity(self):
        self.last_command_time = time.time()

    def check_failsafe(self):
        if self.current_mode == "CODE":
            if time.time() - self.last_command_time > self.timeout:
                self.set_rc_control(reason="FAILSAFE")
                return True
        return False