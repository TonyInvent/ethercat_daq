import sys
import time
import ctypes
import threading
import os

import pysoem

# Define a ctypes Structure for the PDO data based on the received data format.
# The device sends 8 channels of 32-bit floating-point values.
class ZsAi8EcatPdo(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('analog_in1', ctypes.c_float),
        ('analog_in2', ctypes.c_float),
        ('analog_in3', ctypes.c_float),
        ('analog_in4', ctypes.c_float),
        ('analog_in5', ctypes.c_float),
        ('analog_in6', ctypes.c_float),
        ('analog_in7', ctypes.c_float),
        ('analog_in8', ctypes.c_float),
    ]

def main():
    # pysoem requires raw socket access, so it needs to be run with sudo.
    # On Linux, check if the effective user ID is 0 (root).
    try:
        if os.getuid() != 0:
            print("This script must be run as root (e.g., 'sudo python3 read_daq.py')")
            sys.exit(1)
    except AttributeError:
        # os.getuid() is not available on Windows. We'll just have to hope for the best.
        print("Warning: Could not check for root privileges. The script may fail if not run as admin.")

    # --- IMPORTANT --- 
    # Change this to the name of your network interface connected to the EtherCAT bus.
    # You can find the interface name on Linux with commands like `ip a` or `ifconfig`.
    ifname = 'eth0'

    try:
        # Initialize the EtherCAT master
        master = pysoem.Master()
        master.open(ifname)
    except pysoem.SoemError as e:
        print(f'Failed to open master on interface {ifname}. Error: {e}')
        print('Please make sure the interface name is correct and the device is connected.')
        # List available interfaces to help the user
        try:
            print("Available network interfaces:")
            for adapter in pysoem.find_adapters():
                print(f'- {adapter.name}: {adapter.desc}')
        except Exception as e_find:
            print(f"Could not list network interfaces: {e_find}")
        sys.exit(1)

    # Discover slaves on the network
    slave_count = master.config_init()
    if slave_count == 0:
        print("No slaves found!")
        master.close()
        sys.exit(1)

    print(f"{slave_count} slaves found on the bus.")

    # Find the specific DAQ slave using its Vendor ID and Product Code from the XML file.
    # VendorID: #x00000b95, ProductCode: #x04570862
    PRODUCT_CODE = 0x04570862
    VENDOR_ID = 0x00000b95
    
    daq_slave = None
    for i in range(slave_count):
        slave = master.slaves[i]
        if slave.man == VENDOR_ID and slave.id == PRODUCT_CODE:
            daq_slave = slave
            print(f"Found DAQ device '{slave.name}' at position {i+1}")
            break
            
    if daq_slave is None:
        print("Could not find the ZS-AI-IV-4-ECAT device.")
        print("Please check device connection and power.")
        master.close()
        sys.exit(1)

    # Configure PDO mapping
    master.config_map()

    # Wait for all slaves to reach SAFE_OP state
    if master.state_check(pysoem.SAFEOP_STATE, timeout=5_000_000) != pysoem.SAFEOP_STATE:
        print("Not all slaves reached SAFEOP state.")
        master.close()
        sys.exit(1)

    # Set the master and slaves to OP (Operational) state
    master.state = pysoem.OP_STATE
    master.write_state()
    master.state_check(pysoem.OP_STATE, timeout=5_000_000)

    if master.state != pysoem.OP_STATE:
        print("Not all slaves reached OP state.")
        master.close()
        sys.exit(1)

    print("All slaves in OP state. Starting data acquisition...")

    # Create a thread for handling EtherCAT process data
    stop_thread = threading.Event()
    pd_thread = threading.Thread(target=process_data_thread, args=(master, stop_thread))
    pd_thread.start()

    try:
        while True:
            raw_data = bytearray(daq_slave.input)
            if len(raw_data) >= ctypes.sizeof(ZsAi8EcatPdo):
                pdo_data = ZsAi8EcatPdo.from_buffer(raw_data)
                print(
                    f"AI1: {pdo_data.analog_in1:<4.1f} | "
                    f"AI2: {pdo_data.analog_in2:<4.1f} | "
                    f"AI3: {pdo_data.analog_in3:<4.1f} | "
                    f"AI4: {pdo_data.analog_in4:<4.1f} | "
                    f"AI5: {pdo_data.analog_in5:<4.1f} | "
                    f"AI6: {pdo_data.analog_in6:<4.1f} | "
                    f"AI7: {pdo_data.analog_in7:<4.1f} | "
                    f"AI8: {pdo_data.analog_in8:<4.1f}",
                    # end='\r'
                )
            time.sleep(0.05)  # 20Hz display rate

    except KeyboardInterrupt:
        print("\nStopping data acquisition.")
    finally:
        stop_thread.set()
        pd_thread.join()
        # Set slaves back to INIT state
        print("\nSetting slaves to INIT state...")
        master.state = pysoem.INIT_STATE
        master.write_state()
        master.close()
        print("Master closed.")

def process_data_thread(master, stop_event):
    """Thread to handle EtherCAT process data cycle."""
    while not stop_event.is_set():
        master.send_processdata()
        master.receive_processdata(200000)
        # time.sleep(0.05) # 20Hz cycle rate

if __name__ == '__main__':
    main()
