import struct
import time
from machine import UART, Pin, Timer


# communicates with Cube's Telem 2 port
# uses physical pin numbers 6 and 7. Thats GPIO Pins 4 and 6 on the Pico
uart = UART(0, baudrate=115200, tx=Pin(4), rx=Pin(5))          # make sure the "SERIAL2_BAUD" parameter in mission planner is set to 115


# Other hardware settings
UART_BAUD = 115200
MAV_SYS_ID = 1      # Must match Cube's "SYSID_THISMAV" parameter in mission planner (default is 1, but can be changed in mission planner)
MAV_COMP_ID = 1     # Component ID for the sender (Pico).
MSG_ID_NAMED_FLOAT = 251   # basically the identifier that this is flap angle and not telemetry date
CRC_EXTRA = 170            # The extra byte that checks the integrity of the message





# the 'LISTENER' Function -----> for incoming commands from the UI

# This checks if the UI clicked 'Toggle' or 'Zero'
def check_commands():
    global current_wing
    if uart.any(): # Is there data waiting in the buffer?
        cmd = uart.read() 
        
        # checks raw strings sent by UI's self.mav.write()
        if b"ZERO_FLAPS" in cmd:
            sensor.reset()                                #  <----- placeholder for the actual encoder reset function that you used.
            print("Command Received: Resetting Encoder to 0")
            
        if b"TOGGLE_WING" in cmd:
            # Flips the label so the GCS knows which wing is being sent
            current_wing = "FlapR" if current_wing == "FlapL" else "FlapL"
            print(f"Command Received: Labeling as {current_wing}")








# The 'YAPPER' function -----> for sending angles to the UI

# This packages the angle into a MAVLink-compliant format  (AI generated part, I don't really get it but it should work)
def send_mavlink_float(name, value):
    # MAVLink 1 Frame Structure:
    # [STX] [LEN] [SEQ] [SYSID] [COMPID] [MSGID] [PAYLOAD] [CRC]
    
    # Payload: 4 bytes (time), 4 bytes (float value), 10 bytes (name string)
    name_bytes = (name[:10]).encode('utf-8').ljust(10, b'\x00')
    payload = struct.pack("<If10s", int(time.ticks_ms()), value, name_bytes)
    
    # Header
    header = struct.pack("<BBBBBB", 
                         0xFE,          # STX (Start of Frame)
                         len(payload),  # Length of data
                         0,             # Sequence (Pico handles this as 0 for simplicity)
                         1,             # System ID (Must match Cube's SYSID_THISMAV)
                         1,             # Component ID
                         251)           # Message ID for NAMED_VALUE_FLOAT
    
    # Integrity Check: ArduPilot will reject the packet if the CRC is wrong
    crc = calculate_crc(header[1:] + payload, 170) # 170 is the 'Extra' CRC for this msg
    
    # Physical send across the wire to the Cube
    uart.write(header + payload + struct.pack("<H", crc))
    

# Part of the function above really
# MAVLink CRC-16 Calculation (ArduPilot uses a custom CRC-16 with an extra byte for each message type)
def crc8_accumulate(b, crc):
    accum = b ^ (crc & 0xff)
    accum ^= (accum << 4) & 0xff
    return ((crc >> 8) ^ (accum << 8) ^ (accum << 3) ^ (accum >> 4)) & 0xFFFF

def calculate_crc(data, extra):
    crc = 0xFFFF
    for b in data:
        crc = crc8_accumulate(b, crc)
    crc = crc8_accumulate(extra, crc)
    return crc