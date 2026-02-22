##########################################
# Servo Control UI
# Author: Bhakti Jenna, Weilian Chen, Ismail Zarif
# Updated: Integrated Pico Flap Monitoring
##########################################
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import time
from New_Ground import get_connection_status, get_attitude
from pymavlink import mavutil


class ServoUI(ctk.CTk):
    def __init__(self, servo_config=None):
        super().__init__()
        self.title("Cube Status Monitor & Linked Servo Controller")
        self.geometry("1000(950")
        self.servo_config = servo_config or {}
        self.mav = next(iter(self.servo_config.values())).mav if self.servo_config else None

        # --- FLAP MONITORING STATE ---
        self.current_flap_angle = 0.0
        self.active_wing_label = "FlapL" # Default
        
        # UI Theme Configuration
        ctk.set_appearance_mode("white")
        ctk.set_default_color_theme("blue")

        # Grid Layout Configuration
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # State Variables
        self.safety_enabled = True
        self.armed = False
        self.debug_mode = False 
        
        self.aircraft_mapping = {
            "Port Wing": {
                "Port Flaps": [0, 1],
                "Port Aileron": [2]
            },
            "Starboard Wing": {
                "Starboard Flap": [3],
                "Starboard Aileron": [4]
            },
            "Empennage": {
                "Elevators": [5, 6],
                "Rudder": [7]
            }
        }
        
        self.surface_entries = {} 
        self.servo_container = None 

        # Initialize UI Components
        self._setup_sidebar()
        self._setup_main_content()

        # Start real-time updates
        self.update_status()
        self.update_attitude()
        self.poll_flap_data() # New dedicated loop for Pico data

    def _setup_sidebar(self):
        """Setup left sidebar with connection/status controls"""
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(9, weight=1) 

        ctk.CTkLabel(
            self.sidebar_frame, text="Status Monitor",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=(20, 10))

        self.status_var = tk.StringVar(value="Disconnected")
        self.status_label = ctk.CTkLabel(
            self.sidebar_frame, textvariable=self.status_var,
            font=ctk.CTkFont(size=14)
        )
        self.status_label.grid(row=1, column=0, padx=20, pady=(5, 5))

        # --- PICO CONTROL BUTTONS ---
        self.toggle_wing_button = ctk.CTkButton(
            self.sidebar_frame, text="Toggle Wing (L/R)",
            fg_color="#5a189a", command=self.send_toggle_wing
        )
        self.toggle_wing_button.grid(row=2, column=0, padx=20, pady=10)

        self.zero_flap_button = ctk.CTkButton(
            self.sidebar_frame, text="Zero Flap Angle",
            fg_color="#3c096c", command=self.send_zero_flaps
        )
        self.zero_flap_button.grid(row=3, column=0, padx=20, pady=5)

        # Existing Buttons shifted down
        self.debug_button = ctk.CTkButton(
            self.sidebar_frame, text="Enter Debug Mode",
            fg_color="gray", command=self.toggle_debug_mode
        )
        self.debug_button.grid(row=4, column=0, padx=20, pady=10)

        self.safety_button = ctk.CTkButton(
            self.sidebar_frame, text="Safety Enabled",
            command=self.toggle_safety
        )
        self.safety_button.grid(row=5, column=0, padx=20, pady=5)

        self.arming_button = ctk.CTkButton(
            self.sidebar_frame, text="Arming Disabled",
            command=self.toggle_arming
        )
        self.arming_button.grid(row=6, column=0, padx=20, pady=5)

        self.lua_start_button = ctk.CTkButton(
            self.sidebar_frame, text="Start Lua Script",
            fg_color="#2c6e49", command=lambda: self.trigger_lua(1)
        )
        self.lua_start_button.grid(row=7, column=0, padx=20, pady=5)

        self.lua_stop_button = ctk.CTkButton(
            self.sidebar_frame, text="Stop Lua Script",
            fg_color="#a11d33", command=lambda: self.trigger_lua(0)
        )
        self.lua_stop_button.grid(row=8, column=0, padx=20, pady=5)

        self.arming_status_label = ctk.CTkLabel(
            self.sidebar_frame, text="DISARMED\nNo LOGGING",
            text_color="white", fg_color="red",
            corner_radius=6, padx=10, pady=10
        )
        self.arming_status_label.grid(row=10, column=0, padx=20, pady=(10, 20), sticky="s")

    def _setup_main_content(self):
        """Setup main content area"""
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Flap angle dashboard section (Only for Wind Tunnel testing)
        dash_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        dash_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        ctk.CTkLabel(dash_frame, text="Dashboard", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="w"
        )

        self.flap_wing_var = tk.StringVar(value="Testing: PORT (Left)")
        self.flap_angle_var = tk.StringVar(value="0.00 °")

        ctk.CTkLabel(dash_frame, textvariable=self.flap_wing_var, font=ctk.CTkFont(size=13, weight="bold")).grid(row=1, column=0, padx=10, sticky="w")
        ctk.CTkLabel(dash_frame, textvariable=self.flap_angle_var, font=ctk.CTkFont(size=24)).grid(row=2, column=0, padx=10, pady=(0, 10), sticky="w")

        # ... (Rest of sections 2, 3, 4 remain same as your original)
        att_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        att_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        att_frame.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkLabel(att_frame, text="Live Orientation (°)", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="w", columnspan=3
        )
        self.roll_var = tk.StringVar(value="Roll: 0.00"); self.pitch_var = tk.StringVar(value="Pitch: 0.00"); self.yaw_var = tk.StringVar(value="Yaw: 0.00")
        ctk.CTkLabel(att_frame, textvariable=self.roll_var).grid(row=1, column=0, padx=10, pady=5)
        ctk.CTkLabel(att_frame, textvariable=self.pitch_var).grid(row=1, column=1, padx=10, pady=5)
        ctk.CTkLabel(att_frame, textvariable=self.yaw_var).grid(row=1, column=2, padx=10, pady=5)

        self.servo_container = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.servo_container.grid(row=2, column=0, sticky="nsew", pady=(0, 20))
        self.servo_container.grid_columnconfigure(0, weight=1)
        self._build_servo_grid()

        manual_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        manual_frame.grid(row=3, column=0, sticky="ew")
        self.attitude_entry = ctk.CTkEntry(manual_frame, width=400, height=30, font=ctk.CTkFont(size=14), placeholder_text="-- MAVLink Raw Stream --")
        self.attitude_entry.pack(padx=20, pady=20, fill="x")

    # --- NEW PICO INTERACTION METHODS ---

    def send_toggle_wing(self):
        """Sends command to Pico to switch labeling between FlapL and FlapR"""
        if self.mav:
            # We use the raw write method since our Pico code looks for this string
            self.mav.write(b"TOGGLE_WING")
            # Update UI expectation
            if self.active_wing_label == "FlapL":
                self.active_wing_label = "FlapR"
                self.flap_wing_var.set("Testing: STARBOARD (Right)")
            else:
                self.active_wing_label = "FlapL"
                self.flap_wing_var.set("Testing: PORT (Left)")
            print(f"Sent Toggle: Now expecting {self.active_wing_label}")

    def send_zero_flaps(self):
        """Sends command to Pico to reset current position to 0 degrees"""
        if self.mav:
            self.mav.write(b"ZERO_FLAPS")
            messagebox.showinfo("Pico Calibration", "Zeroing command sent to Flap Sensor.")

    def poll_flap_data(self):
        """Dedicated loop to catch MAVLink NAMED_VALUE_FLOAT from the Pico"""
        if self.mav:
            try:
                # Look for named float messages
                msg = self.mav.recv_match(type='NAMED_VALUE_FLOAT', blocking=False)    #blocking False to prevent UI freeze, we will poll every 50ms
                if msg:
                    # Check if it matches the flap we are currently testing
                    if msg.name == self.active_wing_label:
                        self.current_flap_angle = msg.value
                        self.flap_angle_var.set(f"{self.current_flap_angle:.2f} °")
            except Exception as e:
                print(f"MAVLink Read Error: {e}")

        # Run this loop every 50ms (20Hz) to ensure we don't miss Pico's 10Hz data
        self.after(50, self.poll_flap_data)

    
    def _build_servo_grid(self):
        for widget in self.servo_container.winfo_children(): widget.destroy()
        self.surface_entries = {}; current_row = 0
        if not self.debug_mode:
            for section, surfaces in self.aircraft_mapping.items():
                ctk.CTkLabel(self.servo_container, text=section, font=ctk.CTkFont(size=15, weight="bold"), text_color="#1f538d").grid(row=current_row, column=0, sticky="w", padx=20, pady=(15, 5))
                current_row += 1
                group_frame = ctk.CTkFrame(self.servo_container, fg_color="transparent")
                group_frame.grid(row=current_row, column=0, sticky="ew", padx=30, pady=(0, 10))
                for i, (surface_name, indices) in enumerate(surfaces.items()):
                    col_offset = (i % 2) * 3; row_offset = i // 2
                    ctk.CTkLabel(group_frame, text=f"{surface_name}:").grid(row=row_offset, column=col_offset, padx=5, pady=5, sticky="e")
                    entry = ctk.CTkEntry(group_frame, width=75); entry.grid(row=row_offset, column=col_offset + 1, padx=5, pady=5)
                    self.surface_entries[tuple(indices)] = entry 
                    ctk.CTkButton(group_frame, text="Send", width=60, command=lambda idxs=indices, name=surface_name: self.send_angle(idxs, name)).grid(row=row_offset, column=col_offset + 2, padx=5, pady=5)
                current_row += 1
        else:
            ctk.CTkLabel(self.servo_container, text="DEBUG MODE: Individual Servo Control", font=ctk.CTkFont(size=15, weight="bold"), text_color="#d35b5b").grid(row=0, column=0, pady=15)
            debug_frame = ctk.CTkFrame(self.servo_container, fg_color="transparent"); debug_frame.grid(row=1, column=0, padx=30, pady=10)
            for i in range(8):
                row_offset, col_offset = i // 2, (i % 2) * 3
                ctk.CTkLabel(debug_frame, text=f"Servo {i+1}:").grid(row=row_offset, column=col_offset, padx=5, pady=10)
                entry = ctk.CTkEntry(debug_frame, width=75); entry.grid(row=row_offset, column=col_offset+1, padx=5)
                self.surface_entries[(i,)] = entry
                ctk.CTkButton(debug_frame, text="Send", width=60, command=lambda idx=(i,), n=f"CH {i+1}": self.send_angle(idx, n)).grid(row=row_offset, column=col_offset+2, padx=5)

    def toggle_debug_mode(self):
        self.debug_mode = not self.debug_mode
        self.debug_button.configure(text="Exit Debug Mode" if self.debug_mode else "Enter Debug Mode", fg_color="#d35b5b" if self.debug_mode else "gray")
        self._build_servo_grid()

    def trigger_lua(self, action):
        if not self.mav: return
        self.mav.mav.command_long_send(self.mav.target_system, self.mav.target_component, mavutil.mavlink.MAV_CMD_SCRIPTING, 0, 0, action, 0, 0, 0, 0, 0)
        status_map = {0: "Stopped", 1: "Started", 2: "Restarted"}
        messagebox.showinfo("Lua Trigger", f"Script successfully {status_map.get(action, 'Triggered')}")

    def toggle_safety(self):
        if not self.mav: return
        import Arm_example
        new_state = not self.safety_enabled
        if Arm_example.toggle_safety_switch(self.mav, new_state):
            self.safety_enabled = new_state
            self.safety_button.configure(text="Safety Enabled" if self.safety_enabled else "Safety Disabled")

    def toggle_arming(self):
        if not self.mav: return
        import Arm_example
        new_state = not self.armed
        if Arm_example.toggle_arming_switch(self.mav, new_state):
            self.armed = new_state
            self.arming_button.configure(text="Arming Enabled" if self.armed else "Arming Disabled")
            self.arming_status_label.configure(text="ARMED\nDATA LOGGING" if self.armed else "DISARMED\nNO LOGGING", fg_color="green" if self.armed else "red")

    def send_angle(self, servo_indices, surface_name):
        if not self.mav: return
        try:
            entry_widget = self.surface_entries[tuple(servo_indices)]
            angle = float(entry_widget.get().strip())
            for idx in servo_indices:
                servo_ctrl = self.servo_config.get(idx + 1)
                if servo_ctrl: servo_ctrl.send_angle(angle)
            messagebox.showinfo("Success", f"{surface_name} set to {angle}°")
        except Exception as e: messagebox.showerror("Error", str(e))

    def update_status(self):
        status = get_connection_status().capitalize()
        self.status_var.set(status)
        self.status_label.configure(text_color="green" if status == "Connected" else "red")
        self.after(1000, self.update_status)

    def update_attitude(self):
        if get_connection_status() == "connected":
            att = get_attitude()
            self.roll_var.set(f"Roll: {att['roll']:.2f}"); self.pitch_var.set(f"Pitch: {att['pitch']:.2f}"); self.yaw_var.set(f"Yaw: {att['yaw']:.2f}")
            self.attitude_entry.delete(0, tk.END); self.attitude_entry.insert(0, f"R:{att['roll']:.2f} P:{att['pitch']:.2f} Y:{att['yaw']:.2f}")
        self.after(100, self.update_attitude)

if __name__ == "__main__":
    app = ServoUI()
    app.mainloop()

