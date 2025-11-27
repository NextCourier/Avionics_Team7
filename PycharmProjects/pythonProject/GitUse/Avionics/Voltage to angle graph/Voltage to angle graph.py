import pandas as pd
import matplotlib.pyplot as plt

voltage_data = pd.read_csv("Lua Script Voltage Log.csv") #read csv file

time = voltage_data["Time [ms]"]
sensor0 = voltage_data[" Sensor0 [mV]"]

plt.figure(figsize = (10,5))   #plot voltage vs time graph
plt.plot(time, sensor0, color = "red")
plt.xlabel("Time [ms]")
plt.ylabel("Voltage [mV]")
plt.title("Voltage vs time for potentiometer")

plt.savefig("Voltage-angle_graph.jpg",dpi=300, bbox_inches = "tight")   #save graph
plt.show()

