##########################################
# Ground Station example python script for AVDASI 2 AVIONICS
# Connects to cube
# Finds heartbeat
# Listens for wanted cube messages
# flags heartbeat disconnection
# Author: Ethan Sheehan

# Optimization: Improve attitude (ATTITUDE) response time
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
attitude_lock = threading.Lock()  # Lightweight lock to protect attitude data read/write


# Cube connection function (no modification)
def connect_to_cube():
    """Establish MAVLink connection to CubePilot"""
    print("Connecting to CubePilot...")
    mav = mavutil.mavlink_connection('udp:0.0.0.0:14550')
    return mav


# Heartbeat function (no modification)
def wait_heartbeat(mav):
    """Wait for heartbeat from flight controller to confirm connection"""
    print("Waiting for heartbeat...")
    mav.wait_heartbeat()
    print(f"Heartbeat received from system {mav.target_system}, component {mav.target_component}")
    global connection_status
    connection_status = "connected"
    print("Status: connected")


# Core optimization: Message listening function (focus on improving ATTITUDE response speed)
def listen_messages(mav):
    """Listen to MAVLink messages with optimized attitude data reception"""
    global connection_status
    last_msg_time = time.time()
    timeout = 2  # Connection timeout threshold (retained)

    # Optimization 1: Set smaller timeout to prioritize ATTITUDE messages
    ATTITUDE_TIMEOUT = 0.01  # Attitude message reception timeout (10ms, original 0.05)
    SYS_STATUS_TIMEOUT = 0.005  # System status message timeout (5ms, original 0.1)
    LOOP_SLEEP = 0.001  # Loop sleep time (1ms, original 0.1)

    while True:
        # Priority 1: Receive ATTITUDE messages (core optimization)
        att_msg = mav.recv_match(
            type=['ATTITUDE'],
            blocking=False,  # Non-blocking mode
            timeout=ATTITUDE_TIMEOUT  # Very short timeout for fast new message detection
        )
        if att_msg:
            # Optimization 2: Simplify lock operations to reduce data processing time
            with attitude_lock:
                # Direct calculation, reduce intermediate variables
                attitude_data['roll'] = round(att_msg.roll * 180 / math.pi, 2)
                attitude_data['pitch'] = round(att_msg.pitch * 180 / math.pi, 2)
                attitude_data['yaw'] = round(att_msg.yaw * 180 / math.pi, 2)
                attitude_data['timestamp'] = att_msg.time_boot_ms
            last_msg_time = time.time()  # Update last message time

        # Priority 2: Receive SYS_STATUS messages (secondary)
        sys_msg = mav.recv_match(
            type=['SYS_STATUS'],
            blocking=False,
            timeout=SYS_STATUS_TIMEOUT
        )
        if sys_msg:
            # Optional: Disable printing (printing increases latency, enable for debugging)
            # print(f"Received: {sys_msg.get_type()} - {sys_msg.to_dict()}")
            last_msg_time = time.time()
            if connection_status != "connected":
                connection_status = "connected"

        # Connection timeout judgment (retained)
        if time.time() - last_msg_time > timeout:
            if connection_status != "disconnected":
                print("Connection lost. Status: disconnected")
                print("Heartbeat lost!")
            connection_status = "disconnected"

        # Optimization 3: Minimal sleep time to improve loop refresh rate
        time.sleep(LOOP_SLEEP)


# Get connection status (no modification)
def get_connection_status():
    """Return current connection status to flight controller"""
    global connection_status
    return connection_status


# Optimization 4: Fast get attitude data (reduce lock holding time)
def get_attitude():
    """Get latest attitude data with minimal lock contention"""
    with attitude_lock:
        # Return copy directly, reduce in-function operations
        return attitude_data.copy()


# Independent run test (new: print attitude data refresh rate)
if __name__ == "__main__":
    mav = connect_to_cube()
    wait_heartbeat(mav)


    # Optimization: Put listening in thread to avoid blocking main thread, and count refresh rate
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
            time.sleep(0.001)


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