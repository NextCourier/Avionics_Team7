"""
AMT103 Encoder Test for Raspberry Pi Pico
This code reads quadrature encoder signals and tracks position/direction
"""

from machine import Pin
import time

class AMT103Encoder:
    def __init__(self, pin_a, pin_b, pin_index=None):
        """
        Initialize the AMT103 encoder
        
        Args:
            pin_a: GPIO pin number for Channel A
            pin_b: GPIO pin number for Channel B
            pin_index: GPIO pin number for Index channel (optional)
        """
        self.pin_a = Pin(pin_a, Pin.IN, Pin.PULL_UP)
        self.pin_b = Pin(pin_b, Pin.IN, Pin.PULL_UP)
        
        if pin_index is not None:
            self.pin_index = Pin(pin_index, Pin.IN, Pin.PULL_UP)
        else:
            self.pin_index = None
        
        self.position = 0
        self.direction = 0  # 1 for CW, -1 for CCW, 0 for no movement
        self.last_a = self.pin_a.value()
        self.last_b = self.pin_b.value()
        
        # Set up interrupts on both channels for maximum responsiveness
        self.pin_a.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._callback)
        self.pin_b.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._callback)
        
        if self.pin_index is not None:
            self.index_count = 0
            self.pin_index.irq(trigger=Pin.IRQ_RISING, handler=self._index_callback)
    
    def _callback(self, pin):
        """
        Interrupt callback for encoder state changes
        Uses quadrature decoding to determine direction
        """
        a = self.pin_a.value()
        b = self.pin_b.value()
        
        # Quadrature decoding logic
        if a != self.last_a:
            if a == b:
                self.position -= 1
                self.direction = -1  # Counter-clockwise
            else:
                self.position += 1
                self.direction = 1   # Clockwise
        
        self.last_a = a
        self.last_b = b
    
    def _index_callback(self, pin):
        """Callback for index pulse (if connected)"""
        self.index_count += 1
    
    def get_position(self):
        """Return current position count"""
        return self.position
    
    def get_direction(self):
        """Return current direction (1=CW, -1=CCW, 0=stopped)"""
        return self.direction
    
    def reset_position(self):
        """Reset position counter to zero"""
        self.position = 0
    
    def get_index_count(self):
        """Return number of index pulses detected"""
        if self.pin_index is not None:
            return self.index_count
        return None


def test_encoder():
    """
    Main test function - displays encoder data in real-time
    """
    print("AMT103 Encoder Test Starting...")
    print("="*50)
    
    # Initialize encoder on GPIO 14 (A) and 15 (B), with optional index on 16
    encoder = AMT103Encoder(pin_a=14, pin_b=15, pin_index=16)
    
    print("Encoder initialized successfully!")
    print("Rotate the encoder shaft to test...")
    print("Press Ctrl+C to stop")
    print("="*50)
    
    last_position = 0
    rpm_samples = []
    last_time = time.ticks_ms()
    
    try:
        while True:
            current_position = encoder.get_position()
            direction = encoder.get_direction()
            
            # Calculate RPM (assuming 2048 PPR for AMT103-V)
            current_time = time.ticks_ms()
            time_diff = time.ticks_diff(current_time, last_time)
            
            if time_diff >= 100:  # Update every 100ms
                position_change = current_position - last_position
                
                # RPM calculation (adjust PPR based on your AMT103 model)
                PPR = 2048  # Pulses Per Revolution - adjust for your model
                if time_diff > 0:
                    rpm = (position_change / PPR) * (60000 / time_diff)
                else:
                    rpm = 0
                
                # Direction indicator
                dir_symbol = "→" if direction > 0 else "←" if direction < 0 else "●"
                
                print(f"Position: {current_position:6d} | "
                      f"Change: {position_change:+5d} | "
                      f"Dir: {dir_symbol} | "
                      f"RPM: {rpm:7.2f}", end="")
                
                # Display index count if available
                index_count = encoder.get_index_count()
                if index_count is not None:
                    print(f" | Index: {index_count}", end="")
                
                print("\r", end="")
                
                last_position = current_position
                last_time = current_time
            
            time.sleep(0.01)  # Small delay to prevent excessive CPU usage
            
    except KeyboardInterrupt:
        print("\n" + "="*50)
        print("Test stopped by user")
        print(f"Final position: {encoder.get_position()}")
        if encoder.get_index_count() is not None:
            print(f"Index pulses detected: {encoder.get_index_count()}")
        print("="*50)


def diagnostic_test():
    """
    Diagnostic test to verify encoder connections
    """
    print("AMT103 Encoder Diagnostic Test")
    print("="*50)
    
    # Test pins without interrupts first
    pin_a = Pin(14, Pin.IN, Pin.PULL_UP)
    pin_b = Pin(15, Pin.IN, Pin.PULL_UP)
    pin_i = Pin(16, Pin.IN, Pin.PULL_UP)
    
    print("Reading pin states (should be HIGH when idle):")
    print(f"Channel A (GPIO 14): {pin_a.value()} {'✓' if pin_a.value() == 1 else '✗'}")
    print(f"Channel B (GPIO 15): {pin_b.value()} {'✓' if pin_b.value() == 1 else '✗'}")
    print(f"Index    (GPIO 16): {pin_i.value()} {'✓' if pin_i.value() == 1 else '✗'}")
    print("\nRotate encoder slowly and watch for changes...")
    print("Press Ctrl+C to stop diagnostic")
    print("="*50)
    
    try:
        last_a, last_b, last_i = pin_a.value(), pin_b.value(), pin_i.value()
        while True:
            a, b, i = pin_a.value(), pin_b.value(), pin_i.value()
            
            if a != last_a or b != last_b or i != last_i:
                print(f"A:{a} B:{b} I:{i}  ", end="\r")
                last_a, last_b, last_i = a, b, i
            
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nDiagnostic complete")


if __name__ == "__main__":
    # Uncomment the test you want to run:
    
    # Run full encoder test
    test_encoder()
    
    # Or run diagnostic test first
    # diagnostic_test()
