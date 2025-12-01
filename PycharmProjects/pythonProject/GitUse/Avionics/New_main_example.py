##########################################
#Main example python script for AVDASI 2 AVIONICS
#Executes all other example scripts and runs fully functional GCS
#Author: Ethan Sheehan

#To run this file you need the other example scripts in the same folder and have cube properly set up
#Potential upgrades:
    #As you add your own scripts or additionally functions you'll have to ammend them in here

##########################################

#import needed python modules
import tkinter as tk #UI module
import threading # The threading module allows parts of the program to run concurrently

#Call other example codes
import GS_example
import Servo_example_3Servo_Move
import UI_example
import Switch
#Setup function
def setup_mav():
    mav = GS_example.connect_to_cube() #call connection function from GS example
    if mav is None: #No connection, return None
        return None, None
    GS_example.wait_heartbeat(mav) #call the heartbeat function from GS example
    servo_config = Servo_example_3Servo_Move.ServoController(mav) #call the servo configuration from Servo example
    servo_config.write_servo_params() #write the new servo parameters
    return servo_config, mav

#Main function
def main():
    # initialise MAVLINK connection and servo
    servo_config, mav = setup_mav()

    # （parameter give to servo_config directly，no need for tk.Tk()）
    app = UI_example.ServoUI(servo_config)

    # start listening process
    if mav is not None:
        threading.Thread(target=GS_example.listen_messages, args=(mav,), daemon=True).start()

    # Start main UI loop
    app.mainloop()

#Independence call
if __name__ == "__main__": #Ensures this script runs only when executed directly, not when imported
    main() #Calls the main function to start the ground station application