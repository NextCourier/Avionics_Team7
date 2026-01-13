##########################################
#Main example python script for AVDASI 2 AVIONICS
#Executes all other example scripts and runs fully functional GCS
#Author: Ethan Sheehan

#To run this file you need the other example scripts in the same folder and have cube properly set up
#Potential upgrades:
    #As you add your own scripts or additionally functions you'll have to ammend them in here

##########################################

#import needed python modules
import tkinter as tk
import threading
import New_Ground
import New_UI
from Switch import SwitchController
import Servo_example_3Servo_Move as servo_module
from Attitude_Listening import AttitudeMonitor


def setup_mav():
    mav = New_Ground.connect_to_cube()
    if mav is None:
        return None
    if not New_Ground.wait_heartbeat(mav):
        return None
    return mav


def main():
    mav = setup_mav()
    if not mav:
        print("MAVLink connection failed, exit")
        return

    servo_controllers = {}
    try:
        servo_controllers[1] = servo_module.ServoController(mav)
        servo_controllers[2] = servo_module.ServoController1(mav)
        servo_controllers[3] = servo_module.ServoController2(mav)

        servo_controllers[1].write_servo_params()
        servo_controllers[2].write_servo_params1()
        servo_controllers[3].write_servo_params2()
    except Exception as e:
        print(f"Servo init error: {e}")
        return

    attitude_monitor = AttitudeMonitor(mav)
    attitude_monitor.start()


    app = New_UI.ServoUI(servo_controllers)


    try:

        threading.Thread(target=New_Ground.listen_messages, args=(mav,), daemon=True).start()

        switch_ctrl = SwitchController(mav, servo_controllers)
        switch_ctrl.start()
    except Exception as e:
        print(f"Monitor init error: {e}")


    try:
        app.mainloop()
    except KeyboardInterrupt:
        print("User stopped program")
    finally:
        if 'switch_ctrl' in locals():
            switch_ctrl.stop()
        attitude_monitor.stop()
        print("All modules stopped")


if __name__ == "__main__":
    main()