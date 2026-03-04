##########################################
# Servo Control UI
# Authors: Bhakti Jenna, Weilian Chen, Ismail Zarif
# Updated: Switch for control mode and add logging system.
##########################################
import csv
import os
from datetime import datetime
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import time
from GS_example import get_connection_status, get_attitude
from pymavlink import mavutil
from Servo_example import angle_to_pwm, Servo, DEFAULT_SERVO_CONFIG


class ServoUI(ctk.CTk):
    def __init__(self, servo_config=None, connection_type="WIFI" , control_manager=None):
        super().__init__()
        self.title("Cube Status Monitor & Linked Servo Controller")
        self.geometry("1400x1200")
        self.servo_config = servo_config or {}
        self.last_logged_positions = {}
        self.override_channels = [65535] * 8
        self.override_active = False
        self.mav = next(iter(self.servo_config.values())).mav if self.servo_config else None
        self.local_logging_active = False
        self.csv_writer = None
        self.csv_file = None
        self.attitude_logging_active = False
        self.att_csv_file = None
        self.att_csv_writer = None
        self.current_flap_angle = 0.0
        self.active_wing_label = "FlapL"
        self.connection_type = connection_type
        self.control_manager = control_manager

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

        # Mapping logic: Surface Name : List of MAVLink Indices (0-7)
        self.aircraft_mapping = {
            "Port Wing": {
                "Port Flaps(Pin1,Pin2)": [0, 1],
                "Port Aileron(Pin3)": [2]
            },
            "Starboard Wing": {
                "Starboard Flap(Pin4)": [3],
                "Starboard Aileron(Pin5)": [4]
            },
            "Empennage": {
                "Elevators(Pin6,Pin7)": [5, 6],
                "Rudder(Pin8)": [7]
            }
        }

        self.surface_entries = {}
        self.pwm_display_labels = {}
        self.servo_container = None

        # Initialize UI Components
        self._setup_sidebar()
        self._setup_main_content()

        self.update_connection_label()
        self.logging_on = False
        self.master_update()
        self.update_control_mode_label()
        self.aircraft_mapping = {
            "Port Wing": {
                "Port Flaps (Pin1, Pin2)": {"indices": [0, 1], "init": 0},
                "Port Aileron(Pin3)": {"indices": [2], "init": 90}
            },
            "Starboard Wing": {
                "Starboard Flap(Pin4)": {"indices": [3], "init": 0},
                "Starboard Aileron(Pin5)": {"indices": [4], "init": 90}
            },
            "Empennage": {
                "Elevators(Pin6,Pin7)": {"indices": [5, 6], "init": 90},
                "Rudder(Pin8)": {"indices": [7], "init": 90}
            }
        }

    def start_keep_alive(self):
        self.maintain_current_angles()
        self.after(500, self.start_keep_alive)

    def maintain_current_angles(self):
        angles = {}
        last_input = "Auto_KeepAlive"
        for indices, entry in self.surface_entries.items():
            try:
                val = float(entry.get())
                last_input = val
                for idx in indices:
                    angles[idx + 1] = val
            except:
                continue
        if angles:
            self._batch_send(angles, input_angle=last_input)

    def send_initial_positions(self):
        if not self.mav: return
        initial_map = {}
        for section in self.aircraft_mapping.values():
            for surface, data in section.items():
                for idx in data["indices"]:
                    servo_num = idx + 1
                    initial_map[servo_num] = data["init"]
        self._batch_send(initial_map)
        print("Initial positions sent (Flaps: 0, Others: 90)")

    def _setup_sidebar(self):
        """Setup left sidebar with logical grouped layout"""

        self.sidebar_frame = ctk.CTkFrame(self, width=160, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_columnconfigure(0, weight=1)

        row = 0

        ctk.CTkLabel(
            self.sidebar_frame,
            text="STATUS",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=row, column=0, padx=20, pady=(20, 5))
        row += 1

        self.status_var = tk.StringVar(value="Disconnected")
        self.status_label = ctk.CTkLabel(
            self.sidebar_frame,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=14)
        )
        self.status_label.grid(row=row, column=0, padx=20, pady=(0, 15))
        row += 1

        ctk.CTkLabel(
            self.sidebar_frame,
            text="FLIGHT SAFETY",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=row, column=0, padx=20, pady=(10, 5))
        row += 1

        self.safety_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Safety Enabled",
            command=self.toggle_safety
        )
        self.safety_button.grid(row=row, column=0, padx=20, pady=5)
        row += 1

        self.arming_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Arming Disabled",
            command=self.toggle_arming
        )
        self.arming_button.grid(row=row, column=0, padx=20, pady=5)
        row += 1

        self.arming_status_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="DISARMED\nNO LOGGING",
            text_color="white",
            fg_color="red",
            corner_radius=6,
            padx=10,
            pady=10
        )
        self.arming_status_label.grid(row=row, column=0, padx=20, pady=(10, 20))
        row += 1

        ctk.CTkLabel(
            self.sidebar_frame,
            text="CONTROL MODE",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=row, column=0, padx=20, pady=(10, 5))
        row += 1

        self.control_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Switch to CODE",
            fg_color="#2a9d8f",
            command=self.toggle_control_mode
        )
        self.control_button.grid(row=row, column=0, padx=20, pady=5)
        row += 1

        self.control_mode_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="RC CONTROL",
            text_color="white",
            fg_color="#f4a261",
            corner_radius=6,
            padx=10,
            pady=10
        )
        self.control_mode_label.grid(row=row, column=0, padx=20, pady=(5, 15))
        row += 1

        ctk.CTkLabel(
            self.sidebar_frame,
            text="CONNECTION",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=row, column=0, padx=20, pady=(10, 5))
        row += 1

        self.connection_button = ctk.CTkButton(
            self.sidebar_frame,
            text=f"Switch to {'USB' if self.connection_type == 'WIFI' else 'WIFI'}",
            command=self.toggle_connection
        )
        self.connection_button.grid(row=row, column=0, padx=20, pady=5)
        row += 1

        self.connection_mode_label = ctk.CTkLabel(
            self.sidebar_frame,
            text=f"{self.connection_type} MODE",
            text_color="white",
            fg_color="#3a86ff" if self.connection_type == "WIFI" else "#7209b7",
            corner_radius=6,
            padx=10,
            pady=10
        )
        self.connection_mode_label.grid(row=row, column=0, padx=20, pady=(5, 15))
        row += 1

        ctk.CTkLabel(
            self.sidebar_frame,
            text="WING CONTROL",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=row, column=0, padx=20, pady=(5, 5))
        row += 1

        self.toggle_wing_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Toggle Wing (L/R)",
            fg_color="#5a189a",
            command=self.send_toggle_wing
        )
        self.toggle_wing_button.grid(row=row, column=0, padx=20, pady=5)
        row += 1

        self.zero_flap_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Zero Flap Angle",
            fg_color="#3c096c",
            command=self.send_zero_flaps
        )
        self.zero_flap_button.grid(row=row, column=0, padx=20, pady=5)
        row += 1

        ctk.CTkLabel(
            self.sidebar_frame,
            text="LUA CONTROL",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=row, column=0, padx=20, pady=(15, 5))
        row += 1

        self.lua_start_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Start Lua Script",
            fg_color="#2c6e49",
            command=lambda: self.trigger_lua(1)
        )
        self.lua_start_button.grid(row=row, column=0, padx=20, pady=5)
        row += 1

        self.lua_stop_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Stop Lua Script",
            fg_color="#a11d33",
            command=lambda: self.trigger_lua(0)
        )
        self.lua_stop_button.grid(row=row, column=0, padx=20, pady=5)
        row += 1

        ctk.CTkLabel(
            self.sidebar_frame,
            text="LOGGING",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=row, column=0, padx=20, pady=(15, 5))
        row += 1

        self.log_toggle_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Start Pico Logging",
            fg_color="#2a9d8f",
            command=self.toggle_pico_logging
        )
        self.log_toggle_button.grid(row=row, column=0, padx=20, pady=5)
        row += 1

        self.att_log_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Start Attitude Log",
            fg_color="#3a86ff",
            command=self.toggle_attitude_logging
        )
        self.att_log_button.grid(row=row, column=0, padx=20, pady=5)
        row += 1

        self.local_log_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Start Servo Pos Log",
            fg_color="#4361ee",
            command=self.toggle_local_logging
        )
        self.local_log_button.grid(row=row, column=0, padx=20, pady=5)
        row += 1

        ctk.CTkLabel(
            self.sidebar_frame,
            text="DEBUG",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=row, column=0, padx=20, pady=(20, 5))
        row += 1

        self.debug_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Enter Debug Mode",
            fg_color="gray",
            command=self.toggle_debug_mode
        )
        self.debug_button.grid(row=row, column=0, padx=20, pady=5)
        row += 1

        self.batch_send_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Batch Send (Debug)",
            fg_color="gray",
            state="disabled",
            command=self.batch_send_all_servos
        )
        self.batch_send_button.grid(row=row, column=0, padx=20, pady=5)
        row += 1

        self.sidebar_frame.grid_rowconfigure(row, weight=1)

    def toggle_local_logging(self):
        if not self.local_logging_active:
            self.csv_filename = f"servo_manual_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            try:
                self.csv_file = open(self.csv_filename, mode='w', newline='')
                self.csv_writer = csv.writer(self.csv_file)
                header = ['Timestamp', 'Input_Angle'] + [f'CH{i + 1}_PWM' for i in range(8)]
                self.csv_writer.writerow(header)

                self.local_logging_active = True
                self.local_log_button.configure(text="Stop Local CSV Log", fg_color="#ef233c")
                print(f"Started logging to {self.csv_filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not create log file: {e}")
        else:
            self.local_logging_active = False
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
            self.local_log_button.configure(text="Start Local CSV Log", fg_color="#4361ee")
            messagebox.showinfo("Success", f"Log saved to {self.csv_filename}")

    def _setup_main_content(self):
        """Setup main content area with dashboard and control surfaces"""
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Dashboard Section for Pico Encoder monitoring
        dash_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        dash_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        ctk.CTkLabel(dash_frame, text="Dashboard", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="w"
        )
        self.flap_wing_var = tk.StringVar(value="Testing: PORT (Left)")
        self.flap_angle_var = tk.StringVar(value="0.00 °")
        ctk.CTkLabel(dash_frame, textvariable=self.flap_wing_var, font=ctk.CTkFont(size=13, weight="bold")).grid(row=1,
                                                                                                                 column=0,
                                                                                                                 padx=10,
                                                                                                                 sticky="w")
        ctk.CTkLabel(dash_frame, textvariable=self.flap_angle_var, font=ctk.CTkFont(size=24)).grid(row=2, column=0,
                                                                                                   padx=10,
                                                                                                   pady=(0, 10),
                                                                                                   sticky="w")

        # Orientation Data
        att_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        att_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        att_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.roll_var = tk.StringVar(value="Roll: 0.00");
        self.pitch_var = tk.StringVar(value="Pitch: 0.00");
        self.yaw_var = tk.StringVar(value="Yaw: 0.00")
        ctk.CTkLabel(att_frame, textvariable=self.roll_var).grid(row=1, column=0, padx=10, pady=5)
        ctk.CTkLabel(att_frame, textvariable=self.pitch_var).grid(row=1, column=1, padx=10, pady=5)
        ctk.CTkLabel(att_frame, textvariable=self.yaw_var).grid(row=1, column=2, padx=10, pady=5)

        # Servo Control Grid
        self.servo_container = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.servo_container.grid(row=2, column=0, sticky="nsew", pady=(0, 20))
        self.servo_container.grid_columnconfigure(0, weight=1)
        self._build_servo_grid()

        # MAVLink Stream display
        manual_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        manual_frame.grid(row=3, column=0, sticky="ew")
        self.attitude_entry = ctk.CTkEntry(manual_frame, width=400, height=30,
                                           placeholder_text="-- MAVLink Raw Stream --")
        self.attitude_entry.pack(padx=20, pady=20, fill="x")

        # Flap Angle Data Logger
        self.log_status_var = tk.StringVar(value="Pico Log: Inactive")
        ctk.CTkLabel(dash_frame, textvariable=self.log_status_var, font=ctk.CTkFont(size=12, slant="italic")).grid(
            row=3, column=0, padx=10, pady=(0, 10), sticky="w")

    def toggle_control_mode(self):
        if not self.control_manager:
            return
        if self.control_manager.is_code_control():
            self.control_manager.set_rc_control()
            self.control_button.configure(
                text="Switch to CODE",
                fg_color="#2a9d8f"
            )
        else:
            self.control_manager.set_code_control()
            self.control_button.configure(
                text="Switch to RC",
                fg_color="#e63946"
            )

    def toggle_connection(self):
        import main_example
        import GS_example
        new_type = "USB" if self.connection_type == "WIFI" else "WIFI"
        print(f"Switching to {new_type}...")
        servo_config, mav = main_example.setup_mav(new_type)
        if mav:
            self.connection_type = new_type
            self.mav = mav

            self.connection_button.configure(
                text=f"Switch to {'USB' if new_type == 'WIFI' else 'WIFI'}"
            )

            self.connection_mode_label.configure(
                text=f"{new_type} MODE",
                fg_color="#3a86ff" if new_type == "WIFI" else "#7209b7"
            )

            import threading
            threading.Thread(
                target=GS_example.listen_messages,
                args=(mav,),
                daemon=True
            ).start()

            print("Reconnected successfully")
        else:
            print("Connection failed")

    def _build_servo_grid(self):
        """Clears and rebuilds the servo grid with live PWM display"""
        for widget in self.servo_container.winfo_children(): widget.destroy()
        self.surface_entries = {};
        self.pwm_display_labels = {};
        current_row = 0

        if not self.debug_mode:
            for section, surfaces in self.aircraft_mapping.items():

                ctk.CTkLabel(self.servo_container, text=section, font=ctk.CTkFont(size=15, weight="bold"),
                             text_color="#1f538d").grid(row=current_row, column=0, sticky="w", padx=20, pady=(15, 5))
                current_row += 1
                group_frame = ctk.CTkFrame(self.servo_container, fg_color="transparent")
                group_frame.grid(row=current_row, column=0, sticky="ew", padx=30, pady=(0, 10))
                for i, (surface_name, indices) in enumerate(surfaces.items()):
                    col = (i % 2) * 4;
                    row = i // 2
                    ctk.CTkLabel(group_frame, text=f"{surface_name}:").grid(row=row, column=col, padx=5, pady=5,
                                                                            sticky="e")
                    entry = ctk.CTkEntry(group_frame, width=75);
                    entry.grid(row=row, column=col + 1, padx=5, pady=5)

                    entry.bind("<KeyRelease>", lambda e, k=tuple(indices): self.update_pwm_display(k))
                    self.surface_entries[tuple(indices)] = entry

                    pwm_label = ctk.CTkLabel(group_frame, text="PWM: --", text_color="#118ab2")
                    pwm_label.grid(row=row, column=col + 2, padx=5, pady=5)
                    self.pwm_display_labels[tuple(indices)] = pwm_label

                    ctk.CTkButton(group_frame, text="Send", width=60,
                                  command=lambda idxs=indices, name=surface_name: self.send_angle(idxs, name)).grid(
                        row=row, column=col + 3, padx=5, pady=5)
                current_row += 1

        else:
            debug_frame = ctk.CTkFrame(self.servo_container, fg_color="transparent");
            debug_frame.grid(row=1, column=0, padx=30, pady=10)
            for i in range(8):
                row, col = i // 2, (i % 2) * 4
                ctk.CTkLabel(debug_frame, text=f"Servo {i + 1}:").grid(row=row, column=col, padx=5, pady=10)
                entry = ctk.CTkEntry(debug_frame, width=75);
                entry.grid(row=row, column=col + 1, padx=5)
                entry.bind("<KeyRelease>", lambda e, k=(i,): self.update_pwm_display(k))
                self.surface_entries[(i,)] = entry
                pwm_label = ctk.CTkLabel(debug_frame, text="PWM: --", text_color="#118ab2")
                pwm_label.grid(row=row, column=col + 2, padx=5)
                self.pwm_display_labels[(i,)] = pwm_label
                ctk.CTkButton(debug_frame, text="Send", width=60,
                              command=lambda idx=(i,), n=f"CH {i + 1}": self.send_angle(idx, n)).grid(row=row,
                                                                                                      column=col + 3,
                                                                                                      padx=5)

    def update_control_mode_label(self):
        if not self.control_manager:
            return

        if self.control_manager.is_code_control():
            self.control_mode_label.configure(
                text="CODE CONTROL",
                fg_color="#2a9d8f"
            )
        else:
            self.control_mode_label.configure(
                text="RC CONTROL",
                fg_color="#f4a261"
            )


        self.after(200, self.update_control_mode_label)

    def send_toggle_wing(self):
        """Sends MAVLink STATUSTEXT 'TOGGLE' to Pico via Cube forwarding"""
        if self.mav:
            text = "TOGGLE"
            self.mav.mav.statustext_send(mavutil.mavlink.MAV_SEVERITY_INFO, text.encode())

            # Update UI state
            self.active_wing_label = "FlapR" if self.active_wing_label == "FlapL" else "FlapL"
            self.flap_wing_var.set(
                f"Testing: {'STARBOARD (Right)' if self.active_wing_label == 'FlapR' else 'PORT (Left)'}")
            print(f"Sent MAVLink Text: {text}")

    def send_zero_flaps(self):
        """Sends MAVLink STATUSTEXT 'ZERO' to Pico via Cube forwarding"""
        if self.mav:
            text = "ZERO"
            self.mav.mav.statustext_send(mavutil.mavlink.MAV_SEVERITY_INFO, text.encode())
            messagebox.showinfo("Pico", "Zeroing command sent via MAVLink Text.")
            print(f"Sent MAVLink Text: {text}")

    def update_connection_label(self):
        """Slow loop (1Hz) to check if the Cube is still talking to us."""
        status = get_connection_status().capitalize()
        self.status_var.set(status)
        # Visual color cue for connection
        self.status_label.configure(text_color="green" if status == "Connected" else "red")

        # Schedule next check in 1000ms
        self.after(1000, self.update_connection_label)

    def master_update(self):
        att = get_attitude()

        r = att['roll']
        p = att['pitch']
        y = att['yaw']

        self.roll_var.set(f"Roll: {r:.2f}")
        self.pitch_var.set(f"Pitch: {p:.2f}")
        self.yaw_var.set(f"Yaw: {y:.2f}")

        if self.attitude_logging_active and self.att_csv_writer:
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            self.att_csv_writer.writerow([timestamp, r, p, y])

        self.after(5, self.master_update)

    def update_pwm_display(self, key):
        entry = self.surface_entries.get(key);
        label = self.pwm_display_labels.get(key)
        if not entry or not label: return
        try:
            angle = float(entry.get().strip())
            pwm = (20 / 3) * angle + 950
            pwm = max(DEFAULT_SERVO_CONFIG["min_pwm"], min(DEFAULT_SERVO_CONFIG["max_pwm"], pwm))
            label.configure(text=f"PWM: {int(pwm)}", text_color="#118ab2")
        except:
            label.configure(text="PWM: --")

    def send_angle(self, servo_indices, surface_name):
        if not self.mav: return
        try:
            val_str = self.surface_entries[tuple(servo_indices)].get().strip()
            angle = float(val_str)
            servo_angle_map = {}
            for idx in servo_indices:
                servo_num = idx + 1
                target_angle = (180 - angle) if (servo_num == 2 and 1 in [i + 1 for i in servo_indices]) else angle
                servo_angle_map[servo_num] = target_angle
            self._batch_send(servo_angle_map, input_angle=angle)  # 传入 angle
            messagebox.showinfo("Success", f"{surface_name} sent.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _batch_send(self, servo_angles, input_angle="N/A"):
        if not self.control_manager or not self.control_manager.is_code_control():
            print("Ignored: Not in CODE control mode")
            return
        if not self.mav:
            return

        if 1 in servo_angles and 2 not in servo_angles:
            servo_angles[2] = 180 - servo_angles[1]

        if 2 in servo_angles and 1 not in servo_angles:
            servo_angles[1] = 180 - servo_angles[2]

        # if 6 in servo_angles:
        #     servo_angles[7] = 180 - servo_angles[6]
        # elif 7 in servo_angles:
        #     servo_angles[6] = 180 - servo_angles[7]

        for servo_num, angle in servo_angles.items():

            if servo_num == 3:
                if angle == 0:
                    angle = 1
                elif angle == 180:
                    angle = 179



            if servo_num == 3:
                if angle == 380:
                    servo_angle = 65535
                else:
                    angle = max(-40, min(40, angle))
                    servo_angle = 1.3155 * angle + 90.204

            elif servo_num == 4:
                # angle = max(0, min(30, angle))
                servo_angle = 4.4753 * angle + 45.566

            elif servo_num == 5:
                angle = max(-45, min(45, angle))
                servo_angle = -0.1158 * angle -125.9285

            elif servo_num in [6, 7]:

                angle = max(-45, min(45, angle))

                base_servo_angle = 1.926 * angle + 83.4

                if servo_num == 7:
                    servo_angle = 180 - base_servo_angle - 10
                else:
                    servo_angle = base_servo_angle

            elif servo_num == 8:
                angle = max(-45, min(45, angle))
                servo_angle = 1.8305 * angle + 85

            else:
                servo_angle = angle

            servo_angle = max(0, min(180, servo_angle))

            pwm = (20 / 3) * servo_angle + 950
            pwm = max(DEFAULT_SERVO_CONFIG["min_pwm"],
                      min(DEFAULT_SERVO_CONFIG["max_pwm"], pwm))

            self.override_channels[servo_num - 1] = int(pwm)

        self.mav.mav.rc_channels_override_send(
            self.mav.target_system,
            self.mav.target_component,
            *self.override_channels
        )

        if self.local_logging_active and self.csv_writer:

            if self.override_channels != self.last_logged_positions.get("channels"):
                timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                self.csv_writer.writerow(
                    [timestamp, input_angle] + self.override_channels
                )
                self.csv_file.flush()

                self.last_logged_positions["channels"] = self.override_channels.copy()

    def batch_send_all_servos(self):
        if not self.debug_mode or not self.mav: return
        angles = {}
        for (idx,), entry in self.surface_entries.items():
            val = entry.get().strip()
            if val: angles[idx + 1] = float(val)
        if angles: self._batch_send(angles)

    def toggle_debug_mode(self):
        self.debug_mode = not self.debug_mode
        self.debug_button.configure(text="Exit Debug" if self.debug_mode else "Enter Debug",
                                    fg_color="#d35b5b" if self.debug_mode else "gray")
        self.batch_send_button.configure(state="normal" if self.debug_mode else "disabled",
                                         fg_color="#118ab2" if self.debug_mode else "gray")
        self._build_servo_grid()

    def toggle_safety(self):
        if not self.mav: return
        import Arm_example
        self.safety_enabled = not self.safety_enabled
        if Arm_example.toggle_safety_switch(self.mav, self.safety_enabled):
            self.safety_button.configure(text="Safety Enabled" if self.safety_enabled else "Safety Disabled")

    def toggle_arming(self):
        if not self.mav: return
        import Arm_example
        self.armed = not self.armed
        if Arm_example.toggle_arming_switch(self.mav, self.armed):
            self.arming_button.configure(text="Arming Enabled" if self.armed else "Arming Disabled")
            self.arming_status_label.configure(text="ARMED\nLOGGING" if self.armed else "DISARMED\nNO LOGGING",
                                               fg_color="green" if self.armed else "red")

    def trigger_lua(self, action):
        if not self.mav: return
        self.mav.mav.command_long_send(self.mav.target_system, self.mav.target_component,
                                       mavutil.mavlink.MAV_CMD_SCRIPTING, 0, 0, action, 0, 0, 0, 0, 0)

    def update_status(self):
        status = get_connection_status().capitalize()
        self.status_var.set(status);
        self.status_label.configure(text_color="green" if status == "Connected" else "red")
        self.after(1000, self.update_status)

    def toggle_pico_logging(self):
        if not self.mav:
            messagebox.showwarning("Connection", "Cube not connected!")
            return

        if not self.logging_on:
            # User wants to START
            self.mav.mav.statustext_send(mavutil.mavlink.MAV_SEVERITY_INFO, "START_LOG".encode())
            self.logging_on = True

            # Update Button Appearance
            self.log_toggle_button.configure(text="Stop Pico Logging", fg_color="#e76f51")
            self.log_status_var.set("Pico Log: RECORDING")
            print("Command Sent: START_LOG")
        else:
            # User wants to STOP
            self.mav.mav.statustext_send(mavutil.mavlink.MAV_SEVERITY_INFO, "STOP_LOG".encode())
            self.logging_on = False

            # Update Button Appearance back to default
            self.log_toggle_button.configure(text="Start Pico Logging", fg_color="#2a9d8f")
            self.log_status_var.set("Pico Log: Idle")
            print("Command Sent: STOP_LOG")
            messagebox.showinfo("Pico Logging", "Data successfully saved to Pico flash.")

    def toggle_attitude_logging(self):
        if not self.attitude_logging_active:
            self.att_filename = f"attitude_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            try:
                self.att_csv_file = open(self.att_filename, mode='w', newline='')
                self.att_csv_writer = csv.writer(self.att_csv_file)
                self.att_csv_writer.writerow(['Timestamp', 'Roll_deg', 'Pitch_deg', 'Yaw_deg'])

                self.attitude_logging_active = True
                self.att_log_button.configure(text="Stop Attitude Log", fg_color="#fb5607")
                print(f"Logging attitude to {self.att_filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create log file: {e}")
        else:
            self.attitude_logging_active = False
            if self.att_csv_file:
                self.att_csv_file.close()
                self.att_csv_file = None
            self.att_log_button.configure(text="Start Attitude Log", fg_color="#3a86ff")
            messagebox.showinfo("Success", f"Attitude log saved to {self.att_filename}")

if __name__ == "__main__":
    app = ServoUI()
    app.mainloop()

