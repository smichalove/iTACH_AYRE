"""
Monitors a power sensor on a Global Cache iTach device and toggles power.

This script connects to a Global Cache iTach device to monitor a sensor
(like a relay) connected to port 2. It treats this port as a power sensor,
where a state of '0' is OFF and '1' is ON.

The script's primary function is to detect a change in the power sensor's
state (a "state transition"). When the sensor state changes from OFF to ON
(0 -> 1) or from ON to OFF (1 -> 0), the script:
1. Sends a 250ms pulse to a relay on a separate iTach IP2CC device.
2. Sends an infrared (IR) "power toggle" command to two separate IR ports
   (port 1 and port 3) on the primary iTach device.

To avoid sending commands repeatedly, the script persists the last known
state of the sensor in a local file. It assumes an initial state of OFF
on its first run. The script runs in a continuous loop, checking the sensor
every 15 seconds until manually stopped (Ctrl+C).
"""
import socket
import sys
import time
from pathlib import Path
from typing import Optional

# --- Configuration ---
start_state: int = 0
IP2CC: str = "192.168.86.105"  # IP of iTach IP2CC (for relay)
HOST: str = "192.168.86.121"    # IP of iTach (for sensor and IR)
PORT: int = 4998               # Default command port for iTach devices
TIMEOUT: int = 5               # Connection timeout in seconds
BUFFER_SIZE: int = 1024        # Buffer for receiving data
# Use pathlib for robust path handling
STATE_FILE: Path = Path("d:/python/power_sensor_state.txt")

# --- iTach Command Definitions ---
POWER_TOGGLE_COMMAND: str = "sendir,1:1,1,36000,1,1,32,32,64,64,64,32,32,32,32,32,32,32,32,32,32,64,32,32,64,32,32,2487"
GET_SENSOR_STATE_COMMAND: str = "getstate,1:2"

# --- State Management Functions ---

def get_last_sensor_state() -> str:
    """Reads the last known sensor state from the state file."""
    if not STATE_FILE.exists():
        # Assume the initial state is OFF ('0')
        return '0'
    try:
        return STATE_FILE.read_text().strip()
    except Exception as e:
        print(f"!!! ERROR reading state file: {e}", file=sys.stderr)
        return '0' # Default to '0' on error

def set_sensor_state(state: str) -> None:
    """Writes the sensor's current state to the state file."""
    try:
        STATE_FILE.write_text(state)
        print(f"--> State change recorded. New baseline state is: {state}")
    except Exception as e:
        print(f"!!! ERROR writing to state file: {e}", file=sys.stderr)

# --- Network & Command Functions ---

def send_command(sock: socket.socket, command: str, command_name: str = "command") -> Optional[str]:
    """Sends a command to the iTach device and returns the response."""
    print(f"--> Sending {command_name}: {command}")
    try:
        full_command = (command + "\r\n").encode('ascii')
        sock.sendall(full_command)
        response = sock.recv(BUFFER_SIZE).decode('ascii').strip()
        print(f"<-- Received response: {response}")
        return response
    except socket.timeout:
        print(f"!!! TIMEOUT on '{command_name}'.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"!!! ERROR sending '{command_name}': {e}", file=sys.stderr)
        return None

def pulse_ip2cc_relay() -> None:
    """Connects to the IP2CC and sends a momentary 250ms pulse to relay 1."""
    global start_state
    print("--> Pulsing relay on IP2CC...")
    ip2cc_sock: Optional[socket.socket] = None
    try:
        ip2cc_sock = socket.create_connection((IP2CC, PORT), timeout=TIMEOUT)
        close_relay_cmd = "setstate,1:1,1"
        open_relay_cmd = "setstate,1:1,0"

        # 1. Close the relay
        send_command(ip2cc_sock, close_relay_cmd, "IP2CC_RELAY_CLOSE")
        # 2. Wait
        time.sleep(0.25)
        # 3. Open the relay
        send_command(ip2cc_sock, open_relay_cmd, "IP2CC_RELAY_OPEN")

        if start_state == 0:
            print("Wait for Aplifier to Boot...")
            time.sleep(6)
            send_command(ip2cc_sock, close_relay_cmd, "IP2CC_RELAY_CLOSE")
            time.sleep(0.25)
            send_command(ip2cc_sock, open_relay_cmd, "IP2CC_RELAY_OPEN")
            start_state += 1
        
        print("--> IP2CC relay pulse complete.")

    except (socket.timeout, ConnectionRefusedError) as e:
        print(f"!!! ERROR: Connection to IP2CC {IP2CC} failed: {e}", file=sys.stderr)
    except Exception as e:
        print(f"!!! An unexpected error occurred during IP2CC relay pulse: {e}", file=sys.stderr)
    finally:
        if ip2cc_sock:
            ip2cc_sock.close()

# --- Main Logic ---

def monitor_sensor_and_toggle_on_change() -> None:
    """Checks the power sensor and triggers commands on a state transition."""
    last_state: str = get_last_sensor_state()
    state_desc: str = 'ON' if last_state == '1' else 'OFF'
    print(f"\nWaiting for sensor state to change from: {last_state} ({state_desc})")

    s: Optional[socket.socket] = None
    try:
        s = socket.create_connection((HOST, PORT), timeout=TIMEOUT)
        response = send_command(s, GET_SENSOR_STATE_COMMAND, "GET_SENSOR_STATE")

        if not response or not response.startswith('state,1:2,'):
            print("!!! Could not get valid sensor state. Skipping this cycle.")
            return

        current_state: str = response[-1]

        if current_state != last_state:
            if last_state == '0' and current_state == '1':
                print("*** DETECTED TRANSITION: OFF -> ON. Toggling power. ***")
            elif last_state == '1' and current_state == '0':
                print("*** DETECTED TRANSITION: ON -> OFF. Toggling power. ***")

            pulse_ip2cc_relay()

            send_command(s, POWER_TOGGLE_COMMAND.replace("sendir,1:1", "sendir,1:1"), "POWER_TOGGLE_PORT_1")
            time.sleep(1) # Brief pause
            send_command(s, POWER_TOGGLE_COMMAND.replace("sendir,1:1", "sendir,1:3"), "POWER_TOGGLE_PORT_3")

            set_sensor_state(current_state)
        else:
            print(f"--> Sensor state remains {current_state}. No action needed.")

    except (socket.timeout, ConnectionRefusedError) as e:
        print(f"!!! ERROR: Connection to {HOST} failed: {e}", file=sys.stderr)
    except Exception as e:
        print(f"!!! An unexpected error occurred: {e}", file=sys.stderr)
    finally:
        if s:
            s.close()

# --- Main Loop ---

if __name__ == "__main__":
    # Ensure the directory for the state file exists
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"!!! CRITICAL: Could not create directory {STATE_FILE.parent}. Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        while True:
            monitor_sensor_and_toggle_on_change()
            print("\n--- Waiting for 15 seconds before next check ---")
            time.sleep(15)
    except KeyboardInterrupt:
        print("\nScript stopped by user. Exiting.")
        sys.exit(0)
