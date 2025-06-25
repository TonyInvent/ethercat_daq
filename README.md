# EtherCAT DAQ on Raspberry Pi 4B

This guide details how to set up an EtherCAT master on a Raspberry Pi 4B (running Debian 12 or a compatible OS) and use the provided Python script (`read_daq.py`) to read data from an EtherCAT DAQ slave device.

---

## 1. Install the EtherCAT Master

First, we will add the EtherLab repository, which provides the EtherCAT master software, and install the necessary packages.

```bash
# Add the EtherLab repository GPG key
export KEYRING=/usr/share/keyrings/etherlab.gpg
curl -fsSL https://download.opensuse.org/repositories/science:/EtherLab/Debian_12/Release.key | gpg --dearmor | sudo tee "$KEYRING" >/dev/null

# Add the repository to the system's sources list
echo "deb [signed-by=$KEYRING] https://download.opensuse.org/repositories/science:/EtherLab/Debian_12/ ./" | sudo tee /etc/apt/sources.list.d/etherlab.list > /dev/null

# Update your package lists
sudo apt-get update

# Install the EtherCAT master and development libraries
sudo apt install ethercat-master libethercat-dev
```

## 2. Configure the EtherCAT Master

The master needs to be configured to use the correct network interface. 

First, find the MAC address of the Ethernet port connected to your EtherCAT devices. You can find this using the `ip a` command. Look for an interface like `eth0` and find its `link/ether` address.

Next, edit the configuration file:

```bash
sudo vi /etc/ethercat.conf
```

Inside the file, you must set `MASTER0_DEVICE` to the MAC address you found and ensure `DEVICE_MODULES` is set to `generic`.

```conf
# Replace with the MAC address of your EtherCAT network interface
MASTER0_DEVICE="xx:xx:xx:xx:xx:xx"

# Use the generic driver module
DEVICE_MODULES="generic"
```

## 3. Start the EtherCAT Service

Now, enable and start the EtherCAT service. This will bring the master online.

```bash
# Enable the service to start automatically on boot
sudo systemctl enable ethercat.service

# Start the service now
sudo systemctl start ethercat.service

# Check the status to ensure it's running correctly
sudo systemctl status ethercat.service

# Grant read/write permissions to all users for the EtherCAT device node
# This allows running client applications (like our Python script) without sudo
# Note: For production systems, consider more restrictive group-based permissions.
sudo chmod 666 /dev/EtherCAT0
```

## 4. Verify Slave Communication

With the master running, you can check if it has detected your slave devices.

```bash
# List all detected EtherCAT slaves
ethercat slaves
```

This command should output a list of all slaves connected on the bus, confirming that the hardware is communicating correctly.

## 5. Install Python Dependencies

The `read_daq.py` script uses the `pysoem` library. Install it using pip.

```bash
# Install pysoem for the system's default Python 3
sudo python3 -m pip install pysoem
```

## 6. Run the DAQ Reader Script

Finally, you are ready to run the Python script to read data from your DAQ.

1.  **Configure the Interface**: Open `read_daq.py` and ensure the `ifname` variable is set to the name of your EtherCAT network interface (e.g., `eth0`).

2.  **Run the Script**: Execute the script from your terminal.

    ```bash
    python3 read_daq.py
    ```

The script will initialize, find the DAQ device, and begin printing the analog input values to your console in real-time. Press `Ctrl+C` to stop.
