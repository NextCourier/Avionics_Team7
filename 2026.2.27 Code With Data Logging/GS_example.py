##########################################
# Ground Station example python script for AVDASI 2 AVIONICS
# Update: Add the switch between USB connection and WIFI connection
##########################################

from pymavlink import mavutil
import time
import threading
import math

# Global connection status
global connection_status
connection_status = "disconnected"

status_lock = threading.Lock()
attitude_data = {
    "roll": 0.0,
    "pitch": 0.0,
    "yaw": 0.0,
    "timestamp": 0.0
}
attitude_lock = threading.Lock()

current_connection_type = "WIFI"

def connect_to_cube(connection_type="WIFI"):
    global current_connection_type

    print(f"Connecting via {connection_type}...")

    if connection_type == "WIFI":
        mav = mavutil.mavlink_connection('udp:0.0.0.0:15110')
    elif connection_type == "USB":
        # change the com number for different computers
        mav = mavutil.mavlink_connection('COM3', baud=115200)
    else:
        raise ValueError("Invalid connection type")

    current_connection_type = connection_type
    return mav

def wait_heartbeat(mav):
    """Wait for heartbeat from flight controller to confirm connection"""
    print("Waiting for heartbeat...")
    mav.wait_heartbeat()
    print(f"Heartbeat received from system {mav.target_system}, component {mav.target_component}")
    global connection_status
    connection_status = "connected"
    print("Status: connected")

def listen_messages(mav):
    global connection_status
    last_msg_time = time.time()
    timeout = 2
    ATTITUDE_TIMEOUT = 0.01
    SYS_STATUS_TIMEOUT = 0.005
    LOOP_SLEEP = 0.001

    while True:
        att_msg = mav.recv_match(
            type=['ATTITUDE'],
            blocking=False,
            timeout=ATTITUDE_TIMEOUT
        )
        if att_msg:
            with attitude_lock:
                # Direct calculation, reduce intermediate variables
                attitude_data['roll'] = round(att_msg.roll * 180 / math.pi, 2)
                attitude_data['pitch'] = round(att_msg.pitch * 180 / math.pi, 2)
                attitude_data['yaw'] = round(att_msg.yaw * 180 / math.pi, 2)
                attitude_data['timestamp'] = att_msg.time_boot_ms
            last_msg_time = time.time()  # Update last message time
        sys_msg = mav.recv_match(
            type=['SYS_STATUS'],
            blocking=False,
            timeout=SYS_STATUS_TIMEOUT
        )
        if sys_msg:
            last_msg_time = time.time()
            if connection_status != "connected":
                connection_status = "connected"

        # Connection timeout judgment
        if time.time() - last_msg_time > timeout:
            if connection_status != "disconnected":
                print("Connection lost. Status: disconnected")
                print("Heartbeat lost!")
            connection_status = "disconnected"
        time.sleep(LOOP_SLEEP)

# Get connection status
def get_connection_status():
    """Return current connection status to flight controller"""
    global connection_status
    return connection_status

def get_attitude():
    """Get latest attitude data with minimal lock contention"""
    with attitude_lock:
        return attitude_data.copy()

# Independent run test
if __name__ == "__main__":
    mav = connect_to_cube()
    wait_heartbeat(mav)

    def monitor_attitude_fps():
        """Count attitude data refresh rate (verify response time)"""
        last_time = time.time()
        count = 0
        while True:
            count += 1
            current_time = time.time()
            if current_time - last_time >= 1.0:
                fps = round(count / (current_time - last_time), 1)
                att = get_attitude()
                print(f"\nAttitude refresh rate: {fps} Hz | Angles: Roll={att['roll']}°, Pitch={att['pitch']}°, Yaw={att['yaw']}°")
                count = 0
                last_time = current_time
            time.sleep(0.01)

    # Start listening thread
    listener_thread = threading.Thread(target=listen_messages, args=(mav,))
    listener_thread.daemon = True
    listener_thread.start()

    # Start refresh rate monitoring thread
    fps_thread = threading.Thread(target=monitor_attitude_fps)
    fps_thread.daemon = True
    fps_thread.start()

    # Keep main thread running
    while True:
        time.sleep(1)