import socket
import time
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import base64
import json
import os
import winreg
import urllib.request
import subprocess

# --- PROJECT CONFIGURATION ---
CURRENT_VERSION = "1.3"

# DIRECT RAW LINKS TO YOUR REPO
# Updated to match your new 'ts3-afk-manager' repo
VERSION_URL = "https://raw.githubusercontent.com/RBx9/ts3-afk-manager/refs/heads/main/version.txt"
EXE_DOWNLOAD_URL = "https://github.com/RBx9/ts3-afk-manager/raw/refs/heads/main/AFK_Manager.exe"

# --- SETTINGS FILE ---
SETTINGS_FILE = "bot_settings.json"

# --- EMBEDDED ICON ---
ICON_DATA = """
iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAABHNCSVQICAgIfAhkiAAAAAlwSFlz
AAAOxAAADsQBlSsOGwAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAJwSURB
VFhH7ZexWxNBGMV/M7t3RyQaREywCkZQYWcvWAmInZ1/wU60sLQVLSy0sLJQYSOIDbEyiYWNnQ2s
rCwsRDBgcjfk7st45C6X3CS3d5t44eXd7r79dvbtzt0S/1lJ0f5K0f6P0l4w5yWzL832B7P90mxX
zHZm/j6a7ZLZT2b7tNl+M9tbs723gB/MdmG2K7O9NttVsz0y2y+z/TDbm9n/K2AvzPbabC/MdsNs
T812Y7Y3Zvs021WzXTDbb7P9Mdt7s12Y7YXZnsw2Bf9gto9m+2i2b2b7YLaPZvtstt9m+2y2L2b7
bLa3Zvtsth9m+2S2H2b7YraPZvtqtp9m+2q2n2b7ZrafZvtotp9m+2n2b7Y7Y/Zvtjtr9m+2u2v2
v2b7Z7Z/Zvtntn9m+2+2/2b7b7b/Zvt/JmB/zPbXbH/N9tds/8z2z2z/zPbPbP/N9t9s/83232z/
z/4J2H5sLwTsxtk/Adtx27Yf24v92F4I2I6zf27A9mN7sR/bCwHbcbbj7J8bsP3YXuzH9kLAdpzt
OPvnBmw/thf7sb0QsB1nO87+uQHbTezFfmwvBGzH2Y6zf27A9mN7sR/bCwHbcbbj7J8bsP3YXuzH
9kLAdpztOPvnBmw/thf7sb0QsB1nO87+uQHbje3FfmwvBGzH2Y6zf27A9mN7sR/bCwHbcbbj7J8b
sP3YXuzH9kLAdpztOPvnBmw/thf7sb0QsB1nO87+uQHbje3FfmwvBGzH2Y6zf27A9mN7sR/bCwHb
cbbj7J8bsP3YXuzH9kLAdpztOPvnBmw/thf7sb0QsB1nO87+uQHbje3FfmwvBGzH2Y6zf27A9mN7
sR/bCwHbcbbj7J8b+A0u65hW08NqOAAAAABJRU5ErkJggg==
"""

# --- NETWORK CLASS ---
class SimpleTS3:
    def __init__(self, host, port):
        self.sock = socket.create_connection((host, port), timeout=15)
        self.f = self.sock.makefile('rw', encoding='utf-8', newline='\n')
        self.f.readline() 
        self.f.readline() 

    def send(self, cmd):
        try:
            self.f.write(cmd + "\n"); self.f.flush()
        except: return None
        data = ""
        while True:
            line = self.f.readline()
            if not line: break
            line = line.strip()
            if line.startswith("error"):
                if "id=0" not in line: return line
                break
            data += line
        return "OK" if not data else data

    def parse_list(self, raw_data):
        if not raw_data or raw_data == "OK": return []
        items = []
        for item_str in raw_data.split("|"):
            item_dict = {}
            for prop in item_str.split(" "):
                if "=" in prop:
                    key, val = prop.split("=", 1)
                    item_dict[key] = val.replace(r"\s", " ").replace(r"\p", "|").replace(r"\/", "/")
            items.append(item_dict)
        return items

# --- GUI CLASS ---
class ModernBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"TS3 AFK Manager Pro v{CURRENT_VERSION}")
        self.root.geometry("500x820") 
        self.root.configure(bg="#2b2b2b")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Icon
        try:
            icondata = base64.b64decode(ICON_DATA)
            img = tk.PhotoImage(data=icondata)
            self.root.iconphoto(True, img)
        except: pass

        self.COLORS = {
            "bg": "#2b2b2b", "card": "#383838", "text": "#ffffff", 
            "accent": "#00a8ff", "success": "#2ecc71", "danger": "#e74c3c", 
            "input_bg": "#4a4a4a", "input_fg": "#ffffff"
        }
        
        self.stop_event = threading.Event()
        self.is_running = False
        self.live_config = {'CID': 9, 'TIME': 900, 'EXEMPT': [6, 10], 'POKE': True}

        self.setup_ui()
        self.load_settings()
        
        # --- AUTO UPDATE CHECK ---
        # Run check in background so app opens instantly
        threading.Thread(target=self.check_for_updates, daemon=True).start()

        # AUTO START CHECK
        if self.var_autostart.get():
            self.log_message("[SYSTEM] Auto-Start Enabled. Launching in 3s...")
            self.root.after(3000, self.start_bot)

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Header
        header = tk.Frame(self.root, bg=self.COLORS["bg"], pady=15)
        header.pack(fill="x")
        tk.Label(header, text="AFK MANAGER", font=("Segoe UI", 16, "bold"), bg=self.COLORS["bg"], fg=self.COLORS["accent"]).pack()
        tk.Label(header, text=f"Version {CURRENT_VERSION}", font=("Segoe UI", 8), bg=self.COLORS["bg"], fg="#666").pack()

        # Cards
        self.create_card("Live Controls", self.setup_controls)
        self.create_card("Connection Settings", self.setup_connection)
        self.create_card("System Settings", self.setup_system) 

        # Buttons
        btn_frame = tk.Frame(self.root, bg=self.COLORS["bg"], pady=10)
        btn_frame.pack()
        self.btn_start = tk.Button(btn_frame, text="START ENGINE", bg=self.COLORS["success"], fg="white", font=("Segoe UI", 11, "bold"), relief="flat", padx=20, pady=8, command=self.start_bot)
        self.btn_start.pack(side="left", padx=10)
        self.btn_stop = tk.Button(btn_frame, text="STOP", bg=self.COLORS["danger"], fg="white", font=("Segoe UI", 11, "bold"), relief="flat", padx=20, pady=8, command=self.stop_bot, state="disabled")
        self.btn_stop.pack(side="left", padx=10)

        # Log
        log_frame = tk.Frame(self.root, bg=self.COLORS["bg"], padx=15, pady=5)
        log_frame.pack(fill="both", expand=True)
        tk.Label(log_frame, text="System Log", bg=self.COLORS["bg"], fg="#888888", font=("Segoe UI", 8)).pack(anchor="w")
        self.log_area = scrolledtext.ScrolledText(log_frame, height=10, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 9), relief="flat", borderwidth=0)
        self.log_area.pack(fill="both", expand=True)
        self.log_message("[SYSTEM] Ready.")

    def create_card(self, title, setup_func):
        card = tk.Frame(self.root, bg=self.COLORS["card"], padx=15, pady=10)
        card.pack(fill="x", padx=15, pady=5)
        tk.Label(card, text=title.upper(), font=("Segoe UI", 8, "bold"), bg=self.COLORS["card"], fg="#888888").pack(anchor="w", pady=(0, 5))
        inner = tk.Frame(card, bg=self.COLORS["card"])
        inner.pack(fill="x")
        setup_func(inner)

    def create_labeled_entry(self, parent, label, row):
        tk.Label(parent, text=label, bg=self.COLORS["card"], fg=self.COLORS["text"], font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w", pady=5)
        entry = tk.Entry(parent, bg=self.COLORS["input_bg"], fg=self.COLORS["input_fg"], insertbackground="white", relief="flat", font=("Segoe UI", 10))
        entry.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
        parent.grid_columnconfigure(1, weight=1)
        return entry

    def setup_controls(self, parent):
        self.entry_cid = self.create_labeled_entry(parent, "Target Channel ID:", 0)
        self.entry_time = self.create_labeled_entry(parent, "Max Idle Time (s):", 1)
        self.entry_exempt = self.create_labeled_entry(parent, "Ignore Group IDs:", 2)
        tk.Label(parent, text="(e.g. 6, 10)", bg=self.COLORS["card"], fg="#666", font=("Segoe UI", 8)).grid(row=3, column=1, sticky="w")
        
        self.var_poke = tk.BooleanVar(value=True)
        self.chk_poke = tk.Checkbutton(parent, text="Poke user when moved?", variable=self.var_poke, 
                                       bg=self.COLORS["card"], fg=self.COLORS["accent"], 
                                       selectcolor=self.COLORS["bg"], activebackground=self.COLORS["card"], 
                                       activeforeground=self.COLORS["accent"], font=("Segoe UI", 10))
        self.chk_poke.grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 5))

        btn = tk.Button(parent, text="Update Live Settings", bg=self.COLORS["accent"], fg="white", relief="flat", font=("Segoe UI", 8, "bold"), command=self.update_live_settings)
        btn.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))

    def setup_connection(self, parent):
        self.entry_host = self.create_labeled_entry(parent, "Host Address:", 0)
        self.entry_user = self.create_labeled_entry(parent, "Username:", 1)
        self.entry_pass = self.create_labeled_entry(parent, "Password:", 2)

    def setup_system(self, parent):
        self.var_windows_start = tk.BooleanVar(value=False)
        chk_win = tk.Checkbutton(parent, text="Run on Windows Startup", variable=self.var_windows_start, 
                                 bg=self.COLORS["card"], fg="white", selectcolor=self.COLORS["bg"], 
                                 activebackground=self.COLORS["card"], activeforeground="white", font=("Segoe UI", 10))
        chk_win.pack(anchor="w")

        self.var_autostart = tk.BooleanVar(value=False)
        chk_auto = tk.Checkbutton(parent, text="Auto-Connect Engine on Launch", variable=self.var_autostart, 
                                  bg=self.COLORS["card"], fg="white", selectcolor=self.COLORS["bg"], 
                                  activebackground=self.COLORS["card"], activeforeground="white", font=("Segoe UI", 10))
        chk_auto.pack(anchor="w")

    # --- UPDATE LOGIC ---
    def check_for_updates(self):
        # Skip if links are default or invalid
        if "YOUR_USER" in VERSION_URL: return
        try:
            self.log_message("[UPDATE] Checking for updates...")
            # 1. Download version.txt
            with urllib.request.urlopen(VERSION_URL, timeout=5) as response:
                latest_version = response.read().decode('utf-8').strip()
            
            # 2. Compare Versions
            if float(latest_version) > float(CURRENT_VERSION):
                self.log_message(f"[UPDATE] New version found: {latest_version}")
                if messagebox.askyesno("Update Available", f"Version {latest_version} is available.\nDo you want to update now?"):
                    self.perform_update()
            else:
                self.log_message("[UPDATE] App is up to date.")
        except Exception as e:
            self.log_message(f"[UPDATE] Check failed: {e}")

    def perform_update(self):
        try:
            self.log_message("[UPDATE] Downloading new version...")
            # 1. Download the new EXE as 'new_ver.exe'
            new_exe_name = "new_ver.exe"
            urllib.request.urlretrieve(EXE_DOWNLOAD_URL, new_exe_name)
            
            # 2. Create the BAT script to swap files
            current_exe = sys.executable
            batch_script = f"""
@echo off
timeout /t 2 /nobreak >nul
del "{current_exe}"
ren "{new_exe_name}" "{os.path.basename(current_exe)}"
start "" "{current_exe}"
del "%~f0"
            """
            
            with open("updater.bat", "w") as f:
                f.write(batch_script)

            # 3. Launch script and exit
            self.log_message("[UPDATE] Restarting to apply...")
            subprocess.Popen("updater.bat", shell=True)
            self.root.quit()
        except Exception as e:
            self.log_message(f"[UPDATE] Update failed: {e}")

    # --- REGISTRY LOGIC ---
    def set_startup_registry(self):
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            app_name = "AFK_Manager_Pro"
            
            # Use sys.executable if frozen (exe), else use __file__
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
            else:
                exe_path = os.path.abspath(__file__)

            if self.var_windows_start.get():
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{exe_path}"')
                self.log_message("[SYSTEM] Startup Registry Added.")
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                    self.log_message("[SYSTEM] Startup Registry Removed.")
                except FileNotFoundError: pass
            
            winreg.CloseKey(key)
        except Exception as e:
            self.log_message(f"[ERROR] Registry Access Failed: {e}")

    # --- SAVE / LOAD ---
    def save_settings(self):
        data = {
            "host": self.entry_host.get(),
            "user": self.entry_user.get(),
            "pass": self.entry_pass.get(),
            "cid": self.entry_cid.get(),
            "time": self.entry_time.get(),
            "exempt": self.entry_exempt.get(),
            "poke": self.var_poke.get(),
            "win_startup": self.var_windows_start.get(),
            "auto_connect": self.var_autostart.get()
        }
        try:
            with open(SETTINGS_FILE, "w") as f: json.dump(data, f)
            self.set_startup_registry() 
        except: pass

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    self.entry_host.insert(0, data.get("host", ""))
                    self.entry_user.insert(0, data.get("user", ""))
                    self.entry_pass.insert(0, data.get("pass", ""))
                    self.entry_cid.insert(0, data.get("cid", "9"))
                    self.entry_time.insert(0, data.get("time", "900"))
                    self.entry_exempt.insert(0, data.get("exempt", "6, 10"))
                    self.var_poke.set(data.get("poke", True))
                    self.var_windows_start.set(data.get("win_startup", False))
                    self.var_autostart.set(data.get("auto_connect", False))
            except: self.default_fill()
        else: self.default_fill()

    def default_fill(self):
        self.entry_host.insert(0, "") 
        self.entry_user.insert(0, "")
        self.entry_pass.insert(0, "")
        self.entry_cid.insert(0, "9")
        self.entry_time.insert(0, "900") 
        self.entry_exempt.insert(0, "6, 10")
        self.var_poke.set(True)

    def on_close(self):
        self.save_settings()
        self.root.destroy()

    # --- LOGIC ---
    def log_message(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def update_live_settings(self):
        try:
            self.live_config['CID'] = int(self.entry_cid.get())
            self.live_config['TIME'] = int(self.entry_time.get())
            self.live_config['POKE'] = self.var_poke.get()
            raw_exempt = self.entry_exempt.get()
            self.live_config['EXEMPT'] = [int(x.strip()) for x in raw_exempt.split(',') if x.strip().isdigit()]
            self.log_message(f"[CONFIG] Updated: ID={self.live_config['CID']} | Poke={self.live_config['POKE']}")
            self.save_settings()
        except: messagebox.showerror("Error", "Please check your inputs.")

    def start_bot(self):
        if self.is_running: return
        self.save_settings()
        self.update_live_settings()
        self.is_running = True
        self.stop_event.clear()
        self.btn_start.config(state="disabled", bg="#4a4a4a")
        self.btn_stop.config(state="normal", bg=self.COLORS["danger"])
        
        login = {'HOST': self.entry_host.get(), 'USER': self.entry_user.get(), 'PASS': self.entry_pass.get()}
        self.thread = threading.Thread(target=self.run_logic, args=(login,))
        self.thread.daemon = True
        self.thread.start()

    def stop_bot(self):
        if not self.is_running: return
        self.log_message("[SYSTEM] Stopping engine...")
        self.stop_event.set()

    def run_logic(self, login):
        try:
            self.log_message(f"[NET] Connecting to {login['HOST']}...")
            ts = SimpleTS3(login['HOST'], 10011)

            self.log_message("[NET] Authenticating...")
            res = ts.send(f"login {login['USER']} {login['PASS']}")
            if res != "OK":
                self.log_message(f"[ERROR] LOGIN FAILED: {res}")
                return

            ts.send(f"use sid=1") 
            ts.send("clientupdate client_nickname=AFK_Manager")
            self.log_message("[SUCCESS] Bot is online and scanning.")

            while not self.stop_event.is_set():
                target_cid = self.live_config['CID']
                target_time = self.live_config['TIME']
                exempt_groups = self.live_config['EXEMPT']
                do_poke = self.live_config['POKE']
                
                response = ts.send("clientlist -times -groups")
                if response != "OK" and not response.startswith("error"):
                    clients = ts.parse_list(response)
                    for client in clients:
                        if client.get("client_type") == '1': continue 
                        
                        clid = client.get("clid")
                        name = client.get("client_nickname", "Unknown")
                        cid = int(client.get("cid", 0))
                        idle = int(client.get("client_idle_time", 0)) / 1000
                        
                        # Exempt Check
                        groups = [int(g) for g in client.get("client_servergroups", "").split(",") if g.isdigit()]
                        if any(g in exempt_groups for g in groups): continue

                        # Move Check
                        if cid != target_cid and idle > target_time:
                            self.log_message(f"[MOVE] {name} (Idle: {int(idle)}s)")
                            ts.send(f"clientmove clid={clid} cid={target_cid}")
                            if do_poke:
                                ts.send(f"clientpoke clid={clid} msg=AFK\\sMove.")
                
                for _ in range(5): 
                    if self.stop_event.is_set(): break
                    time.sleep(1)
                
                if not self.stop_event.is_set(): ts.send("whoami")

        except Exception as e:
            self.log_message(f"[ERROR] Connection Failed: {e}")
        finally:
            self.log_message("[SYSTEM] Engine Stopped.")
            self.is_running = False
            self.root.after(0, lambda: self.btn_start.config(state="normal", bg="#00a8ff"))
            self.root.after(0, lambda: self.btn_stop.config(state="disabled", bg="#4a4a4a"))

if __name__ == "__main__":
    root = tk.Tk()
    app = ModernBotGUI(root)
    root.mainloop()