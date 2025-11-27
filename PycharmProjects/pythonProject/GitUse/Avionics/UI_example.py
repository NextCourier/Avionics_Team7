##########################################
#UI example python script for AVDASI 2 AVIONICS
#Creates a barebones UI for your GS
#shows connections status
#Arming button
#Safety switch toggle button
#Set servo angle
#Author: Ethan Sheehan

#This file should be able to run independently
#Potential upgrades:
    #Make it actually look good
    #Allow multiple servos simulatneously
    #Mode switching
    #Flap position
    #Flap angle graph
    #Live data graphing
    #Use another module/code to make it look better (tkinter has its limits)
    #Make it run faster/smoother/better response time

##########################################

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

import Servo_example
import GS_example
import Arm_example

class ServoUI(ctk.CTk):
    def __init__(self, servo_config=None):
        # Initialize the main window
        super().__init__()
        self.title("Servo Control")
        self.geometry("800x600")
        self.servo_config = servo_config
        
        ctk.set_appearance_mode("light") #You can change it to light mode if you wanna be boring :P
        ctk.set_default_color_theme("blue")

        #Configure main window grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left area for status
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1) # Push content down

        #Main Content frame
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=0) #Allows dashboard area to expand
        self.main_frame.grid_rowconfigure(1, weight=1) 

        # Initialize variables
        self.safety_enabled = True
        self.armed = False
        self.angle_entries = [] 

        # Populate the frames
        self._setup_sidebar()
        self._setup_main_content()

        # Start status updater loop
        self.update_status()

    # --- Setup Functions ---

    def _setup_sidebar(self):
        #Left status display
        ctk.CTkLabel(self.sidebar_frame, text="Status display", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10))
        
        #Connection Status
        self.status_var = tk.StringVar(value=GS_example.connection_status.capitalize())
        
        status_label = ctk.CTkLabel(self.sidebar_frame, textvariable=self.status_var)
        status_label.grid(row=1, column=0, padx=20, pady=(5, 5))
        self.status_label = status_label 

        #Safety & Arming Controls
        self.safety_button = ctk.CTkButton(
            self.sidebar_frame, text="Safety Enabled", command=self.toggle_safety
        )
        self.safety_button.grid(row=2, column=0, padx=20, pady=5)

        self.arming_button = ctk.CTkButton(
            self.sidebar_frame, text="Arming Disabled", command=self.toggle_arming
        )
        self.arming_button.grid(row=3, column=0, padx=20, pady=5)
        
        #Disarmed Status Label
        self.arming_status_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="DISARMED\nNO LOGGING",
            text_color="white",
            fg_color="red",
            corner_radius=6
        )
        self.arming_status_label.grid(row=5, column=0, padx=20, pady=(10, 20), sticky="s")


    def _setup_main_content(self):
        # A. Data Display Area 
        data_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        data_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        data_frame.grid_columnconfigure(0, weight=1)
        
        # Placeholder Label
        ctk.CTkLabel(data_frame, text="AERA FOR DASHBOARD :P",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        # Flap Data Display (work in progress)
        ctk.CTkLabel(data_frame, text="Flap Position: --", justify="right").grid(row=1, column=0, padx=10, sticky="e")
        ctk.CTkLabel(data_frame, text="Flap Angle: -- °", justify="right").grid(row=2, column=0, padx=10, pady=(0, 10), sticky="e")
        
        #Servo controls
        controls_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        controls_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        controls_frame.grid_columnconfigure(0, weight=1)
        controls_frame.grid_columnconfigure(1, weight=1)

        #Servo angles
        angle_group_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        angle_group_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        for i in range(1, 4):
            row = i - 1
            label_text = f"Angle {i} (°):"
            
            ctk.CTkLabel(angle_group_frame, text=label_text).grid(row=row, column=0, sticky="w", padx=5, pady=5)
            
            angle_entry = ctk.CTkEntry(angle_group_frame, width=80)
            angle_entry.grid(row=row, column=1, padx=5, pady=5)
            self.angle_entries.append(angle_entry)
            
            # Use lambda to pass the correct index (i.e., which servo)
            ctk.CTkButton(angle_group_frame, text="Send", width=60, 
                          command=lambda idx=i: self.send_angle(idx - 1)).grid(row=row, column=2, padx=5, pady=5)

        #attitude
        attitude_group_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        attitude_group_frame.grid(row=0, column=1, padx=20, pady=20, sticky="e")
        
        ctk.CTkLabel(attitude_group_frame, text="ATTITUDE (m)").pack(pady=(0, 5))
        
        #Attitude Display
        self.attitude_entry = ctk.CTkEntry(attitude_group_frame, width=215,height=30, 
                                           font=ctk.CTkFont(size=16, weight="bold"), 
                                           placeholder_text="-- Mission Planner Data --")
        self.attitude_entry.pack(pady=(0, 5))
        

    

    def toggle_safety(self):
        # Toggles the safety switch state
        if not self.servo_config:
            messagebox.showwarning("Not connected", "Connect first.")
            return
            
        mav = getattr(self.servo_config, 'mav', None)
        if not mav:
             messagebox.showwarning("Error", "MAVLink connection not initialized.")
             return
             
        new_state = not self.safety_enabled
        success = Arm_example.toggle_safety_switch(mav, new_state) 
        
        if success:
            self.safety_enabled = new_state
            self.safety_button.configure(text="Safety Enabled" if self.safety_enabled else "Safety Disabled")
        else:
            messagebox.showerror("Safety Switch", "Failed to toggle safety switch.")

    def toggle_arming(self):
        # Toggles the arming state
        if not self.servo_config:
            messagebox.showwarning("Not connected", "Connect first.")
            return
            
        mav = getattr(self.servo_config, 'mav', None)
        if not mav:
             messagebox.showwarning("Error", "MAVLink connection not initialized.")
             return
             
        self.armed = not self.armed
        success = Arm_example.toggle_arming_switch(mav, self.armed)
        
        if success:
            if self.armed:
                self.arming_button.configure(text="Arming Enabled")
                self.arming_status_label.configure(text="ARMED\nAND LOGGING", fg_color="green")
            else:
                self.arming_button.configure(text="Arming Disabled")
                self.arming_status_label.configure(text="DISARMED\nNO LOGGING", fg_color="red")
        
    def update_status(self):
        # Updates the connection status label
        status = GS_example.connection_status.capitalize() 
        self.status_var.set(status) 
        
        # Change color based on status
        color = "green" if status == "Connected" else "red"
        self.status_label.configure(text_color=color)
        
        self.after(1000, self.update_status)

    def send_angle(self, servo_index: int):
        # Sends angle value entered by the user to the specific servo
        if not self.servo_config: 
            messagebox.showwarning("Not connected", "Connect first.")
            return
        try:
            angle = float(self.angle_entries[servo_index].get())
            # self.servo_config.send_angle(servo_index + 1, angle) # Actual send command
            messagebox.showinfo("Sent", f"Sent angle {angle}° to Servo {servo_index + 1}")
        except ValueError:
            messagebox.showerror("Input Error", "Please enter a valid number for the angle.")
        except Exception as e: 
            messagebox.showerror("Send Error", str(e))

# Independence call
if __name__ == "__main__":
    # Create the ctk root and run the application
    servo_config = None
    try:
        servo_config = Servo_example()  
        GS_example.connection_status = "connected" 
    except Exception as e: 
        GS_example.connection_status = "disconnected" 
        servo_config = None

    app = ServoUI(servo_config)
    app.mainloop()