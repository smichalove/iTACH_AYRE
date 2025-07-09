"""
Monitors a power sensor on a Global Cache iTach device and toggles power.

This script connects to a Global Cache iTach device to monitor a sensor
(like a relay) connected to port 2. It treats this port as a power sensor,
where a state of '0' is OFF and '1' is ON.

The script's primary function is to detect a change in the power sensor's
state (a "state transition"). When the sensor state changes from OFF to ON
(0 -> 1) or from ON to OFF (1 -> 0), the script sends an infrared (IR)
"power toggle" command to two separate IR ports (port 1 and port 3).

To avoid sending commands repeatedly, the script persists the last known
state of the sensor in a local file (`power_sensor_state.txt`). It assumes
an initial state of OFF on its first run. The script runs in a continuous
loop, checking the sensor every 30 seconds until manually stopped (Ctrl+C).
"""
import socket
import sys
import time
import os

# --- Configuration ---
HOST = "192.168.86.126"  # IP address of your Global Cache iTach device
PORT = 4998              # Default command port for iTach devices
TIMEOUT = 5              # Connection timeout in seconds
BUFFER_SIZE = 1024       # Buffer for receiving data
STATE_FILE = "power_sensor_state.txt" # File to store the sensor's last state

# --- iTach Command Definitions ---
# This IR command should be the 'power toggle' for your AV device.
POWER_TOGGLE_COMMAND = "sendir,1:1,1,36000,1,1,32,32,64,64,64,32,32,32,32,32,32,32,32,32,32,64,32,32,64,32,32,2487"

# Command to get the power state from the sensor on module 1, port 2
GET_SENSOR_STATE_COMMAND = "getstate,1:2"

# --- State Management Functions ---

def get_last_sensor_state():
    """
    Reads the last known sensor state from the state file.

    If the state file does not exist (e.g., on the first run), it defaults
    to '0' to align with the initial assumption that the connected device
    is powered off.

    Returns:
        str: The last known state ('0' for OFF, '1' for ON).
    """
    if not os.path.exists(STATE_FILE):
        # Assume the initial state is OFF ('0') as requested.
        return '0'
    try:
        with open(STATE_FILE, "r") as f:
            return f.read().strip()
    except Exception as e:
        print(f"!!! ERROR reading state file: {e}", file=sys.stderr)
        return '0'

def set_sensor_state(state):
    """
    Writes the sensor's current state to the state file.

    This function is called after a state transition has been detected and
    handled. It overwrites the file with the new state, establishing a new
    baseline for future checks.

    Args:
        state (str): The new state to write to the file ('0' or '1').
    """
    try:
        with open(STATE_FILE, "w") as f:
            f.write(state)
        print(f"--> State change recorded. New baseline state is: {state}")
    except Exception as e:
        print(f"!!! ERROR writing to state file: {e}", file=sys.stderr)

# --- Network & Command Functions ---

def send_command(sock, command, command_name="command"):
    """
    Sends a command to the iTach device and returns the response.

    This is a general-purpose function that handles encoding the command
    string, sending it over the provided socket connection, and decoding
    the response from the device.

    Args:
        sock (socket.socket): The active socket connection to the iTach.
        command (str): The command string to send (e.g., "getstate,1:2").
        command_name (str, optional): A friendly name for the command for
                                      logging purposes. Defaults to "command".

    Returns:
        str or None: The stripped response string from the device, or None
                     if a timeout or other error occurs.
    """
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

# --- Main Logic ---

def monitor_sensor_and_toggle_on_change():
    """
    Checks the power sensor and triggers IR commands on a state transition.

    This is the core logic function. It performs the following steps:
    1. Gets the last known state from the state file.
    2. Connects to the iTach and queries the current sensor state.
    3. Compares the current state to the last known state.
    4. If they differ (a transition occurred), it sends the power toggle
       command to both IR ports and updates the state file with the new state.
    5. If they are the same, it does nothing.
    """
    last_state = get_last_sensor_state()
    print(f"\nWaiting for sensor state to change from: {last_state} ({'ON' if last_state == '1' else 'OFF'})")

    s = None
    try:
        s = socket.create_connection((HOST, PORT), timeout=TIMEOUT)

        # 1. Get the current power sensor state from port 2
        response = send_command(s, GET_SENSOR_STATE_COMMAND, "GET_SENSOR_STATE")

        if not response or not response.startswith('state,1:2,'):
            print("!!! Could not get valid sensor state. Skipping this cycle.")
            return

        # The response is "state,1:2,X", so we get the last character ('0' or '1').
        current_state = response[-1]

        # 2. Check if a state transition has occurred.
        if current_state != last_state:
            if last_state == '0' and current_state == '1':
                print(f"*** DETECTED TRANSITION: OFF -> ON. Toggling power. ***")
            elif last_state == '1' and current_state == '0':
                print(f"*** DETECTED TRANSITION: ON -> OFF. Toggling power. ***")

            # 3. Send the power toggle command to both IR ports.
            send_command(s, POWER_TOGGLE_COMMAND.replace("sendir,1:1", "sendir,1:1"), "POWER_TOGGLE_PORT_1")
            time.sleep(1) # Brief pause for reliability
            send_command(s, POWER_TOGGLE_COMMAND.replace("sendir,1:1", "sendir,1:3"), "POWER_TOGGLE_PORT_3")

            # 4. Save the new state to establish a new baseline.
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
    try:
        while True:
            monitor_sensor_and_toggle_on_change()
            print(f"\n--- Waiting for 15 seconds before next check ---")
            time.sleep(15)
    except KeyboardInterrupt:
        print("\nScript stopped by user. Exiting.")
        sys.exit(0)
