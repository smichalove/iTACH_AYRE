## This repo demonstrates python code to power toggle the Ayre v-1x using Global Cache [iTACH](https://www.amazon.com/stores/page/87D23D98-A025-47EE-AAAF-FE41280B7371?ingress=2&visitId=5ce6c02b-6105-46b7-8996-f6ff75a32544&store_ref=bl_ast_dp_brandLogo_sto&ref_=ast_bln)
* use case is
*   The V-1x does not have a 12v controller signal input/output so in order to slave it to other devices code is needed
*   This repo contains images related to orientation of the IR transmitters provided in box by iTach Global Cache
## Raw codes:
function, code1, hexcode1, code2, hexcode2

"POWER TOGGLE","sendir,1:1,1,36000,1,1,32,32,64,64,64,32,32,32,32,32,32,32,32,32,32,64,32,32,64,32,32,2487",
"0000 0073 000B 0000 0020 0020 0040 0040 0040 0020 0020 0020 0020 0020 0020 0020 0020 0020 0020 0040 0020 0020 0040 0020 0020 09B7","sendir,1:1,1,36000,1,1,32,32,32,32,32,32,64,32,32,32,32,32,32,32,32,32,32,64,32,32,64,32,32,2487",
"0000 0073 000C 0000 0020 0020 0020 0020 0020 0020 0040 0020 0020 0020 0020 0020 0020 0020 0020 0020 0020 0040 0020 0020 0040 0020 0020 09B7"

## Added powerd.py daemon like functionalty

## Home Theater Power Automation (powerd.py)
powerd.py is a Python script designed to automate the power-on sequence of a home theater system based on the detection of a specific network drive or mounted drive. It integrates with a Global Cache iTach device for IR control and an Anthem AVR for direct IP control.

Features
Drive Monitoring: Continuously checks for the presence of a specified drive (e.g., a network share, USB drive).
Use Google Home (or similar) and something like a Kasa Smartplug to turn both the V-1x and a USB drive as a hack so that CeC is not required to monitor HDMI 

Automated Power-On: When the drive is detected, the script initiates a power-on sequence after a configurable delay.

iTach Integration: Sends IR commands via a Global Cache iTach device (e.g., to power on a projector or screen).

Anthem AVR Control: Powers on an Anthem Audio/Video Receiver via its IP control interface.

Persistent State: Saves the power status to a JSON file to maintain state across restarts.

Cross-Platform Compatibility: Supports Windows and Windows Subsystem for Linux (WSL) for drive path resolution.

Configurable: All key parameters (drive letter, IP addresses, delays, etc.) are configurable via command-line arguments.

Requirements
Python 3.7+

python-anthemav library:

pip install python-anthemav


A Global Cache iTach device configured to receive commands.

An Anthem AVR connected to your network.

A designated drive (network share or local) that indicates the "on" state of your home theater.

Installation
Clone the repository:

git clone <your-repository-url>
cd <your-repository-directory>


Install dependencies:

pip install -r requirements.txt


(Note: You'll need to create a requirements.txt file containing python-anthemav if you haven't already.)

Configuration
The script uses default values for various parameters, but these can be overridden using command-line arguments.

Default Configuration
The following defaults are defined within powerd.py:

DEFAULT_DRIVE_LETTER: "F" (e.g., F: on Windows, /mnt/f/ on WSL)

DEFAULT_ITACH_HOST: "192.168.86.104"

DEFAULT_ITACH_PORT: 4998

DEFAULT_ITACH_COMMAND: "sendir,1:1,1,36000,1,1,32,32,64,64,64,32,32,32,32,32,32,32,32,32,32,64,32,32,64,32,32,2487" (Example IR command)

DEFAULT_ANTHEM_HOST: "192.168.86.72"

DEFAULT_ANTHEM_PORT: 14999

DEFAULT_POLLING_INTERVAL: 10 seconds

POWER_ON_DELAY: 30 seconds

JSON_STATUS_FILE: "power_status.json"

Command-Line Arguments
You can customize the behavior by passing arguments when running the script:

--drive <LETTER>: Specify the drive letter to monitor (e.g., --drive G).

--itach-host <IP>: Set the IP address of your iTach device.

--anthem-host <IP>: Set the IP address of your Anthem AVR.

--interval <SECONDS>: Define how often (in seconds) the script checks the drive status.

--delay <SECONDS>: Set the delay (in seconds) between drive detection and sending power-on commands.

--status-file <PATH>: Specify the path to the JSON file for storing power status.

Usage
To run the script with default settings:

python powerd.py


To run with custom settings:

python powerd.py --drive E --itach-host 192.168.1.100 --anthem-host 192.168.1.150 --interval 5 --delay 60 --status-file /var/log/power_status.json


Running in the Background (Linux/WSL)
For continuous operation, you might want to run this script in the background using nohup or systemd.

Using nohup:

nohup python powerd.py &


This will run the script in the background and redirect output to nohup.out.

Status File
The script creates and updates a power_status.json (or the file specified by --status-file) to store the current power state (power_on: true/false) and the last_change timestamp. This ensures that if the script restarts, it can pick up from its last known state.

How it Works
Initialization: The script initializes DriveChecker, ITachController, and AnthemAVRController instances with the provided configuration. It also loads the last known power status from power_status.json.

Main Loop: The run method enters an infinite loop, polling the drive status at the specified polling_interval.

Drive Detection:

If the drive is detected and the system believes it's currently "off", it starts an asynchronous _handle_power_on_sequence task.

If the drive is not detected and the system believes it's "on", it updates the status to "off" and cancels any pending power-on tasks.

Power-On Sequence (_handle_power_on_sequence):

Waits for the power_on_delay.

Re-checks if the drive is still present after the delay.

If the drive is present, it attempts to:

Send the configured IR command via the iTach device.

Connect to and power on the Anthem AVR.

Updates the power_status.json file to reflect the new "on" state.

If the drive disappears during the delay, the sequence is cancelled.

Logging: The script uses Python's logging module to provide informative messages about its operations, including connection attempts, status changes, and errors.

Troubleshooting
python-anthemav not found: Ensure you have installed the library using pip install python-anthemav.

iTach/Anthem connection refused:

Verify the IP addresses and ports are correct.

Ensure the iTach and Anthem devices are powered on and accessible on the network.

Check for firewall rules that might be blocking communication.

Drive not detected:

Double-check the drive letter and ensure it's correctly mapped/mounted.

For WSL, ensure the drive is correctly mounted under /mnt/.

Verify the drive is actually present and accessible from where the script is running.

IR commands not working:

Confirm the DEFAULT_ITACH_COMMAND is the correct IR code for your device.

Ensure the iTach device's IR emitter is properly positioned.

Script not powering on Anthem:

Verify the Anthem AVR supports IP control and is configured for it.

Check Anthem's documentation for any specific settings required for external control.

"An unhandled error occurred": Review the detailed traceback in the logs for more information.

Contributing
Feel free to fork this repository, open issues, or submit pull requests if you have improvements or bug fixes.

License
**[GNU](https://www.gnu.org/licenses/lgpl-3.0.md)**


# A note about iTACH ports
* Ports are not numbered in hardware. No documentation is provided of port numbers
* Port 1 - **farthest from Ethernet RJ46**
* Port 3 - used for IR  blaster **adjacent to RJ45**
* IR transmitter signal [path](https://github.com/smichalove/iTACH_AYRE/blob/main/itach%20IR.png)
* Blaster signal [path](https://github.com/smichalove/iTACH_AYRE/blob/main/itach%20IR.png)
* Input IR path on [v-1x](https://www.ayre.com/wp-content/uploads/2018/06/Ayre_V1xe_Manual.pdf) found on page 7

## Amazon Store ITACH
https://www.amazon.com/stores/Global+Cach%C3%A9/page/9B16D5C3-4BA1-4A4E-8331-C4AF232F1FD6?lp_asin=B003BFTKUC&ref_=ast_bln&store_ref=bl_ast_dp_brandLogo_sto

## Anthem
https://www.anthemav.com/products-current/type=av-processor/model=avm-70-8k/page=overview

## Ayre Accoustics
https://www.ayre.com/wp-content/uploads/2018/06/Ayre_V1xe_Manual.pdf

## ITACH GLOBAL CACHE IR CODE DATABASE
https://irdb.globalcache.com/Home/Database
