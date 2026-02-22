##########################################
# Servo Control UI
# Author: Ethan Sheehan
# Updated for 8-servo support
##########################################
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import time
from New_Ground import get_connection_status, get_attitude


class ServoUI(ctk.CTk):
    def __init__(self, servo_config=None):
        super().__init__()
        self.title("Cube Status Monitor & 8-Servo Controller")
        self.geometry("1000x800")  # Expanded window for 8 servos
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
        self.angle_entries = []  # Stores entries for 8 servos

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
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        # Sidebar Title
        ctk.CTkLabel(
            self.sidebar_frame, text="Status Monitor",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=(20, 10))

        # Connection Status
        self.status_var = tk.StringVar(value="Disconnected")
        self.status_label = ctk.CTkLabel(
            self.sidebar_frame, textvariable=self.status_var,
            font=ctk.CTkFont(size=14)
        )
        self.status_label.grid(row=1, column=0, padx=20, pady=(5, 5))

        # Safety Switch Button
        self.safety_button = ctk.CTkButton(
            self.sidebar_frame, text="Safety Enabled",
            command=self.toggle_safety
        )
        self.safety_button.grid(row=2, column=0, padx=20, pady=5)

        # Arming Button
        self.arming_button = ctk.CTkButton(
            self.sidebar_frame, text="Arming Disabled",
            command=self.toggle_arming
        )
        self.arming_button.grid(row=3, column=0, padx=20, pady=5)

        # Arming Status Label
        self.arming_status_label = ctk.CTkLabel(
            self.sidebar_frame, text="DISARMED\nNo LOGGING",
            text_color="white", fg_color="red",
            corner_radius=6, padx=10, pady=10
        )
        self.arming_status_label.grid(row=5, column=0, padx=20, pady=(10, 20), sticky="s")

    def _setup_main_content(self):
        """Setup main content area with dashboard and 8-servo controls"""
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
        ctk.CTkLabel(att_frame, text="Live Yaw/Roll/Pitch angle (°)", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="w", columnspan=3
        )

        # Attitude Value Labels
        self.roll_var = tk.StringVar(value="Roll: 0.00")
        self.pitch_var = tk.StringVar(value="Pitch: 0.00")
        self.yaw_var = tk.StringVar(value="Yaw: 0.00")

        ctk.CTkLabel(att_frame, textvariable=self.roll_var).grid(row=1, column=0, padx=10, pady=5)
        ctk.CTkLabel(att_frame, textvariable=self.pitch_var).grid(row=1, column=1, padx=10, pady=5)
        ctk.CTkLabel(att_frame, textvariable=self.yaw_var).grid(row=1, column=2, padx=10, pady=5)

        # 3. 8-Servo Control Section
        servo_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        servo_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 20))
        servo_frame.grid_columnconfigure((0, 1), weight=1)

        # 3.1 Servo Angle Input Grid (2 columns x 4 rows for 8 servos)
        angle_frame = ctk.CTkFrame(servo_frame, fg_color="transparent")
        angle_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        # Create input fields for 8 servos (2 columns, 4 rows)
        for i in range(8):
            row = i // 2  # 0-3 for rows
            col = (i % 2) * 3  # 0,3 for columns (spacing between servo groups)

            # Servo Label
            ctk.CTkLabel(angle_frame, text=f"Servo {i + 1} Angle (°):").grid(
                row=row, column=col, sticky="w", padx=5, pady=5
            )

            # Angle Input Entry
            entry = ctk.CTkEntry(angle_frame, width=80)
            entry.grid(row=row, column=col + 1, padx=5, pady=5)
            self.angle_entries.append(entry)

            # Send Button
            ctk.CTkButton(
                angle_frame, text="Send", width=60,
                command=lambda idx=i: self.send_angle(idx)
            ).grid(row=row, column=col + 2, padx=5, pady=5)

        # 3.2 Manual Data Display
        manual_frame = ctk.CTkFrame(servo_frame, fg_color="transparent")
        manual_frame.grid(row=0, column=1, padx=20, pady=20, sticky="e")
        ctk.CTkLabel(manual_frame, text="Manual (m)").pack(pady=(0, 5))
        self.attitude_entry = ctk.CTkEntry(
            manual_frame, width=215, height=30,
            font=ctk.CTkFont(size=16, weight="bold"),
            placeholder_text="-- Mission Planner Data --"
        )
        self.attitude_entry.pack(pady=(0, 5))

    def toggle_safety(self):
        """Toggle safety switch state"""
        if not self.mav:
            messagebox.showwarning("Warning", "Please connect to flight controller first")
            return

        import Arm_example
        new_state = not self.safety_enabled
        success = Arm_example.toggle_safety_switch(self.mav, new_state)

        if success:
            self.safety_enabled = new_state
            self.safety_button.configure(
                text="Safety Enabled" if self.safety_enabled else "Safety Disabled"
            )
            messagebox.showinfo("Success", f"Safety switch has been {'enabled' if self.safety_enabled else 'disabled'}")
        else:
            messagebox.showerror("Error", "Failed to toggle safety switch")

    def toggle_arming(self):
        """Toggle flight controller arming state"""
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
            messagebox.showinfo("Success", f"Arming state has been {'enabled' if self.armed else 'disabled'}")
        else:
            messagebox.showerror("Error", "Failed to toggle arming state")

    def send_angle(self, servo_index):
        """Send target angle to specified servo (1-8)"""
        if not self.mav:
            messagebox.showwarning("Warning", "Please connect to flight controller first")
            return

        try:
            # Get and validate angle input
            angle_str = self.angle_entries[servo_index].get().strip()
            if not angle_str:
                raise ValueError("Angle input cannot be empty")

            angle = float(angle_str)
            if not (0 <= angle <= 180):
                raise ValueError("Angle must be between 0 and 180 degrees")

            # Get servo controller and send angle
            servo_ctrl = self.servo_config.get(servo_index + 1)
            if servo_ctrl:
                # Unified send_angle method for all 8 servos (compatible with updated ServoController)
                servo_ctrl.send_angle(angle)
                messagebox.showinfo("Success", f"Servo {servo_index + 1} set to {angle}°")
            else:
                messagebox.showerror("Error", f"Servo {servo_index + 1} controller not found")

        except ValueError as e:
            messagebox.showerror("Input Error", f"Invalid angle: {str(e)}")
        except Exception as e:
            messagebox.showerror("Send Error", f"Failed to send command: {str(e)}")

    def update_status(self):
        """Update connection status in real-time"""
        status = get_connection_status().capitalize()
        self.status_var.set(status)
        self.status_label.configure(text_color="green" if status == "Connected" else "red")
        self.after(1000, self.update_status)

    def update_attitude(self):
        """Update attitude data (roll/pitch/yaw) in real-time"""
        if get_connection_status() == "connected":
            att = get_attitude()
            self.roll_var.set(f"Roll: {att['roll']:.2f}")
            self.pitch_var.set(f"Pitch: {att['pitch']:.2f}")
            self.yaw_var.set(f"Yaw: {att['yaw']:.2f}")

            # Update manual data entry
            self.attitude_entry.delete(0, tk.END)
            self.attitude_entry.insert(0, f"Roll:{att['roll']:.2f} Pitch:{att['pitch']:.2f} Yaw:{att['yaw']:.2f}")
        else:
            self.roll_var.set("Roll: --")
            self.pitch_var.set("Pitch: --")
            self.yaw_var.set("Yaw: --")

        self.after(100, self.update_attitude)


if __name__ == "__main__":
    app = ServoUI()
    app.mainloop()
