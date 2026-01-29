##########################################
# Main example python script for AVDASI 2 AVIONICS
# Executes all other example scripts and runs a fully functional Ground Control Station (GCS)
# Author: Ethan Sheehan

# To run this file, you need to place other example scripts in the same folder and have the Cube properly configured
# Potential upgrades:
    # As you add your own scripts or additional functions, you will need to integrate them here

##########################################

# Import required python modules
import threading  # The threading module enables concurrent execution of different parts of the program

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
        time.sleep(0.05)
    return servo_config, mav

# Main function
def main():
    # Critical Fix 1: No longer manually create a tk.Tk() root window (handled by CustomTkinter's ServoUI)
    # Critical Fix 2: Restructure servo_config into a dictionary (to adapt to the index-based calling logic in the UI)
    servo_config, mav = setup_mav()
    # Convert to {1: ServoController1, 2: ServoController2,...8: ServoController8}
    servo_config_dict = {}
    if servo_config:
        for idx, ctrl in enumerate(servo_config, 1):
            servo_config_dict[idx] = ctrl

    # Critical Fix 3: When instantiating ServoUI, only pass servo_config (no longer pass root)
    app = UI_example.ServoUI(servo_config=servo_config_dict)

    # Start background listener if connected to Cube
    if mav is not None:
        threading.Thread(target=GS_example.listen_messages, args=(mav,), daemon=True).start()

    # Critical Fix 4: Call CustomTkinter's mainloop (instead of tk.Tk's mainloop)
    app.mainloop()

# Script entry point (run independently)
if __name__ == "__main__":
    main()