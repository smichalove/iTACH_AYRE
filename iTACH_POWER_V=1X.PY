import socket
import sys
import time  # Import time for adding delays

# --- Configuration ---
HOST = "192.168.86.104"  # IP address of your Global Cache iTach device
PORT = 4998            # Default command port for Global Cache iTach devices
TIMEOUT = 5             # Connection and read timeout in seconds
BUFFER_SIZE = 1024      # Size of the buffer for receiving data

# --- iTach Command Definitions ---
# The following variables define the IR commands to be sent to the iTach.
# Each command is a string formatted according to the iTach's "sendir" protocol.
# For detailed information on the "sendir" format, please refer to the Global Cache documentation.

# Example command to toggle the power state of a device.
# The specific parameters (protocol, carrier frequency, burst pairs, etc.)
# will vary depending on the IR signal being emulated.
# Global Cache IR Database:  https://irdb.globalcache.com/Home/Database#
POWER_TOGGLE = "sendir,1:1,1,36000,1,1,32,32,64,64,64,32,32,32,32,32,32,32,32,32,32,64,32,32,64,32,32,2487" # Example IR code

# Another example command (currently commented out but can be used).
# COMMAND2 = "sendir,1:1,1,36000,3,1,32,32,64,64,64,32,32,32,32,32,32,32,32,32,32,64,32,32,64,32,32,2487" # Example IR code

# --- End Configuration ---

# Append the required carriage return and newline characters to the command
# for the iTach to recognize and execute it. Then, encode the string into bytes.
full_command_bytes = (POWER_TOGGLE + "\r\n").encode('ascii')
# full_command_bytes2 = (COMMAND2 + "\r\n").encode('ascii')

# Initialize the socket object to None. This is important for the finally block
# to ensure we only try to close the socket if it was successfully created.
s = None
responses = []  # Create an empty list to store responses received from the iTach.

try:
    # Create a socket object using IPv4 (AF_INET) and TCP (SOCK_STREAM).
    print(f"Attempting to connect to {HOST}:{PORT}...")
    # socket.create_connection is a convenient way to create and connect a socket
    # in one step, handling hostname resolution and connection establishment.
    s = socket.create_connection((HOST, PORT), timeout=TIMEOUT)
    print("Connection successful.")

    # --- Optional: Receive Initial Connection Message ---
    # Some iTach devices might send an initial message upon connection.
    # This block attempts to receive and print any such message.
    try:
        initial_data = s.recv(BUFFER_SIZE)
        initial_response = initial_data.decode('ascii').strip()
        if initial_response:
            print(f"Initial data from device: {initial_response}")
            responses.append(initial_response)
        else:
            print("No initial data received.")
    except socket.timeout:
        print("No initial data received within timeout.")
        pass  # It's okay if there's no initial message

    # --- Sending Commands ---
    # This section sends the defined iTach commands to the device.

    try:
        # --- Send the First Command (POWER_TOGGLE) ---
        print(f"Sending command 1: {POWER_TOGGLE}")
        # Send the command bytes over the socket. sendall ensures that all data
        # is transmitted or raises an exception.
        s.sendall(full_command_bytes)
        print("Waiting for response...")
        # Receive data from the iTach. The amount of data received is limited
        # by the BUFFER_SIZE.
        response1_bytes = s.recv(BUFFER_SIZE)
        # Decode the received bytes into a string and remove any leading/trailing whitespace.
        response1 = response1_bytes.decode('ascii').strip()
        if response1:
            print(f"Device response to command 1:{POWER_TOGGLE} -> {response1}")
            responses.append(response1)
        else:
            print("No response received for command 1 (or response was empty).")

        # --- Introduce a Delay ---
        # It's often necessary to introduce a delay between sending commands
        # to allow the controlled device time to process the first command
        # before receiving the next. Adjust the sleep duration as needed.
        time.sleep(30)  # Wait for 30 seconds

        # --- Send the Second Command (COMMAND2 - currently commented out) ---
        # If you have a second command to send, uncomment this block.
        # print(f"Sending command 2: {COMMAND2}")
        # s.sendall(full_command_bytes2)
        # print("Waiting for response...")
        # response2_bytes = s.recv(BUFFER_SIZE)
        # response2 = response2_bytes.decode('ascii').strip()
        # if response2:
        #     print(f"Device response to command 2: {COMMAND2} -> {response2}")
        #     responses.append(response2)
        # else:
        #     print("No response received for command 2 (or response was empty).")

    except KeyboardInterrupt:
        # This block handles the user pressing Ctrl+C to interrupt the script.
        print("KeyboardInterrupt: Exiting command sending loop.")

except socket.timeout:
    # This exception is raised if the connection or a receive operation times out.
    print(f"ERROR: Connection or read timed out after {TIMEOUT} seconds. Check device power/network.", file=sys.stderr)
    sys.exit(1)
except ConnectionRefusedError:
    # This exception is raised if the target machine actively refuses the connection.
    print(f"ERROR: Connection refused by {HOST}:{PORT}. Is the device IP correct and is it running?", file=sys.stderr)
    sys.exit(1)
except socket.gaierror as e:
    # This exception is raised for address-related errors (e.g., invalid hostname).
    print(f"ERROR: Could not resolve hostname {HOST}. Check the IP address. Error: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    # This is a general exception handler for any other unexpected errors.
    print(f"An unexpected error occurred: {e}", file=sys.stderr)
    sys.exit(1)
finally:
    # This block ensures that the socket is closed, regardless of whether an
    # exception occurred or the script ran successfully. It's crucial to release
    # system resources.
    if s:
        print("Closing socket connection.")
        s.close()

# --- Output Responses ---
# After the communication with the iTach is complete (or interrupted), this
# section prints all the responses received from the device.
print("\n--- All Responses Received ---")
for i, resp in enumerate(responses):
    print(f"Response {i + 1}: {resp}")

print("Script finished.")
