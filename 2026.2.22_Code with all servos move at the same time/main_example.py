##########################################
# Main example python script for AVDASI 2 AVIONICS
# Executes all other example scripts and runs a fully functional Ground Control Station (GCS)
##########################################
# Import required python modules
import threading

# Import other example code modules
import GS_example
import Servo_example
import UI_example
import time

# Setup function
def setup_mav():
    mav = GS_example.connect_to_cube()
    if mav is None:
        return None, None
    GS_example.wait_heartbeat(mav)
    # Create a list of controllers for servos 1 to 8
    servo_config = [Servo_example.ServoController(mav, i) for i in range(1, 9)]
    # Write parameters to each servo
    for controller in servo_config:
        controller.write_servo_params()
        time.sleep(0.1)
    return servo_config, mav

# Main function
def main():
    servo_config, mav = setup_mav()
    # Convert to {1: ServoController1, 2: ServoController2,...8: ServoController8}
    servo_config_dict = {}
    if servo_config:
        for idx, ctrl in enumerate(servo_config, 1):
            servo_config_dict[idx] = ctrl
    app = UI_example.ServoUI(servo_config=servo_config_dict)
    # Start background listener if connected to Cube
    if mav is not None:
        threading.Thread(target=GS_example.listen_messages, args=(mav,), daemon=True).start()
    app.mainloop()

# Script entry point (run independently)
if __name__ == "__main__":
    main()