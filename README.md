# iTACH_AYRE Power Daemon

Monitors a power sensor on a Global Cache iTach device and orchestrates complex power-on/off sequences involving IR commands, relay pulses, Wake-on-LAN, and Kasa Smart Home devices.

---

## Table of Contents

- [How It Works](#how-it-works)
- [Features](#features)
- [Requirements](#requirements)
- [Security & Secrets](#security--secrets)
- [Installation & Configuration](#installation--configuration)
- [Usage](#usage)
- [Hardware & Resources](#hardware--resources)

## **How It Works**

The script operates in a continuous loop (defaulting to a 15-second check interval) with the following logic:

1. **Monitor Sensor:** Polls a contact closure/voltage sensor on **port 2** of an iTach IP2IR device.
2. **Persist State:** Tracks the last known state in `power_sensor_state.txt` to handle restarts and prevent redundant triggers.
3. **Detect Transition:** Compares the current sensor state to the persisted state.
4. **Trigger Orchestration:** If a transition is detected (0 -> 1 or 1 -> 0), it triggers a sequence:
   * **IR Commands:** Sends discrete or toggle IR codes (e.g., Ayre V-1xe and AX-7).
   * **Relay Pulse:** Connects to an iTach IP2CC to pulse an external relay (e.g., for Mark Levinson 331).
   * **Kasa Smart Home:** Toggles TP-Link Kasa smart switches/plugs (e.g., for rack fans or lights).
   * **Wake-on-LAN:** Sends a magic packet to wake a configured PC.

---

## **Features**

* **Multi-Device Orchestration:** Coordinates commands across iTach IP2IR, IP2CC, and Kasa Smart Home devices simultaneously.
* **Security Hardened:** Uses environment variables for credentials—no passwords stored in the code.
* **Robust Authentication:** Automatically cycles through multiple fallback passwords for Kasa devices to handle legacy or varied credentials.
* **Persistent State:** Safely handles reboots by saving the system state to disk.
* **Modern Python:** Fully type-hinted and follows strict documentation standards for maximum maintainability.

---

## **Requirements**

* **Python 3.7+**
* **Global Cache iTach Hardware:**
  1. IP2IR (for IR control and sensor input).
  2. IP2CC (for relay/contact closure control).
* **TP-Link Kasa Device:** Any Kasa-compatible smart switch or plug.
* **Libraries:**
  * `python-kasa` (for smart home control).

---

## **Security & Secrets**

This script is designed for security. It **does not** store passwords in the `.py` file. Instead, it pulls them from your system's environment variables.

### Setting up your Secrets (Linux/Pi)
You can use the provided `powerd_secrets.example` file as a template. Create a hidden file in your home directory:
```bash
cp powerd_secrets.example ~/.powerd_secrets
nano ~/.powerd_secrets
```
Add your credentials:
```bash
# Your Kasa account email
export KASA_EMAIL="your_email@example.com"

# Your Kasa passwords (comma-separated for multi-password fallback support)
export KASA_PASSWORDS="password1,password2,password3"
```
Lock the file down:
```bash
chmod 600 /home/steven/.powerd_secrets
```

---

## **Installation & Configuration**

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/smichalove/iTACH_AYRE
    cd iTACH_AYRE
    ```
2.  **Install Dependencies:**
    ```bash
    # For virtual environments (Recommended)
    pip install -r requirements.txt

    # For global installation on modern Raspberry Pi OS:
    pip install -r requirements.txt --break-system-packages
    ```
3.  **Configure Constants:**
    Edit the top of `powerd.py` to match your local IPs and MAC addresses:
    * `IP2CC` / `HOST`: IPs of your iTach devices.
    * `KASA_DEVICE_IP`: IP of your smart switch.
    * `WOL_MAC_ADDRESS`: MAC of the PC you wish to wake.
    * `STATE_FILE` / `LOG_FILE`: These default to your home directory (`~/`) but can be customized at the top of the script.

> [!IMPORTANT]
> **Networking Tip:** This script uses hardcoded IP addresses for speed and reliability. To ensure the automation remains stable, you should configure **Static DHCP Reservations** (IP Pinning) for your iTach and Kasa devices in your router's DHCP settings so their addresses never change.

### **Network Discovery Fallback**
If you cannot pin IP addresses via DHCP and a device's IP changes, you can rediscover it by running a "ping sweep" on your local network to populate your system's ARP table:

```bash
# Example for a 192.168.8.x network
for i in {1..254}; do (ping -c 2 -W 1 192.168.8.$i | grep "from" &); done | sort -V
```
After running this, use `arp -a` to find the MAC addresses and IPs of your Global Caché or TP-Link devices.

---

## **Usage**

### Manual Run (Testing)
Before you automate the script, you should run it manually to verify the connections. **Note:** You must "source" your secrets file so the script can see your passwords:
```bash
# Source the secrets and run the script
. /home/steven/.powerd_secrets && python3 powerd.py
```

### Automation (Recommended)
Add an `@reboot` entry to your crontab to ensure it starts after power outages:
```bash
@reboot . /home/steven/.powerd_secrets && /usr/bin/python3 /home/steven/iTACH_AYRE/powerd.py >> /home/steven/logfile.txt 2>&1 &
```

> [!NOTE]
> **Logging Strategy:** This crontab entry uses `>> logfile.txt 2>&1` to capture all console output (stdout and stderr). While the script is designed to be quiet, this redirection acts as a critical "safety net" to capture interpreter-level crashes or tracebacks that might occur outside the script's internal error handling.

---

## **Hardware & Resources**

* **iHelp Discovery Tool:** [Global Caché Downloads](https://www.globalcache.com/downloads) (Used to find iTach IP addresses on your network).
* **Global Caché IP2IR iTach:** [Amazon Link](https://www.amazon.com/Global-Cache-IP2IR-iTach-Wired/dp/B003BFTKUC)
* **Global Caché IP2CC iTach:** [Amazon Link](https://www.amazon.com/Global-Cache-Contact-Closure-IP2CC-P/dp/B002ZV8FVI)
* **iTACH Voltage Sensor:** [HomeControls Link](https://www.homecontrols.com/Global-Cache-iTach-Voltage-Sensor-Cable-GCITSP1)
* **Ayre V-1xe Manual:** [PDF Link](https://www.ayre.com/wp-content/uploads/2018/06/Ayre_V1xe_Manual.pdf)

# **A note about iTACH ports**
* Port 1 - farthest from Ethernet RJ45.
* Port 3 - adjacent to RJ45.
* Port 2 - used for sensor input.
