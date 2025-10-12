"""
Monitors a power sensor on a Global Cache iTach device and toggles power.

This script connects to a Global Cache iTach device to monitor a sensor
(like a relay) connected to port 2. It treats this port as a power sensor,
where a state of '0' is OFF and '1' is ON.

The script's primary function is to detect a change in the power sensor's
state (a "state transition"). When the sensor state changes from OFF to ON
(0 -> 1) or from ON to OFF (1 -> 0), the script triggers a sequence of commands.

A special condition exists for the very first time the sensor transitions from
OFF to ON during a single run of the script. In this "first power-on" event,
an additional 12-second delay is introduced after an initial relay pulse to
allow an amplifier time to boot up before a second relay pulse and subsequent
IR commands are sent.

To avoid sending commands repeatedly on every check, the script persists the
last known state of the sensor in a local file. It assumes an initial state
of OFF on its first run. The script runs in a continuous loop, checking the
sensor every 15 seconds until manually stopped (Ctrl+C).

All actions and errors are logged to /home/steve/logfile.txt.
"""
import socket
import sys
import time
import struct
import logging
from pathlib import Path
from typing import Optional

# --- Configuration ---
IP2CC: str = "192.168.86.105"  # IP of iTach IP2CC (for relay)
HOST: str = "192.168.86.121"   # IP of iTach (for sensor and IR)
PORT: int = 4998               # Default command port for iTach devices
TIMEOUT: int = 5               # Connection timeout in seconds
BUFFER_SIZE: int = 1024        # Buffer for receiving data
# Use pathlib for robust cross-platform path handling
# NOTE: Path updated to /home/steven/ as requested.
STATE_FILE: Path = Path("/home/steven/power_sensor_state.txt")
LOG_FILE: Path = Path("/home/steven/logfile.txt")

# --- Wake-on-LAN Configuration ---
# MAC address of the PC to wake up.
WOL_MAC_ADDRESS: str = "24-4B-FE-CC-05-D6"
WOL_BROADCAST_ADDRESS: str = "192.168.86.255"

# --- iTach Command Definitions ---
POWER_TOGGLE_COMMAND: str = "sendir,1:1,1,36000,1,1,32,32,64,64,64,32,32,32,32,32,32,32,32,32,32,64,32,32,64,32,32,2487"
GET_SENSOR_STATE_COMMAND: str = "getstate,1:2"

# --- State Management Functions ---

def get_last_sensor_state() -> str:
    """
    Reads the last known sensor state from the state file.
    If the file doesn't exist or an error occurs, it defaults to '0' (OFF).
    """
    if not STATE_FILE.exists():
        # Assume the initial state is OFF ('0') if no state file is found.
        return '0'
    try:
        return STATE_FILE.read_text().strip()
    except Exception as e:
        logging.error(f"Error reading state file: {e}")
        return '0' # Default to '0' on error to be safe

def set_sensor_state(state: str) -> None:
    """Writes the sensor's current state to the state file for persistence."""
    try:
        STATE_FILE.write_text(state)
        logging.info(f"State change recorded. New baseline state is: {state}")
    except Exception as e:
        logging.error(f"Error writing to state file: {e}")

# --- Network & Command Functions ---

def send_command(sock: socket.socket, command: str, command_name: str = "command") -> Optional[str]:
    """Sends a command to the iTach device and returns the response."""
    logging.info(f"Sending {command_name}: {command}")
    try:
        # iTach commands must be terminated with a carriage return
        full_command = (command + "\r").encode('ascii')
        sock.sendall(full_command)
        response = sock.recv(BUFFER_SIZE).decode('ascii').strip()
        logging.info(f"Received response: {response}")
        return response
    except socket.timeout:
        logging.warning(f"TIMEOUT on '{command_name}'. No response from device.")
        return None
    except Exception as e:
        logging.error(f"Error sending '{command_name}': {e}")
        return None

def pulse_ip2cc_relay() -> None:
    """
    Connects to the IP2CC and sends a momentary 250ms pulse to relay 1.
    This function establishes a new connection, sends the commands to
    close and then open the relay, and then closes the connection.
    This is needed to be compatiple with the mark levinson 331
    """
    logging.info("Pulsing relay on IP2CC...")
    ip2cc_sock: Optional[socket.socket] = None
    try:
        # Establish connection to the iTach IP2CC device
        ip2cc_sock = socket.create_connection((IP2CC, PORT), timeout=TIMEOUT)
        close_relay_cmd = "setstate,1:1,1"
        open_relay_cmd = "setstate,1:1,0"

        # 1. Close the relay (turn it ON)
        send_command(ip2cc_sock, close_relay_cmd, "IP2CC_RELAY_CLOSE")
        # 2. Wait for 350 milliseconds
        time.sleep(0.35)
        # 3. Open the relay (turn it OFF)
        send_command(ip2cc_sock, open_relay_cmd, "IP2CC_RELAY_OPEN")
        time.sleep(2.25)
        logging.info("IP2CC relay pulse complete.")

    except (socket.timeout, ConnectionRefusedError) as e:
        logging.error(f"Connection to IP2CC {IP2CC} failed: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during IP2CC relay pulse: {e}")
    finally:
        if ip2cc_sock:
            ip2cc_sock.close()

def wake_on_lan(mac_address: str, broadcast_address: str) -> None:
    """
    Sends a Wake-on-LAN magic packet to the specified MAC address.

    Args:
        mac_address (str): The MAC address of the target computer.
        broadcast_address (str): The broadcast address of the network.
    """
    logging.info(f"Attempting to wake PC with MAC: {mac_address}")
    try:
        # Remove any separators from the MAC address and convert to bytes
        mac_bytes = bytes.fromhex(mac_address.replace(':', '').replace('-', ''))

        # The magic packet is 6 bytes of FF followed by 16 repetitions of the MAC address
        magic_packet = b'\xff' * 6 + mac_bytes * 16

        # Create a UDP socket
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            # Enable broadcasting mode
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            # Send the magic packet to the broadcast address on port 9
            sock.sendto(magic_packet, (broadcast_address, 9))
            logging.info(f"Wake-on-LAN magic packet sent to {mac_address} via {broadcast_address}")
    except Exception as e:
        logging.error(f"Failed to send Wake-on-LAN packet: {e}")


# --- Main Logic ---

def monitor_sensor_and_toggle_on_change(first_power_on_check: bool) -> bool:
    """
    Checks the power sensor, and if a state transition is detected,
    triggers the relay pulse and IR commands. It also handles the special
    one-time delay logic for the first power-on event.

    Args:
        first_power_on_check: A boolean flag that is True if the script has not yet
                              detected its first OFF-to-ON transition.

    Returns:
        The updated state of the first_power_on_check flag. It will be set to
        False after the first power-on event occurs.
    """
    last_state: str = get_last_sensor_state()
    state_desc: str = 'ON' if last_state == '1' else 'OFF'
    logging.info(f"Waiting for sensor state to change from: {last_state} ({state_desc})")

    s: Optional[socket.socket] = None
    try:
        # Create a single connection for this check cycle
        s = socket.create_connection((HOST, PORT), timeout=TIMEOUT)
        response = send_command(s, GET_SENSOR_STATE_COMMAND, "GET_SENSOR_STATE")

        if not response or not response.startswith('state,1:2,'):
            logging.warning("Could not get valid sensor state. Skipping this cycle.")
            return first_power_on_check # Return the flag unchanged

        current_state: str = response.split(',')[-1]

        if current_state != last_state:
            # --- BRANCH 1: Transition from OFF to ON ---
            if last_state == '0' and current_state == '1':
                logging.info("*** DETECTED TRANSITION: OFF -> ON. Triggering actions. ***")
                
                # Per amplifier manual: First pulse brings amp from OFF to STANDBY.
                logging.info("Sending first pulse (OFF -> STANDBY)...")
                pulse_ip2cc_relay()

                # Per manual: Wait for power supply to charge.
                logging.info("Waiting for amplifier power supply to charge (12s)...")
                time.sleep(12)

                # Special handling for the very first power-on event during this script's run.
                if first_power_on_check:
                    logging.info("First power-on: Waking up PC.")
                    wake_on_lan(WOL_MAC_ADDRESS, WOL_BROADCAST_ADDRESS)
                    first_power_on_check = False

                # Send IR power toggle command to the pre-amp and other devices
                logging.info("Sending IR power toggle command to port 1...")
                send_command(s, POWER_TOGGLE_COMMAND, "POWER_TOGGLE_IR_PORT1")
                time.sleep(1)
                logging.info("Sending IR power toggle command to port 3...")
                send_command(s, POWER_TOGGLE_COMMAND.replace(",1:1,", ",1:3,"), "POWER_TOGGLE_IR_PORT3")

                # Per manual: Second pulse brings amp from STANDBY to OPERATE.
                logging.info("Sending second pulse (STANDBY -> OPERATE)...")
                pulse_ip2cc_relay()
            # --- BRANCH 2: Transition from ON to OFF ---
            elif last_state == '1' and current_state == '0':
                logging.info("*** DETECTED TRANSITION: ON -> OFF. Triggering actions. ***")
                
                # For powering off, send IR commands first, then pulse the amplifier relay last.
                send_command(s, POWER_TOGGLE_COMMAND.replace("sendir,1:1", "sendir,1:1"), "POWER_TOGGLE_PORT_1")
                time.sleep(1)
                send_command(s, POWER_TOGGLE_COMMAND.replace("sendir,1:1", "sendir,1:3"), "POWER_TOGGLE_PORT_3")
                time.sleep(1) # Brief pause before turning off amp
                pulse_ip2cc_relay()

            # After either transition, persist the new state.
            set_sensor_state(current_state)
        else:
            logging.info(f"Sensor state remains {current_state}. No action needed.")

    except (socket.timeout, ConnectionRefusedError) as e:
        logging.error(f"Connection to {HOST} failed: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        if s:
            s.close()

    # Return the potentially updated flag
    return first_power_on_check

# --- Main Loop ---

if __name__ == "__main__":
    # --- Setup Logging ---
    # Ensure the directory for the log file and state file exists.
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Configure logging to write to a file and to the console.
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(LOG_FILE, mode='a'), # Append to the log file
                logging.StreamHandler(sys.stdout)       # Also output to console
            ]
        )
    except OSError as e:
        # If logging can't be set up, print to stderr and exit.
        print(f"!!! CRITICAL: Could not create log file directory {LOG_FILE.parent}. Error: {e}", file=sys.stderr)
        sys.exit(1)

    logging.info("--- Script starting up ---")

    # This flag tracks if the script needs to perform the special one-time
    # amplifier boot-up delay. It's set to False after the first
    # OFF-to-ON power event is detected and handled.
    is_first_power_on_event = True

    try:
        while True:
            # Pass the flag to the function and update it with the return value.
            is_first_power_on_event = monitor_sensor_and_toggle_on_change(is_first_power_on_event)
            logging.info("--- Waiting for 15 seconds before next check ---")
            time.sleep(15)
    except KeyboardInterrupt:
        logging.info("Script stopped by user. Exiting.")
        sys.exit(0)
    except Exception as e:
        logging.critical(f"An unhandled exception occurred: {e}", exc_info=True)
        sys.exit(1)