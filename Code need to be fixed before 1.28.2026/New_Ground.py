from pymavlink import mavutil
import time
import threading
import sys
import socket
import math


connection_status = "disconnected"
status_lock = threading.Lock()

attitude_data = {
    "roll": 0.0,
    "pitch": 0.0,
    "yaw": 0.0,
    "timestamp": 0.0
}
attitude_lock = threading.Lock()


def connect_to_cube(udp_port=14550, target_ip=None, target_port=14551):


    if not target_ip:
        conn_str = f'udp:0.0.0.0:{udp_port}'
        print(f"\n[CONNECT] start UDP listening: {conn_str}")

    else:
        conn_str = f'udp:{target_ip}:{target_port}'
        print(f"\n[CONNECT] UDP connecting : {conn_str}")

    try:
        mav = mavutil.mavlink_connection(
            conn_str,
            source_system=1,
            source_component=1,
            mavlink20=True,
            autoreconnect=True
        )


        if not check_udp_socket_status(mav):
            print("[ERROR] UDP initialise failed")
            return None

        print("[CONNECT] UDP initialised successfully")
        return mav
    except Exception as e:
        print(f"[ERROR] UDP connection failed: {str(e)}")
        return None


def check_udp_socket_status(mav):
    try:
        udp_socket = mav.port
        if not isinstance(udp_socket, socket.socket):
            return False


        udp_socket.settimeout(1.0)
        udp_socket.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
        udp_socket.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
        return True
    except (socket.error, AttributeError):
        return False



def wait_heartbeat(mav, timeout=15):

    if not mav:
        print("[HEARTBEAT] UDP channel not found")
        return False

    print(f"[HEARTBEAT] waiting for heartbeat（timeout {timeout}seconds）...")
    try:
        msg = mav.wait_heartbeat(timeout=timeout)
        if not msg:
            print("[HEARTBEAT] timeout triggered （check Cube!）")
            return False

        system_id = getattr(msg, 'system', 0)
        component_id = getattr(msg, 'component', 0)

        if system_id == 0 or component_id == 0:
            print(f"[WARNING] invalid heartbeat: system={system_id}, component={component_id}（继续运行）")
        else:
            print(f"[HEARTBEAT] Heartbeat received: system={system_id}, component={component_id}")
        with status_lock:
            global connection_status
            connection_status = "connected"
        print("[HEARTBEAT] Connected")
        return True

    except Exception as e:
        print(f"[ERROR] Heartbeat detection failed: {str(e)}")
        return False


def listen_messages(mav, max_timeout=30, normal_timeout=8):

    if not mav:
        print("[LISTENER] No valid UDP connection")
        return

    global connection_status
    last_msg_time = time.time()
    heartbeat_count = 0
    last_print_time = time.time()
    udp_check_interval = 2

    print("[LISTENER] Start UDP listening...")
    while True:

        if time.time() - last_print_time > udp_check_interval:
            if not check_udp_socket_status(mav):
                print("[WARNING] UDP Connection failed, try to re-connecting...")
                conn_str = mav.address
                mav.close()
                mav = mavutil.mavlink_connection(conn_str, mavlink20=True)
                time.sleep(1)
                continue
            last_print_time = time.time()


        msg = mav.recv_match(type=['SYS_STATUS', 'HEARTBEAT', 'ATTITUDE'], timeout=1)

        with status_lock:
            if msg:
                last_msg_time = time.time()

                if msg.get_type() == 'ATTITUDE':
                    with attitude_lock:
                        attitude_data['roll'] = round(msg.roll * 180 / math.pi, 2)
                        attitude_data['pitch'] = round(msg.pitch * 180 / math.pi, 2)
                        attitude_data['yaw'] = round(msg.yaw * 180 / math.pi, 2)
                        attitude_data['timestamp'] = msg.time_boot_ms

                if msg.get_type() == 'HEARTBEAT':
                    heartbeat_count += 1
                    if time.time() - last_print_time >= 2:
                        print(f"[STATUS] Heartbeat counter: {heartbeat_count} | Connection status: {connection_status}")
                        last_print_time = time.time()

                if connection_status != "connected":
                    connection_status = "connected"
                    print("[LISTENER] UDP successfully reconnected")

            else:
                if time.time() - last_msg_time > normal_timeout:
                    if connection_status != "disconnected":
                        connection_status = "disconnected"
                        print("[WARNING] UDP connection lost")

        if time.time() - last_msg_time > max_timeout:
            print(f"[WARNING] {max_timeout} seconds haven't hear heartbeat from Cube, still try to hearing...")
            last_msg_time = time.time()

        time.sleep(0.1)



def get_attitude():
    with attitude_lock:
        return attitude_data.copy()


def get_connection_status():
    with status_lock:
        return connection_status



if __name__ == "__main__":

    UDP_LOCAL_PORT = 14550
    UDP_TARGET_IP = None
    UDP_TARGET_PORT = 14551


    mav_conn = connect_to_cube(
        udp_port=UDP_LOCAL_PORT,
        target_ip=UDP_TARGET_IP,
        target_port=UDP_TARGET_PORT
    )
    if not mav_conn:
        sys.exit(1)


    if not wait_heartbeat(mav_conn):
        print("[TEST] Listening to Heartbeat...")


    listen_thread = threading.Thread(
        target=listen_messages,
        args=(mav_conn,),
        daemon=True
    )
    listen_thread.start()

    print("\n[TEST] Print angles（UDP mode | quit with Ctrl+C）...")
    try:
        while True:
            if get_connection_status() == "connected":
                att = get_attitude()
                print(f"[ATTITUDE] Roll: {att['roll']:6.2f}° | Pitch: {att['pitch']:6.2f}° | Yaw: {att['yaw']:6.2f}°")
            else:
                print("[ATTITUDE] UDP not connected, no data given by cube")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[TEST] program stopped, closing the hearing system...")
        mav_conn.close()
        sys.exit(0)