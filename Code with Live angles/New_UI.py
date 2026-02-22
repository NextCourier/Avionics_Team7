import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import time
from New_Ground import get_connection_status, get_attitude


class ServoUI(ctk.CTk):
    def __init__(self, servo_config=None):
        super().__init__()
        self.title("Cube_Status_Monitor & Servo_Controller")
        self.geometry("900x700")
        self.servo_config = servo_config


        ctk.set_appearance_mode("white")
        ctk.set_default_color_theme("blue")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)


        self.safety_enabled = True
        self.armed = False
        self.angle_entries = []


        self._setup_sidebar()
        self._setup_main_content()


        self.update_status()
        self.update_attitude()

    def _setup_sidebar(self):

        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)


        ctk.CTkLabel(
            self.sidebar_frame,
            text="Status monitor",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=(20, 10))


        self.status_var = tk.StringVar(value="Disconnected")
        self.status_label = ctk.CTkLabel(
            self.sidebar_frame,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=14)
        )
        self.status_label.grid(row=1, column=0, padx=20, pady=(5, 5))


        self.safety_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Safety Enabled",
            command=self.toggle_safety
        )
        self.safety_button.grid(row=2, column=0, padx=20, pady=5)


        self.arming_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Arming Disabled",
            command=self.toggle_arming
        )
        self.arming_button.grid(row=3, column=0, padx=20, pady=5)


        self.arming_status_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="DISARMED\nNo LOGGING",
            text_color="white",
            fg_color="red",
            corner_radius=6,
            padx=10,
            pady=10
        )
        self.arming_status_label.grid(row=5, column=0, padx=20, pady=(10, 20), sticky="s")

    def _setup_main_content(self):

        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)


        dash_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        dash_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        ctk.CTkLabel(dash_frame, text="Dashboard", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="w"
        )
        ctk.CTkLabel(dash_frame, text="Flap Position: --").grid(row=1, column=0, padx=10, sticky="e")
        ctk.CTkLabel(dash_frame, text="Flap Angle: -- °").grid(row=2, column=0, padx=10, pady=(0, 10), sticky="e")


        att_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        att_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))

        att_frame.grid_columnconfigure(0, weight=1)
        att_frame.grid_columnconfigure(1, weight=1)
        att_frame.grid_columnconfigure(2, weight=1)


        ctk.CTkLabel(att_frame, text="Live Yaw/Roll/Pitch angle (°)", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="w", columnspan=3
        )


        self.roll_var = tk.StringVar(value="Roll: 0.00")
        ctk.CTkLabel(att_frame, textvariable=self.roll_var, font=ctk.CTkFont(size=12)).grid(
            row=1, column=0, padx=10, pady=5
        )


        self.pitch_var = tk.StringVar(value="Pitch: 0.00")
        ctk.CTkLabel(att_frame, textvariable=self.pitch_var, font=ctk.CTkFont(size=12)).grid(
            row=1, column=1, padx=10, pady=5
        )


        self.yaw_var = tk.StringVar(value="Yaw: 0.00")
        ctk.CTkLabel(att_frame, textvariable=self.yaw_var, font=ctk.CTkFont(size=12)).grid(
            row=1, column=2, padx=10, pady=5
        )


        servo_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        servo_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        servo_frame.grid_columnconfigure(0, weight=1)
        servo_frame.grid_columnconfigure(1, weight=1)


        angle_frame = ctk.CTkFrame(servo_frame, fg_color="transparent")
        angle_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        for i in range(3):
            ctk.CTkLabel(angle_frame, text=f"Servo {i + 1} Angle (°):").grid(
                row=i, column=0, sticky="w", padx=5, pady=5
            )
            entry = ctk.CTkEntry(angle_frame, width=80)
            entry.grid(row=i, column=1, padx=5, pady=5)
            self.angle_entries.append(entry)
            ctk.CTkButton(
                angle_frame, text="Send", width=60,
                command=lambda idx=i: self.send_angle(idx)
            ).grid(row=i, column=2, padx=5, pady=5)


        manual_frame = ctk.CTkFrame(servo_frame, fg_color="transparent")
        manual_frame.grid(row=0, column=1, padx=20, pady=20, sticky="e")
        ctk.CTkLabel(manual_frame, text="Manual (m)").pack(pady=(0, 5))
        self.attitude_entry = ctk.CTkEntry(
            manual_frame, width=215, height=30,
            font=ctk.CTkFont(size=16, weight="bold"),
            placeholder_text="-- Mission Planner DAta --"
        )
        self.attitude_entry.pack(pady=(0, 5))

    def toggle_safety(self):

        if not self.servo_config:
            messagebox.showwarning("Caution", "Connect to Cube")
            return
        self.safety_enabled = not self.safety_enabled
        self.safety_button.configure(
            text="Safety Enabled" if self.safety_enabled else "Safety disabled"
        )
        messagebox.showinfo("Caution", f"Safety switch{'enabled' if self.safety_enabled else 'disabled'}")

    def toggle_arming(self):

        if not self.servo_config:
            messagebox.showwarning("Caution", "Connect to Cube first")
            return
        self.armed = not self.armed
        if self.armed:
            self.arming_button.configure(text="Arming Enabled")
            self.arming_status_label.configure(
                text="ARMED\nDATA LOGGING", fg_color="green"
            )
        else:
            self.arming_button.configure(text="Arming disabled")
            self.arming_status_label.configure(
                text="DISARMED\nNO LOGGING", fg_color="red"
            )

    def send_angle(self, servo_index):

        if not self.servo_config:
            messagebox.showwarning("Caution", "Connect to cube first")
            return
        try:
            angle = float(self.angle_entries[servo_index].get())
            if not (0 <= angle <= 180):
                raise ValueError("Angle need to between 0-180°")

            servo_ctrl = self.servo_config.get(servo_index + 1)
            if servo_ctrl:
                messagebox.showinfo("Successful;", f"Servo {servo_index + 1} set to {angle}°")
            else:
                messagebox.showerror("Fault", f"Servo {servo_index + 1} not found")
        except ValueError as e:
            messagebox.showerror("ValueError", f"Invalid angle：{e}")
        except Exception as e:
            messagebox.showerror("Sending Fault", str(e))

    def update_status(self):

        status = get_connection_status().capitalize()
        self.status_var.set(status)
        self.status_label.configure(
            text_color="green" if status == "Connected" else "red"
        )
        self.after(1000, self.update_status)

    def update_attitude(self):

        if get_connection_status() == "connected":
            att = get_attitude()
            self.roll_var.set(f"Roll: {att['roll']:.2f}")
            self.pitch_var.set(f"Pitch: {att['pitch']:.2f}")
            self.yaw_var.set(f"Yaw: {att['yaw']:.2f}")
        else:
            self.roll_var.set("Roll: --")
            self.pitch_var.set("Pitch: --")
            self.yaw_var.set("Yaw: --")
        self.after(100, self.update_attitude)


if __name__ == "__main__":

    app = ServoUI()
    app.mainloop()
