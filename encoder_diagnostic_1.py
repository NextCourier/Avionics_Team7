"""
AMT103 Encoder Troubleshooting Diagnostic
This script helps identify connection and wiring issues
"""

from machine import Pin
import time

print("="*70)
print("AMT103 ENCODER DIAGNOSTIC TOOL")
print("="*70)
print("\nThis tool will help identify why your encoder isn't working.")
print("Follow the steps and observe the output.\n")

# Initialize pins first
pin_a = 14
pin_b = 15
pin_i = None

# Test 1: Check if pins can be read at all
print("TEST 1: GPIO Pin Initialization")
print("-"*70)
try:
    pin_a = Pin(14, Pin.IN, Pin.PULL_UP)
    pin_b = Pin(15, Pin.IN, Pin.PULL_UP)
    pin_i = Pin(16, Pin.IN, Pin.PULL_UP)
    print("✓ Pins initialized successfully")
    print(f"  GPIO 14 (Channel A): Configured")
    print(f"  GPIO 15 (Channel B): Configured")
    print(f"  GPIO 16 (Index):     Configured")
except Exception as e:
    print(f"✗ ERROR initializing pins: {e}")
    print("Check your MicroPython installation")
    import sys
    sys.exit(1)

# Test 2: Read initial states
print("\nTEST 2: Initial Pin States")
print("-"*70)
print("Reading pins (should typically be HIGH/1 when idle)...")
a_state = pin_a.value()
b_state = pin_b.value()
i_state = pin_i.value()

print(f"  Channel A (GPIO 14): {a_state} {'✓ HIGH' if a_state == 1 else '✗ LOW (unexpected)'}")
print(f"  Channel B (GPIO 15): {b_state} {'✓ HIGH' if b_state == 1 else '✗ LOW (unexpected)'}")
print(f"  Index     (GPIO 16): {i_state} {'✓ HIGH' if i_state == 1 else '✗ LOW (unexpected)'}")

if a_state == 0 and b_state == 0 and i_state == 0:
    print("\n⚠️  WARNING: All pins read LOW!")
    print("   Possible causes:")
    print("   - Encoder not powered (check VDD connection)")
    print("   - Wrong GPIO pins")
    print("   - Voltage divider not working")
    print("   - Wiring issue")

# Test 3: Continuous monitoring
print("\nTEST 3: Real-Time Signal Monitoring")
print("-"*70)
print("Slowly rotate the encoder shaft and watch for changes...")
print("Press Ctrl+C to stop\n")
print("Format: A B I  (0=LOW, 1=HIGH)")
print("-"*70)

last_a = a_state
last_b = b_state
last_i = i_state
change_count = 0
last_change_time = time.ticks_ms()

try:
    while True:
        a = pin_a.value()
        b = pin_b.value()
        i = pin_i.value()
        
        # Detect ANY change
        if a != last_a or b != last_b or i != last_i:
            change_count += 1
            current_time = time.ticks_ms()
            time_since_last = time.ticks_diff(current_time, last_change_time)
            
            # Visual indicator of which pin changed
            a_change = "→" if a != last_a else " "
            b_change = "→" if b != last_b else " "
            i_change = "→" if i != last_i else " "
            
            print(f"{a}{a_change} {b}{b_change} {i}{i_change}  | Change #{change_count} | Time: {time_since_last}ms")
            
            last_a = a
            last_b = b
            last_i = i
            last_change_time = current_time
        
        time.sleep(0.001)  # 1ms polling
        
except KeyboardInterrupt:
    print("\n" + "="*70)
    print("DIAGNOSTIC RESULTS:")
    print("="*70)
    print(f"Total changes detected: {change_count}")
    
    if change_count == 0:
        print("\n✗ NO CHANGES DETECTED - PROBLEM IDENTIFIED!")
        print("\nPossible issues (in order of likelihood):")
        print("\n1. VOLTAGE DIVIDER ISSUE:")
        print("   - Check resistor values (should be 47kΩ + 68kΩ)")
        print("   - Verify resistor connections are solid")
        print("   - Make sure the junction point connects to GPIO")
        print("   - Measure voltage at GPIO pins with multimeter (should be ~3V)")
        
        print("\n2. WRONG GPIO PINS:")
        print("   - Verify you're using GPIO 14, 15, 16 (not physical pin numbers)")
        print("   - Physical pins: 19, 20, 21 on Pico")
        
        print("\n3. ENCODER NOT POWERED:")
        print("   - Check 5V at encoder VDD pin")
        print("   - Verify ground connection")
        
        print("\n4. ENCODER OUTPUTS NOT CONNECTED:")
        print("   - Verify A, B, I pins from encoder go to voltage dividers")
        print("   - Check for loose breadboard connections")
        
        print("\n5. ENCODER DEFECTIVE:")
        print("   - Try measuring encoder outputs directly (should be 0-5V)")
        
    elif change_count < 10:
        print("\n⚠️  FEW CHANGES DETECTED - INTERMITTENT CONNECTION!")
        print("\nLikely issues:")
        print("   - Loose breadboard connections")
        print("   - Bad solder joints (if soldered)")
        print("   - Intermittent voltage divider connection")
        
    else:
        print("\n✓ ENCODER IS WORKING!")
        print("\nIf the main program still doesn't work, the issue is likely:")
        print("   - Interrupt handling problem")
        print("   - Code issue (not hardware)")
        print("   - Try running the simple polling version instead")

print("\n" + "="*70)
print("NEXT STEPS:")
print("="*70)
print("\nTo measure voltages with a multimeter:")
print("1. Encoder VDD: Should read ~5V")
print("2. At GPIO pins: Should read ~3V when encoder outputs HIGH")
print("3. At GPIO pins: Should read ~0V when encoder outputs LOW")
print("\nTo test encoder outputs directly (CAREFULLY - 5V):")
print("1. Disconnect from Pico")
print("2. Measure encoder A, B outputs with multimeter")
print("3. Rotate shaft - voltage should change between 0V and 5V")
