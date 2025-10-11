# iTach Power-State Monitor and Controller

This repository contains a Python (powerd.py)  script that monitors a sensor on a Global Cache iTach device and triggers actions on a state change. It's designed to integrate devices that lack modern control inputs (like 12V triggers) by using a sensor's state (e.g., ON/OFF) to control other equipment via a separate iTach IP2CC relay and iTach IR commands.

The original use case was to power-toggle an Ayre V-1x amplifier, which does not have a 12V trigger input.

---

## Table of Contents

- [How It Works](#how-it-works)
- [Features](#features)
- [Requirements](#requirements)
- [Installation & Configuration](#installation--configuration)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [Hardware](#hardware)
- [iTach Port Information](#itach-port-information)

## **How It Works**

The script operates in a continuous loop with the following logic:

1. **Monitor Sensor:** The script continuously polls a sensor connected to **port 2** on a primary iTach device to get its current state (0 for OFF, 1 for ON).  
2. **Persist State:** It keeps track of the sensor's last known state in a simple text file (power\_sensor\_state.txt) to prevent sending redundant commands and to know the system's state across restarts.  
3. **Detect Transition:** It compares the current state to the last known state from the file.  
4. **Trigger Actions:** If a state change is detected (e.g., from OFF \-\> ON), the script performs two main actions:  
   * **Pulse Relay:** It connects to a **separate iTach IP2CC device** to send a brief pulse to a connected relay. This is useful for devices that require a momentary contact closure.  
   * **Send IR Commands:** It sends a pre-defined infrared (IR) "power toggle" command from two different ports (1 and 3\) on the primary iTach device.

---

## **Features**

* **iTach Sensor Monitoring:** Continuously checks a contact closure port on an iTach device.  
* **State Transition Detection:** Triggers actions only when the sensor state changes from ON-to-OFF or OFF-to-ON.  
* **Dual-Device Control:** Orchestrates commands across two different Global Cache devices (e.g., an IP2IR and an IP2CC).  
* **Persistent State:** Saves the last known sensor state to a local file to correctly handle script restarts.  
* **Robust & Type-Hinted:** The code is written with modern Python features, including strict type hinting for clarity and pathlib for file path management.

---

## **Requirements**

* Python 3.7+  
* Two Global Cache iTach devices accessible on your network:  
  1. An iTach for IR control and sensor input (e.g., IP2IR).  
  2. An iTach for relay/contact closure control (e.g., IP2CC).  
* A sensor compatible with the iTach's sensor port.

---

## **Installation & Configuration**
1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```
2.  **No external libraries are needed.** The script uses only standard Python libraries.
3.  **Configure the Script:**
    All configuration is done by editing the constants at the top of the `powerd.py` script. You must set the correct values for your environment.

   * IP2CC: The IP address of your iTach IP2CC (for relay control).  
   * HOST: The IP address of your primary iTach (for sensor and IR).  
   * STATE\_FILE: The full path to the file where the script will store the sensor's state (e.g., Path("d:/python/power\_sensor\_state.txt")). The script will attempt to create the directory if it doesn't exist.  
   * POWER\_TOGGLE\_COMMAND: The raw Global Cache sendir command string for your device.

---

## **Usage**

To run the script continuously, execute it from your terminal:

```bash
python powerd.py
```

To run it as a background process on Linux or macOS, you can use nohup:

```bash
nohup python powerd.py &
```

This will run the script in the background and redirect its output to a file named nohup.out.

---

## **Troubleshooting**

* **Connection Refused/Timeout:**  
  * Verify the HOST and IP2CC IP addresses are correct in the script.  
  * Ensure both iTach devices are powered on and connected to the network.  
  * Check for firewall rules that might be blocking communication on port 4998\.  
* **IR Commands Not Working:**  
  * Confirm the POWER\_TOGGLE\_COMMAND is the correct sendir code for your device.  
  * Ensure the iTach device's IR emitter is correctly positioned over your equipment's IR receiver.  
* **Relay Not Pulsing:**  
  * Double-check the IP2CC address.  
  * Ensure your relay is wired correctly to the IP2CC's contact closure port.  
* **Script Errors on Startup:**  
  * Make sure the path for STATE\_FILE is valid and that the script has permission to write to that location.

---

## **Hardware & Resources**

* **Used in this Code:**  
  * **Global Caché IP2IR iTach TCP/IP to IR Converter:** Used for sending IR commands and monitoring the sensor port.  
  * **Global Caché IP2CC-P iTach TCP/IP to Contact Closure Converter:** Used for pulsing the external relay.  
  * **iTACH Voltage Sensor:** A compatible sensor for detecting state changes.  
* **Links:**  
  * **Ayre V-1xe Manual:** [PDF Link](https://www.ayre.com/wp-content/uploads/2018/06/Ayre_V1xe_Manual.pdf)  
  * **Global Cache IR Database:** [irdb.globalcache.com](https://irdb.globalcache.com/Home/Database)  
  * **Amazon Store:** [Global Caché](https://www.google.com/search?q=https://www.amazon.com/stores/Global%2BCach%25C3%25A9/page/9B16D5C3-4BA1-4A4E-8331-C4AF232F1FD6)
## *Hardware Used*
* *Global Caché IP2IR iTach TCP/IP to IR Converter*

Connects Infrared Control Devices to a Wired Ethernet.

https://www.amazon.com/Global-Cache-IP2IR-iTach-Wired/dp/B003BFTKUC

* *Global Caché IP2CC-P iTach TCP/IP to Contact Closure Converter With Power Over Ethernet.*

https://www.amazon.com/Global-Cache-Contact-Closure-IP2CC-P/dp/B002ZV8FVI

* *iTACH Voltage Sensor*

https://www.homecontrols.com/Global-Cache-iTach-Voltage-Sensor-Cable-GCITSP1

# **A note about iTACH ports**

* Ports are not numbered in hardware. No documentation is provided of port numbers  
* Port 1 \- farthest from Ethernet RJ46  
* Port 3 \- used for IR blaster adjacent to RJ45  
* IR transmitter signal [path](https://github.com/smichalove/iTACH_AYRE/blob/main/itach%20IR.png)  
* Blaster signal [path](https://github.com/smichalove/iTACH_AYRE/blob/main/itach%20IR.png)  
* Input IR path on [v-1x](https://www.ayre.com/wp-content/uploads/2018/06/Ayre_V1xe_Manual.pdf) found on page 7
