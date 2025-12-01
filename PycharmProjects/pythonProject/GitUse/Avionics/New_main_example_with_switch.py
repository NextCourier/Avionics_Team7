##########################################
#Main example python script for AVDASI 2 AVIONICS
#Executes all other example scripts and runs fully functional GCS
#Author: Ethan Sheehan

#To run this file you need the other example scripts in the same folder and have cube properly set up
#Potential upgrades:
    #As you add your own scripts or additionally functions you'll have to ammend them in here

##########################################

#import needed python modules
import threading
import GS_example
import UI_example
import Servo_example_3Servo_Move
import Switch


def setup_mav():
    mav = GS_example.connect_to_cube()
    if mav is None:
        return None, None
    GS_example.wait_heartbeat(mav)
    servo_config = Servo_example_3Servo_Move.ServoController(mav)
    servo_config.write_servo_params()
    return servo_config, mav


def main():
    # initialise MAV and servos
    servo_config, mav = setup_mav()

    # initialise UI
    app = UI_example.ServoUI(servo_config)

    # start MAV listening
    if mav is not None:
        threading.Thread(target=GS_example.listen_messages, args=(mav,), daemon=True).start()

        # initialise Switch and enable this part
        switch_controller = Switch.SwitchController(mav, servo_config)
        switch_controller.start()

    app.mainloop()

    # UI closed and stop Switch detect
    if 'switch_controller' in locals():
        switch_controller.stop()


if __name__ == "__main__":
    main()