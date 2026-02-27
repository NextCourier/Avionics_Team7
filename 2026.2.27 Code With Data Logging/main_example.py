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
import ControlMode
# Setup function
def setup_mav(connection_type="WIFI"):

    mav = GS_example.connect_to_cube(connection_type)
    if mav is None:
        return None, None

    GS_example.wait_heartbeat(mav)

    servo_config = [Servo_example.ServoController(mav, i) for i in range(1, 9)]

    for controller in servo_config:
        controller.write_servo_params()
        time.sleep(0.1)

    return servo_config, mav

# Main function
def main():

    connection_type = "WIFI"

    servo_config, mav = setup_mav(connection_type)

    control_manager = None
    if mav is not None:
        control_manager = ControlMode.ControlModeManager(mav)

    servo_config_dict = {}
    if servo_config:
        for idx, ctrl in enumerate(servo_config, 1):
            servo_config_dict[idx] = ctrl

    app = UI_example.ServoUI(
        servo_config=servo_config_dict,
        connection_type=connection_type,
        control_manager=control_manager
    )

    if mav is not None:
        threading.Thread(
            target=GS_example.listen_messages,
            args=(mav,),
            daemon=True
        ).start()

    app.mainloop()

# Script entry point (run independently)
if __name__ == "__main__":
    main()