import socket
import sys
import time

# --- Configuration ---
# Purpose: This script sends an IR command, then ensures a specific
#          relay is closed, verifying its final state.

HOST = "192.168.86.104"  # IP address of your Global Cache iTach device
PORT = 4998              # Default command port for iTach devices
TIMEOUT = 5              # Connection and read timeout in seconds
BUFFER_SIZE = 1024       # Size of the buffer for receiving data

# --- iTach Command Definitions ---

# 1. IR Command
# This is an example 'sendir' command. Replace with your actual IR code.
# Global Cache IR Database: https://irdb.globalcache.com/
POWER_TOGGLE_CMD = "sendir,1:1,1,36000,1,1,32,32,64,64,64,32,32,32,32,32,32,32,32,32,32,64,32,32,64,32,32,2487"

# 2. Relay Commands (for module 1, connector 2)
CLOSE_RELAY_CMD = "setstate,1:2,1"
GET_STATE_CMD = "getstate,1:2"
EXPECTED_OPEN_STATE = "state,1:2,0"
EXPECTED_CLOSED_STATE = "state,1:2,1"


def send_itach_command(command: str) -> str | None:
    """
    Establishes a connection to the iTach, sends a single command,
    and returns the response. Creates a new connection for each command.

    Args:
        command: The command string to send to the iTach device.

    Returns:
        The device's response as a string, or None if an error occurs.
    """
    # Use a 'with' statement for the socket to ensure it's always closed
    try:
        with socket.create_connection((HOST, PORT), timeout=TIMEOUT) as s:
            print(f"Connected to {HOST}:{PORT}")
            full_command = (command + "\r\n").encode('ascii')

            # Send the command
            print(f"--> Sending: {command}")
            s.sendall(full_command)

            # Wait for and receive the response
            data = s.recv(BUFFER_SIZE)
            response = data.decode('ascii').strip()
            print(f"<-- Received: {response}")
            return response

    except socket.timeout:
        print(f"ERROR: Connection or read timed out after {TIMEOUT} seconds.", file=sys.stderr)
    except ConnectionRefusedError:
        print(f"ERROR: Connection refused by {HOST}:{PORT}. Check IP and device status.", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
    
    return None


def main():
    """
    Main function to run the IR and relay control sequence.
    """
    print("--- Starting IR and Relay Control Script ---\n")

    # Step 1: Send the IR Power Toggle Command
    print("Step 1: Sending IR command...")
    ir_response = send_itach_command(POWER_TOGGLE_CMD)
    if not ir_response:
        print("Failed to send IR command. Aborting.")
        sys.exit(1)
    print("IR command sent successfully.\n")

    # Wait for the device to respond to the IR signal
    print("Waiting 3 seconds for device to power on...")
    time.sleep(3)
    print("-" * 20 + "\n")


    # Step 2: Check the current state of the relay
    print("Step 2: Checking current relay state...")
    current_state = send_itach_command(GET_STATE_CMD)
    if not current_state:
        print("Failed to get relay state. Aborting.")
        sys.exit(1)
    print("-" * 20 + "\n")


    # Step 3: Close the relay ONLY if it's currently open
    if current_state == EXPECTED_OPEN_STATE:
        print("Step 3: Relay is open. Sending command to close it...")
        close_response = send_itach_command(CLOSE_RELAY_CMD)
        if not close_response:
            print("Failed to execute close command. Aborting.")
            sys.exit(1)
        # We need to get the state again to confirm the change
        current_state = send_itach_command(GET_STATE_CMD)
        print("-" * 20 + "\n")
    elif current_state == EXPECTED_CLOSED_STATE:
        print("Step 3: Relay is already closed. No action needed.\n")
    else:
        print(f"Warning: Relay is in an unknown state ('{current_state}'). Proceeding to final check.\n")


    # Step 4: Final verification
    print("Step 4: Verifying final relay state...")
    if current_state == EXPECTED_CLOSED_STATE:
        print(f"SUCCESS: Relay is confirmed to be in the CLOSED state.")
    else:
        print(f"FAILURE: Relay is NOT in the closed state. Final state: '{current_state}'.")

    print("\nScript finished.")


if __name__ == "__main__":
    main()