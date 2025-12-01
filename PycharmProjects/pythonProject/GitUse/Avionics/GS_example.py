##########################################
#Ground Station example python script for AVDASI 2 AVIONICS
#Connects to cube
#Finds heartbeat
#Listens for wanted cube messages
#flags heartbeat disconnection
#Author: Ethan Sheehan

#This file should be able to run independently
#Potential upgrades:
    #Choose which messages you want to listen for
    #Speed up/opptimize process
    #integrate messages into UI

##########################################

from pymavlink import mavutil
import time
import threading
import sys
import socket  # for detect cube+ via UDP channel
# import GS_example
connection_status = "disconnected"
status_lock = threading.Lock()


def connect_to_cube():
    print("Connecting to CubePilot via UDP...")
    try:
        # create UDP channel
        mav = mavutil.mavlink_connection('udpin:0.0.0.0:14550')
        # check UDP channel valid or not
        if not check_udp_socket_status(mav):
            print("UDP initialise failed")
            return None
        return mav
    except Exception as e:
        print(f"can't connect to cube+: {e}")
        return None


def check_udp_socket_status(mav):
    try:
        # get pymavlink state
        udp_socket = mav.port
        if not isinstance(udp_socket, socket.socket):
            print("no valid UDP channel detected")
            return False

        # check the channel live or not
        udp_socket.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)  # check sending area cache
        udp_socket.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)  # check receiving area cache
        return True
    except socket.error as e:
        print(f"UDP basic connection create failed: {e}")
        return False
    except Exception as e:
        print(f"UDP state failed: {e}")
        return False



def wait_heartbeat(mav):
    if not mav:
        print("Cube+ not detected")
        return False
    print("Waiting for heartbeat...")
    try:
        # wait for heartbeat, timeout 10 seconds
        msg = mav.wait_heartbeat(timeout=10)
        if not msg:
            print("no heartbeat received")
            return False

        # 核心修改：用 getattr 安全获取属性，不存在则返回默认值 0（保留验证逻辑）
        system_id = getattr(msg, 'system', 0)
        component_id = getattr(msg, 'component', 0)

        # validate heartbeat state
        if system_id == 0 or component_id == 0:
            print(f"connected from system：system {system_id}, component {component_id}")
            return False

        # heartbeat valid, start to give further message
        print(f"Heartbeat received from system {system_id}, component {component_id}")
        with status_lock:
            global connection_status
            connection_status = "connected"
        print("Status: connected")
        return True
    except Exception as e:
        print(f"fail to wait for heartbeat: {e}")
        return False


def listen_messages(mav, max_timeout=5):
    if not mav:
        print("no cube+ detected, can't start listening system")
        sys.exit(1)
    global connection_status
    last_msg_time = time.time()
    heartbeat_count = 0
    last_print_time = time.time()  # time for last print
    print_interval = 1  # time offset for print
    normal_timeout = 2
    udp_check_interval = 1
    last_udp_check_time = time.time()
    while True:
        # check UDP connection regularly
        if time.time() - last_udp_check_time > udp_check_interval:
            if not check_udp_socket_status(mav):
                print("UDP connection stopped")
                sys.exit(1)
            last_udp_check_time = time.time()
        # listening to cube+ message
        msg = mav.recv_match(type=['SYS_STATUS', 'HEARTBEAT'], timeout=1)
        with status_lock:
            if msg:
                last_msg_time = time.time()
                # find heartbeat, start to print message
                if msg.get_type() == 'HEARTBEAT':
                    system_id = getattr(msg, 'system', 0)
                    component_id = getattr(msg, 'component', 0)
                    if system_id != 0 and component_id != 0:
                        heartbeat_count += 1
                        # add offset to avoid huge amount of output
                        if time.time() - last_print_time >= print_interval:
                            print(f"heartbeat counter: {heartbeat_count} | system ID: {system_id}, component ID: {component_id}")
                            last_print_time = time.time()
                if connection_status != "connected":
                    connection_status = "connected"
                    print("Connected to flight controller (message received)")
            else:
                # timeout in case of no message hearing
                if time.time() - last_msg_time > normal_timeout:
                    if connection_status != "disconnected":
                        connection_status = "disconnected"
                        print("Temporarily disconnected (no messages received)")
        # due with lone time no message
        if time.time() - last_msg_time > max_timeout:
            print(f"Fatal: No messages received for {max_timeout} seconds. Stopping program.")
            sys.exit(1)
        time.sleep(0.1)




if __name__ == "__main__":
    # connect to cube then check the state
    mav = connect_to_cube()
    if not mav:
        sys.exit(1)

    # wait for heartbeat
    if not wait_heartbeat(mav):
        sys.exit(1)

    # listening message via only one thread
    threading.Thread(
        target=listen_messages,
        args=(mav,),
        daemon=True
    ).start()

    # makesure main thread still working
    while True:
        time.sleep(1)