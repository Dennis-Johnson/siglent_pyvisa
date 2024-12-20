import pyvisa
import csv
import pandas as pd
import matplotlib.pyplot as plt
from pynput import keyboard
import time
import os
import platform
from datetime import datetime

# Queried on the USB-B connection. 
RESOURCE_STRING = "USB0::62700::5168::SPD3XHBC2R0462::0::INSTR"

# Channel 1 on the two-channel DC supply I have. 
ACTIVE_CHANNEL  = 1

def get_measurements(channel):
    try:
        rm = pyvisa.ResourceManager()
        inst = rm.open_resource(RESOURCE_STRING)
        inst.timeout = 10000  # 10 seconds

        # Select the channel and measure voltage and current
        inst.write(f":INST:NSEL {channel}")
        voltage = float(inst.query(":MEAS:VOLT?").strip())
        current = float(inst.query(":MEAS:CURR?").strip())

        inst.close()
        return voltage, current
    
    except pyvisa.errors.VisaIOError as e:
        print(f"VISA I/O Error: {e}")
        return None, None
    
    except Exception as e:
        print(f"Exception: {e}")
        return None, None


keep_logging = True
request_shutdown = False


def main():
    print(f"Detected Platform {platform.system()}")
    user_temp_dir = (
        os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "Temp")
        if platform.system() == "Windows"
        else "/tmp/"
    )
    user_temp_dir = os.path.join(user_temp_dir, "power_supply_logs")
    print(f"Outputs will be stored in : {user_temp_dir}")

    filepath = os.path.join(user_temp_dir, "PD.csv")
    current_plot = os.path.join(user_temp_dir, "current.png")
    voltage_plot = os.path.join(user_temp_dir, "voltage.png")
    power_plot = os.path.join(user_temp_dir, "power.png")

    PDfile = open(filepath, "w", newline="")
    writer = csv.writer(PDfile)

    # If the file is empty, write the header
    if PDfile.tell() == 0:
        writer.writerow(["Count", "Time", "Voltage", "Current", "Power"])

    count = 0

    # Start keyboard listener. Used to initiate a shutdown later.
    def stop_logging(key):
        if not hasattr(key, "char"):
            print("invalid")
            return

        global request_shutdown
        if key.char == "r":
            print("request")
            request_shutdown = True
        elif key.char == "q" and request_shutdown:
            print("Quiting logger.")
            global keep_logging
            keep_logging = False
        else:
            print("invalid char ", key.char)
            request_shutdown = False

    listener = keyboard.Listener(on_press=stop_logging)
    listener.start()
    print("Press 'q' to quit the script")

    try:
        while keep_logging:
            count += 1
            voltage, current = get_measurements(ACTIVE_CHANNEL)

            # Ensure valid readings before writing to file
            if voltage is not None and current is not None:
                now = datetime.now()
                timestring = now.strftime("%H:%M:%S")
                power = voltage * current
                current_PD = [count, timestring, voltage, current, power]
                writer.writerow(current_PD)
                print(f"Logged: {current_PD}")

            # Sleep for a short interval to avoid rapid polling
            time.sleep(0.1)

        # Save files, plot, and cleanup.
        if not keep_logging:
            PDfile.close()
            print("Stopping logging process")

            df = pd.read_csv(filepath)
            plt.plot(df["Count"], df["Voltage"])
            plt.xlabel("time")
            plt.ylabel("voltage")
            plt.savefig(voltage_plot, format="png")
            plt.close()
            plt.plot(df["Count"], df["Current"])
            plt.xlabel("time")
            plt.ylabel("current")
            plt.savefig(current_plot, format="png")
            plt.close()
            plt.plot(df["Count"], df["Power"])
            plt.xlabel("time")
            plt.ylabel("Power")
            plt.savefig(power_plot, format="png")
            plt.close()

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
