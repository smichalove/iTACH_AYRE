import tkinter as tk
from tkinter import font as tkFont
import socket
import sys

class AyrePreampUI:
    """
    A Tkinter GUI that emulates the front panel of the Ayre K-5xeMP preamplifier
    and sends IR commands over the network to a Global Caché iTach device.
    """

    def __init__(self, master):
        """
        Initializes the preamplifier UI.

        Args:
            master: The root Tkinter window.
        """
        self.master = master
        self.master.title("Ayre K-5xeMP Network Control")
        self.master.geometry("600x500") # Increased height for network settings
        self.master.configure(bg="#EAEAEB")
        self.master.resizable(False, False)

        # --- Network Configuration ---
        self.host_var = tk.StringVar(value="192.168.86.104")
        self.port_var = tk.StringVar(value="4998")

        # --- IR Command Dictionary ---
        self.ir_codes = {
            "DIMMER": "sendir,1:1,1,36000,1,1,32,32,64,64,64,32,32,32,32,32,32,32,32,64,64,32,32,64,64,2487",
            "INPUT 1": "sendir,1:1,1,36000,1,1,32,32,64,64,64,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,64,32,2487",
            "INPUT 2": "sendir,1:1,1,36000,1,1,32,32,64,64,64,32,32,32,32,32,32,32,32,32,32,32,32,32,32,64,64,2487",
            "INPUT 3": "sendir,1:1,1,36000,1,1,32,32,64,64,64,32,32,32,32,32,32,32,32,32,32,32,32,32,32,64,32,32,32,2487",
            "INPUT 4": "sendir,1:1,1,36000,1,1,32,32,64,64,64,32,32,32,32,32,32,32,32,32,32,32,32,64,64,32,32,2487",
            "MUTE TOGGLE": "sendir,1:1,1,36000,1,1,32,32,64,64,64,32,32,32,32,32,32,32,32,32,32,64,32,32,64,64,32,2487",
            "POWER OFF": "sendir,1:1,1,36000,1,1,32,32,64,64,64,32,32,32,32,32,32,64,32,32,32,32,64,32,32,64,32,2487",
            "POWER ON": "sendir,1:1,1,36000,1,1,32,32,64,64,64,32,32,32,32,32,32,64,32,32,32,32,64,32,32,32,32,2487",
            "VOLUME DOWN": "sendir,1:1,1,36000,1,1,32,32,64,64,64,32,32,32,32,32,32,32,32,64,64,32,32,32,32,64,32,2487",
            "VOLUME UP": "sendir,1:1,1,36000,1,1,32,32,64,64,64,32,32,32,32,32,32,32,32,64,64,32,32,32,32,32,32,2487",
        }

        # --- UI State Variables ---
        self.is_on = True
        self.volume = 33
        self.is_muted = False
        self.current_input = "B1"
        self.tape_on = False
        self.input_map = {"B1": "INPUT 1", "B2": "INPUT 2", "S1": "INPUT 3", "S2": "INPUT 4"}

        # Define fonts
        self.display_font = tkFont.Font(family="DS-Digital", size=60, weight="bold")
        self.button_font = tkFont.Font(family="Arial", size=10)
        self.label_font = tkFont.Font(family="Arial", size=9)
        self.net_font = tkFont.Font(family="Arial", size=10, weight="bold")

        self._create_widgets()
        self.update_display()

    def _create_widgets(self):
        """Creates and places all the GUI widgets."""

        # --- Network Configuration Frame ---
        net_frame = tk.Frame(self.master, bg="#C0C0C0", bd=2, relief=tk.GROOVE)
        net_frame.pack(pady=10, padx=10, fill=tk.X)
        
        tk.Label(net_frame, text="iTach Settings", font=self.net_font, bg="#C0C0C0").grid(row=0, column=0, columnspan=4, pady=5)
        
        tk.Label(net_frame, text="IP Address:", bg="#C0C0C0").grid(row=1, column=0, padx=5, sticky='e')
        ip_entry = tk.Entry(net_frame, textvariable=self.host_var, width=15)
        ip_entry.grid(row=1, column=1, padx=5, pady=5)
        
        tk.Label(net_frame, text="Port:", bg="#C0C0C0").grid(row=1, column=2, padx=5, sticky='e')
        port_entry = tk.Entry(net_frame, textvariable=self.port_var, width=6)
        port_entry.grid(row=1, column=3, padx=5, pady=5)

        # --- Main Faceplate Frame ---
        faceplate = tk.Frame(self.master, bg="#DCDDDE", bd=2, relief=tk.RAISED)
        faceplate.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        logo_font = tkFont.Font(family="Arial", size=20, weight="bold")
        logo_label = tk.Label(faceplate, text="Ayre", font=logo_font, bg="#DCDDDE", fg="black")
        logo_label.place(relx=0.1, rely=0.2, anchor=tk.W)

        display_frame = tk.Frame(faceplate, bg="black", bd=5, relief=tk.SUNKEN)
        display_frame.place(relx=0.45, rely=0.3, anchor=tk.CENTER, width=200, height=80)
        self.display_label = tk.Label(display_frame, text="33", font=self.display_font, bg="black", fg="#39FF14")
        self.display_label.pack(expand=True, fill=tk.BOTH)

        input_frame = tk.Frame(faceplate, bg="#DCDDDE")
        input_frame.place(relx=0.45, rely=0.7, anchor=tk.CENTER)
        
        buttons_info = [("B1", "B1"), ("B2", "B2"), ("S1", "S1"), ("S2", "S2"), ("TAPE", "TAPE")]
        for text, name in buttons_info:
            btn = tk.Button(input_frame, text=text, font=self.button_font,
                            command=lambda n=name: self.select_input(n),
                            bg="#C0C0C0", fg="black", relief=tk.RAISED, borderwidth=2)
            btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        vol_frame = tk.Frame(faceplate, bg="#DCDDDE")
        vol_frame.place(relx=0.85, rely=0.4, anchor=tk.CENTER)
        
        tk.Button(vol_frame, text="▲ VOL", font=self.button_font, command=self.volume_up, width=6).pack(pady=2)
        tk.Button(vol_frame, text="MUTE (ø)", font=self.button_font, command=self.toggle_mute).pack(pady=5)
        tk.Button(vol_frame, text="▼ VOL", font=self.button_font, command=self.volume_down, width=6).pack(pady=2)

        # --- System Controls Frame ---
        power_frame = tk.Frame(self.master, bg="#EAEAEB")
        power_frame.pack(pady=10)
        
        tk.Button(power_frame, text="Power On", command=lambda: self.process_command("POWER ON"), width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(power_frame, text="Power Off", command=lambda: self.process_command("POWER OFF"), width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(power_frame, text="Dimmer", command=lambda: self.process_command("DIMMER"), width=10).pack(side=tk.LEFT, padx=5)
        
        self.status_label = tk.Label(self.master, text="Enter iTach IP/Port and press a button.", bd=1, relief=tk.SUNKEN, anchor=tk.W, padx=10)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def _send_to_itach(self, command_str):
        """Connects to the iTach, sends a command, and returns the response."""
        host = self.host_var.get()
        s = None
        try:
            port = int(self.port_var.get())
        except ValueError:
            self.status_label.config(text="ERROR: Port must be a number.")
            return None, False

        try:
            self.status_label.config(text=f"Connecting to {host}:{port}...")
            self.master.update_idletasks() # Force UI update

            s = socket.create_connection((host, port), timeout=5)
            full_command = (command_str + "\r\n").encode('ascii')
            
            s.sendall(full_command)
            response_bytes = s.recv(1024)
            response = response_bytes.decode('ascii').strip()
            
            self.status_label.config(text=f"SUCCESS: Sent '{command_str}'. Response: {response}")
            return response, True

        except socket.timeout:
            self.status_label.config(text=f"ERROR: Connection to {host} timed out.")
            return None, False
        except ConnectionRefusedError:
            self.status_label.config(text=f"ERROR: Connection refused by {host}.")
            return None, False
        except Exception as e:
            self.status_label.config(text=f"ERROR: {e}")
            return None, False
        finally:
            if s:
                s.close()

    def process_command(self, function_name):
        """Processes a command, sends it to the iTach, and updates UI state on success."""
        if not self.is_on and function_name not in ["POWER ON"]:
            self.status_label.config(text="System is OFF. Please power on first.")
            return

        command_to_send = self.ir_codes.get(function_name)
        if not command_to_send:
            self.status_label.config(text=f"No IR Code for: {function_name}")
            return
            
        _response, success = self._send_to_itach(command_to_send)

        if success:
            # Update internal state only if command was sent successfully
            if function_name == "POWER OFF": self.is_on = False
            elif function_name == "POWER ON": self.is_on = True
            elif function_name == "VOLUME UP": self.volume = min(66, self.volume + 1)
            elif function_name == "VOLUME DOWN": self.volume = max(0, self.volume - 1)
            elif function_name == "MUTE TOGGLE": self.is_muted = not self.is_muted
            elif function_name.startswith("INPUT"):
                 self.current_input = function_name.split()[-1] # e.g., "B1" from "INPUT 1"
                 for ui_name, ir_name in self.input_map.items():
                     if ir_name == function_name:
                         self.current_input = ui_name
                         break

            self.update_display()
            
    def volume_up(self):
        if self.is_muted: self.process_command("MUTE TOGGLE")
        self.process_command("VOLUME UP")

    def volume_down(self):
        if self.is_muted: self.process_command("MUTE TOGGLE")
        self.process_command("VOLUME DOWN")

    def toggle_mute(self):
        self.process_command("MUTE TOGGLE")

    def select_input(self, input_name):
        if input_name == "TAPE":
            self.tape_on = not self.tape_on
            self.status_label.config(text=f"Tape Output Toggled. No IR code to send.")
            self.update_display()
            return
        
        ir_command_name = self.input_map.get(input_name)
        if ir_command_name:
            self.process_command(ir_command_name)

    def update_display(self):
        """Updates the text on the display label based on the current state."""
        if not self.is_on:
            self.display_label.config(text="")
            return

        if self.is_muted:
            self.display_label.config(text="--")
        else:
            display_text = f"{self.volume:02d}"
            self.display_label.config(text=display_text)

if __name__ == '__main__':
    root = tk.Tk()
    try:
        tkFont.Font(family="DS-Digital", size=1)
    except tk.TclError:
        print("NOTE: For the best visual experience, install the 'DS-Digital' font.")
    app = AyrePreampUI(root)
    root.mainloop()

