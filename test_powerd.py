import unittest
from unittest.mock import patch, MagicMock, call, mock_open
import socket
import sys
from pathlib import Path

# Add the script's directory to the Python path to allow importing
sys.path.insert(0, '/home/steven')

# Now we can import the script we want to test
import powerd

class TestPowerd(unittest.TestCase):
    """
    Test suite for the powerd.py script.

    This class contains unit tests for the state management, network communication,
    and main logic functions within the powerd.py script. It uses mocking
    extensively to isolate functions and simulate hardware responses.
    """

    def setUp(self):
        """Prepare for each test by mocking the logging module."""
        # Patch logging to avoid cluttering test output and check log messages
        self.patcher = patch('powerd.logging')
        self.mock_logging = self.patcher.start()

    def tearDown(self):
        """Clean up after each test by stopping the patcher."""
        self.patcher.stop()

    # --- Test State Management Functions ---

    @patch('powerd.STATE_FILE.exists', return_value=False)
    def test_get_last_sensor_state_no_file(self, mock_exists):
        """Test get_last_sensor_state when the state file does not exist."""
        self.assertEqual(powerd.get_last_sensor_state(), '0')
        mock_exists.assert_called_once()

    @patch('powerd.STATE_FILE.exists', return_value=True)
    @patch('powerd.STATE_FILE.read_text', return_value='1\n ')
    def test_get_last_sensor_state_file_exists(self, mock_read_text, mock_exists):
        """Test get_last_sensor_state reads correctly when the file exists."""
        self.assertEqual(powerd.get_last_sensor_state(), '1')
        mock_exists.assert_called_once()
        mock_read_text.assert_called_once()

    @patch('powerd.STATE_FILE.exists', return_value=True)
    @patch('powerd.STATE_FILE.read_text', side_effect=IOError("Can't read"))
    def test_get_last_sensor_state_read_error(self, mock_read_text, mock_exists):
        """Test get_last_sensor_state defaults to '0' on a file read error."""
        self.assertEqual(powerd.get_last_sensor_state(), '0')
        self.mock_logging.error.assert_called_with("Error reading state file: Can't read")

    @patch('powerd.STATE_FILE.write_text')
    def test_set_sensor_state_success(self, mock_write_text):
        """Test set_sensor_state successfully writes the new state to a file."""
        powerd.set_sensor_state('1')
        mock_write_text.assert_called_once_with('1')
        self.mock_logging.info.assert_called_with("State change recorded. New baseline state is: 1")

    @patch('powerd.STATE_FILE.write_text', side_effect=IOError("Can't write"))
    def test_set_sensor_state_write_error(self, mock_write_text):
        """Test set_sensor_state logs an error when a file write fails."""
        powerd.set_sensor_state('0')
        mock_write_text.assert_called_once_with('0')
        self.mock_logging.error.assert_called_with("Error writing to state file: Can't write")

    # --- Test Network & Command Functions ---

    def test_send_command_success(self):
        """Test send_command sends data and returns a decoded response."""
        mock_sock = MagicMock()
        mock_sock.recv.return_value = b'complete,1:1\r'
        response = powerd.send_command(mock_sock, "getstate,1:1", "TEST_CMD")

        mock_sock.sendall.assert_called_once_with(b'getstate,1:1\r')
        self.assertEqual(response, 'complete,1:1')
        self.mock_logging.info.assert_any_call("Sending TEST_CMD: getstate,1:1")

    def test_send_command_timeout(self):
        """Test send_command returns None and logs a warning on socket timeout."""
        mock_sock = MagicMock()
        mock_sock.sendall.side_effect = socket.timeout
        response = powerd.send_command(mock_sock, "getstate,1:1", "TEST_CMD")

        self.assertIsNone(response)
        self.mock_logging.warning.assert_called_with("TIMEOUT on 'TEST_CMD'. No response from device.")

    @patch('socket.create_connection')
    @patch('powerd.send_command')
    @patch('time.sleep')
    def test_pulse_ip2cc_relay(self, mock_sleep, mock_send_command, mock_create_connection):
        """Test pulse_ip2cc_relay sends close/open commands in sequence."""
        mock_sock = MagicMock()
        mock_create_connection.return_value = mock_sock

        powerd.pulse_ip2cc_relay()

        mock_create_connection.assert_called_once_with((powerd.IP2CC, powerd.PORT), timeout=powerd.TIMEOUT)
        
        expected_calls = [
            call(mock_sock, "setstate,1:1,1", "IP2CC_RELAY_CLOSE"),
            call(mock_sock, "setstate,1:1,0", "IP2CC_RELAY_OPEN")
        ]
        mock_send_command.assert_has_calls(expected_calls)

        sleep_calls = [call(0.35), call(2.25)]
        mock_sleep.assert_has_calls(sleep_calls)

        mock_sock.close.assert_called_once()

    @patch('socket.socket')
    def test_wake_on_lan(self, mock_socket_constructor):
        """Test wake_on_lan constructs and sends a correct magic packet."""
        mock_sock_instance = MagicMock()
        # Make the socket constructor return our mock instance
        mock_socket_constructor.return_value.__enter__.return_value = mock_sock_instance

        mac = "AA-BB-CC-DD-EE-FF"
        broadcast = "192.168.1.255"
        powerd.wake_on_lan(mac, broadcast)

        # Check socket creation
        mock_socket_constructor.assert_called_with(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Check setsockopt call
        mock_sock_instance.setsockopt.assert_called_once_with(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Check that sendto was called with the correct magic packet
        mac_bytes = bytes.fromhex("AABBCCDDEEFF")
        magic_packet = b'\xff' * 6 + mac_bytes * 16
        mock_sock_instance.sendto.assert_called_once_with(magic_packet, (broadcast, 9))

    # --- Test Main Logic ---

    @patch('powerd.set_sensor_state')
    @patch('powerd.pulse_ip2cc_relay')
    @patch('powerd.wake_on_lan')
    @patch('powerd.send_command')
    @patch('socket.create_connection')
    @patch('powerd.get_last_sensor_state', return_value='0')
    @patch('time.sleep')
    def test_monitor_off_to_on_first_time(self, mock_sleep, mock_get_last_state, mock_create_conn, mock_send_cmd, mock_wol, mock_pulse, mock_set_state):
        """
        Test the OFF-to-ON transition for the first power-on event.

        Verifies that the sequence includes a relay pulse, a WoL packet, a special
        delay, and then the IR commands, finally setting the new state.
        """
        mock_sock = MagicMock()
        mock_create_conn.return_value = mock_sock
        # Simulate the device reporting state '1' (ON)
        mock_send_cmd.side_effect = [
            'state,1:2,1',  # Response for getstate
            'complete',     # Response for power toggle 1
            'complete'      # Response for power toggle 3
        ]

        # is_first_power_on_event is True initially
        updated_flag = powerd.monitor_sensor_and_toggle_on_change(first_power_on_check=True)

        # 1. Check that the initial state was read
        mock_get_last_state.assert_called_once()

        # 2. Check that the relay was pulsed first
        mock_pulse.assert_called_once()

        # 3. Check that Wake-on-LAN was called
        mock_wol.assert_called_once_with(powerd.WOL_MAC_ADDRESS, powerd.WOL_BROADCAST_ADDRESS)

        # 4. Check for the special 12-second delay
        self.assertIn(call(12), mock_sleep.call_args_list)

        # 5. Check that IR commands were sent
        ir_calls = [
            call(mock_sock, powerd.POWER_TOGGLE_COMMAND.replace("sendir,1:1", "sendir,1:1"), "POWER_TOGGLE_PORT_1"),
            call(mock_sock, powerd.POWER_TOGGLE_COMMAND.replace("sendir,1:1", "sendir,1:3"), "POWER_TOGGLE_PORT_3")
        ]
        mock_send_cmd.assert_has_calls(ir_calls, any_order=False)

        # 6. Check that the new state was persisted
        mock_set_state.assert_called_once_with('1')

        # 7. Check that the flag is now False
        self.assertFalse(updated_flag)

    @patch('powerd.set_sensor_state')
    @patch('powerd.pulse_ip2cc_relay')
    @patch('powerd.wake_on_lan')
    @patch('powerd.send_command')
    @patch('socket.create_connection')
    @patch('powerd.get_last_sensor_state', return_value='0')
    @patch('time.sleep')
    def test_monitor_off_to_on_subsequent(self, mock_sleep, mock_get_last_state, mock_create_conn, mock_send_cmd, mock_wol, mock_pulse, mock_set_state):
        """
        Test the OFF-to-ON transition for a subsequent power-on event.

        Verifies that the special delay and Wake-on-LAN are skipped.
        """
        mock_sock = MagicMock()
        mock_create_conn.return_value = mock_sock
        mock_send_cmd.side_effect = ['state,1:2,1', 'complete', 'complete']

        # is_first_power_on_event is now False
        updated_flag = powerd.monitor_sensor_and_toggle_on_change(first_power_on_check=False)

        # Check that the relay was pulsed
        mock_pulse.assert_called_once()

        # Wake-on-LAN should NOT be called
        mock_wol.assert_not_called()

        # The special 12s sleep should NOT have happened
        self.assertNotIn(call(12), mock_sleep.call_args_list)

        # IR commands should still be sent
        ir_calls = [
            call(mock_sock, powerd.POWER_TOGGLE_COMMAND.replace("sendir,1:1", "sendir,1:1"), "POWER_TOGGLE_PORT_1"),
            call(mock_sock, powerd.POWER_TOGGLE_COMMAND.replace("sendir,1:1", "sendir,1:3"), "POWER_TOGGLE_PORT_3")
        ]
        mock_send_cmd.assert_has_calls(ir_calls)

        # New state should be persisted
        mock_set_state.assert_called_once_with('1')

        # Flag should remain False
        self.assertFalse(updated_flag)

    @patch('powerd.set_sensor_state')
    @patch('powerd.pulse_ip2cc_relay')
    @patch('powerd.wake_on_lan')
    @patch('powerd.send_command')
    @patch('socket.create_connection')
    @patch('powerd.get_last_sensor_state', return_value='1')
    @patch('time.sleep')
    def test_monitor_on_to_off(self, mock_sleep, mock_get_last_state, mock_create_conn, mock_send_cmd, mock_wol, mock_pulse, mock_set_state):
        """
        Test the ON-to-OFF transition.

        Verifies that the sequence sends IR commands first, then pulses the relay.
        """
        mock_sock = MagicMock()
        mock_create_conn.return_value = mock_sock
        mock_send_cmd.side_effect = ['state,1:2,0', 'complete', 'complete']

        powerd.monitor_sensor_and_toggle_on_change(first_power_on_check=False)

        # 1. Check that IR commands were sent FIRST
        ir_calls = [
            call(mock_sock, powerd.POWER_TOGGLE_COMMAND.replace("sendir,1:1", "sendir,1:1"), "POWER_TOGGLE_PORT_1"),
            call(mock_sock, powerd.POWER_TOGGLE_COMMAND.replace("sendir,1:1", "sendir,1:3"), "POWER_TOGGLE_PORT_3")
        ]
        mock_send_cmd.assert_has_calls(ir_calls, any_order=False)

        # 2. Check that the relay was pulsed LAST
        mock_pulse.assert_called_once()

        # Check call order between send_command and pulse_ip2cc_relay
        # We can use the Mock Manager to check call order
        manager = MagicMock()
        manager.attach_mock(mock_send_cmd, 'send_command')
        manager.attach_mock(mock_pulse, 'pulse_relay')
        
        expected_call_order = [
            call.send_command(mock_sock, 'getstate,1:2', 'GET_SENSOR_STATE'),
            call.send_command(mock_sock, powerd.POWER_TOGGLE_COMMAND.replace("sendir,1:1", "sendir,1:1"), "POWER_TOGGLE_PORT_1"),
            call.send_command(mock_sock, powerd.POWER_TOGGLE_COMMAND.replace("sendir,1:1", "sendir,1:3"), "POWER_TOGGLE_PORT_3"),
            call.pulse_relay()
        ]
        # This is a bit complex, but it verifies the high-level order
        self.assertTrue(manager.mock_calls[0].__eq__(expected_call_order[0]))
        self.assertTrue(manager.mock_calls[1].__eq__(expected_call_order[1]))
        self.assertTrue(manager.mock_calls[2].__eq__(expected_call_order[2]))
        self.assertTrue(manager.mock_calls[3].__eq__(expected_call_order[3]))

        # 3. Wake-on-LAN should NOT be called
        mock_wol.assert_not_called()

        # 4. New state should be persisted
        mock_set_state.assert_called_once_with('0')

    @patch('powerd.set_sensor_state')
    @patch('powerd.pulse_ip2cc_relay')
    @patch('powerd.send_command')
    @patch('socket.create_connection')
    @patch('powerd.get_last_sensor_state', return_value='1')
    def test_monitor_no_change(self, mock_get_last_state, mock_create_conn, mock_send_cmd, mock_pulse, mock_set_state):
        """Test that no actions are taken when the sensor state does not change."""
        mock_sock = MagicMock()
        mock_create_conn.return_value = mock_sock
        # Simulate the device reporting the same state '1' (ON)
        mock_send_cmd.return_value = 'state,1:2,1'

        powerd.monitor_sensor_and_toggle_on_change(first_power_on_check=False)

        # Check that getstate was called
        mock_send_cmd.assert_called_once_with(mock_sock, 'getstate,1:2', 'GET_SENSOR_STATE')

        # No other action functions should be called
        mock_pulse.assert_not_called()
        mock_set_state.assert_not_called()

if __name__ == '__main__':
    unittest.main(verbosity=2)