import asyncio
import socket
import sys
import time
import os
import logging
import argparse
import json
import platform
from datetime import datetime
from typing import Optional, List, Dict, Any

# Ensure you have the 'python-anthemav' library installed:
# pip install python-anthemav
import anthemav

# --- Configuration ---
DEFAULT_DRIVE_LETTER = "F"
DEFAULT_ITACH_HOST = "192.168.86.104"
DEFAULT_ITACH_PORT = 4998
DEFAULT_ITACH_COMMAND = "sendir,1:1,1,36000,1,1,32,32,64,64,64,32,32,32,32,32,32,32,32,32,32,64,32,32,64,32,32,2487"
DEFAULT_ANTHEM_HOST = "192.168.86.72"
DEFAULT_ANTHEM_PORT = 14999
DEFAULT_POLLING_INTERVAL = 10  # Seconds
POWER_ON_DELAY = 30 # Seconds to wait after drive appears before sending commands
JSON_STATUS_FILE = "power_status.json"

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Helper Functions ---

def is_wsl() -> bool:
    """Check if the script is running inside Windows Subsystem for Linux."""
    return 'microsoft-standard' in platform.uname().release.lower()

def get_drive_path(drive_letter: str) -> str:
    """Get the appropriate path for the drive based on OS (Windows or WSL)."""
    drive_letter = drive_letter.strip().upper()
    if sys.platform == "win32":
        return f"{drive_letter}:\\"
    elif is_wsl():
        return f"/mnt/{drive_letter.lower()}/"
    else: # Assume other Linux/macOS - adjust if needed
        logger.warning(f"Unsupported platform {sys.platform} for drive letter checking. Assuming /mnt/ style.")
        return f"/mnt/{drive_letter.lower()}/"

def load_power_status(filepath: str) -> Dict[str, Any]:
    """Loads the power status from a JSON file."""
    default_status = {'power_on': False, 'last_change': None}
    if not os.path.exists(filepath):
        logger.info(f"Status file '{filepath}' not found. Assuming power is OFF.")
        return default_status
    try:
        with open(filepath, 'r') as f:
            status = json.load(f)
            logger.info(f"Loaded power status: {status}")
            return status
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading status file '{filepath}': {e}. Assuming power is OFF.")
        return default_status

def save_power_status(filepath: str, power_on: bool) -> None:
    """Saves the current power status to a JSON file."""
    status = {
        'power_on': power_on,
        'last_change': datetime.now().isoformat()
    }
    try:
        with open(filepath, 'w') as f:
            json.dump(status, f, indent=4)
        logger.info(f"Saved power status: {status}")
    except IOError as e:
        logger.error(f"Error saving status file '{filepath}': {e}")


# --- Classes (Modified and Original) ---

class DriveChecker:
    """Manages the detection of a specific drive path."""

    def __init__(self, path_to_check: str):
        """Initializes the DriveChecker with the specific path."""
        self.path_to_check = path_to_check
        logger.info(f"DriveChecker initialized to monitor path: {self.path_to_check}")

    def is_drive_present(self) -> bool:
        """Checks if the configured drive path exists."""
        found = os.path.exists(self.path_to_check)
        logger.debug(f"Checking for {self.path_to_check}: {'Found' if found else 'Not Found'}")
        return found

class ITachController:
    """Manages communication with a Global Cache iTach device to send IR commands."""
    def __init__(self, host: str, port: int, timeout: int = 5, buffer_size: int = 1024):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.buffer_size = buffer_size

    def send_ir_command(self, command: str) -> bool:
        """Sends an IR command string to the iTach device."""
        full_command_bytes = (command + "\r\n").encode('ascii')
        sock: Optional[socket.socket] = None
        try:
            logger.info(f"Attempting to connect to iTach at {self.host}:{self.port}...")
            sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
            logger.info("iTach connection successful.")
            
            # Optional: Read initial data if any (often empty)
            try:
                sock.settimeout(0.5) # Quick check
                initial_data = sock.recv(self.buffer_size)
                logger.debug(f"Initial iTach data: {initial_data.decode('ascii').strip()}")
            except socket.timeout:
                logger.debug("No initial iTach data.")
            except Exception as e:
                 logger.warning(f"Error receiving initial iTach data: {e}")

            sock.settimeout(self.timeout) # Reset timeout for command
            logger.info(f"Sending iTach command: '{command}'")
            sock.sendall(full_command_bytes)
            response_bytes = sock.recv(self.buffer_size)
            response = response_bytes.decode('ascii').strip()
            logger.info(f"iTach device response: '{response}'")
            # Check for specific 'completeir' or expected response if needed
            return True

        except socket.timeout:
            logger.error(f"iTach connection or read timed out for {self.host}:{self.port}.")
            return False
        except ConnectionRefusedError:
            logger.error(f"Connection refused by iTach {self.host}:{self.port}.")
            return False
        except Exception as e:
            logger.exception(f"An unexpected error occurred with iTach: {e}")
            return False
        finally:
            if sock:
                sock.close()
                logger.info("iTach socket closed.")

class AnthemAVRController:
    """Manages connection and control for an Anthem AVR device."""
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.conn: Optional[anthemav.Connection] = None

    async def _anthem_update_callback(self, message: str) -> None:
        logger.debug(f"AnthemAVR callback: {message}")

    async def power_on(self) -> bool:
        """Attempts to connect and power on the Anthem AVR."""
        logger.info(f"Attempting to connect to Anthem AVR at {self.host}:{self.port}...")
        loop = asyncio.get_running_loop()
        try:
            self.conn = await anthemav.Connection.create(
                host=self.host, port=self.port, loop=loop,
                update_callback=self._anthem_update_callback
            )
            logger.info("Anthem connection established.")
            await asyncio.sleep(0.5) # Settle time

            if not self.conn.protocol.power:
                logger.info("Anthem AVR is off. Sending power on...")
                self.conn.protocol.power = True
                await asyncio.sleep(2) # Wait for power on
                logger.info(f"Anthem power state after command: {self.conn.protocol.power}")
            else:
                logger.info("Anthem AVR is already on.")
            return True

        except (ConnectionRefusedError, asyncio.TimeoutError) as e:
            logger.error(f"Anthem connection failed ({type(e).__name__}): {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected Anthem error: {e}")
            return False
        finally:
            if self.conn:
                self.conn.close()
                logger.info("Anthem connection closed.")

class HomeAutomationSystem:
    """Orchestrates drive checking, power status tracking, and device control."""

    def __init__(self,
                 drive_to_check: str,
                 itach_host: str, itach_port: int, itach_command: str,
                 anthem_host: str, anthem_port: int,
                 polling_interval: int,
                 power_on_delay: int,
                 status_file: str):

        self.drive_path = get_drive_path(drive_to_check)
        self.drive_checker = DriveChecker(self.drive_path)
        self.itach_controller = ITachController(itach_host, itach_port)
        self.anthem_controller = AnthemAVRController(anthem_host, anthem_port)

        self.itach_command = itach_command
        self.polling_interval = polling_interval
        self.power_on_delay = power_on_delay
        self.status_file = status_file

        # Load initial state from JSON
        self.power_status = load_power_status(self.status_file)
        self._is_power_on = self.power_status.get('power_on', False)
        self._power_on_task: Optional[asyncio.Task] = None # To manage the delay task


    async def _handle_power_on_sequence(self):
        """Waits for the delay, re-checks drive, and sends commands."""
        logger.info(f"Power On detected. Waiting {self.power_on_delay} seconds before sending commands...")
        try:
            await asyncio.sleep(self.power_on_delay)

            # Re-check drive after delay
            if self.drive_checker.is_drive_present():
                logger.info("Drive still present after delay. Proceeding with power-on actions.")

                logger.info("\n--- Attempting to send 'sendir' command ---")
                itach_success = self.itach_controller.send_ir_command(self.itach_command)
                if itach_success:
                    logger.info("'sendir' command sent successfully.")
                else:
                    logger.error("Failed to send 'sendir' command.")

                logger.info("\n--- Attempting Anthem AVR power on ---")
                anthem_success = await self.anthem_controller.power_on()
                if anthem_success:
                    logger.info("Anthem power on executed successfully.")
                else:
                    logger.error("Anthem power on failed.")

                # Only update and save if commands were attempted (even if they failed)
                self._is_power_on = True
                save_power_status(self.status_file, True)

            else:
                logger.warning("Drive disappeared during the power-on delay. Cancelling actions.")
                # If it disappeared, we go back to power-off state
                if self._is_power_on: # Should be False, but just in case
                   self._is_power_on = False
                   save_power_status(self.status_file, False)

        except asyncio.CancelledError:
            logger.info("Power-on sequence cancelled (likely due to drive disappearing).")
        finally:
            self._power_on_task = None # Clear the task handle

    async def run(self) -> None:
        """Main loop for monitoring and acting."""
        logger.info("--- Starting Home Automation System ---")
        logger.info(f"Monitoring path: {self.drive_path}")
        logger.info(f"Polling interval: {self.polling_interval}s")
        logger.info(f"Power-on delay: {self.power_on_delay}s")
        logger.info(f"Platform: {sys.platform} {'(WSL)' if is_wsl() else ''}")


        while True:
            logger.debug(f"\n--- Checking Drive Status ---")
            current_drive_found = self.drive_checker.is_drive_present()

            # --- Power ON Logic ---
            if current_drive_found and not self._is_power_on:
                # If drive appears and we think power is off
                if self._power_on_task is None or self._power_on_task.done():
                    # Start the power-on sequence *only* if not already running
                    self._power_on_task = asyncio.create_task(self._handle_power_on_sequence())
                else:
                    logger.debug("Power-on sequence already in progress.")

            # --- Power OFF Logic ---
            elif not current_drive_found and self._is_power_on:
                # If drive disappears and we think power is on
                logger.info("Power Off detected (drive disappeared).")
                
                # Cancel any ongoing power-on task if it exists
                if self._power_on_task is not None and not self._power_on_task.done():
                    logger.info("Cancelling ongoing power-on task.")
                    self._power_on_task.cancel()
                    self._power_on_task = None # Ensure it's cleared

                self._is_power_on = False
                save_power_status(self.status_file, False)
                logger.info("Power status updated to OFF.")
                # NOTE: No power-off commands are sent based on requirements.

            # --- No Change Logic ---
            else:
                 logger.debug(f"No change in power status (Drive: {current_drive_found}, Power: {self._is_power_on}).")


            await asyncio.sleep(self.polling_interval)

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated home theater control with power status tracking.")
    parser.add_argument("--drive", default=DEFAULT_DRIVE_LETTER, help="Drive letter to check.")
    parser.add_argument("--itach-host", default=DEFAULT_ITACH_HOST, help="IP of iTach.")
    parser.add_argument("--anthem-host", default=DEFAULT_ANTHEM_HOST, help="IP of Anthem AVR.")
    parser.add_argument("--interval", type=int, default=DEFAULT_POLLING_INTERVAL, help="Polling interval (s).")
    parser.add_argument("--delay", type=int, default=POWER_ON_DELAY, help="Power-on delay (s).")
    parser.add_argument("--status-file", default=JSON_STATUS_FILE, help="Path to JSON status file.")
    args = parser.parse_args()

    system = HomeAutomationSystem(
        drive_to_check=args.drive,
        itach_host=args.itach_host,
        itach_port=DEFAULT_ITACH_PORT,
        itach_command=DEFAULT_ITACH_COMMAND,
        anthem_host=args.anthem_host,
        anthem_port=DEFAULT_ANTHEM_PORT,
        polling_interval=args.interval,
        power_on_delay=args.delay,
        status_file=args.status_file
    )

    try:
        asyncio.run(system.run())
    except KeyboardInterrupt:
        logger.info("Script stopped by user (Ctrl+C).")
    except Exception as e:
        logger.critical(f"An unhandled error occurred: {e}", exc_info=True)
    finally:
        logger.info("Script exiting.")