##########################################
# Main example python script for AVDASI 2 AVIONICS
# Executes all other example scripts and runs fully functional GCS
# Author: Ethan Sheehan

# To run this file you need the other example scripts in the same folder and have cube properly set up
# Potential upgrades:
# As you add your own scripts or additional functions you'll have to amend them in here
##########################################

# Import required Python modules
import tkinter as tk
import threading
import time  # Added for servo parameter write delay
import New_Ground
import New_UI
from Switch import SwitchController
import Servo_example_3Servo_Move as servo_module
from Attitude_Listening import AttitudeMonitor
import Arm_example
import data_Analysis


def setup_mav():
    """
    Initialize and validate MAVLink connection to flight controller
    Returns:
        mavutil.mavlink_connection: Validated MAVLink connection object, None if failed
    """
    mav = New_Ground.connect_to_cube()
    if mav is None:
        return None
    if not New_Ground.wait_heartbeat(mav):
        return None
    return mav


def main():
    # Initialize data logging module
    data_monitor = None
    try:
        data_monitor = data_Analysis.FlightDataMonitor('udpin:0.0.0.0:14550')
        data_monitor.start_monitoring()
        print("Data logging module initialized successfully")
    except Exception as e:
        print(f"Initial data logging error: {e}")

    # Initialize MAVLink connection to flight controller
    mav = setup_mav()
    if not mav:
        print("MAVLink connection failed - exiting program")
        return

    # Initialize 8-servo controllers (IDs 1-8)
    servo_controllers = {}
    try:
        # Create controller instances for all 8 servos
        for servo_num in range(1, 9):
            servo_controllers[servo_num] = servo_module.ServoController(mav, servo_num)

        # Write configuration parameters to each servo (with small delay to prevent overload)
        for servo_num in range(1, 9):
            servo_controllers[servo_num].write_servo_params()
            time.sleep(0.1)  # Prevent excessive frequency of parameter writes

        print("8-servo controllers initialized and parameters written successfully")
    except Exception as e:
        print(f"Servo initialization error: {e}")
        # Cleanup before exit
        if data_monitor:
            data_monitor.stop_monitoring()
        mav.close()
        return

    # Initialize attitude monitoring system
    try:
        attitude_monitor = AttitudeMonitor(mav)
        attitude_monitor.start()
        print("Attitude monitoring system initialized successfully")
    except Exception as e:
        print(f"Attitude monitor initialization error: {e}")
        # Cleanup before exit
        if data_monitor:
            data_monitor.stop_monitoring()
        mav.close()
        return

    # Initialize main UI (8-servo compatible)
    try:
        app = New_UI.ServoUI(servo_controllers)
        print("8-servo control UI initialized successfully")
    except Exception as e:
        print(f"UI initialization error: {e}")
        # Cleanup before exit
        attitude_monitor.stop()
        if data_monitor:
            data_monitor.stop_monitoring()
        mav.close()
        return

    # Start background monitoring threads
    try:
        # Start MAVLink message listening thread (daemon mode - auto-exits with main thread)
        threading.Thread(target=New_Ground.listen_messages, args=(mav,), daemon=True).start()

        # Start switch controller for hardware switch monitoring
        switch_ctrl = SwitchController(mav, servo_controllers)
        switch_ctrl.start()

        print("Background monitoring threads started successfully")
    except Exception as e:
        print(f"Monitor thread initialization error: {e}")

    # Run main UI event loop (blocks until UI is closed)
    try:
        app.mainloop()
    except KeyboardInterrupt:
        print("User interrupted program execution via keyboard (Ctrl+C)")
    finally:
        # Graceful shutdown of all modules
        print("Initiating graceful shutdown of all systems...")

        # Stop switch controller if initialized
        if 'switch_ctrl' in locals():
            switch_ctrl.stop()

        # Stop attitude monitoring
        attitude_monitor.stop()

        # Stop data logging and generate CSV report
        if data_monitor:
            data_monitor.stop_monitoring()
            data_Analysis.generate_csv_file()

        # Close MAVLink connection to flight controller
        mav.close()

        print("All systems shut down successfully - program exited cleanly")


if __name__ == "__main__":
    # Launch main program
    main()