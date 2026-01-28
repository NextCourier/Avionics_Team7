##########################################
# Servo Control UI
# Author: Bhakti Jenna, Weilian Chen
# Updated: Multi-Servo Support + Dynamic Debug Mode
##########################################
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import time
from New_Ground import get_connection_status, get_attitude


class ServoUI(ctk.CTk):
    def __init__(self, servo_config=None):
        super().__init__()
        self.title("Cube Status Monitor & Linked Servo Controller")
        self.geometry("1000x950")
        self.servo_config = servo_config or {}
        self.mav = next(iter(self.servo_config.values())).mav if self.servo_config else None

        # UI Theme Configuration
        ctk.set_appearance_mode("white")
        ctk.set_default_color_theme("blue")

        # Grid Layout Configuration
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # State Variables
        self.safety_enabled = True
        self.armed = False
        self.debug_mode = False  # Track if we are in individual servo mode
        
        # Mapping logic: Surface Name : List of MAVLink Indices (0-7)
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
        
        # Stores the Entry widgets. Keyed by a tuple of indices.
        self.surface_entries = {} 
        self.servo_container = None # Reference for dynamic grid rebuilding

        # Initialize UI Components
        self._setup_sidebar()
        self._setup_main_content()

        # Start real-time updates
        self.update_status()
        self.update_attitude()

    def _setup_sidebar(self):
        """Setup left sidebar with connection/status controls"""
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

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

        # Debug Mode Toggle Button
        self.debug_button = ctk.CTkButton(
            self.sidebar_frame, text="Enter Debug Mode",
            fg_color="gray", command=self.toggle_debug_mode
        )
        self.debug_button.grid(row=2, column=0, padx=20, pady=10)

        self.safety_button = ctk.CTkButton(
            self.sidebar_frame, text="Safety Enabled",
            command=self.toggle_safety
        )
        self.safety_button.grid(row=3, column=0, padx=20, pady=5)

        self.arming_button = ctk.CTkButton(
            self.sidebar_frame, text="Arming Disabled",
            command=self.toggle_arming
        )
        self.arming_button.grid(row=4, column=0, padx=20, pady=5)

        self.arming_status_label = ctk.CTkLabel(
            self.sidebar_frame, text="DISARMED\nNo LOGGING",
            text_color="white", fg_color="red",
            corner_radius=6, padx=10, pady=10
        )
        self.arming_status_label.grid(row=6, column=0, padx=20, pady=(10, 20), sticky="s")

    def _setup_main_content(self):
        """Setup main content area with dashboard and categorized control surfaces"""
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # 1. Dashboard Section
        dash_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        dash_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        ctk.CTkLabel(dash_frame, text="Dashboard", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="w"
        )
        ctk.CTkLabel(dash_frame, text="Flap Position: --").grid(row=1, column=0, padx=10, sticky="e")
        ctk.CTkLabel(dash_frame, text="Flap Angle: -- °").grid(row=2, column=0, padx=10, pady=(0, 10), sticky="e")

        # 2. Attitude Data Section
        att_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        att_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        att_frame.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkLabel(att_frame, text="Live Orientation (°)", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="w", columnspan=3
        )

        self.roll_var = tk.StringVar(value="Roll: 0.00")
        self.pitch_var = tk.StringVar(value="Pitch: 0.00")
        self.yaw_var = tk.StringVar(value="Yaw: 0.00")

        ctk.CTkLabel(att_frame, textvariable=self.roll_var).grid(row=1, column=0, padx=10, pady=5)
        ctk.CTkLabel(att_frame, textvariable=self.pitch_var).grid(row=1, column=1, padx=10, pady=5)
        ctk.CTkLabel(att_frame, textvariable=self.yaw_var).grid(row=1, column=2, padx=10, pady=5)

        # 3. Servo Grid Container
        self.servo_container = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.servo_container.grid(row=2, column=0, sticky="nsew", pady=(0, 20))
        self.servo_container.grid_columnconfigure(0, weight=1)

        # Build initial grid
        self._build_servo_grid()

        # 4. Manual Data Display
        manual_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        manual_frame.grid(row=3, column=0, sticky="ew")
        self.attitude_entry = ctk.CTkEntry(
            manual_frame, width=400, height=30,
            font=ctk.CTkFont(size=14),
            placeholder_text="-- MAVLink Raw Stream --"
        )
        self.attitude_entry.pack(padx=20, pady=20, fill="x")

    def _build_servo_grid(self):
        """Clears and rebuilds the servo grid based on current mode"""
        # Clear existing widgets
        for widget in self.servo_container.winfo_children():
            widget.destroy()
        
        self.surface_entries = {}
        current_row = 0

        if not self.debug_mode:
            # Default Mode: Control Surfaces
            for section, surfaces in self.aircraft_mapping.items():
                ctk.CTkLabel(self.servo_container, text=section, 
                             font=ctk.CTkFont(size=15, weight="bold"),
                             text_color="#1f538d").grid(row=current_row, column=0, sticky="w", padx=20, pady=(15, 5))
                current_row += 1

                group_frame = ctk.CTkFrame(self.servo_container, fg_color="transparent")
                group_frame.grid(row=current_row, column=0, sticky="ew", padx=30, pady=(0, 10))
                
                for i, (surface_name, indices) in enumerate(surfaces.items()):
                    col_offset = (i % 2) * 3 
                    row_offset = i // 2
                    ctk.CTkLabel(group_frame, text=f"{surface_name}:").grid(row=row_offset, column=col_offset, padx=5, pady=5, sticky="e")
                    entry = ctk.CTkEntry(group_frame, width=75)
                    entry.grid(row=row_offset, column=col_offset + 1, padx=5, pady=5)
                    self.surface_entries[tuple(indices)] = entry 
                    ctk.CTkButton(group_frame, text="Send", width=60,
                                  command=lambda idxs=indices, name=surface_name: self.send_angle(idxs, name)).grid(
                                      row=row_offset, column=col_offset + 2, padx=5, pady=5)
                current_row += 1
        else:
            # Debug Mode: 8 Individual Servo Controls
            ctk.CTkLabel(self.servo_container, text="DEBUG MODE: Individual Servo Control", 
                         font=ctk.CTkFont(size=15, weight="bold"),
                         text_color="#d35b5b").grid(row=0, column=0, pady=15)
            
            debug_frame = ctk.CTkFrame(self.servo_container, fg_color="transparent")
            debug_frame.grid(row=1, column=0, padx=30, pady=10)
            
            for i in range(8):
                row_offset, col_offset = i // 2, (i % 2) * 3
                ctk.CTkLabel(debug_frame, text=f"Servo {i+1}:").grid(row=row_offset, column=col_offset, padx=5, pady=10)
                entry = ctk.CTkEntry(debug_frame, width=75)
                entry.grid(row=row_offset, column=col_offset+1, padx=5)
                self.surface_entries[(i,)] = entry
                ctk.CTkButton(debug_frame, text="Send", width=60, 
                              command=lambda idx=(i,), n=f"CH {i+1}": self.send_angle(idx, n)).grid(
                                  row=row_offset, column=col_offset+2, padx=5)

    def toggle_debug_mode(self):
        """Toggle between Normal and Debug modes"""
        self.debug_mode = not self.debug_mode
        if self.debug_mode:
            self.debug_button.configure(text="Exit Debug Mode", fg_color="#d35b5b")
        else:
            self.debug_button.configure(text="Enter Debug Mode", fg_color="gray")
        self._build_servo_grid()

    def toggle_safety(self):
        if not self.mav:
            messagebox.showwarning("Warning", "Please connect to flight controller first")
            return
        import Arm_example
        new_state = not self.safety_enabled
        success = Arm_example.toggle_safety_switch(self.mav, new_state)
        if success:
            self.safety_enabled = new_state
            self.safety_button.configure(text="Safety Enabled" if self.safety_enabled else "Safety Disabled")
            messagebox.showinfo("Success", f"Safety {'enabled' if self.safety_enabled else 'disabled'}")

    def toggle_arming(self):
        if not self.mav:
            messagebox.showwarning("Warning", "Please connect to flight controller first")
            return
        import Arm_example
        new_state = not self.armed
        success = Arm_example.toggle_arming_switch(self.mav, new_state)
        if success:
            self.armed = new_state
            self.arming_button.configure(text="Arming Enabled" if self.armed else "Arming Disabled")
            self.arming_status_label.configure(
                text="ARMED\nDATA LOGGING" if self.armed else "DISARMED\nNO LOGGING",
                fg_color="green" if self.armed else "red"
            )

    def send_angle(self, servo_indices, surface_name):
        """Send target angle to one or multiple linked servos"""
        if not self.mav:
            messagebox.showwarning("Warning", "No MAVLink connection")
            return

        try:
            entry_widget = self.surface_entries[tuple(servo_indices)]
            angle_str = entry_widget.get().strip()
            
            if not angle_str:
                raise ValueError("Angle cannot be empty")

            angle = float(angle_str)
            if not (0 <= angle <= 180):
                raise ValueError("Range: 0-180")

            for idx in servo_indices:
                servo_ctrl = self.servo_config.get(idx + 1)
                if servo_ctrl:
                    servo_ctrl.send_angle(angle)
                else:
                    print(f"Warning: Config for Channel {idx+1} not found")

            messagebox.showinfo("Success", f"{surface_name} set to {angle}°")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_status(self):
        status = get_connection_status().capitalize()
        self.status_var.set(status)
        self.status_label.configure(text_color="green" if status == "Connected" else "red")
        self.after(1000, self.update_status)

    def update_attitude(self):
        if get_connection_status() == "connected":
            att = get_attitude()
            self.roll_var.set(f"Roll: {att['roll']:.2f}")
            self.pitch_var.set(f"Pitch: {att['pitch']:.2f}")
            self.yaw_var.set(f"Yaw: {att['yaw']:.2f}")
            self.attitude_entry.delete(0, tk.END)
            self.attitude_entry.insert(0, f"R:{att['roll']:.2f} P:{att['pitch']:.2f} Y:{att['yaw']:.2f}")
        self.after(100, self.update_attitude)


if __name__ == "__main__":
    app = ServoUI()
    app.mainloop()
