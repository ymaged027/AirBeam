import os
import sys
import time
import json
import struct
import socket
import threading
import subprocess
import re
import base64
import shutil
from typing import Optional

if getattr(sys, "frozen", False):
    APP_ROOT = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, "_MEIPASS", APP_ROOT)
else:
    APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    BUNDLE_DIR = os.path.dirname(__file__)

LOG_FILE_PATH = os.path.join(APP_ROOT, "airbeam_sender.log")
LAST_HOME_WIFI_FILE = os.path.join(APP_ROOT, "last_home_wifi.txt")

class SafeLogStream:
    def __init__(self, filepath):
        self.filepath = filepath
    def write(self, data):
        if not data:
            return
        try:
            with open(self.filepath, "a", encoding="utf-8", errors="replace") as f:
                f.write(data)
        except Exception:
            pass
    def flush(self):
        pass

import traceback

def log_error_to_file(prefix, err_str):
    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n[{prefix} {time.strftime('%Y-%m-%d %H:%M:%S')}] {err_str}\n")
    except Exception:
        pass

def global_excepthook(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    err = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    log_error_to_file("GLOBAL EXCEPTION", err)

sys.excepthook = global_excepthook

if hasattr(threading, "excepthook"):
    def thread_excepthook(args):
        err = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
        log_error_to_file(f"THREAD EXCEPTION ({args.thread.name})", err)
    threading.excepthook = thread_excepthook

# Fix pythonw.exe crash: always provide SafeLogStream
sys.stdout = SafeLogStream(LOG_FILE_PATH)
sys.stderr = SafeLogStream(LOG_FILE_PATH)

# Suppress flashing CMD/console windows from subprocess calls on Windows
if sys.platform == "win32":
    _orig_run = subprocess.run
    _orig_popen = subprocess.Popen

    def _silent_run(*args, **kwargs):
        if "startupinfo" not in kwargs:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0  # SW_HIDE
            kwargs["startupinfo"] = si
        kwargs["creationflags"] = kwargs.get("creationflags", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        return _orig_run(*args, **kwargs)

    def _silent_popen(*args, **kwargs):
        if "startupinfo" not in kwargs:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0  # SW_HIDE
            kwargs["startupinfo"] = si
        kwargs["creationflags"] = kwargs.get("creationflags", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        return _orig_popen(*args, **kwargs)

    subprocess.run = _silent_run
    subprocess.Popen = _silent_popen

import urllib.request
import urllib.parse
import tempfile
import webbrowser
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from http.server import HTTPServer, SimpleHTTPRequestHandler, BaseHTTPRequestHandler, ThreadingHTTPServer
import mimetypes
import atexit
import io
import uuid
import zipfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import qrcode

# ==============================================================================
# NATIVE OLE DRAG-AND-DROP ENGINE (TKINTERDND2)
# ==============================================================================
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    TKDND_AVAILABLE = True
except Exception:
    TKDND_AVAILABLE = False

if TKDND_AVAILABLE:
    class BaseTkApp(TkinterDnD.Tk):
        pass
else:
    class BaseTkApp(tk.Tk):
        pass



SESSION_NODE_ID = uuid.uuid4().hex[:8]

def sanitize_ntfs_filename(name: str) -> str:
    """Strips directory traversal and replaces illegal Windows NTFS characters (<>:"/\\|?* and control chars) with '_'."""
    if not name:
        return f"file_{int(time.time())}"
    clean = os.path.basename(name.replace("\\", "/").strip())
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', clean)
    clean = clean.rstrip(". ")
    if not clean:
        clean = f"file_{int(time.time())}"
    return clean

def get_all_local_ips() -> set:
    ips = {"127.0.0.1", "192.168.137.1"}
    try:
        host = socket.gethostname()
        for ip in socket.gethostbyname_ex(host)[2]:
            ips.add(ip)
    except Exception:
        pass
    try:
        local = get_local_ip()
        if local:
            ips.add(local)
    except Exception:
        pass
    return ips

class SocketStreamAdapter(io.RawIOBase):
    """Zero-copy raw socket stream adapter for streaming uncompressed zip data over HTTP sockets."""
    def __init__(self, wfile, record_cb=None):
        self.wfile = wfile
        self.record_cb = record_cb
        self._pos = 0

    def write(self, b):
        if not b:
            return 0
        self.wfile.write(b)
        n = len(b)
        self._pos += n
        if self.record_cb:
            self.record_cb(n)
        return n

    def seekable(self):
        return False

    def tell(self):
        return self._pos

mimetypes.add_type("application/vnd.android.package-archive", ".apk")

UDP_PORT = 7778
NIO_PORT = 7777
HTTP_PORT = 8080
APK_SERVER_PORT = 8888
IPHONE_PORTAL_PORT = 8080
IPHONE_PORTAL_PORTS = (8080, 8090)
IPHONE_RECEIVED_DIR = os.path.join(APP_ROOT, "Received_From_iPhone")
IPHONE_CONFIG_FILE = os.path.join(APP_ROOT, "iphone_hotspot_config.json")
PC_RECEIVED_DIR = os.path.join(APP_ROOT, "Received_From_PC")
os.makedirs(IPHONE_RECEIVED_DIR, exist_ok=True)
os.makedirs(PC_RECEIVED_DIR, exist_ok=True)
DEFAULT_STRIPE_SIZE = 16 * 1024 * 1024  # 16 MB stripes
CHUNK_SLICE_BYTES = 2 * 1024 * 1024     # 2 MB smooth streaming slices
SOCKET_SNDBUF_SIZE = 8 * 1024 * 1024    # 8 MB TCP send buffer
PARALLEL_STREAMS = 6                    # Adaptive (6 for >= 64MB, 4 for smaller)
HEADER_STRUCT = struct.Struct("!4sQIIQQ")  # 36 bytes: magic, transfer_id, chunk_index, total_chunks, chunk_offset, chunk_length

def get_local_ip():
    # 1. Try socket connection to public DNS (fastest when internet connected)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
            return ip
    except Exception:
        pass

    # 2. Try socket getaddrinfo for local hostname (works completely offline / hotspot!)
    try:
        hostname = socket.gethostname()
        for item in socket.getaddrinfo(hostname, None):
            if item[0] == socket.AF_INET:
                ip = item[4][0]
                if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                    return ip
    except Exception:
        pass

    # 3. Try PowerShell Get-NetIPAddress on active Wi-Fi interface
    try:
        cmd = ["powershell", "-NoProfile", "-Command",
               "Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias 'Wi-Fi*' -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -notlike '169.254.*' } | Select-Object -ExpandProperty IPAddress"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        for line in res.stdout.splitlines():
            ip = line.strip()
            if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                return ip
    except Exception:
        pass

    return "127.0.0.1"

def format_bytes(size):
    if size < 1024:
        return f"{int(size)} B"
    for unit in ['KB', 'MB', 'GB', 'TB']:
        size /= 1024.0
        if size < 1024.0:
            return f"{size:.1f} {unit}"
    return f"{size:.1f} PB"

def format_speed(bps):
    if bps < 1.0:
        return "0 B/s"
    elif bps < 1024.0:
        return f"{int(bps)} B/s"
    elif bps < 1024.0 * 1024.0:
        return f"{bps / 1024.0:.1f} KB/s"
    elif bps < 1024.0 * 1024.0 * 1024.0:
        return f"{bps / (1024.0 * 1024.0):.1f} MB/s"
    else:
        return f"{bps / (1024.0 * 1024.0 * 1024.0):.2f} GB/s"

def format_speed_with_mbps(bps):
    if bps < 1.0:
        return "0.0 MB/s (0 Mbps)"
    mb_s = bps / (1024.0 * 1024.0)
    mbps = (bps * 8.0) / 1_000_000.0
    return f"{mb_s:.1f} MB/s ({int(mbps)} Mbps)"

def format_eta(seconds):
    if seconds <= 0:
        return "00:00"
    if seconds >= 3600:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"

def parse_wifi_telemetry():
    """
    Parses 'netsh wlan show interfaces' for active Wi-Fi link parameters:
    SSID, Band, Channel, Link Rate (Mbps), Signal (%).
    """
    try:
        res = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True, timeout=2)
        data = {}
        for line in res.stdout.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                data[k.strip().lower()] = v.strip()

        state = data.get("state", "").lower()
        if state != "connected":
            cur_prof = get_current_wifi_profile()
            if cur_prof:
                link_speed = "Auto"
                try:
                    c_cmd = ["powershell", "-NoProfile", "-Command",
                             "(Get-NetAdapter -Name 'Wi-Fi*' -ErrorAction SilentlyContinue | Select-Object -First 1).LinkSpeed"]
                    c_res = subprocess.run(c_cmd, capture_output=True, text=True, timeout=2)
                    if c_res.stdout.strip():
                        link_speed = c_res.stdout.strip()
                except Exception:
                    pass
                return {
                    "connected": True,
                    "ssid": cur_prof,
                    "band": "Wi-Fi",
                    "channel": "",
                    "rate": link_speed,
                    "signal": "Good",
                    "is_airbeam": (cur_prof.lower() == "airbeam")
                }
            return {"connected": False, "state": state or "disconnected"}

        ssid = data.get("ssid", "Unknown")
        radio = data.get("radio type", "")
        band = data.get("band", "")
        channel = data.get("channel", "")
        rx_rate = data.get("receive rate (mbps)", "")
        tx_rate = data.get("transmit rate (mbps)", "")
        signal = data.get("signal", "")

        # Infer band if not explicit
        if not band:
            if radio in ("802.11ax", "802.11ac", "802.11a"):
                band = "5 GHz"
            elif channel and channel.isdigit() and int(channel) > 14:
                band = "5 GHz"
            else:
                band = "2.4 GHz"

        rate_val = rx_rate or tx_rate or "0"
        return {
            "connected": True,
            "ssid": ssid,
            "band": band,
            "channel": channel,
            "rate": rate_val,
            "signal": signal,
            "is_airbeam": (ssid.lower() == "airbeam")
        }
    except Exception:
        return {"connected": False, "state": "unknown"}

class HotspotToggleSwitch(tk.Canvas):
    """
    Animated Custom Toggle Switch Widget with sliding pill track.
    #475569 Slate Gray when OFF, #10B981 Emerald Green when ON.
    """
    def __init__(self, parent, command=None, width=52, height=26, bg="#162032"):
        super().__init__(parent, width=width, height=height, bg=bg, highlightthickness=0, cursor="hand2")
        self.width = width
        self.height = height
        self.command = command
        self.is_on = False
        self.anim_pos = 0.0  # 0.0 = OFF (left), 1.0 = ON (right)
        self._animating = False

        self.bind("<Button-1>", self._on_click)
        self._draw()

    def _draw(self):
        self.delete("all")
        r = self.height / 2
        # Interpolate color: OFF: #475569 (71, 85, 105), ON: #10B981 (16, 185, 129)
        r_c = int(71 + (16 - 71) * self.anim_pos)
        g_c = int(85 + (185 - 85) * self.anim_pos)
        b_c = int(105 + (129 - 105) * self.anim_pos)
        track_color = f"#{r_c:02x}{g_c:02x}{b_c:02x}"

        # Draw rounded pill track
        self.create_oval(1, 1, self.height - 1, self.height - 1, fill=track_color, outline=track_color)
        self.create_oval(self.width - self.height + 1, 1, self.width - 1, self.height - 1, fill=track_color, outline=track_color)
        self.create_rectangle(r, 1, self.width - r, self.height - 1, fill=track_color, outline=track_color)

        # Sliding white thumb circle
        thumb_padding = 3
        thumb_radius = r - thumb_padding
        travel = self.width - 2 * r
        center_x = r + travel * self.anim_pos
        center_y = r
        self.create_oval(
            center_x - thumb_radius, center_y - thumb_radius,
            center_x + thumb_radius, center_y + thumb_radius,
            fill="#FFFFFF", outline="#FFFFFF"
        )

    def _on_click(self, event=None):
        new_state = not self.is_on
        self.set_state(new_state, trigger_callback=True)

    def set_state(self, state, trigger_callback=False, animated=True):
        if self.is_on == state and not self._animating:
            return
        self.is_on = bool(state)
        target = 1.0 if self.is_on else 0.0
        if animated:
            self._animate_to(target)
        else:
            self.anim_pos = target
            self._draw()
        if trigger_callback and self.command:
            self.command(self.is_on)

    def _animate_to(self, target):
        step = 0.25 if target > self.anim_pos else -0.25
        new_pos = self.anim_pos + step
        if (step > 0 and new_pos >= target) or (step < 0 and new_pos <= target):
            self.anim_pos = target
            self._animating = False
            self._draw()
        else:
            self.anim_pos = new_pos
            self._animating = True
            self._draw()
            self.after(16, lambda: self._animate_to(target))

def get_connected_hotspot_client_ips():
    ips = []
    try:
        proc = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=1)
        in_hotspot_section = False
        for line in proc.stdout.splitlines():
            line = line.strip()
            if "192.168.137.1" in line:
                in_hotspot_section = True
                continue
            elif line.startswith("Interface:"):
                in_hotspot_section = False
                continue
            if in_hotspot_section:
                parts = line.split()
                if len(parts) >= 2:
                    ip = parts[0]
                    if ip.startswith("192.168.137.") and not ip.endswith(".1") and not ip.endswith(".255"):
                        ips.append(ip)
    except Exception:
        pass
    return ips

def find_hotspot_device_ip():
    """Finds the tablet's IP on 192.168.43.1 (tablet-hosted hotspot) or 192.168.137.x (Windows hotspot)."""
    # 0. Check preferred tablet IP (10.150.131.50) and standard gateway (192.168.43.1)
    for tip in ("10.150.131.50", "192.168.43.1"):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.20)
            if s.connect_ex((tip, NIO_PORT)) == 0:
                s.close()
                return tip
            s.close()
        except Exception:
            pass

    # 1. First probe any IPs in Windows ARP table for 192.168.137.x
    clients = get_connected_hotspot_client_ips()
    for ip in clients:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.20)
            if s.connect_ex((ip, NIO_PORT)) == 0:
                s.close()
                return ip
            s.close()
        except Exception:
            pass

    # 2. Fast multi-threaded TCP sweep on 192.168.137.2 - 254 (Port 7777)
    def probe(ip):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.20)
        try:
            if s.connect_ex((ip, NIO_PORT)) == 0:
                return ip
        except Exception:
            pass
        finally:
            s.close()
        return None

    test_ips = [f"192.168.137.{i}" for i in range(2, 255)]
    with ThreadPoolExecutor(max_workers=60) as pool:
        for res in pool.map(probe, test_ips):
            if res:
                return res
    return None

PREVIOUS_WIFI_SSID = None

def ensure_windows_airbeam_profile(ssid="airbeam", password="airbeam123"):
    """Installs or updates the Windows Wi-Fi profile for given SSID & password inside the app folder."""
    profile_xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>manual</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>"""
    tmp_path = os.path.join(APP_ROOT, f"{ssid}_wifi_profile.xml")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(profile_xml)
        subprocess.run(["netsh", "wlan", "add", "profile", f"filename={tmp_path}", "user=current"], capture_output=True, timeout=3)
    except Exception as e:
        print(f"Error ensuring Wi-Fi profile: {e}")
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

def save_last_home_wifi(profile_name: str):
    """Persists the detected home Wi-Fi profile name to disk."""
    if not profile_name or profile_name.strip().lower() == "airbeam":
        return
    try:
        with open(LAST_HOME_WIFI_FILE, "w", encoding="utf-8") as f:
            f.write(profile_name.strip())
    except Exception as e:
        print(f"Error saving last home wifi: {e}")

def is_hotspot_profile_name(name: str) -> bool:
    if not name:
        return False
    nl = name.strip().lower()
    return any(k in nl for k in ("airbeam", "iphone", "hotspot", "galaxy", "redmi", "realme", "android"))

def native_wlan_connect(profile_name: str) -> Tuple[bool, int]:
    """Connects Windows Wi-Fi to a specified profile using native wlanapi.dll.
    Bypasses netsh elevation and Windows 11 location privacy restrictions.
    """
    import ctypes
    from ctypes import wintypes

    wlan = ctypes.windll.wlanapi
    handle = wintypes.HANDLE()
    negotiated = wintypes.DWORD()
    ret = wlan.WlanOpenHandle(2, None, ctypes.byref(negotiated), ctypes.byref(handle))
    if ret != 0:
        return False, ret

    try:
        class GUID(ctypes.Structure):
            _fields_ = [
                ('Data1', wintypes.DWORD),
                ('Data2', wintypes.WORD),
                ('Data3', wintypes.WORD),
                ('Data4', ctypes.c_byte * 8)
            ]

        class WLAN_INTERFACE_INFO(ctypes.Structure):
            _fields_ = [
                ('InterfaceGuid', GUID),
                ('strInterfaceDescription', wintypes.WCHAR * 256),
                ('isState', wintypes.DWORD)
            ]

        class WLAN_INTERFACE_INFO_LIST(ctypes.Structure):
            _fields_ = [
                ('dwNumberOfItems', wintypes.DWORD),
                ('dwIndex', wintypes.DWORD),
                ('InterfaceInfo', WLAN_INTERFACE_INFO * 1)
            ]

        info_list_ptr = ctypes.POINTER(WLAN_INTERFACE_INFO_LIST)()
        ret = wlan.WlanEnumInterfaces(handle, None, ctypes.byref(info_list_ptr))
        if ret != 0 or info_list_ptr.contents.dwNumberOfItems == 0:
            return False, ret

        guid = info_list_ptr.contents.InterfaceInfo[0].InterfaceGuid

        class WLAN_CONNECTION_PARAMETERS(ctypes.Structure):
            _fields_ = [
                ('wlanConnectionMode', ctypes.c_uint32),
                ('padding', ctypes.c_uint32),
                ('strProfile', wintypes.LPCWSTR),
                ('pDot11Ssid', ctypes.c_void_p),
                ('pDesiredBssidList', ctypes.c_void_p),
                ('dot11BssType', ctypes.c_uint32),
                ('dwFlags', ctypes.c_uint32)
            ]

        conn_params = WLAN_CONNECTION_PARAMETERS()
        conn_params.wlanConnectionMode = 0 # wlan_connection_mode_profile
        conn_params.padding = 0
        conn_params.strProfile = profile_name
        conn_params.pDot11Ssid = None
        conn_params.pDesiredBssidList = None
        conn_params.dot11BssType = 1 # dot11_BSS_type_infrastructure
        conn_params.dwFlags = 0

        ret = wlan.WlanConnect(handle, ctypes.byref(guid), ctypes.byref(conn_params), None)
        return ret == 0, ret
    except Exception as e:
        print(f"native_wlan_connect error: {e}")
        return False, -1
    finally:
        wlan.WlanCloseHandle(handle, None)

def native_wlan_disconnect() -> bool:
    """Disconnects Windows Wi-Fi using native wlanapi.dll."""
    import ctypes
    from ctypes import wintypes

    wlan = ctypes.windll.wlanapi
    handle = wintypes.HANDLE()
    negotiated = wintypes.DWORD()
    ret = wlan.WlanOpenHandle(2, None, ctypes.byref(negotiated), ctypes.byref(handle))
    if ret != 0:
        return False

    try:
        class GUID(ctypes.Structure):
            _fields_ = [('Data1', wintypes.DWORD), ('Data2', wintypes.WORD), ('Data3', wintypes.WORD), ('Data4', ctypes.c_byte * 8)]
        class WLAN_INTERFACE_INFO(ctypes.Structure):
            _fields_ = [('InterfaceGuid', GUID), ('strInterfaceDescription', wintypes.WCHAR * 256), ('isState', wintypes.DWORD)]
        class WLAN_INTERFACE_INFO_LIST(ctypes.Structure):
            _fields_ = [('dwNumberOfItems', wintypes.DWORD), ('dwIndex', wintypes.DWORD), ('InterfaceInfo', WLAN_INTERFACE_INFO * 1)]
        info_list_ptr = ctypes.POINTER(WLAN_INTERFACE_INFO_LIST)()
        if wlan.WlanEnumInterfaces(handle, None, ctypes.byref(info_list_ptr)) != 0:
            return False
        guid = info_list_ptr.contents.InterfaceInfo[0].InterfaceGuid
        ret = wlan.WlanDisconnect(handle, ctypes.byref(guid), None)
        return ret == 0
    except Exception:
        return False
    finally:
        wlan.WlanCloseHandle(handle, None)

def find_matching_saved_wifi_profile(target_ssid: str) -> Optional[str]:
    """Finds a matching saved Windows Wi-Fi profile, handling:
    1. Exact match
    2. Case-insensitive match
    3. Unicode apostrophe vs ASCII apostrophe normalization (e.g. \u2019 vs ')
    """
    if not target_ssid:
        return None

    saved_profiles = []
    try:
        res = subprocess.run(["netsh", "wlan", "show", "profiles"], capture_output=True, text=True, timeout=3)
        for line in res.stdout.splitlines():
            m = re.match(r"^\s*(?:All|Current)\s*User Profile\s*:\s*(.+)$", line, re.IGNORECASE)
            if m:
                prof = m.group(1).strip()
                if prof and prof not in saved_profiles:
                    saved_profiles.append(prof)
    except Exception:
        pass

    target_norm = target_ssid.replace("\u2019", "'").replace("`", "'").strip().lower()

    # Exact match first
    for p in saved_profiles:
        if p == target_ssid:
            return p

    # Normalized match
    for p in saved_profiles:
        p_norm = p.replace("\u2019", "'").replace("`", "'").strip().lower()
        if p_norm == target_norm:
            return p

    # Substring match if name is unique enough (e.g. "iphone" in name)
    for p in saved_profiles:
        p_norm = p.replace("\u2019", "'").replace("`", "'").strip().lower()
        if target_norm in p_norm or p_norm in target_norm:
            return p

    return None

def get_current_wifi_profile() -> Optional[str]:
    r"""
    Extracts the active Wi-Fi profile or network name.
    1. Queries PowerShell Get-NetConnectionProfile for Wi-Fi interface (fast & works without elevation/location).
    2. Falls back to 'netsh wlan show interfaces'.
    """
    try:
        cmd = ["powershell", "-NoProfile", "-Command",
               "(Get-NetConnectionProfile -InterfaceAlias 'Wi-Fi*' -ErrorAction SilentlyContinue).Name"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        val = res.stdout.strip()
        if val:
            return val
    except Exception:
        pass

    try:
        res = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True, timeout=2)
        for line in res.stdout.splitlines():
            m = re.match(r"^\s*Profile\s*:\s*(.+)$", line)
            if m:
                val = m.group(1).strip()
                if val and val.lower() != "<none>":
                    return val
        for line in res.stdout.splitlines():
            if line.strip().lower().startswith("bssid"):
                continue
            m = re.match(r"^\s*SSID\s*:\s*(.+)$", line)
            if m:
                val = m.group(1).strip()
                if val and val.lower() != "<none>":
                    return val
    except Exception:
        pass

    return None

get_current_wifi_connection = get_current_wifi_profile

def get_best_home_wifi_profile(app_instance=None) -> Optional[str]:
    r"""
    Resolves the user's home Wi-Fi profile:
    1. Checks in-memory previous_wifi_ssid (if not a hotspot).
    2. Otherwise reads last_home_wifi.txt if it exists.
    3. Otherwise runs netsh wlan show profiles, extracts saved profiles, filters out hotspots.
    4. Defaults safely to Orange-youssef.
    """
    # 1. In-memory profile
    cand = None
    if app_instance is not None:
        cand = getattr(app_instance, "previous_wifi_ssid", None)
    if not cand:
        global PREVIOUS_WIFI_SSID
        cand = PREVIOUS_WIFI_SSID
    if cand and not is_hotspot_profile_name(cand):
        return cand.strip()

    # 2. Disk persistence (last_home_wifi.txt)
    if os.path.exists(LAST_HOME_WIFI_FILE):
        try:
            with open(LAST_HOME_WIFI_FILE, "r", encoding="utf-8") as f:
                saved = f.read().strip()
                if saved and not is_hotspot_profile_name(saved):
                    return saved
        except Exception:
            pass

    # 3. Query netsh wlan show profiles for saved user profiles
    try:
        res = subprocess.run(["netsh", "wlan", "show", "profiles"], capture_output=True, text=True, timeout=3)
        for line in res.stdout.splitlines():
            m = re.match(r"^\s*(?:All|Current)\s*User Profile\s*:\s*(.+)$", line, re.IGNORECASE)
            if m:
                prof = m.group(1).strip()
                if prof and not is_hotspot_profile_name(prof):
                    return prof
    except Exception:
        pass

    return "Orange-youssef"

def get_wifi_gateway_ip():
    """Queries the default gateway IP on the Wi-Fi interface (tablet DHCP gateway)."""
    try:
        cmd = ["powershell", "-NoProfile", "-Command",
               "(Get-NetIPConfiguration -InterfaceAlias 'Wi-Fi*').IPv4DefaultGateway.NextHop"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        for line in res.stdout.splitlines():
            ip = line.strip()
            if ip and ip != "0.0.0.0" and len(ip.split(".")) == 4:
                return ip
    except Exception:
        pass
    return None

def connect_windows_to_airbeam(ssid="airbeam", password="airbeam123", app_instance=None):
    """
    Records previous Wi-Fi profile, disconnects from it, auto-generates profile, and connects to airbeam.
    """
    global PREVIOUS_WIFI_SSID
    current_net = get_current_wifi_profile()
    if current_net and current_net.strip().lower() != ssid.lower():
        PREVIOUS_WIFI_SSID = current_net.strip()
        save_last_home_wifi(PREVIOUS_WIFI_SSID)
        if app_instance is not None:
            app_instance.previous_wifi_ssid = PREVIOUS_WIFI_SSID
        try:
            subprocess.run(["netsh", "wlan", "disconnect"], capture_output=True, timeout=2)
            time.sleep(1.2)
        except Exception:
            pass
    elif current_net and current_net.strip().lower() == ssid.lower():
        return True

    # Ensure profile is registered via user=current before connecting
    ensure_windows_airbeam_profile(ssid=ssid, password=password)
    try:
        subprocess.run(["netsh", "wlan", "set", "profileparameter", f"name={ssid}", "connectionmode=manual"], capture_output=True, timeout=2)
        subprocess.run(["netsh", "wlan", "connect", f"name={ssid}", f"ssid={ssid}"], capture_output=True, timeout=3)
        if app_instance is not None:
            app_instance.connected_to_airbeam = True
        return True
    except Exception as e:
        print(f"Error connecting to {ssid}: {e}")
        return False

_EXIT_CLEANUP_DONE = False

def cleanup_airbeam_wifi_on_exit(app_instance=None):
    """
    Disconnects from airbeam, ensures manual connection mode, and reconnects to home Wi-Fi.
    Synchronously performs netsh wlan disconnect in ~90ms so the PC immediately disconnects
    from airbeam before exit, then spawns a detached background PowerShell process to handle
    the Intel AX201 deauth settling delay (1.5s) and reconnect to the home Wi-Fi network.
    """
    global _EXIT_CLEANUP_DONE
    if _EXIT_CLEANUP_DONE:
        return
    _EXIT_CLEANUP_DONE = True

    home_profile = get_best_home_wifi_profile(app_instance)

    # Check whether the app or system is on airbeam
    is_on_airbeam = False
    if app_instance is not None:
        switch = getattr(app_instance, "hotspot_switch", None)
        if switch and getattr(switch, "is_on", False):
            is_on_airbeam = True
        if getattr(app_instance, "connected_to_airbeam", False):
            is_on_airbeam = True
        if getattr(app_instance, "connected_to_iphone_hotspot", False):
            is_on_airbeam = True
        try:
            WindowsHotspotController.stop_hotspot(async_mode=True)
        except Exception:
            pass
        portal = getattr(app_instance, "iphone_portal", None)
        if portal:
            try: portal.stop()
            except: pass

    cur = get_current_wifi_profile()
    if cur and cur.lower() == "airbeam":
        is_on_airbeam = True
    elif cur and home_profile and cur.lower() != home_profile.lower():
        is_on_airbeam = True
    elif not cur:
        if app_instance is not None:
            mode = getattr(app_instance, "connection_mode", None)
            if mode and mode.get() == "TABLET_HOTSPOT":
                is_on_airbeam = True

    # 1. ALWAYS set airbeam & iPhone profiles to manual mode so they never auto-connect
    try:
        subprocess.run(["netsh", "wlan", "set", "profileparameter", "name=airbeam", "connectionmode=manual"], capture_output=True, timeout=2)
        if app_instance is not None:
            ip_ssid = getattr(app_instance, "iphone_hotspot_ssid", None)
            if ip_ssid:
                subprocess.run(["netsh", "wlan", "set", "profileparameter", f"name={ip_ssid}", "connectionmode=manual"], capture_output=True, timeout=2)
    except Exception:
        pass

    # 2. If connected to airbeam or hotspot, disconnect synchronously RIGHT NOW in Python (takes ~90ms)
    if is_on_airbeam:
        try:
            native_wlan_disconnect()
            time.sleep(0.5)
        except Exception:
            pass

    # 3. If home_profile exists, set it to auto-connect immediately and connect natively
    if home_profile:
        try:
            subprocess.run(["netsh", "wlan", "set", "profileparameter", f"name={home_profile}", "connectionmode=auto"], capture_output=True, timeout=2)
            native_wlan_connect(home_profile)
        except Exception:
            pass

        # 4. Spawn detached, silent background PowerShell process to reconnect to home Wi-Fi
        #    after the Intel AX201 1.5s deauthentication settling delay
        escaped_home = home_profile.replace('"', '`"')
        ps_lines = [
            "Start-Sleep -Milliseconds 1500",
            "for ($i = 0; $i -lt 4; $i++) {",
            f'    netsh wlan connect name="{escaped_home}"',
            "    Start-Sleep -Milliseconds 1500",
            '    $curProf = (Get-NetConnectionProfile -InterfaceAlias "Wi-Fi*" -ErrorAction SilentlyContinue).Name',
            f'    if ($curProf -eq "{escaped_home}") {{ break }}',
            "}"
        ]
        ps_script = "\n".join(ps_lines)
        enc = base64.b64encode(ps_script.encode("utf-16le")).decode("ascii")

        detached_flags = 0x08000000 | 0x00000008 | 0x00000200
        try:
            subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", enc],
                creationflags=detached_flags,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True
            )
        except Exception as e:
            print(f"Error launching detached Wi-Fi restore: {e}")

atexit.register(cleanup_airbeam_wifi_on_exit)

# --- WinRT Mobile Hotspot Controller (Auto 5 GHz -> 2.4 GHz) ---
class WindowsHotspotController:
    PS_SCRIPT = r"""
try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    [Windows.Foundation.IAsyncAction, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
    [Windows.Networking.Connectivity.NetworkInformation, Windows.Networking.Connectivity, ContentType=WindowsRuntime] | Out-Null
    [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager, Windows.Networking.NetworkOperators, ContentType=WindowsRuntime] | Out-Null
    [Windows.Networking.NetworkOperators.TetheringWiFiBand, Windows.Networking.NetworkOperators, ContentType=WindowsRuntime] | Out-Null
    [Windows.Networking.NetworkOperators.NetworkOperatorTetheringOperationResult, Windows.Networking.NetworkOperators, ContentType=WindowsRuntime] | Out-Null

    # Firewall inbound rules for AirBeam ports (including iOS portal 8090)
    try {
        netsh advfirewall firewall add rule name="AirBeam iOS Web Portal" dir=in action=allow protocol=TCP localport=8090 profile=any 2>$null | Out-Null
        netsh advfirewall firewall add rule name="AirBeam High-Speed Transfer" dir=in action=allow protocol=TCP localport=7777 profile=any 2>$null | Out-Null
        netsh advfirewall firewall add rule name="AirBeam APK Server" dir=in action=allow protocol=TCP localport=8888 profile=any 2>$null | Out-Null
        netsh advfirewall firewall add rule name="AirBeam UDP Discovery" dir=in action=allow protocol=UDP localport=7778 profile=any 2>$null | Out-Null
    } catch {}

    $asTaskAction = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq "AsTask" -and -not $_.IsGenericMethod -and $_.GetParameters().Count -eq 1
    } | Select-Object -First 1

    $asTaskOpGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { 
        $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetGenericArguments().Count -eq 1 -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name.StartsWith('IAsyncOperation')
    } | Select-Object -First 1

    $opResultType = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringOperationResult]
    $asTaskOp = $asTaskOpGeneric.MakeGenericMethod($opResultType)

    $profile = [Windows.Networking.Connectivity.NetworkInformation]::GetInternetConnectionProfile()
    if ($profile -eq $null) {
        Write-Output '{"error":"No active network connection profile"}'
        exit
    }
    $manager = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager]::CreateFromConnectionProfile($profile)
    $config = $manager.GetCurrentAccessPointConfiguration()

    if ($preferredBand -eq $null -or $preferredBand -eq "") {
        $preferredBand = "5GHz"
    }

    $isOn = ($manager.TetheringOperationalState -eq [Windows.Networking.NetworkOperators.TetheringOperationalState]::On)
    $currentBand = $config.Band.ToString()

    # Determine if we need to stop tethering to change band
    $needsBandChange = $false
    if ($isOn) {
        if ($preferredBand -eq "2.4GHz" -and $currentBand -like "*Five*") {
            $needsBandChange = $true
        } elseif ($preferredBand -eq "5GHz" -and $currentBand -like "*Two*") {
            $needsBandChange = $true
        }
    }

    if ($needsBandChange) {
        try {
            $opStop = $manager.StopTetheringAsync()
            $tStop = $asTaskOp.Invoke($null, @($opStop))
            $tStop.Wait()
            Start-Sleep -Milliseconds 800
        } catch {}
        $isOn = ($manager.TetheringOperationalState -eq [Windows.Networking.NetworkOperators.TetheringOperationalState]::On)
    }

    # Reconfigure and start if not On
    if (-not $isOn) {
        $config = $manager.GetCurrentAccessPointConfiguration()
        if ($preferredBand -eq "2.4GHz") {
            $band24 = [Windows.Networking.NetworkOperators.TetheringWiFiBand]::TwoPointFourGigahertz
            $configured = $false
            try {
                if ($config.IsBandSupported($band24)) {
                    $config.Band = $band24
                    $action = $manager.ConfigureAccessPointAsync($config)
                    $t = $asTaskAction.Invoke($null, @($action))
                    $t.Wait()
                    $configured = $true
                }
            } catch {}

            if (-not $configured) {
                try {
                    $config = $manager.GetCurrentAccessPointConfiguration()
                    $config.Band = [Windows.Networking.NetworkOperators.TetheringWiFiBand]::Auto
                    $action = $manager.ConfigureAccessPointAsync($config)
                    $t = $asTaskAction.Invoke($null, @($action))
                    $t.Wait()
                } catch {}
            }

            # Start tethering on 2.4GHz / Auto
            $op = $manager.StartTetheringAsync()
            $t = $asTaskOp.Invoke($null, @($op))
            $t.Wait()
        } else {
            # 5 GHz preferred
            $band5GHz = [Windows.Networking.NetworkOperators.TetheringWiFiBand]::FiveGigahertz
            if ($config.IsBandSupported($band5GHz)) {
                try {
                    $config.Band = $band5GHz
                    $action = $manager.ConfigureAccessPointAsync($config)
                    $t = $asTaskAction.Invoke($null, @($action))
                    $t.Wait()
                } catch {}
            }

            # Attempt to start tethering
            $op = $manager.StartTetheringAsync()
            $t = $asTaskOp.Invoke($null, @($op))
            $t.Wait()
            $res = $t.Result

            # Fallback to Auto if 5GHz failed to start
            if ($manager.TetheringOperationalState -ne [Windows.Networking.NetworkOperators.TetheringOperationalState]::On -or ($res -ne $null -and $res.Status -ne [Windows.Networking.NetworkOperators.TetheringOperationStatus]::Success)) {
                try {
                    $config = $manager.GetCurrentAccessPointConfiguration()
                    $config.Band = [Windows.Networking.NetworkOperators.TetheringWiFiBand]::Auto
                    $action = $manager.ConfigureAccessPointAsync($config)
                    $t = $asTaskAction.Invoke($null, @($action))
                    $t.Wait()

                    $op = $manager.StartTetheringAsync()
                    $t = $asTaskOp.Invoke($null, @($op))
                    $t.Wait()
                } catch {}
            }
        }
    }

    # Wait for Beacon Warm-Up (4 seconds) so 802.11 beacons and virtual adapter settle
    Start-Sleep -Seconds 4

    $activeConfig = $manager.GetCurrentAccessPointConfiguration()
    $hostIp = "192.168.137.1"
    for ($i = 0; $i -lt 10; $i++) {
        try {
            $ipObj = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { 
                $_.IPAddress -like "192.168.137.*" -or (($_.InterfaceAlias -like "*Wi-Fi Direct*" -or $_.InterfaceAlias -like "*Local Area Connection*") -and $_.IPAddress -notlike "169.254.*" -and $_.IPAddress -ne "127.0.0.1")
            } | Select-Object -First 1
            if ($ipObj -ne $null -and $ipObj.IPAddress) {
                $hostIp = $ipObj.IPAddress
                break
            }
        } catch {}
        Start-Sleep -Milliseconds 400
    }

    $outObj = @{
        enabled = ($manager.TetheringOperationalState -eq [Windows.Networking.NetworkOperators.TetheringOperationalState]::On)
        ssid = $activeConfig.Ssid.Trim()
        passphrase = $activeConfig.Passphrase.Trim()
        band = $activeConfig.Band.ToString()
        host_ip = $hostIp
    }
    Write-Output ($outObj | ConvertTo-Json -Compress)
} catch {
    Write-Output ('{"error":' + ($_.Exception.Message | ConvertTo-Json) + '}')
}
"""

    @classmethod
    def ensure_hotspot_active(cls, preferred_band="5GHz"):
        try:
            ps_script = f'$preferredBand = "{preferred_band}"\n' + cls.PS_SCRIPT
            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
            output = proc.stdout.strip()
            for line in output.splitlines():
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    data = json.loads(line)
                    if data.get("enabled"):
                        return data
                    elif "error" in data:
                        print(f"Hotspot warning ({preferred_band}):", data["error"])
        except Exception as e:
            print(f"Error starting hotspot ({preferred_band}): {e}")
        return None

    @classmethod
    def ensure_5ghz_hotspot_active(cls):
        return cls.ensure_hotspot_active(preferred_band="5GHz")

    @classmethod
    def stop_hotspot(cls, async_mode=False):
        stop_ps = r"""
try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    [Windows.Foundation.IAsyncAction, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
    [Windows.Networking.Connectivity.NetworkInformation, Windows.Networking.Connectivity, ContentType=WindowsRuntime] | Out-Null
    [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager, Windows.Networking.NetworkOperators, ContentType=WindowsRuntime] | Out-Null
    $profile = [Windows.Networking.Connectivity.NetworkInformation]::GetInternetConnectionProfile()
    if ($profile -ne $null) {
        $manager = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager]::CreateFromConnectionProfile($profile)
        if ($manager -ne $null -and $manager.TetheringOperationalState -eq [Windows.Networking.NetworkOperators.TetheringOperationalState]::On) {
            $asTaskOpGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { 
                $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetGenericArguments().Count -eq 1 -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name.StartsWith('IAsyncOperation')
            } | Select-Object -First 1
            $opResultType = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringOperationResult]
            $asTaskOp = $asTaskOpGeneric.MakeGenericMethod($opResultType)
            $op = $manager.StopTetheringAsync()
            $t = $asTaskOp.Invoke($null, @($op))
            $t.Wait()
        }
    }
} catch {}
"""
        try:
            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", stop_ps]
            if async_mode:
                subprocess.Popen(cmd, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000))
            else:
                subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        except Exception:
            pass

# --- Background APK Download Server ---
class ApkServer(threading.Thread):
    def __init__(self, apk_path, port=APK_SERVER_PORT):
        super().__init__(daemon=True)
        self.apk_path = apk_path
        self.port = port

    def run(self):
        apk_dir = os.path.dirname(self.apk_path)
        apk_name = os.path.basename(self.apk_path)

        class CustomHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=apk_dir, **kwargs)

            def log_message(self, format, *args):
                try:
                    with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
                        f.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))
                except Exception:
                    pass

            def guess_type(self, path):
                if str(path).lower().endswith(".apk"):
                    return "application/vnd.android.package-archive"
                return super().guess_type(path)

            def end_headers(self):
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                super().end_headers()

            def do_GET(self):
                if self.path in ('/', '/download', '/apk'):
                    self.send_response(302)
                    self.send_header('Location', f'/{urllib.parse.quote(apk_name)}')
                    self.end_headers()
                    return
                super().do_GET()

        try:
            httpd = HTTPServer(('0.0.0.0', self.port), CustomHandler)
            httpd.serve_forever()
        except Exception:
            pass

# --- High-Speed iPhone / iOS Web Portal (Port 8090) ---
IOS_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover, user-scalable=no">
    <meta name="theme-color" content="#0B1120">
    <title>AirBeam v5.0 • Web Portal</title>
    <style>
        :root {
            --bg: #0B1120;
            --card-bg: rgba(30, 41, 59, 0.78);
            --card-border: rgba(71, 85, 105, 0.45);
            --text-primary: #F8FAFC;
            --text-secondary: #94A3B8;
            --accent-cyan: #38BDF8;
            --accent-green: #10B981;
            --accent-blue: #2563EB;
            --accent-purple: #8B5CF6;
        }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body {
            margin: 0;
            padding: env(safe-area-inset-top, 20px) 16px env(safe-area-inset-bottom, 20px);
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Segoe UI", Roboto, sans-serif;
            background: var(--bg);
            color: var(--text-primary);
            min-height: 100vh;
        }
        .header {
            text-align: center;
            padding: 16px 0 20px;
        }
        .header h1 {
            margin: 0;
            font-size: 24px;
            font-weight: 700;
            letter-spacing: -0.5px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        .header p {
            margin: 6px 0 0;
            color: var(--text-secondary);
            font-size: 13px;
        }
        .badge-p2p {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid var(--accent-green);
            color: var(--accent-green);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            margin-top: 10px;
        }
        .pulse-dot {
            width: 8px;
            height: 8px;
            background: var(--accent-green);
            border-radius: 50%;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }
        .card {
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--card-border);
            border-radius: 18px;
            padding: 18px;
            margin-bottom: 16px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        .card-title {
            font-size: 16px;
            font-weight: 600;
            margin: 0 0 12px 0;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .card-title span.badge {
            font-size: 12px;
            background: rgba(56, 189, 248, 0.2);
            color: var(--accent-cyan);
            padding: 2px 8px;
            border-radius: 10px;
            font-weight: 500;
        }
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            padding: 12px 18px;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 600;
            border: none;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.2s ease;
            width: 100%;
        }
        .btn:active { transform: scale(0.98); opacity: 0.9; }
        .btn-primary { background: linear-gradient(135deg, #2563EB, #1D4ED8); color: #fff; }
        .btn-green { background: linear-gradient(135deg, #10B981, #059669); color: #fff; }
        .btn-secondary { background: rgba(51, 65, 85, 0.8); color: var(--text-primary); border: 1px solid var(--card-border); }
        .file-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-top: 10px;
        }
        .file-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid rgba(71, 85, 105, 0.3);
            border-radius: 12px;
            padding: 12px;
            gap: 12px;
        }
        .file-info {
            flex: 1;
            overflow: hidden;
        }
        .file-name {
            font-size: 14px;
            font-weight: 600;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            color: var(--text-primary);
        }
        .file-size {
            font-size: 12px;
            color: var(--accent-cyan);
            margin-top: 2px;
        }
        .btn-download {
            padding: 8px 14px;
            font-size: 13px;
            width: auto;
            border-radius: 8px;
            white-space: nowrap;
            background: var(--accent-blue);
            color: #fff;
            text-decoration: none;
            font-weight: 600;
        }
        .btn-download:active { opacity: 0.8; }
        .progress-box {
            margin-top: 12px;
            background: rgba(15, 23, 42, 0.9);
            border-radius: 12px;
            padding: 14px;
            display: none;
        }
        .progress-bar-bg {
            background: #334155;
            height: 10px;
            border-radius: 5px;
            overflow: hidden;
            margin: 8px 0;
        }
        .progress-bar-fill {
            background: linear-gradient(90deg, #10B981, #38BDF8);
            height: 100%;
            width: 0%;
            transition: width 0.15s ease;
        }
        .progress-meta {
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            color: var(--text-secondary);
        }
        .speed-pill {
            color: var(--accent-green);
            font-weight: 600;
        }
        .clipboard-box {
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 12px;
            font-size: 13px;
            word-break: break-all;
            margin-bottom: 10px;
            max-height: 100px;
            overflow-y: auto;
        }
        .clipboard-actions {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }
        textarea.input-box {
            width: 100%;
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid var(--card-border);
            border-radius: 10px;
            color: var(--text-primary);
            padding: 10px;
            font-size: 13px;
            resize: none;
            margin-bottom: 8px;
            font-family: inherit;
        }
        textarea.input-box:focus {
            outline: none;
            border-color: var(--accent-cyan);
        }
        .toast {
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(15, 23, 42, 0.95);
            border: 1px solid var(--accent-green);
            color: #fff;
            padding: 10px 20px;
            border-radius: 24px;
            font-size: 13px;
            font-weight: 600;
            display: none;
            z-index: 1000;
            box-shadow: 0 4px 16px rgba(0,0,0,0.4);
        }
    </style>
</head>
<body>
    <div class="header">
        <h1><span>⚡</span> AirBeam v5.0</h1>
        <p>Ultra-Fast Wireless Transfer for PC, iPhone & iPad</p>
        <div class="badge-p2p">
            <div class="pulse-dot"></div>
            <span>DIRECT 5GHz WI-FI PIPE (50-95+ MB/s)</span>
        </div>
        <div id="wakeLockBadge" style="display:none;align-items:center;justify-content:center;gap:6px;background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.35);color:#10B981;font-size:12px;font-weight:600;padding:4px 12px;border-radius:14px;margin:8px auto 0;width:fit-content;">
            <span>🔒</span> Screen Wake Lock Active during transfer
        </div>
    </div>

    <!-- 1. Download Files from PC Card -->
    <div class="card">
        <div class="card-title">
            <span>📥 Files from PC</span>
            <span class="badge" id="fileCountBadge">0 files</span>
        </div>
        <div id="fileListContainer" class="file-list">
            <p style="color:var(--text-secondary);font-size:13px;margin:8px 0;text-align:center;">No files staged on PC yet. Add files on your PC or wait a moment.</p>
        </div>
        <button id="btnDownloadAll" class="btn btn-green" style="margin-top:12px;display:none;" onclick="downloadAllFiles()">⚡ Download All Files (Single ZIP Stream)</button>
    </div>

    <!-- 2. Send Files to PC Card -->
    <div class="card">
        <div class="card-title">
            <span>📸 Send to PC</span>
            <span class="badge">Atomic Part Upload</span>
        </div>
        <p style="color:var(--text-secondary);font-size:13px;margin:0 0 12px;">Send photos, 4K videos, or files directly to your PC's <code>Received_From_iPhone</code> folder at full Wi-Fi speed.</p>
        <input type="file" id="filePicker" multiple style="display:none;" onchange="handleFileSelect(this.files)">
        <button class="btn btn-primary" onclick="document.getElementById('filePicker').click()">📸 Select Photos, Videos & Files</button>

        <div id="uploadProgressBox" class="progress-box">
            <div style="font-size:13px;font-weight:600;margin-bottom:4px;" id="uploadFileName">Uploading file...</div>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" id="uploadBarFill"></div>
            </div>
            <div class="progress-meta">
                <span class="speed-pill" id="uploadSpeed">0.0 MB/s</span>
                <span id="uploadPercent">0%</span>
            </div>
        </div>

        <!-- Uploaded Files Section with Clear Button -->
        <div id="uploadedFilesBox" style="margin-top:14px;display:none;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <span style="font-size:13px;font-weight:600;color:var(--text-primary);">✅ Uploaded Files (<span id="uploadedCountBadge">0</span>)</span>
                <button class="btn btn-secondary" style="padding:4px 10px;font-size:12px;margin:0;" onclick="clearUploadedFilesList()">🗑️ Clear Upload List</button>
            </div>
            <div id="uploadedList" class="file-list"></div>
        </div>
    </div>

    <!-- 3. Clipboard Sync Card -->
    <div class="card">
        <div class="card-title">
            <span>📋 Instant Clipboard Sync</span>
            <span class="badge">Two-Way</span>
        </div>
        <div style="font-size:12px;color:var(--text-secondary);margin-bottom:6px;">Current PC Clipboard:</div>
        <div class="clipboard-box" id="pcClipboardText">Loading PC clipboard...</div>
        <div class="clipboard-actions">
            <button class="btn btn-secondary" onclick="copyPcClipboard()">📋 Copy to iPhone</button>
            <button class="btn btn-secondary" id="btnOpenLink" onclick="openPcLink()" style="display:none;">🔗 Open Link</button>
        </div>

        <hr style="border:none;border-top:1px solid var(--card-border);margin:16px 0;">

        <div style="font-size:12px;color:var(--text-secondary);margin-bottom:6px;">Send Text / Link to PC:</div>
        <textarea id="txtSendClipboard" class="input-box" rows="2" placeholder="Type or paste text/URL here to send to PC clipboard..."></textarea>
        <button class="btn btn-primary" onclick="sendToPcClipboard()">📤 Send to PC Clipboard</button>
    </div>

    <div id="toast" class="toast">Action Complete!</div>

    <script>
        let stagedFiles = [];
        let currentPcClipboard = "";

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.style.display = 'block';
            setTimeout(() => { t.style.display = 'none'; }, 2500);
        }

        async function fetchFiles() {
            try {
                const res = await fetch('/api/files');
                stagedFiles = await res.json();
                renderFiles();
            } catch (e) {
                console.error("Fetch files error:", e);
            }
        }

        function renderFiles() {
            const container = document.getElementById('fileListContainer');
            const badge = document.getElementById('fileCountBadge');
            const btnAll = document.getElementById('btnDownloadAll');

            badge.innerText = `${stagedFiles.length} file${stagedFiles.length === 1 ? '' : 's'}`;

            if (stagedFiles.length === 0) {
                container.innerHTML = '<p style="color:var(--text-secondary);font-size:13px;margin:8px 0;text-align:center;">No files staged on PC yet. Add files in AirBeam PC.</p>';
                btnAll.style.display = 'none';
                return;
            }

            btnAll.style.display = stagedFiles.length > 1 ? 'block' : 'none';

            let html = '';
            stagedFiles.forEach(f => {
                html += `
                    <div class="file-item">
                        <div class="file-info">
                            <div class="file-name" title="${f.name}">${f.name}</div>
                            <div class="file-size">${f.formatted_size}</div>
                        </div>
                        <a href="/download/${f.index}" class="btn-download" download="${f.name}" onclick="acquireWakeLock()">⬇️ Download</a>
                    </div>
                `;
            });
            container.innerHTML = html;
        }

        let wakeLockSentinel = null;

        async function acquireWakeLock() {
            try {
                if ('wakeLock' in navigator) {
                    wakeLockSentinel = await navigator.wakeLock.request('screen');
                    updateWakeLockBadge(true);
                    wakeLockSentinel.addEventListener('release', () => {
                        wakeLockSentinel = null;
                        updateWakeLockBadge(false);
                    });
                }
            } catch (err) {
                console.log("Screen Wake Lock not acquired:", err);
            }
        }

        async function releaseWakeLock() {
            try {
                if (wakeLockSentinel) {
                    await wakeLockSentinel.release();
                    wakeLockSentinel = null;
                }
            } catch (err) {
                console.log("Screen Wake Lock release error:", err);
            }
            updateWakeLockBadge(false);
        }

        function updateWakeLockBadge(active) {
            const b = document.getElementById('wakeLockBadge');
            if (b) {
                b.style.display = active ? 'inline-flex' : 'none';
            }
        }

        async function downloadAllFiles() {
            if (stagedFiles.length === 0) return;
            await acquireWakeLock();
            const a = document.createElement('a');
            a.href = '/download-all.zip';
            a.download = `AirBeam_Staged_Files_${Date.now()}.zip`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            showToast("⚡ Streaming uncompressed ZIP download started!");
            setTimeout(releaseWakeLock, 60000);
        }

        async function fetchClipboard() {
            try {
                const res = await fetch('/api/clipboard');
                const data = await res.json();
                currentPcClipboard = data.text || "";
                const el = document.getElementById('pcClipboardText');
                const btnLink = document.getElementById('btnOpenLink');

                if (currentPcClipboard.trim()) {
                    el.innerText = currentPcClipboard;
                    if (currentPcClipboard.startsWith('http://') || currentPcClipboard.startsWith('https://')) {
                        btnLink.style.display = 'block';
                    } else {
                        btnLink.style.display = 'none';
                    }
                } else {
                    el.innerText = "(PC Clipboard is empty)";
                    btnLink.style.display = 'none';
                }
            } catch (e) {
                console.error("Fetch clipboard error:", e);
            }
        }

        function copyPcClipboard() {
            if (!currentPcClipboard) return;
            navigator.clipboard.writeText(currentPcClipboard).then(() => {
                showToast("Copied to iPhone clipboard!");
            }).catch(() => {
                showToast("Please allow clipboard permission");
            });
        }

        function openPcLink() {
            if (currentPcClipboard.startsWith('http://') || currentPcClipboard.startsWith('https://')) {
                window.open(currentPcClipboard, '_blank');
            }
        }

        async function sendToPcClipboard() {
            const txt = document.getElementById('txtSendClipboard').value.trim();
            if (!txt) return;
            try {
                const res = await fetch('/api/clipboard', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: txt })
                });
                if (res.ok) {
                    showToast("Sent to PC Clipboard!");
                    document.getElementById('txtSendClipboard').value = '';
                    fetchClipboard();
                }
            } catch (e) {
                showToast("Error sending clipboard");
            }
        }

        async function handleFileSelect(files) {
            if (!files || files.length === 0) return;
            const progressBox = document.getElementById('uploadProgressBox');
            const fileNameEl = document.getElementById('uploadFileName');
            const barFill = document.getElementById('uploadBarFill');
            const speedEl = document.getElementById('uploadSpeed');
            const percentEl = document.getElementById('uploadPercent');

            progressBox.style.display = 'block';
            await acquireWakeLock();

            try {
                for (let i = 0; i < files.length; i++) {
                    const file = files[i];
                    fileNameEl.innerText = `Uploading (${i+1}/${files.length}): ${file.name}`;
                    barFill.style.width = '0%';
                    percentEl.innerText = '0%';
                    speedEl.innerText = '0.0 MB/s';

                    await uploadSingleFile(file, (loaded, total, spd) => {
                        const pct = Math.round((loaded / total) * 100);
                        barFill.style.width = `${pct}%`;
                        percentEl.innerText = `${pct}% (${(loaded / (1024*1024)).toFixed(1)} / ${(total / (1024*1024)).toFixed(1)} MB)`;
                        speedEl.innerText = spd;
                    });

                    uploadedFilesHistory.unshift({
                        name: file.name,
                        size: (file.size / (1024 * 1024)).toFixed(1) + ' MB',
                        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                    });
                    renderUploadedFiles();
                }

                showToast("All files uploaded to PC successfully!");
                setTimeout(() => { progressBox.style.display = 'none'; }, 2000);
                document.getElementById('filePicker').value = '';
            } finally {
                await releaseWakeLock();
            }
        }

        let uploadedFilesHistory = [];

        function renderUploadedFiles() {
            const box = document.getElementById('uploadedFilesBox');
            const list = document.getElementById('uploadedList');
            const badge = document.getElementById('uploadedCountBadge');
            if (!box || !list) return;
            if (uploadedFilesHistory.length === 0) {
                box.style.display = 'none';
                list.innerHTML = '';
                if (badge) badge.innerText = '0';
                return;
            }
            box.style.display = 'block';
            if (badge) badge.innerText = uploadedFilesHistory.length;
            list.innerHTML = uploadedFilesHistory.map(f => `
                <div class="file-item">
                    <div class="file-info">
                        <div class="file-name" style="font-weight:600;">✅ ${f.name}</div>
                        <div class="file-meta">${f.size} • Uploaded at ${f.time}</div>
                    </div>
                </div>
            `).join('');
        }

        function clearUploadedFilesList() {
            uploadedFilesHistory = [];
            renderUploadedFiles();
            showToast("Uploaded files list cleared!");
        }

        function uploadSingleFile(file, onProgress) {
            return new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                let lastTime = Date.now();
                let lastLoaded = 0;

                xhr.upload.onprogress = (e) => {
                    if (e.lengthComputable) {
                        const now = Date.now();
                        const timeDiff = (now - lastTime) / 1000;
                        if (timeDiff >= 0.3) {
                            const bytesDiff = e.loaded - lastLoaded;
                            const speedBytesSec = bytesDiff / timeDiff;
                            const mbSec = (speedBytesSec / (1024 * 1024)).toFixed(1);
                            const mbps = ((speedBytesSec * 8) / (1000 * 1000)).toFixed(0);
                            onProgress(e.loaded, e.total, `⚡ ${mbSec} MB/s (${mbps} Mbps)`);
                            lastTime = now;
                            lastLoaded = e.loaded;
                        } else if (lastLoaded === 0) {
                            onProgress(e.loaded, e.total, `Calculating...`);
                        }
                    }
                };

                xhr.onload = () => {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        resolve();
                    } else {
                        reject(new Error("Upload failed: " + xhr.statusText));
                    }
                };

                xhr.onerror = () => reject(new Error("Network upload error"));

                const uploadUrl = '/upload?filename=' + encodeURIComponent(file.name);
                xhr.open('POST', uploadUrl, true);
                xhr.send(file);
            });
        }

        // Poll files & clipboard every 3.5s
        fetchFiles();
        fetchClipboard();
        setInterval(() => {
            fetchFiles();
            fetchClipboard();
        }, 3500);
    </script>
</body>
</html>
"""

class IPhonePortalHTTPHandler(BaseHTTPRequestHandler):
    @property
    def app(self):
        return self.server.app_instance

    def log_message(self, format, *args):
        try:
            with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
                f.write("[iOS Portal %s] %s\n" % (self.log_date_time_string(), format % args))
        except Exception:
            pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ('/', '/index.html'):
            content = IOS_HTML_TEMPLATE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.end_headers()
            self.wfile.write(content)
            return

        elif path == '/api/files':
            files_list = []
            selected = getattr(self.app, "selected_files", [])
            for idx, fpath in enumerate(selected):
                if os.path.exists(fpath):
                    sz = os.path.getsize(fpath)
                    files_list.append({
                        "index": idx,
                        "name": os.path.basename(fpath),
                        "size": sz,
                        "formatted_size": format_bytes(sz)
                    })
            data = json.dumps(files_list).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data)
            return

        elif path == '/api/clipboard':
            text = self.app.get_clipboard_safe()
            data = json.dumps({"text": text or ""}).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data)
            return

        elif path.startswith('/download/'):
            try:
                idx_str = path[len('/download/'):]
                idx = int(idx_str)
                selected = getattr(self.app, "selected_files", [])
                if idx < 0 or idx >= len(selected):
                    self.send_error(404, "File index out of range")
                    return
                filepath = selected[idx]
                if not os.path.exists(filepath):
                    self.send_error(404, "File not found on disk")
                    return

                total_size = os.path.getsize(filepath)
                filename = os.path.basename(filepath)
                mime_type, _ = mimetypes.guess_type(filepath)
                if not mime_type:
                    mime_type = "application/octet-stream"

                range_header = self.headers.get('Range')
                start_byte = 0
                end_byte = total_size - 1

                if range_header and range_header.startswith('bytes='):
                    try:
                        ranges = range_header[6:].split('-')
                        if ranges[0]:
                            start_byte = int(ranges[0])
                        if ranges[1]:
                            end_byte = int(ranges[1])
                    except Exception:
                        start_byte = 0
                        end_byte = total_size - 1

                chunk_len = (end_byte - start_byte) + 1
                status_code = 206 if range_header else 200

                self.send_response(status_code)
                self.send_header('Content-Type', mime_type)
                safe_name = urllib.parse.quote(filename)
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"; filename*=UTF-8\'\'{safe_name}')
                self.send_header('Accept-Ranges', 'bytes')
                if range_header:
                    self.send_header('Content-Range', f'bytes {start_byte}-{end_byte}/{total_size}')
                self.send_header('Content-Length', str(chunk_len))
                self.end_headers()

                # Stream with 2 MB chunks (zero-copy socket push)
                CHUNK = 2 * 1024 * 1024
                with open(filepath, 'rb') as f:
                    f.seek(start_byte)
                    bytes_remaining = chunk_len
                    while bytes_remaining > 0:
                        to_read = min(CHUNK, bytes_remaining)
                        buf = f.read(to_read)
                        if not buf:
                            break
                        self.wfile.write(buf)
                        bytes_remaining -= len(buf)
                        self.app.record_ios_stream_bytes(len(buf), is_upload=False)
                return
            except Exception:
                return

        elif path == '/download-all.zip':
            try:
                selected = [f for f in getattr(self.app, "selected_files", []) if os.path.exists(f)]
                if not selected:
                    self.send_error(404, "No staged files available to download")
                    return

                self.send_response(200)
                self.send_header('Content-Type', 'application/zip')
                zip_filename = f"AirBeam_Bundle_{int(time.time())}.zip"
                safe_name = urllib.parse.quote(zip_filename)
                self.send_header('Content-Disposition', f'attachment; filename="{zip_filename}"; filename*=UTF-8\'\'{safe_name}')
                self.send_header('Connection', 'close')
                self.end_headers()

                adapter = SocketStreamAdapter(self.wfile, record_cb=lambda n: self.app.record_ios_stream_bytes(n, is_upload=False))
                with zipfile.ZipFile(adapter, mode='w', compression=zipfile.ZIP_STORED) as zf:
                    for fpath in selected:
                        arcname = sanitize_ntfs_filename(os.path.basename(fpath))
                        zf.write(fpath, arcname=arcname)
                return
            except Exception:
                return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/upload':
            query = urllib.parse.parse_qs(parsed.query)
            raw_filename = query.get('filename', ['upload.bin'])[0]
            clean_filename = sanitize_ntfs_filename(urllib.parse.unquote(raw_filename))
            if not clean_filename:
                clean_filename = "unnamed_upload.bin"
            filename = clean_filename

            content_len = int(self.headers.get('Content-Length', 0))
            recv_dir = getattr(self.app, "iphone_received_dir", IPHONE_RECEIVED_DIR)
            os.makedirs(recv_dir, exist_ok=True)

            part_path = os.path.join(recv_dir, filename + ".part")
            final_path = os.path.join(recv_dir, filename)

            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(final_path):
                final_path = os.path.join(recv_dir, f"{base} ({counter}){ext}")
                counter += 1

            CHUNK = 2 * 1024 * 1024
            bytes_left = content_len
            try:
                with open(part_path, 'wb') as f:
                    while bytes_left > 0:
                        to_read = min(CHUNK, bytes_left)
                        buf = self.rfile.read(to_read)
                        if not buf:
                            break
                        f.write(buf)
                        bytes_left -= len(buf)
                        self.app.record_ios_stream_bytes(len(buf), is_upload=True)

                if os.path.exists(part_path):
                    if os.path.exists(final_path):
                        os.remove(final_path)
                    os.rename(part_path, final_path)

                resp = json.dumps({"status": "ok", "filename": os.path.basename(final_path), "size": content_len}).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(resp)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(resp)
                return
            except Exception as e:
                if os.path.exists(part_path):
                    try: os.remove(part_path)
                    except: pass
                self.send_error(500, f"Upload error: {e}")
                return

        elif path == '/api/clipboard':
            content_len = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_len).decode('utf-8', errors='replace')
            try:
                data = json.loads(body)
                text = data.get('text', '')
                self.app.set_clipboard_safe(text)
                resp = json.dumps({"status": "ok", "text": text}).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(resp)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(resp)
                return
            except Exception as e:
                self.send_error(400, f"Invalid JSON: {e}")
                return

        self.send_error(404, "Not Found")

class IPhonePortalServer:
    def __init__(self, app_instance, ports=IPHONE_PORTAL_PORTS):
        self.app_instance = app_instance
        self.ports = list(ports) if isinstance(ports, (list, tuple)) else [ports]
        self.servers = []
        self.threads = []

    def start(self):
        class ThreadedServer(ThreadingHTTPServer):
            pass

        started = []
        for p in self.ports:
            try:
                srv = ThreadedServer(('0.0.0.0', p), IPhonePortalHTTPHandler)
                srv.app_instance = self.app_instance
                try:
                    srv.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    srv.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 8 * 1024 * 1024)
                except Exception:
                    pass
                t = threading.Thread(target=srv.serve_forever, daemon=True)
                t.start()
                self.servers.append(srv)
                self.threads.append(t)
                started.append(p)
                print(f"IPhonePortalServer running on port {p}")
            except Exception as e:
                print(f"Failed to start IPhonePortalServer on port {p}: {e}")
        return len(started) > 0

    def stop(self):
        for srv in self.servers:
            try:
                srv.shutdown()
                srv.server_close()
            except Exception:
                pass
        self.servers.clear()
        self.threads.clear()

# --- AirBeam PC-to-PC Multi-Stream Receiver Server ---
class PCReceiverServer:
    def __init__(self, app_instance, port=NIO_PORT):
        self.app_instance = app_instance
        self.port = port
        self.server_sock = None
        self.running = False
        self.active_transfers = {}
        self.transfers_lock = threading.Lock()

    def start(self):
        if self.running:
            return
        self.running = True
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def stop(self):
        self.running = False
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass

    def _run(self):
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                self.server_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024)
            except Exception:
                pass
            self.server_sock.bind(("0.0.0.0", self.port))
            self.server_sock.listen(32)
            print(f"PCReceiverServer active and listening on port {self.port}")
            if hasattr(self.app_instance, "on_pc_receiver_ready") and getattr(self.app_instance, "_is_alive", True):
                try:
                    self.app_instance.after(0, lambda: self.app_instance.on_pc_receiver_ready(self.port, True))
                except Exception:
                    pass

            while self.running:
                try:
                    client_sock, client_addr = self.server_sock.accept()
                    client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    try:
                        client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024)
                    except Exception:
                        pass
                    threading.Thread(target=self._handle_client, args=(client_sock, client_addr), daemon=True).start()
                except Exception as ex:
                    if self.running:
                        print(f"PCReceiverServer accept error: {ex}")
                    break
        except Exception as e:
            err_msg = str(e)
            print(f"PCReceiverServer bind error on port {self.port}: {err_msg}")
            if hasattr(self.app_instance, "on_pc_receiver_ready") and getattr(self.app_instance, "_is_alive", True):
                try:
                    self.app_instance.after(0, lambda err=err_msg: self.app_instance.on_pc_receiver_ready(self.port, False, err))
                except Exception:
                    pass

    def _read_exact(self, sock, count):
        buf = bytearray(count)
        view = memoryview(buf)
        pos = 0
        while pos < count:
            r = sock.recv_into(view[pos:])
            if not r:
                raise ConnectionResetError("Socket closed prematurely while reading expected data")
            pos += r
        return bytes(buf)

    def _handle_client(self, sock, addr):
        try:
            magic = sock.recv(4)
            if not magic:
                sock.close()
                return

            if magic == b"ABM_":
                rest = self._read_exact(sock, 4)
                if magic + rest == b"ABM_CTRL":
                    self._handle_control_connection(sock, addr)
                else:
                    sock.close()
            elif magic == b"ABM2":
                self._handle_worker_connection(sock, addr)
            elif magic in (b"GET ", b"POST", b"HEAD"):
                ip = get_local_ip()
                body = f"AirBeam v5.0 PC Receiver Active on Port {self.port}!\nTransfer files directly using AirBeam desktop app or open http://{ip}:8080 in your browser.\n".encode("utf-8")
                resp = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: " + str(len(body)).encode("utf-8") + b"\r\nConnection: close\r\n\r\n" + body
                sock.sendall(resp)
                sock.close()
            else:
                sock.close()
        except Exception:
            try:
                sock.close()
            except Exception:
                pass

    def _handle_control_connection(self, sock, addr):
        transfer_id = None
        try:
            hdr_len_bytes = self._read_exact(sock, 4)
            manifest_len = struct.unpack("!I", hdr_len_bytes)[0]
            manifest_json_bytes = self._read_exact(sock, manifest_len)
            manifest = json.loads(manifest_json_bytes.decode("utf-8"))

            transfer_id = manifest["transfer_id"]
            raw_filename = manifest.get("filename", f"received_{int(time.time())}")
            clean_filename = sanitize_ntfs_filename(raw_filename)
            filesize = manifest.get("filesize", 0)
            total_chunks = manifest.get("total_chunks", 1)

            os.makedirs(PC_RECEIVED_DIR, exist_ok=True)
            dest_path = os.path.join(PC_RECEIVED_DIR, clean_filename)
            base, ext = os.path.splitext(clean_filename)
            c = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(PC_RECEIVED_DIR, f"{base} ({c}){ext}")
                c += 1

            part_path = dest_path + ".airbeam.part"

            with open(part_path, "wb") as f_init:
                if filesize > 0:
                    f_init.seek(filesize - 1)
                    f_init.write(b'\0')

            with self.transfers_lock:
                self.active_transfers[transfer_id] = {
                    "transfer_id": transfer_id,
                    "filename": os.path.basename(dest_path),
                    "filesize": filesize,
                    "dest_path": dest_path,
                    "part_path": part_path,
                    "total_chunks": total_chunks,
                    "received_chunks": 0,
                    "bytes_received": 0,
                    "worker_handles": [],
                    "lock": threading.Lock(),
                    "start_time": time.time(),
                    "sender_ip": addr[0],
                    "ctrl_sock": sock,
                    "done_event": threading.Event()
                }

            sock.sendall(b"MANIFEST_OK")

            if hasattr(self.app_instance, "on_pc_receive_start"):
                self.app_instance.after(0, lambda: self.app_instance.on_pc_receive_start(
                    os.path.basename(dest_path), filesize, addr[0]
                ))

            self.active_transfers[transfer_id]["done_event"].wait(timeout=3600.0)

            try:
                sock.close()
            except Exception:
                pass
        except Exception as e:
            print(f"Control connection error: {e}")
            try:
                sock.close()
            except Exception:
                pass
        finally:
            if transfer_id:
                with self.transfers_lock:
                    transfer = self.active_transfers.pop(transfer_id, None)
                if transfer:
                    with transfer["lock"]:
                        for wh in transfer.get("worker_handles", []):
                            try:
                                wh.close()
                            except Exception:
                                pass
                    part_path = transfer.get("part_path")
                    if part_path and os.path.exists(part_path) and not transfer["done_event"].is_set():
                        try:
                            os.remove(part_path)
                        except Exception:
                            pass

    def _handle_worker_connection(self, sock, addr):
        worker_file = None
        current_transfer_id = None
        try:
            while self.running:
                hdr_bytes = bytearray(32)
                hdr_view = memoryview(hdr_bytes)
                pos = 0
                while pos < 32:
                    r = sock.recv_into(hdr_view[pos:])
                    if not r:
                        return
                    pos += r

                transfer_id, chunk_idx, total_chunks, chunk_off, chunk_len = struct.unpack("!QIIQQ", hdr_bytes)

                with self.transfers_lock:
                    transfer = self.active_transfers.get(transfer_id)

                if not transfer:
                    break

                if worker_file is None or current_transfer_id != transfer_id:
                    if worker_file:
                        try:
                            worker_file.close()
                        except Exception:
                            pass
                    current_transfer_id = transfer_id
                    worker_file = open(transfer["part_path"], "r+b", buffering=0)
                    with transfer["lock"]:
                        transfer["worker_handles"].append(worker_file)

                payload = bytearray(chunk_len)
                p_view = memoryview(payload)
                pos = 0
                while pos < chunk_len:
                    r = sock.recv_into(p_view[pos:])
                    if not r:
                        raise ConnectionResetError("Worker socket closed prematurely during chunk payload")
                    pos += r

                # Lock-free parallel NTFS write with independent worker file pointer!
                worker_file.seek(chunk_off)
                worker_file.write(p_view)

                sock.sendall(b"COK!")

                with self.transfers_lock:
                    transfer["bytes_received"] += chunk_len
                    transfer["received_chunks"] += 1
                    done = (transfer["received_chunks"] >= transfer["total_chunks"])
                    cur_bytes = transfer["bytes_received"]
                    tot_bytes = transfer["filesize"]
                    fname = transfer["filename"]
                    elapsed = max(0.001, time.time() - transfer["start_time"])
                    speed = cur_bytes / elapsed

                if hasattr(self.app_instance, "on_pc_receive_progress"):
                    self.app_instance.after(0, lambda fn=fname, cb=cur_bytes, tb=tot_bytes, spd=speed:
                        self.app_instance.on_pc_receive_progress(fn, cb, tb, spd)
                    )

                if done:
                    with transfer["lock"]:
                        for wh in transfer["worker_handles"]:
                            try:
                                wh.flush()
                                wh.close()
                            except Exception:
                                pass
                        transfer["worker_handles"].clear()

                    part_path = transfer["part_path"]
                    dest_path = transfer["dest_path"]
                    try:
                        if os.path.exists(dest_path):
                            os.remove(dest_path)
                        os.replace(part_path, dest_path)
                    except Exception as e:
                        print(f"Error finalizing part file: {e}")

                    transfer["done_event"].set()

                    if hasattr(self.app_instance, "on_pc_receive_complete"):
                        self.app_instance.after(0, lambda fn=fname, tb=tot_bytes, dur=elapsed, spd=speed, dp=dest_path:
                            self.app_instance.on_pc_receive_complete(fn, tb, dur, spd, dp)
                        )
                    with self.transfers_lock:
                        self.active_transfers.pop(transfer_id, None)
                    break
        except Exception:
            try:
                sock.close()
            except Exception:
                pass
        finally:
            if worker_file:
                try:
                    worker_file.close()
                except Exception:
                    pass
            try:
                sock.close()
            except Exception:
                pass

# --- High-Speed Transfer Engine (Multi-Stream Zero-Copy) ---
class HighSpeedTransferEngine:
    def __init__(self, target_host, file_paths, progress_cb, completion_cb, pause_event, cancel_event):
        self.target_host = target_host
        self.file_paths = file_paths
        self.progress_cb = progress_cb
        self.completion_cb = completion_cb
        self.pause_event = pause_event
        self.cancel_event = cancel_event

    def execute(self):
        total_files = len(self.file_paths)
        total_bytes = sum(os.path.getsize(f) for f in self.file_paths if os.path.exists(f))
        sent_total_bytes = 0
        overall_start_time = time.time()
        overall_peak_speed = [0.0]
        errors = []

        for f_idx, file_path in enumerate(self.file_paths):
            if self.cancel_event.is_set():
                break

            filename = os.path.basename(file_path)
            filesize = os.path.getsize(file_path)
            transfer_id = int(time.time() * 1000)

            # Determine chunks
            stripe_size = DEFAULT_STRIPE_SIZE
            total_chunks = (filesize + stripe_size - 1) // stripe_size if filesize > 0 else 1

            num_streams = 6 if filesize >= 64 * 1024 * 1024 else 4

            # 1. Connect Control Socket
            ctrl_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ctrl_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            try:
                ctrl_sock.connect((self.target_host, NIO_PORT))
                # Send MANIFEST
                manifest = {
                    "action": "MANIFEST",
                    "transfer_id": transfer_id,
                    "filename": filename,
                    "filesize": filesize,
                    "stripe_size": stripe_size,
                    "total_chunks": total_chunks,
                    "parallel_streams": num_streams
                }
                manifest_bytes = json.dumps(manifest).encode("utf-8")
                ctrl_hdr = b"ABM_CTRL" + struct.pack("!I", len(manifest_bytes)) + manifest_bytes
                ctrl_sock.sendall(ctrl_hdr)

                resp = ctrl_sock.recv(1024)
                if b"MANIFEST_OK" not in resp:
                    errors.append(f"{filename}: Receiver rejected manifest ({resp})")
                    ctrl_sock.close()
                    continue
            except Exception as e:
                errors.append(f"{filename}: Control connection failed: {e}")
                continue

            # 2. Worker Chunks Partitioning
            chunks = []
            for i in range(total_chunks):
                offset = i * stripe_size
                length = min(stripe_size, filesize - offset)
                chunks.append((i, offset, length))

            # Multi-socket worker execution with dedicated smooth progress monitor
            worker_error = [None]
            file_bytes_sent = [0]
            transfer_lock = threading.Lock()
            stop_monitor = threading.Event()

            def progress_monitor():
                samples = deque()  # (timestamp, total_bytes)
                t0 = time.time()
                samples.append((t0, sent_total_bytes))
                last_ema_speed = [0.0]
                paused_accum = [0.0]
                pause_start = [None]

                while not stop_monitor.is_set():
                    time.sleep(0.15)
                    now = time.time()

                    if not self.pause_event.is_set():
                        if pause_start[0] is None:
                            pause_start[0] = now
                        continue
                    else:
                        if pause_start[0] is not None:
                            paused_accum[0] += now - pause_start[0]
                            pause_start[0] = None

                    with transfer_lock:
                        cur_tot = sent_total_bytes + file_bytes_sent[0]

                    samples.append((now, cur_tot))

                    # Retain samples over the last 1.5 seconds
                    while len(samples) > 2 and (now - samples[0][0]) > 1.5:
                        samples.popleft()

                    dt = now - samples[0][0]
                    delta = cur_tot - samples[0][1]

                    if dt >= 0.2 and delta > 0:
                        window_spd = delta / dt
                        if last_ema_speed[0] > 0:
                            cur_spd = 0.30 * window_spd + 0.70 * last_ema_speed[0]
                        else:
                            cur_spd = window_spd
                        last_ema_speed[0] = cur_spd
                    elif last_ema_speed[0] > 0:
                        cur_spd = last_ema_speed[0]
                    else:
                        cur_spd = 0.0

                    if cur_spd > overall_peak_speed[0]:
                        overall_peak_speed[0] = cur_spd

                    active_elapsed = max(0.001, now - t0 - paused_accum[0])
                    avg_spd = (cur_tot - sent_total_bytes) / active_elapsed if cur_tot > sent_total_bytes else cur_spd

                    rem_bytes = max(0, total_bytes - cur_tot)
                    eta_sec = int(rem_bytes / cur_spd) if cur_spd > 0 else 0

                    pct = int((cur_tot * 100) / total_bytes) if total_bytes > 0 else 0
                    self.progress_cb(f_idx + 1, total_files, filename, pct, cur_spd, avg_spd, eta_sec)

            monitor_t = threading.Thread(target=progress_monitor, daemon=True)
            monitor_t.start()

            def worker_thread(worker_id, assigned_chunks):
                if not assigned_chunks:
                    return
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    try:
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, SOCKET_SNDBUF_SIZE)
                    except Exception:
                        pass
                    sock.connect((self.target_host, NIO_PORT))

                    # Send magic b"ABM2"
                    sock.sendall(b"ABM2")

                    num_stripes = len(assigned_chunks)
                    acks_received = [0]
                    ack_error = [None]
                    ack_stop = threading.Event()

                    # Concurrent ACK reader collects "COK!" without stalling the send pipeline
                    def ack_reader():
                        try:
                            for _ in range(num_stripes):
                                if ack_stop.is_set() or self.cancel_event.is_set():
                                    return
                                ack = b""
                                while len(ack) < 4:
                                    if ack_stop.is_set() or self.cancel_event.is_set():
                                        return
                                    r = sock.recv(4 - len(ack))
                                    if not r:
                                        if not ack_stop.is_set() and not self.cancel_event.is_set():
                                            ack_error[0] = f"Worker {worker_id}: Socket closed prematurely"
                                        return
                                    ack += r
                                if ack != b"COK!":
                                    ack_error[0] = f"Worker {worker_id} stripe ack failed: {ack}"
                                    return
                                acks_received[0] += 1
                        except Exception as ex:
                            if not ack_stop.is_set() and not self.cancel_event.is_set():
                                ack_error[0] = str(ex)

                    ack_t = threading.Thread(target=ack_reader, daemon=True)
                    ack_t.start()

                    # Continuous pipelined stream: stream all assigned stripes back-to-back
                    with open(file_path, "rb") as f_obj:
                        buf = bytearray(CHUNK_SLICE_BYTES)
                        view = memoryview(buf)
                        for chunk_idx, chunk_off, chunk_len in assigned_chunks:
                            if self.cancel_event.is_set() or worker_error[0] or ack_error[0]:
                                break

                            # 32-byte header: transfer_id(Q), chunk_index(I), total_chunks(I), chunk_offset(Q), chunk_length(Q)
                            hdr = struct.pack("!QIIQQ", transfer_id, chunk_idx, total_chunks, chunk_off, chunk_len)
                            sock.sendall(hdr)

                            f_obj.seek(chunk_off)
                            rem_bytes = chunk_len

                            while rem_bytes > 0 and not self.cancel_event.is_set() and not worker_error[0] and not ack_error[0]:
                                self.pause_event.wait()
                                to_read = min(CHUNK_SLICE_BYTES, rem_bytes)
                                bytes_read = f_obj.readinto(view[:to_read])
                                if not bytes_read:
                                    break
                                sock.sendall(view[:bytes_read])
                                rem_bytes -= bytes_read

                                with transfer_lock:
                                    file_bytes_sent[0] += bytes_read

                    # Wait for all stripe ACKs to be confirmed on disk
                    ack_t.join(timeout=15.0)
                    ack_stop.set()
                    try:
                        sock.close()
                    except Exception:
                        pass

                    if ack_error[0]:
                        raise Exception(ack_error[0])
                    if acks_received[0] < num_stripes and not self.cancel_event.is_set():
                        raise Exception(f"Worker {worker_id}: only received {acks_received[0]}/{num_stripes} stripe ACKs")

                except Exception as ex:
                    worker_error[0] = str(ex)

            # Distribute chunks round-robin to adaptive workers
            worker_assignments = [[] for _ in range(num_streams)]
            for idx, c in enumerate(chunks):
                worker_assignments[idx % num_streams].append(c)

            with ThreadPoolExecutor(max_workers=num_streams) as executor:
                futures = [executor.submit(worker_thread, wid, worker_assignments[wid]) for wid in range(num_streams)]
                for fut in futures:
                    fut.result()

            stop_monitor.set()
            monitor_t.join(timeout=0.5)

            sent_total_bytes += file_bytes_sent[0]

            if worker_error[0]:
                errors.append(f"{filename}: {worker_error[0]}")
                ctrl_sock.close()
                continue

            # 3. Finalize on Control Socket
            if not self.cancel_event.is_set():
                fin_payload = json.dumps({"action": "FINALIZE", "transfer_id": transfer_id}).encode("utf-8")
                ctrl_fin = struct.pack("!I", len(fin_payload)) + fin_payload
                ctrl_sock.sendall(ctrl_fin)
                fin_resp = ctrl_sock.recv(1024)
                if b"FINALIZE_OK" not in fin_resp:
                    errors.append(f"{filename}: Finalize failed: {fin_resp}")
            else:
                try:
                    cancel_payload = json.dumps({"action": "CANCEL", "transfer_id": transfer_id}).encode("utf-8")
                    ctrl_cancel = struct.pack("!I", len(cancel_payload)) + cancel_payload
                    ctrl_sock.sendall(ctrl_cancel)
                except Exception:
                    pass
            ctrl_sock.close()

        overall_duration = max(0.01, time.time() - overall_start_time)
        overall_avg_speed = sent_total_bytes / overall_duration if overall_duration > 0 else 0.0
        self.completion_cb(total_files, len(errors), errors, sent_total_bytes, overall_duration, overall_avg_speed, overall_peak_speed[0])

class ScrollableFrame(tk.Frame):
    _active_instances = []
    _global_bound = False

    def __init__(self, parent, bg="#0f172a"):
        super().__init__(parent, bg=bg)
        ScrollableFrame._active_instances.append(self)

        # yscrollincrement=1 ensures 1 unit = exactly 1 pixel for smooth touchpad & mouse scrolling
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, yscrollincrement=1)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_window = tk.Frame(self.canvas, bg=bg)

        self.scrollable_window.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_window, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))

        # Comprehensive global bindings for Windows Precision Touchpad (Tk 9.0 TIP 684),
        # physical mouse wheel, and Linux scroll events
        if not ScrollableFrame._global_bound:
            scroll_events = [
                "<MouseWheel>",
                "<TouchpadScroll>",
                "<Shift-MouseWheel>",
                "<Shift-TouchpadScroll>",
                "<Button-4>",
                "<Button-5>"
            ]
            for ev in scroll_events:
                try:
                    self.bind_all(ev, ScrollableFrame._on_global_scroll)
                except Exception:
                    pass
            ScrollableFrame._global_bound = True

    @classmethod
    def _on_global_scroll(cls, event):
        cls._active_instances = [inst for inst in cls._active_instances if inst.winfo_exists()]
        if not cls._active_instances:
            return

        # Allow internal scrollable widgets (like file listbox) to handle their own scroll
        try:
            w = event.widget
            if isinstance(w, tk.Listbox) and w.yview() != (0.0, 1.0):
                return
        except Exception:
            pass

        target = None
        # 1. Prefer instance containing the hovered widget
        try:
            w_str = str(event.widget)
            for inst in cls._active_instances:
                if w_str.startswith(str(inst)) and inst.winfo_ismapped():
                    target = inst
                    break
        except Exception:
            pass

        # 2. Fallback to currently visible (mapped) tab instance
        if not target:
            for inst in cls._active_instances:
                if inst.winfo_ismapped():
                    target = inst
                    break

        if not target:
            return

        cls.handle_scroll_event(target, event)

    @staticmethod
    def handle_scroll_event(target, event):
        if not target.winfo_exists() or not target.canvas.winfo_exists():
            return

        ev_type = str(getattr(event, "type", ""))
        delta = getattr(event, "delta", 0)
        num = getattr(event, "num", None)

        # 1. Tk 9.0 TIP 684 TouchpadScroll or packed 32-bit delta:
        # Repurposes 32-bit keycode: dx in high 16 bits, dy in low 16 bits
        if ev_type in ("39", "TouchpadScroll") or abs(delta) > 32767:
            u32 = int(delta) & 0xFFFFFFFF
            raw_dy = u32 & 0xFFFF
            dy = raw_dy if raw_dy < 0x8000 else raw_dy - 0x10000
            pixels = int(-dy)
        # 2. Standard MouseWheel (discrete clicks = multiples of 120, or continuous trackpad micro-deltas)
        elif delta:
            if abs(delta) >= 120:
                pixels = int(-1 * (delta / 120) * 35)
            else:
                pixels = int(-1 * delta)
                if pixels == 0:
                    pixels = -2 if delta > 0 else 2
        # 3. Linux Button-4 (up) / Button-5 (down)
        elif num == 4:
            pixels = -35
        elif num == 5:
            pixels = 35
        else:
            return

        if pixels == 0:
            return

        try:
            target.canvas.yview_scroll(pixels, "units")
        except Exception:
            pass


# --- GUI Application ---
class AirBeamSenderApp(BaseTkApp):
    def __init__(self):
        super().__init__()
        self.title("AirBeam v5.0 — PC, Android & iPhone Ultra-Speed Wireless Transfer")
        self.geometry("860x780")
        self.minsize(780, 660)
        self.configure(bg="#0f172a")

        self._is_alive = True
        self.session_node_id = SESSION_NODE_ID
        self.selected_files = []
        self.is_sending = False
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.cancel_event = threading.Event()

        self.hotspot_info = None
        self.connection_mode = tk.StringVar(value="TABLET_HOTSPOT")
        self.tablet_router_ip = "10.150.131.50"
        self.hotspot_state = "IDLE"
        self.current_handover_band = "5GHz"
        self.handover_sent_time = 0.0
        self.hotspot_lock = threading.Lock()
        self.is_negotiating = False
        self.last_valid_speed = 0.0
        self.previous_wifi_ssid = None
        self.connected_to_airbeam = False

        # PC-to-PC Variables & Multi-Stream Receiver Server
        self.pc_connection_mode = tk.StringVar(value="HOME_WIFI")
        self.pc_hotspot_active = False
        self.pc_selected_files = []
        self.target_pc_ip = tk.StringVar(value="")
        self.discovered_pcs = {}
        self.is_pc_sending = False
        self.pc_pause_event = threading.Event()
        self.pc_pause_event.set()
        self.pc_cancel_event = threading.Event()
        self.pc_last_valid_speed = 0.0

        # Start PC Receiver server on Port 7777
        self.pc_receiver = PCReceiverServer(self, port=NIO_PORT)
        self.pc_receiver.start()

        # iPhone Portal & Hotspot variables
        self.iphone_portal_port = IPHONE_PORTAL_PORT
        self.iphone_received_dir = IPHONE_RECEIVED_DIR
        os.makedirs(self.iphone_received_dir, exist_ok=True)
        self.iphone_hotspot_ssid = "iPhone"
        self.iphone_hotspot_password = ""
        self.connected_to_iphone_hotspot = False
        self.win_hotspot_for_iphone_active = False
        self.load_iphone_hotspot_config()

        # iOS stream byte tracker for precision speedometer
        self.ios_ema_speed = 0.0
        self.last_ios_sample_time = time.time()
        self.ios_bytes_in_window = 0

        # Start iPhone iOS Web Portal server on dual ports (8080 & 8090)
        self.iphone_portal = IPhonePortalServer(self, ports=IPHONE_PORTAL_PORTS)
        self.iphone_portal.start()

        # Capture current Wi-Fi profile on startup and persist if home Wi-Fi
        init_profile = get_current_wifi_profile()
        if init_profile and init_profile.strip().lower() != "airbeam":
            self.previous_wifi_ssid = init_profile.strip()
            global PREVIOUS_WIFI_SSID
            PREVIOUS_WIFI_SSID = self.previous_wifi_ssid
            save_last_home_wifi(self.previous_wifi_ssid)

        # Set Windows AppUserModelID so taskbar displays our icon
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('airbeam.wirelessfiletransfer.sender.5.0')
        except Exception:
            pass

        # Set window and taskbar icon
        assets_candidates = [
            os.path.join(BUNDLE_DIR, "assets"),
            os.path.join(os.path.dirname(__file__), "assets"),
            os.path.join(APP_ROOT, "assets"),
            os.path.join(APP_ROOT, "desktop-sender", "assets")
        ]
        assets_dir = next((d for d in assets_candidates if os.path.exists(d)), os.path.join(APP_ROOT, "assets"))
        ico_file = os.path.join(assets_dir, "airbeam.ico")
        png_file = os.path.join(assets_dir, "airbeam.png")
        if os.path.exists(ico_file):
            try:
                self.iconbitmap(ico_file)
            except Exception:
                pass
        if os.path.exists(png_file):
            try:
                self.app_icon = tk.PhotoImage(file=png_file)
                self.iconphoto(False, self.app_icon)
            except Exception:
                pass

        # Pre-install Windows profile for airbeam inside app folder
        ensure_windows_airbeam_profile()

        self.apk_path = self.locate_apk()
        self.local_ip = get_local_ip()

        if self.apk_path and os.path.exists(self.apk_path):
            self.apk_server = ApkServer(self.apk_path)
            self.apk_server.start()

        self.setup_styles()
        self.setup_ui()

        # Window-wide Drag-and-Drop Handler (native OLE IDropTarget via TkinterDnD)
        if TKDND_AVAILABLE:
            self._last_tkdnd_drop_time = 0.0
            self.register_drop_target(self)
            if hasattr(self, "notebook"):
                self.notebook.bind("<<NotebookTabChanged>>", lambda e: self.after(50, lambda: self.register_drop_target(self)))

        # Handle window close to disconnect from airbeam and restore previous Wi-Fi
        self.protocol("WM_DELETE_WINDOW", self.on_window_close)

        # Start Coordinator and Wi-Fi link telemetry poller in background
        self.after(500, self.start_discovery_coordinator)
        self.after(800, self.update_wifi_telemetry_loop)

    def register_drop_target(self, widget):
        """Safely registers an OLE drop target on any Tk widget and its children recursively."""
        if not TKDND_AVAILABLE or not widget:
            return
        try:
            if hasattr(widget, "drop_target_register"):
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self._on_tkdnd_drop)
        except Exception:
            pass
        try:
            for child in widget.winfo_children():
                self.register_drop_target(child)
        except Exception:
            pass

    def _on_tkdnd_drop(self, event):
        """Native OLE Drop callback; parses files cleanly and dispatches to on_global_files_dropped."""
        now = time.time()
        if hasattr(self, "_last_tkdnd_drop_time") and (now - self._last_tkdnd_drop_time) < 0.25:
            return "break"
        self._last_tkdnd_drop_time = now

        raw = getattr(event, "data", "")
        if not raw:
            return "break"
        files = []
        try:
            clean_raw = raw.replace('\\', '/')
            items = list(self.tk.splitlist(clean_raw))
            files = [os.path.normpath(it.strip('{}')) for it in items if it]
        except Exception:
            pass
        if not files:
            import re
            matches = re.findall(r'\{([^}]+)\}|(\S+)', raw)
            for m1, m2 in matches:
                p = (m1 or m2).strip()
                if p:
                    files.append(os.path.normpath(p))
        if files:
            self.on_global_files_dropped(files)
        return "break"

    def get_best_home_wifi_profile(self) -> Optional[str]:
        return get_best_home_wifi_profile(app_instance=self)

    def on_global_files_dropped(self, files):
        """Dispatches dropped files anywhere in the app to the active tab's file queue."""
        if not files:
            return
        current_tab = 0
        try:
            if hasattr(self, "notebook"):
                current_tab = self.notebook.index(self.notebook.select())
        except Exception:
            current_tab = 0

        if current_tab == 1:
            # Tab 1: PC to PC
            self._on_pc_files_dropped(files)
        else:
            # Tab 0: Android, Tab 2: iPhone / iOS, or Tab 3: APK QR fallback
            self._on_main_files_dropped(files)

    def on_window_close(self):
        self._is_alive = False
        try:
            if hasattr(self, "pc_receiver"):
                self.pc_receiver.stop()
        except Exception:
            pass
        try:
            WindowsHotspotController.stop_hotspot(async_mode=True)
        except Exception:
            pass
        try:
            cleanup_airbeam_wifi_on_exit(app_instance=self)
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass

    def locate_apk(self):
        roots = [
            APP_ROOT,
            BUNDLE_DIR,
            os.path.dirname(__file__),
            os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        ]
        candidates = []
        for r in roots:
            candidates.extend([
                os.path.join(r, "release", "AirBeam-v2.7-Receiver.apk"),
                os.path.join(r, "AirBeam-v2.7-Receiver.apk"),
                os.path.join(r, "android-app", "app", "build", "outputs", "apk", "release", "AirBeam-v2.7-Receiver.apk"),
                os.path.join(r, "android-app", "app", "build", "outputs", "apk", "debug", "AirBeam-v2.7-Receiver.apk"),
                os.path.join(r, "release", "AirBeam-v2.6-Receiver.apk"),
                os.path.join(r, "AirBeam-v2.6-Receiver.apk"),
                os.path.join(r, "release", "AirBeam-v2.5-Receiver.apk"),
                os.path.join(r, "AirBeam-v2.5-Receiver.apk"),
            ])
        for p in candidates:
            if os.path.exists(p):
                return p
        return None

    def on_hotspot_toggle_changed(self, is_on):
        if is_on:
            self.lbl_hotspot_toggle_state.config(text="Connecting...", fg="#f59e0b")
            self.connect_to_airbeam_hotspot_action()
        else:
            self.lbl_hotspot_toggle_state.config(text="Disconnecting & restoring home Wi-Fi...", fg="#f59e0b")
            self.disconnect_and_restore_wifi_action()

    def disconnect_and_restore_wifi_action(self):
        home_profile = self.get_best_home_wifi_profile()
        self.lbl_hotspot_toggle_state.config(text="Disconnecting & restoring home Wi-Fi...", fg="#f59e0b")
        self.lbl_device_status.config(text="Disconnecting from 'airbeam'...", style="StatusPending.TLabel")

        def bg():
            reconnected = False
            try:
                subprocess.run(["netsh", "wlan", "set", "profileparameter", "name=airbeam", "connectionmode=manual"], capture_output=True, timeout=2)
                subprocess.run(["netsh", "wlan", "disconnect"], capture_output=True, timeout=2)
                # Wait 1.5s for Intel AX201 radio deauth delay
                time.sleep(1.5)

                if home_profile:
                    subprocess.run(["netsh", "wlan", "set", "profileparameter", f"name={home_profile}", "connectionmode=auto"], capture_output=True, timeout=2)
                    for attempt in range(3):
                        subprocess.run(["netsh", "wlan", "connect", f"name={home_profile}"], capture_output=True, timeout=3)
                        time.sleep(1.5)
                        cur = get_current_wifi_profile()
                        if cur and cur.lower() == home_profile.lower():
                            reconnected = True
                            break
                        res = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True, timeout=2)
                        if "State" in res.stdout and "connected" in res.stdout:
                            reconnected = True
                            break
            except Exception as e:
                print(f"Error during disconnect/restore: {e}")

            status_text = (
                f"Disconnected from 'airbeam' — Reconnected to Home Wi-Fi ({home_profile})"
                if (home_profile and reconnected)
                else (f"Disconnected from 'airbeam'. Reconnected to Home Wi-Fi ({home_profile})" if home_profile else "Disconnected from 'airbeam'.")
            )
            toggle_text = f"OFF ({home_profile})" if home_profile else "OFF (Disconnected)"

            self.after(0, lambda: (
                self.hotspot_switch.set_state(False, trigger_callback=False),
                self.lbl_hotspot_toggle_state.config(text=toggle_text, fg="#94a3b8"),
                self.lbl_device_status.config(text=status_text, style="StatusSuccess.TLabel" if reconnected else "StatusPending.TLabel")
            ))
        threading.Thread(target=bg, daemon=True).start()

    def update_wifi_telemetry_loop(self):
        def loop():
            while True:
                data = parse_wifi_telemetry()
                self.after(0, lambda d=data: self.on_telemetry_updated(d))
                time.sleep(3.0)
        threading.Thread(target=loop, daemon=True).start()

    def on_telemetry_updated(self, data):
        if not hasattr(self, "lbl_telemetry_badge"):
            return
        if data.get("connected"):
            ssid = data.get("ssid", "Unknown")
            band = data.get("band", "Wi-Fi")
            channel = data.get("channel", "")
            rate = data.get("rate", "")
            sig = data.get("signal", "")

            ch_str = f" (Ch {channel})" if channel else ""
            rate_str = f"{rate} Mbps" if rate and "mbps" not in str(rate).lower() else str(rate)
            text = f"📶 SSID: {ssid} | Band: {band}{ch_str} | Link Rate: {rate_str} | Signal: {sig}"
            self.lbl_telemetry_badge.config(text=text)

            is_airbeam = data.get("is_airbeam", False)
            if hasattr(self, "hotspot_switch"):
                self.hotspot_switch.set_state(is_airbeam, trigger_callback=False)
                if is_airbeam:
                    self.connected_to_airbeam = True
                    self.lbl_hotspot_toggle_state.config(text="ON (Connected)", fg="#10b981")
                else:
                    self.lbl_hotspot_toggle_state.config(text="OFF (Disconnected)", fg="#94a3b8")

            # 2.4 GHz performance alert tip
            is_low_rate = False
            try:
                rate_num = float(str(rate).split()[0])
                if rate_num <= 144.0:
                    is_low_rate = True
            except Exception:
                pass

            if is_airbeam and (band == "2.4 GHz" or is_low_rate):
                self.lbl_telemetry_tip.config(text="⚠️ Tip: Switch tablet hotspot band to 5 GHz for 3x–5x faster speeds")
            else:
                self.lbl_telemetry_tip.config(text="")

            # Dynamically sync Option 1 Home Wi-Fi portal URL and QR code if IP changes
            if hasattr(self, "lbl_opt3_status"):
                try:
                    cur_prof = get_current_wifi_profile() or "Wi-Fi"
                    cur_ip = get_local_ip()
                    if getattr(self, "_last_telem_opt3_ip", None) != cur_ip:
                        self._last_telem_opt3_ip = cur_ip
                        self.lbl_opt3_status.config(text=f"✅ Active on Wi-Fi: {cur_prof}  •  PC IP: {cur_ip}")
                        portal_url = f"http://{cur_ip}:{self.iphone_portal_port}/index.html"
                        if hasattr(self, "lbl_opt3_url"):
                            self.lbl_opt3_url.config(text=f"🌐 Safari Portal URL: {portal_url}")
                        if hasattr(self, "qr_opt3_label"):
                            img = self.generate_qr_image(portal_url, box_size=4, border=2)
                            if img:
                                self.qr_opt3_label.config(image=img)
                                self.qr_opt3_label.image = img
                except Exception:
                    pass

            # Auto-detect when PC connects to or disconnects from iPhone Personal Hotspot
            ssid_lower = ssid.lower() if ssid else ""
            my_iphone_ssid = getattr(self, "iphone_hotspot_ssid", "").strip().lower()
            is_iphone = bool(ssid and ("iphone" in ssid_lower or (my_iphone_ssid and my_iphone_ssid in ssid_lower)))
            if is_iphone:
                if not getattr(self, "connected_to_iphone_hotspot", False):
                    self.connected_to_iphone_hotspot = True
                    if hasattr(self, "ios_connect_hotspot_switch"):
                        self.ios_connect_hotspot_switch.set_state(True, trigger_callback=False)
                    cur_ip = get_local_ip()
                    portal_url = f"http://{cur_ip}:{self.iphone_portal_port}/index.html"
                    img_portal = self.generate_qr_image(portal_url, box_size=4, border=2)
                    if hasattr(self, "lbl_ios_connect_hotspot_state"):
                        self.lbl_ios_connect_hotspot_state.config(text=f"ON — Connected to '{ssid}' at {cur_ip}", fg="#10b981")
                    if hasattr(self, "build_opt2_connected_view"):
                        self.build_opt2_connected_view(portal_url, cur_ip, ssid, img_portal)
            else:
                if getattr(self, "connected_to_iphone_hotspot", False):
                    self.connected_to_iphone_hotspot = False
                    if hasattr(self, "ios_connect_hotspot_switch"):
                        self.ios_connect_hotspot_switch.set_state(False, trigger_callback=False)
                    if hasattr(self, "lbl_ios_connect_hotspot_state"):
                        self.lbl_ios_connect_hotspot_state.config(text=f"OFF — Connected to {ssid}", fg="#94a3b8")
                    if hasattr(self, "build_opt2_disconnected_view"):
                        self.build_opt2_disconnected_view()
        else:
            self.lbl_telemetry_badge.config(text="📶 Wi-Fi: Disconnected or Wi-Fi adapter inactive")
            self.lbl_telemetry_tip.config(text="")
            if hasattr(self, "hotspot_switch"):
                self.hotspot_switch.set_state(False, trigger_callback=False)
                self.lbl_hotspot_toggle_state.config(text="OFF (Disconnected)", fg="#94a3b8")
            if getattr(self, "connected_to_iphone_hotspot", False):
                self.connected_to_iphone_hotspot = False
                if hasattr(self, "ios_connect_hotspot_switch"):
                    self.ios_connect_hotspot_switch.set_state(False, trigger_callback=False)
                if hasattr(self, "lbl_ios_connect_hotspot_state"):
                    self.lbl_ios_connect_hotspot_state.config(text="OFF (Wi-Fi Disconnected)", fg="#94a3b8")

        self.update_ios_files_summary()

    def beam_clipboard(self):
        try:
            text = self.clipboard_get()
        except Exception:
            text = None
        if not text or not text.strip():
            messagebox.showinfo("Clipboard Empty", "Your Windows clipboard is empty. Copy text or a URL first!")
            return

        target = self.entry_ip.get().strip()
        if not target or target.startswith("Searching"):
            messagebox.showwarning("No Target", "Target device IP not found. Connect to tablet first.")
            return

        def bg_beam():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.5)
                s.connect((target, NIO_PORT))
                payload = json.dumps({"action": "CLIPBOARD", "type": "CLIPBOARD", "text": text.strip()}).encode("utf-8")
                hdr = b"ABM_CTRL" + struct.pack("!I", len(payload)) + payload
                s.sendall(hdr)
                resp = s.recv(1024)
                s.close()
                preview = text.strip()
                if len(preview) > 60:
                    preview = preview[:60] + "..."
                self.after(0, lambda: messagebox.showinfo("Clipboard Beamed", f"Successfully beamed to tablet:\n\n{preview}"))
            except Exception as ex:
                self.after(0, lambda: messagebox.showerror("Clipboard Error", f"Failed to beam clipboard: {ex}"))

        threading.Thread(target=bg_beam, daemon=True).start()

    def connect_to_airbeam_hotspot_action(self):
        self.lbl_device_status.config(
            text="Disconnecting other networks & connecting to 'airbeam'...",
            style="StatusPending.TLabel"
        )
        def bg():
            connect_windows_to_airbeam(app_instance=self)
            # Allow time for DHCP lease assignment
            time.sleep(1.5)
            gateway_ip = get_wifi_gateway_ip()
            active_target = gateway_ip if gateway_ip else "10.150.131.50"
            if gateway_ip:
                self.after(0, lambda g=gateway_ip: (
                    self.entry_ip.delete(0, tk.END),
                    self.entry_ip.insert(0, g),
                    self.lbl_device_status.config(
                        text=f"Detected Tablet Gateway IP: {g}",
                        style="StatusPending.TLabel"
                    )
                ))

            # Probe candidate IPs
            probe_ips = [active_target]
            if "10.150.131.50" not in probe_ips:
                probe_ips.append("10.150.131.50")
            if "192.168.43.1" not in probe_ips:
                probe_ips.append("192.168.43.1")

            for _ in range(10):
                time.sleep(0.5)
                for tip in probe_ips:
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.settimeout(0.3)
                        if s.connect_ex((tip, NIO_PORT)) == 0:
                            s.close()
                            self.after(0, lambda t=tip: (
                                self.entry_ip.delete(0, tk.END),
                                self.entry_ip.insert(0, t),
                                self.on_tablet_hotspot_ready("samsung SM-T505N", t),
                                self.hotspot_switch.set_state(True, trigger_callback=False),
                                self.lbl_hotspot_toggle_state.config(text="ON (Connected)", fg="#10b981")
                            ))
                            return
                        s.close()
                    except Exception:
                        pass
            cur = get_current_wifi_connection()
            if cur and cur.lower() == "airbeam":
                self.after(0, lambda: (
                    self.lbl_device_status.config(
                        text=f"📶 Connected to 'airbeam' ({active_target}). Ready to beam!",
                        style="StatusSuccess.TLabel"
                    ),
                    self.hotspot_switch.set_state(True, trigger_callback=False),
                    self.lbl_hotspot_toggle_state.config(text="ON (Connected)", fg="#10b981")
                ))
            else:
                self.after(0, lambda: (
                    self.lbl_device_status.config(
                        text="Could not connect to 'airbeam'. Make sure Hotspot is ON on tablet.",
                        style="StatusPending.TLabel"
                    ),
                    self.hotspot_switch.set_state(False, trigger_callback=False),
                    self.lbl_hotspot_toggle_state.config(text="OFF (Failed)", fg="#ef4444")
                ))
        threading.Thread(target=bg, daemon=True).start()

    auto_connect_to_tablet_hotspot = connect_to_airbeam_hotspot_action

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background="#0f172a", foreground="#f8fafc")
        style.configure("Card.TFrame", background="#1e293b", relief="flat")
        style.configure("Header.TLabel", background="#0f172a", foreground="#ffffff", font=("Segoe UI", 16, "bold"))
        style.configure("CardHeader.TLabel", background="#1e293b", foreground="#f8fafc", font=("Segoe UI", 11, "bold"))
        style.configure("CardBody.TLabel", background="#1e293b", foreground="#94a3b8", font=("Segoe UI", 9))
        style.configure("StatusSuccess.TLabel", background="#1e293b", foreground="#10b981", font=("Segoe UI", 10, "bold"))
        style.configure("StatusHotspot.TLabel", background="#1e293b", foreground="#38bdf8", font=("Segoe UI", 10, "bold"))
        style.configure("StatusPending.TLabel", background="#1e293b", foreground="#f59e0b", font=("Segoe UI", 10, "bold"))

        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), background="#2563eb", foreground="#ffffff", borderwidth=0, padding=8)
        style.map("Primary.TButton", background=[("active", "#1d4ed8")])

        style.configure("Secondary.TButton", font=("Segoe UI", 9), background="#334155", foreground="#ffffff", borderwidth=0, padding=6)
        style.map("Secondary.TButton", background=[("active", "#475569")])

        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"), background="#10b981", foreground="#ffffff", borderwidth=0, padding=12)
        style.map("Accent.TButton", background=[("active", "#059669")])

        style.configure("Hotspot.TButton", font=("Segoe UI", 9, "bold"), background="#0284c7", foreground="#ffffff", borderwidth=0, padding=6)
        style.map("Hotspot.TButton", background=[("active", "#0369a1")])

        style.configure("Pause.TButton", font=("Segoe UI", 10, "bold"), background="#f59e0b", foreground="#ffffff", borderwidth=0, padding=10)
        style.map("Pause.TButton", background=[("active", "#d97706")])

        style.configure("Cancel.TButton", font=("Segoe UI", 10, "bold"), background="#ef4444", foreground="#ffffff", borderwidth=0, padding=10)
        style.map("Cancel.TButton", background=[("active", "#dc2626")])

        style.configure("TProgressbar", thickness=16, troughcolor="#334155", background="#2563eb")

    def setup_ui(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=16)

        tab_send = tk.Frame(self.notebook, bg="#0f172a")
        tab_pc = tk.Frame(self.notebook, bg="#0f172a")
        tab_ios = tk.Frame(self.notebook, bg="#0f172a")
        tab_apk = tk.Frame(self.notebook, bg="#0f172a")

        self.notebook.add(tab_send, text="  ⚡ Beam to Android (50-95+ MB/s)  ")
        self.notebook.add(tab_pc, text="  💻 PC to PC (50-100+ MB/s)  ")
        self.notebook.add(tab_ios, text="  📱 iPhone / iOS (50-95+ MB/s)  ")
        self.notebook.add(tab_apk, text="  📥 Install Android APK  ")

        self.register_drop_target(self.notebook)
        self.register_drop_target(tab_send)
        self.register_drop_target(tab_pc)
        self.register_drop_target(tab_ios)

        self.build_send_tab(tab_send)
        self.build_pc_tab(tab_pc)
        self.build_ios_tab(tab_ios)
        self.build_apk_tab(tab_apk)

    def build_send_tab(self, parent):
        scroll_frame = ScrollableFrame(parent, bg="#0f172a")
        scroll_frame.pack(fill="both", expand=True)
        container = scroll_frame.scrollable_window

        # 1. Live Wi-Fi Link & Band Telemetry Badge Card (Top of Window)
        self.telemetry_card = tk.Frame(container, bg="#1e293b", padx=12, pady=7)
        self.telemetry_card.pack(fill="x", padx=10, pady=(6, 10))

        top_telem = tk.Frame(self.telemetry_card, bg="#1e293b")
        top_telem.pack(fill="x")

        self.lbl_telemetry_badge = tk.Label(
            top_telem, text="📶 Wi-Fi: Detecting link telemetry...",
            bg="#1e293b", fg="#38bdf8", font=("Segoe UI", 9, "bold")
        )
        self.lbl_telemetry_badge.pack(side="left")

        self.lbl_telemetry_tip = tk.Label(
            top_telem, text="",
            bg="#1e293b", fg="#f59e0b", font=("Segoe UI", 9, "bold")
        )
        self.lbl_telemetry_tip.pack(side="right")

        # 2. Target Device & Mode Selector Card
        device_card = ttk.Frame(container, style="Card.TFrame", padding=14)
        device_card.pack(fill="x", padx=10, pady=(0, 10))

        top_dev = tk.Frame(device_card, bg="#1e293b")
        top_dev.pack(fill="x", pady=(0, 4))
        ttk.Label(top_dev, text="Target Android Device", style="CardHeader.TLabel").pack(side="left")

        # Connection Mode Selector Bar
        mode_frame = tk.Frame(device_card, bg="#1e293b")
        mode_frame.pack(fill="x", pady=(6, 4))

        tk.Label(mode_frame, text="Mode:", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))

        self.btn_mode_tablet = tk.Button(
            mode_frame, text="📱 Tablet Hotspot",
            bg="#0284c7", fg="#ffffff", font=("Segoe UI", 9, "bold"),
            relief="flat", bd=0, padx=10, pady=5, cursor="hand2",
            command=lambda: self.set_connection_mode("TABLET_HOTSPOT")
        )
        self.btn_mode_tablet.pack(side="left", fill="x", expand=True, padx=2)

        self.btn_mode_laptop = tk.Button(
            mode_frame, text="💻 Laptop Hotspot",
            bg="#334155", fg="#94a3b8", font=("Segoe UI", 9, "bold"),
            relief="flat", bd=0, padx=10, pady=5, cursor="hand2",
            command=lambda: self.set_connection_mode("LAPTOP_HOTSPOT")
        )
        self.btn_mode_laptop.pack(side="left", fill="x", expand=True, padx=2)

        self.btn_mode_router = tk.Button(
            mode_frame, text="🏠 Home Wi-Fi",
            bg="#334155", fg="#94a3b8", font=("Segoe UI", 9, "bold"),
            relief="flat", bd=0, padx=10, pady=5, cursor="hand2",
            command=lambda: self.set_connection_mode("WIFI_ROUTER")
        )
        self.btn_mode_router.pack(side="left", fill="x", expand=True, padx=2)

        self.lbl_mode_desc = tk.Label(
            device_card,
            text="📱 Tablet Hotspot: SSID 'airbeam' | Pass 'airbeam123' (50-95+ MB/s). Use the toggle switch below to connect!",
            bg="#1e293b", fg="#38bdf8", font=("Segoe UI", 9), anchor="w"
        )
        self.lbl_mode_desc.pack(fill="x", pady=(2, 6))

        # Hotspot Interactive Toggle Switch Row
        self.switch_row = tk.Frame(device_card, bg="#162032", padx=10, pady=8)
        self.switch_row.pack(fill="x", pady=(4, 6))

        tk.Label(
            self.switch_row, text="📶 Connect to 'airbeam' Hotspot",
            bg="#162032", fg="#ffffff", font=("Segoe UI", 10, "bold")
        ).pack(side="left")

        self.lbl_hotspot_toggle_state = tk.Label(
            self.switch_row, text="OFF (Disconnected)",
            bg="#162032", fg="#94a3b8", font=("Segoe UI", 9)
        )
        self.lbl_hotspot_toggle_state.pack(side="left", padx=(10, 0))

        self.hotspot_switch = HotspotToggleSwitch(
            self.switch_row, command=self.on_hotspot_toggle_changed, width=52, height=26, bg="#162032"
        )
        self.hotspot_switch.pack(side="right")

        ip_frame = tk.Frame(device_card, bg="#1e293b")
        ip_frame.pack(fill="x", pady=(4, 4))

        tk.Label(ip_frame, text="Target Device IP:", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9)).pack(side="left")
        self.entry_ip = tk.Entry(ip_frame, font=("Segoe UI", 10, "bold"), bg="#0f172a", fg="#38bdf8", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#475569")
        self.entry_ip.insert(0, "10.150.131.50")
        self.entry_ip.pack(side="left", padx=8, ipady=4, fill="x", expand=True)

        btn_test = ttk.Button(ip_frame, text="⚡ Ping / Connect", style="Secondary.TButton", command=self.ping_target)
        btn_test.pack(side="left", padx=3)

        self.btn_action_aux = ttk.Button(ip_frame, text="🔍 Detect", style="Secondary.TButton", command=self.manual_detect)
        self.btn_action_aux.pack(side="left", padx=3)

        self.lbl_device_status = ttk.Label(device_card, text="📱 Ready: Target Device IP 10.150.131.50", style="StatusSuccess.TLabel")
        self.lbl_device_status.pack(anchor="w", pady=(4, 0))

        # Files Card (Where files are selected and listed)
        files_card = ttk.Frame(container, style="Card.TFrame", padding=14)
        files_card.pack(fill="x", padx=10, pady=(0, 10))

        top_file_bar = tk.Frame(files_card, bg="#1e293b")
        top_file_bar.pack(fill="x", pady=(0, 8))

        ttk.Label(top_file_bar, text="📁 Files to Beam", style="CardHeader.TLabel").pack(side="left")

        btn_clipboard = ttk.Button(top_file_bar, text="📋 Beam Clipboard", style="Primary.TButton", command=self.beam_clipboard)
        btn_clipboard.pack(side="right", padx=(4, 0))

        btn_add_files = ttk.Button(top_file_bar, text="+ Add Files", style="Primary.TButton", command=self.add_files)
        btn_add_files.pack(side="right", padx=4)

        btn_add_folder = ttk.Button(top_file_bar, text="+ Add Folder", style="Secondary.TButton", command=self.add_folder)
        btn_add_folder.pack(side="right", padx=4)

        btn_clear = ttk.Button(top_file_bar, text="Clear", style="Secondary.TButton", command=self.clear_files)
        btn_clear.pack(side="right")

        list_frame = tk.Frame(files_card, bg="#0f172a")
        list_frame.pack(fill="x", expand=True)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.listbox_files = tk.Listbox(
            list_frame,
            height=7,
            bg="#0f172a",
            fg="#f8fafc",
            selectbackground="#2563eb",
            selectforeground="#ffffff",
            font=("Segoe UI", 10),
            bd=0,
            highlightthickness=0,
            yscrollcommand=scrollbar.set
        )
        self.listbox_files.pack(fill="both", expand=True, padx=4, pady=4)
        scrollbar.config(command=self.listbox_files.yview)

        self.register_drop_target(files_card)
        self.register_drop_target(self.listbox_files)

        self.lbl_total_size = tk.Label(
            files_card,
            text="0 files selected (0 B) — Drag & drop files anywhere in window or click '+ Add Files' above",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9)
        )
        self.lbl_total_size.pack(anchor="w", pady=(6, 0))

        # Progress & Actions Card
        action_card = ttk.Frame(container, style="Card.TFrame", padding=14)
        action_card.pack(fill="x", padx=10, pady=(0, 14))

        self.progress_bar = ttk.Progressbar(action_card, mode="determinate")
        self.progress_bar.pack(fill="x", pady=(0, 8))

        progress_info = tk.Frame(action_card, bg="#1e293b")
        progress_info.pack(fill="x", pady=(0, 10))

        self.lbl_progress = tk.Label(progress_info, text="Ready to beam", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9))
        self.lbl_progress.pack(side="left")

        self.lbl_speed = tk.Label(progress_info, text="", bg="#1e293b", fg="#38bdf8", font=("Segoe UI", 11, "bold"))
        self.lbl_speed.pack(side="right")

        ctrl_frame = tk.Frame(action_card, bg="#1e293b")
        ctrl_frame.pack(fill="x")

        self.btn_send = ttk.Button(ctrl_frame, text="⚡ Beam Files (Multi-Stream)", style="Accent.TButton", command=self.start_send_thread)
        self.btn_send.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_pause = ttk.Button(ctrl_frame, text="⏸ Pause", style="Pause.TButton", state="disabled", command=self.toggle_pause)
        self.btn_pause.pack(side="left", padx=4)

        self.btn_cancel = ttk.Button(ctrl_frame, text="⏹ Cancel", style="Cancel.TButton", state="disabled", command=self.cancel_transfer)
        self.btn_cancel.pack(side="left", padx=4)

        self.btn_report = ttk.Button(ctrl_frame, text="📊 Speed Report", style="Secondary.TButton", command=self.generate_speed_report)
        self.btn_report.pack(side="right", padx=(6, 0))

    def set_connection_mode(self, mode):
        self.connection_mode.set(mode)
        active_bg = "#0284c7"
        inactive_bg = "#334155"
        active_fg = "#ffffff"
        inactive_fg = "#94a3b8"

        self.btn_mode_tablet.config(
            bg=active_bg if mode == "TABLET_HOTSPOT" else inactive_bg,
            fg=active_fg if mode == "TABLET_HOTSPOT" else inactive_fg
        )
        self.btn_mode_laptop.config(
            bg=active_bg if mode == "LAPTOP_HOTSPOT" else inactive_bg,
            fg=active_fg if mode == "LAPTOP_HOTSPOT" else inactive_fg
        )
        self.btn_mode_router.config(
            bg=active_bg if mode == "WIFI_ROUTER" else inactive_bg,
            fg=active_fg if mode == "WIFI_ROUTER" else inactive_fg
        )

        if mode == "TABLET_HOTSPOT":
            self.lbl_mode_desc.config(
                text="📱 Tablet Hotspot: Connect PC to tablet Wi-Fi. Target: 10.150.131.50",
                fg="#38bdf8"
            )
            self.btn_action_aux.config(text="🔍 Detect", command=self.manual_detect)
            try:
                self.switch_row.pack(fill="x", pady=(4, 6))
            except Exception:
                pass
            current = self.entry_ip.get().strip()
            if not current or current.startswith("Searching") or current.startswith("192.168.137."):
                self.entry_ip.delete(0, tk.END)
                self.entry_ip.insert(0, "10.150.131.50")
            self.lbl_device_status.config(
                text="📱 Tablet Hotspot mode. Use the toggle switch above to connect.",
                style="StatusPending.TLabel"
            )

        elif mode == "LAPTOP_HOTSPOT":
            self.lbl_mode_desc.config(
                text="💻 Laptop Hotspot: PC creates 5 GHz 'joe' hotspot and connects tablet automatically.",
                fg="#a78bfa"
            )
            self.btn_action_aux.config(text="⚡ Start Hotspot", command=lambda: self.trigger_hotspot_handover("5GHz"))
            try:
                self.switch_row.pack_forget()
            except Exception:
                pass
            if self.tablet_router_ip:
                self.trigger_hotspot_handover("5GHz")
            else:
                self.lbl_device_status.config(
                    text="Searching local network to initiate Windows Hotspot handover...",
                    style="StatusPending.TLabel"
                )

        elif mode == "WIFI_ROUTER":
            self.lbl_mode_desc.config(
                text="🏠 Home Wi-Fi: Both devices remain on local Wi-Fi router network.",
                fg="#94a3b8"
            )
            self.btn_action_aux.config(text="🔍 Scan Wi-Fi", command=self.manual_detect)
            try:
                self.switch_row.pack_forget()
            except Exception:
                pass
            target_ip = self.tablet_router_ip or "10.150.131.50"
            self.entry_ip.delete(0, tk.END)
            self.entry_ip.insert(0, target_ip)
            self.lbl_device_status.config(
                text=f"Ready on Home Wi-Fi: Tablet IP {target_ip}",
                style="StatusSuccess.TLabel"
            )

    def manual_detect(self):
        mode = self.connection_mode.get()
        if mode == "TABLET_HOTSPOT":
            self.lbl_device_status.config(text="Probing tablet (10.150.131.50)...", style="StatusPending.TLabel")
        elif mode == "LAPTOP_HOTSPOT":
            self.trigger_hotspot_handover("5GHz")
        else:
            self.lbl_device_status.config(text="Broadcasting discovery on home Wi-Fi...", style="StatusPending.TLabel")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            sock.sendto(b"AIRBEAM_DISCOVER", ("255.255.255.255", UDP_PORT))
            sock.sendto(b"AIRBEAM_DISCOVER", ("192.168.43.1", UDP_PORT))
            sock.sendto(b"AIRBEAM_DISCOVER", ("192.168.43.255", UDP_PORT))
        except Exception:
            pass
        finally:
            sock.close()

    def on_tablet_hotspot_ready(self, model, ip):
        self.hotspot_state = "CONNECTED"
        self.current_handover_band = "5GHz (Tablet)"
        self.entry_ip.delete(0, tk.END)
        self.entry_ip.insert(0, ip)
        self.lbl_device_status.config(
            text=f"🚀 Tablet 5 GHz Hotspot: {model} ({ip}) — 50-95+ MB/s Active!",
            style="StatusHotspot.TLabel"
        )

    # =========================================================================
    # TAB: PC TO PC (50-100+ MB/s Ultra-Speed Transfer)
    # =========================================================================
    def build_pc_tab(self, parent):
        scroll_frame = ScrollableFrame(parent, bg="#0f172a")
        scroll_frame.pack(fill="both", expand=True)
        container = scroll_frame.scrollable_window

        # 1. Header & Live PC Receiver Status Card
        header_card = ttk.Frame(container, style="Card.TFrame", padding=14)
        header_card.pack(fill="x", padx=10, pady=(6, 10))

        top_row = tk.Frame(header_card, bg="#1e293b")
        top_row.pack(fill="x")
        ttk.Label(top_row, text="💻 PC to PC Ultra-Speed Wireless Transfer (50–100+ MB/s)", style="CardHeader.TLabel").pack(side="left")

        self.lbl_pc_rx_badge = tk.Label(
            top_row, text="🟢 PC Receiver Active | Port 7777",
            bg="#064e3b", fg="#34d399", font=("Segoe UI", 9, "bold"), padx=8, pady=2
        )
        self.lbl_pc_rx_badge.pack(side="right")

        ttk.Label(
            header_card,
            text=f"Direct peer-to-peer wireless transfer between Windows PCs. This PC: '{socket.gethostname()}' (Local IP: {self.local_ip})",
            style="CardBody.TLabel"
        ).pack(anchor="w", pady=(4, 8))

        rx_action_bar = tk.Frame(header_card, bg="#1e293b")
        rx_action_bar.pack(fill="x")

        self.lbl_pc_received_summary = tk.Label(
            rx_action_bar, text="📥 Received from PC: 0 file(s) (0 B)",
            bg="#1e293b", fg="#38bdf8", font=("Segoe UI", 9, "bold")
        )
        self.lbl_pc_received_summary.pack(side="left")

        btn_clear_pc_rx = ttk.Button(rx_action_bar, text="🧹 Clear Received PC Files", style="Secondary.TButton", command=self.clear_pc_received_folder)
        btn_clear_pc_rx.pack(side="right", padx=(4, 0))

        btn_open_pc_rx = ttk.Button(rx_action_bar, text="📂 Open Received_From_PC Folder", style="Primary.TButton", command=self.open_pc_received_folder)
        btn_open_pc_rx.pack(side="right")

        # Real-time incoming transfers display
        self.pc_incoming_card = tk.Frame(header_card, bg="#0f172a", padx=10, pady=8, highlightthickness=1, highlightbackground="#334155")
        self.pc_incoming_card.pack(fill="x", pady=(10, 0))

        rx_info_row = tk.Frame(self.pc_incoming_card, bg="#0f172a")
        rx_info_row.pack(fill="x")

        self.lbl_pc_incoming_title = tk.Label(
            rx_info_row, text="📥 Incoming Transfers: Idle (Ready to receive on Port 7777)",
            bg="#0f172a", fg="#94a3b8", font=("Segoe UI", 9, "bold")
        )
        self.lbl_pc_incoming_title.pack(side="left")

        self.lbl_pc_incoming_spd = tk.Label(
            rx_info_row, text="", bg="#0f172a", fg="#10b981", font=("Segoe UI", 9, "bold")
        )
        self.lbl_pc_incoming_spd.pack(side="right")

        self.pc_incoming_bar = ttk.Progressbar(self.pc_incoming_card, mode="determinate")
        self.pc_incoming_bar.pack(fill="x", pady=(6, 0))

        # 2. Connection Mode Selector (Home Wi-Fi vs. Windows 5 GHz Hotspot)
        mode_card = ttk.Frame(container, style="Card.TFrame", padding=12)
        mode_card.pack(fill="x", padx=10, pady=(0, 10))

        top_mode_row = tk.Frame(mode_card, bg="#1e293b")
        top_mode_row.pack(fill="x", pady=(0, 6))

        tk.Label(top_mode_row, text="Mode:", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 8))

        self.btn_pc_mode_wifi = tk.Button(
            top_mode_row, text="🏠 Home / Office Wi-Fi",
            bg="#0284c7", fg="#ffffff", font=("Segoe UI", 9, "bold"),
            relief="flat", bd=0, padx=12, pady=5, cursor="hand2",
            command=lambda: self.set_pc_connection_mode("HOME_WIFI")
        )
        self.btn_pc_mode_wifi.pack(side="left", fill="x", expand=True, padx=3)

        self.btn_pc_mode_hotspot = tk.Button(
            top_mode_row, text="💻 Windows 5 GHz Hotspot (Router-Bypass 50–100+ MB/s)",
            bg="#334155", fg="#94a3b8", font=("Segoe UI", 9, "bold"),
            relief="flat", bd=0, padx=12, pady=5, cursor="hand2",
            command=lambda: self.set_pc_connection_mode("WINDOWS_HOTSPOT")
        )
        self.btn_pc_mode_hotspot.pack(side="left", fill="x", expand=True, padx=3)

        # Panel A: Home Wi-Fi Mode Information
        self.pc_wifi_mode_panel = tk.Frame(mode_card, bg="#0f172a", padx=10, pady=8, highlightthickness=1, highlightbackground="#334155")
        self.pc_wifi_mode_panel.pack(fill="x", pady=(6, 0))

        cur_wifi = get_current_wifi_profile() or "Home Wi-Fi Router"
        self.lbl_pc_wifi_info = tk.Label(
            self.pc_wifi_mode_panel,
            text=f"🏠 Mode: Home / Office Wi-Fi Router  •  Network: '{cur_wifi}'  •  Local IP: {self.local_ip}\nZero setup! Both PCs must be connected to the same Wi-Fi router. AirBeam auto-discovers nearby PCs below.",
            bg="#0f172a", fg="#38bdf8", font=("Segoe UI", 8), justify="left", anchor="w"
        )
        self.lbl_pc_wifi_info.pack(fill="x")

        # Panel B: Windows 5 GHz Hotspot Controls
        self.pc_hotspot_mode_panel = tk.Frame(mode_card, bg="#0f172a", padx=10, pady=8, highlightthickness=1, highlightbackground="#10b981")

        ht_top = tk.Frame(self.pc_hotspot_mode_panel, bg="#0f172a")
        ht_top.pack(fill="x", pady=(0, 6))

        tk.Label(ht_top, text="💻 Windows 5 GHz Mobile Hotspot (Router-Bypass):", bg="#0f172a", fg="#10b981", font=("Segoe UI", 9, "bold")).pack(side="left")

        sw_frame = tk.Frame(ht_top, bg="#0f172a")
        sw_frame.pack(side="right")
        self.pc_hotspot_switch = HotspotToggleSwitch(
            sw_frame, command=self.toggle_windows_hotspot_for_pc,
            width=54, height=26, bg="#0f172a"
        )
        self.pc_hotspot_switch.pack(side="right")

        self.lbl_pc_hotspot_state = tk.Label(
            self.pc_hotspot_mode_panel, text="OFF (Click switch to enable Windows 5 GHz Hotspot)",
            bg="#0f172a", fg="#94a3b8", font=("Segoe UI", 9, "bold")
        )
        self.lbl_pc_hotspot_state.pack(anchor="w", pady=(0, 4))

        self.pc_hotspot_creds_box = tk.Frame(self.pc_hotspot_mode_panel, bg="#162032", padx=8, pady=6, highlightthickness=1, highlightbackground="#334155")
        self.pc_hotspot_creds_box.pack(fill="x", pady=(0, 6))

        self.lbl_pc_hotspot_creds = tk.Label(
            self.pc_hotspot_creds_box,
            text="Turn ON switch above to start 5 GHz Hotspot. Once active, connect the second PC to this hotspot to saturate 50–100+ MB/s!",
            bg="#162032", fg="#94a3b8", font=("Segoe UI", 8), justify="left", anchor="w"
        )
        self.lbl_pc_hotspot_creds.pack(fill="x")

        ht_mid = tk.Frame(self.pc_hotspot_mode_panel, bg="#0f172a")
        ht_mid.pack(fill="x", pady=(2, 0))

        ht_btns = tk.Frame(ht_mid, bg="#0f172a")
        ht_btns.pack(side="left", fill="x", expand=True)

        self.btn_copy_pc_hotspot_url = ttk.Button(ht_btns, text="📋 Copy Hotspot Web URL", style="Primary.TButton", command=self.copy_pc_hotspot_url)
        self.btn_copy_pc_hotspot_url.pack(side="left", padx=(0, 4))

        self.btn_fix_firewall_pc = ttk.Button(ht_btns, text="🛡️ Fix Firewall", style="Secondary.TButton", command=self.launch_firewall_fix)
        self.btn_fix_firewall_pc.pack(side="left", padx=4)

        qr_ht_frame = tk.Frame(ht_mid, bg="#0f172a")
        qr_ht_frame.pack(side="right")

        # QR 1: Wi-Fi Hotspot Auto-Join
        box_qr_wifi = tk.Frame(qr_ht_frame, bg="#162032", padx=6, pady=4, highlightthickness=1, highlightbackground="#334155")
        box_qr_wifi.pack(side="left", padx=4)
        tk.Label(box_qr_wifi, text="📶 Connect Wi-Fi", bg="#162032", fg="#38bdf8", font=("Segoe UI", 8, "bold")).pack()
        self.qr_pc_hotspot_wifi_label = tk.Label(box_qr_wifi, bg="#162032")
        self.qr_pc_hotspot_wifi_label.pack(pady=2)
        tk.Label(box_qr_wifi, text="Scan to auto-join hotspot", bg="#162032", fg="#64748b", font=("Segoe UI", 7)).pack()

        # QR 2: Web Portal Link
        box_qr_portal = tk.Frame(qr_ht_frame, bg="#162032", padx=6, pady=4, highlightthickness=1, highlightbackground="#334155")
        box_qr_portal.pack(side="left", padx=4)
        tk.Label(box_qr_portal, text="🌐 Open Web Portal", bg="#162032", fg="#10b981", font=("Segoe UI", 8, "bold")).pack()
        self.qr_pc_hotspot_portal_label = tk.Label(box_qr_portal, bg="#162032")
        self.qr_pc_hotspot_portal_label.pack(pady=2)
        tk.Label(box_qr_portal, text="Scan to transfer via browser", bg="#162032", fg="#64748b", font=("Segoe UI", 7)).pack()

        self.reset_pc_hotspot_qr_placeholders()

        # 3. Target PC & Discovery Card
        target_card = ttk.Frame(container, style="Card.TFrame", padding=14)
        target_card.pack(fill="x", padx=10, pady=(0, 10))

        top_target = tk.Frame(target_card, bg="#1e293b")
        top_target.pack(fill="x", pady=(0, 4))
        ttk.Label(top_target, text="🎯 Target PC (AirBeam-to-AirBeam)", style="CardHeader.TLabel").pack(side="left")

        btn_rescan_pcs = ttk.Button(top_target, text="🔄 Scan for PCs", style="Secondary.TButton", command=self.scan_for_nearby_pcs)
        btn_rescan_pcs.pack(side="right")

        disc_frame = tk.Frame(target_card, bg="#1e293b")
        disc_frame.pack(fill="x", pady=(6, 8))

        tk.Label(disc_frame, text="Discovered AirBeam PCs on Network:", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold")).pack(anchor="w")

        self.pc_discovered_chips_frame = tk.Frame(disc_frame, bg="#1e293b")
        self.pc_discovered_chips_frame.pack(fill="x", pady=(4, 0))

        self.lbl_no_discovered_pcs = tk.Label(
            self.pc_discovered_chips_frame,
            text="🔍 Listening for nearby AirBeam PCs... (Open AirBeam on the other PC to auto-connect)",
            bg="#1e293b", fg="#64748b", font=("Segoe UI", 9, "italic")
        )
        self.lbl_no_discovered_pcs.pack(anchor="w")

        manual_ip_row = tk.Frame(target_card, bg="#1e293b")
        manual_ip_row.pack(fill="x", pady=(4, 0))

        tk.Label(manual_ip_row, text="Target PC IP:", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))

        self.entry_pc_ip = tk.Entry(
            manual_ip_row, textvariable=self.target_pc_ip,
            font=("Consolas", 10, "bold"), bg="#0f172a", fg="#38bdf8",
            insertbackground="#38bdf8", bd=0, highlightthickness=1,
            highlightbackground="#475569", width=22
        )
        self.entry_pc_ip.pack(side="left", padx=(0, 8), ipady=3)

        btn_ping_pc = ttk.Button(manual_ip_row, text="⚡ Ping / Test Connection", style="Secondary.TButton", command=self.ping_target_pc)
        btn_ping_pc.pack(side="left")

        self.lbl_pc_ping_result = tk.Label(manual_ip_row, text="", bg="#1e293b", fg="#10b981", font=("Segoe UI", 9))
        self.lbl_pc_ping_result.pack(side="left", padx=(8, 0))

        # 3. File Queue & Beaming Card
        send_card = ttk.Frame(container, style="Card.TFrame", padding=14)
        send_card.pack(fill="x", padx=10, pady=(0, 10))

        top_send_bar = tk.Frame(send_card, bg="#1e293b")
        top_send_bar.pack(fill="x", pady=(0, 8))

        ttk.Label(top_send_bar, text="📁 Files to Beam to PC", style="CardHeader.TLabel").pack(side="left")

        btn_add_pc_files = ttk.Button(top_send_bar, text="+ Add Files", style="Primary.TButton", command=self.add_pc_files)
        btn_add_pc_files.pack(side="right", padx=4)

        btn_add_pc_folder = ttk.Button(top_send_bar, text="+ Add Folder", style="Secondary.TButton", command=self.add_pc_folder)
        btn_add_pc_folder.pack(side="right", padx=4)

        btn_clear_pc_files = ttk.Button(top_send_bar, text="Clear", style="Secondary.TButton", command=self.clear_pc_files)
        btn_clear_pc_files.pack(side="right")

        pc_list_frame = tk.Frame(send_card, bg="#0f172a")
        pc_list_frame.pack(fill="x", expand=True)

        pc_scrollbar = tk.Scrollbar(pc_list_frame)
        pc_scrollbar.pack(side="right", fill="y")

        self.listbox_pc_files = tk.Listbox(
            pc_list_frame, height=5, bg="#0f172a", fg="#f8fafc",
            selectbackground="#2563eb", selectforeground="#ffffff",
            font=("Segoe UI", 10), bd=0, highlightthickness=0,
            yscrollcommand=pc_scrollbar.set
        )
        self.listbox_pc_files.pack(fill="both", expand=True, padx=4, pady=4)
        pc_scrollbar.config(command=self.listbox_pc_files.yview)

        self.register_drop_target(send_card)
        self.register_drop_target(self.listbox_pc_files)

        self.lbl_pc_total_size = tk.Label(
            send_card,
            text="0 file(s) selected (0 B) — Drag & drop files anywhere in window or click '+ Add Files' above",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9)
        )
        self.lbl_pc_total_size.pack(anchor="w", pady=(6, 8))

        # Progress & Controls
        self.pc_progress_bar = ttk.Progressbar(send_card, mode="determinate")
        self.pc_progress_bar.pack(fill="x", pady=(0, 8))

        pc_prog_info = tk.Frame(send_card, bg="#1e293b")
        pc_prog_info.pack(fill="x", pady=(0, 10))

        self.lbl_pc_progress = tk.Label(pc_prog_info, text="Ready to beam to PC", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9))
        self.lbl_pc_progress.pack(side="left")

        self.lbl_pc_speed = tk.Label(pc_prog_info, text="", bg="#1e293b", fg="#38bdf8", font=("Segoe UI", 11, "bold"))
        self.lbl_pc_speed.pack(side="right")

        pc_ctrl_frame = tk.Frame(send_card, bg="#1e293b")
        pc_ctrl_frame.pack(fill="x")

        self.btn_send_pc = ttk.Button(pc_ctrl_frame, text="⚡ Beam Files to PC (50-100+ MB/s)", style="Accent.TButton", command=self.start_pc_send_thread)
        self.btn_send_pc.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_pause_pc = ttk.Button(pc_ctrl_frame, text="⏸ Pause", style="Pause.TButton", state="disabled", command=self.toggle_pc_pause)
        self.btn_pause_pc.pack(side="left", padx=4)

        self.btn_cancel_pc = ttk.Button(pc_ctrl_frame, text="⏹ Cancel", style="Cancel.TButton", state="disabled", command=self.cancel_pc_transfer)
        self.btn_cancel_pc.pack(side="left", padx=4)

        # 4. Received Files History Card
        self.pc_history_card = ttk.Frame(container, style="Card.TFrame", padding=14)
        self.pc_history_card.pack(fill="x", padx=10, pady=(0, 10))

        hist_top = tk.Frame(self.pc_history_card, bg="#1e293b")
        hist_top.pack(fill="x", pady=(0, 6))
        ttk.Label(hist_top, text="📥 Received PC Files History", style="CardHeader.TLabel").pack(side="left")
        ttk.Label(hist_top, text="(Double-click any file to open/reveal)", style="CardBody.TLabel").pack(side="right")

        hist_list_frame = tk.Frame(self.pc_history_card, bg="#0f172a")
        hist_list_frame.pack(fill="x", expand=True)

        hist_scroll = tk.Scrollbar(hist_list_frame)
        hist_scroll.pack(side="right", fill="y")

        self.listbox_pc_history = tk.Listbox(
            hist_list_frame, height=4, bg="#0f172a", fg="#f8fafc",
            selectbackground="#0284c7", selectforeground="#ffffff",
            font=("Segoe UI", 9), bd=0, highlightthickness=0,
            yscrollcommand=hist_scroll.set
        )
        self.listbox_pc_history.pack(fill="both", expand=True, padx=4, pady=4)
        hist_scroll.config(command=self.listbox_pc_history.yview)
        self.listbox_pc_history.bind("<Double-Button-1>", lambda e: self.open_selected_pc_received_file())

        # 5. Zero-Install Web Mode Card (For PCs Without AirBeam)
        web_card = ttk.Frame(container, style="Card.TFrame", padding=14)
        web_card.pack(fill="x", padx=10, pady=(0, 14))

        top_web = tk.Frame(web_card, bg="#1e293b")
        top_web.pack(fill="x", pady=(0, 4))
        ttk.Label(top_web, text="🌐 Zero-Install Web Mode (For PCs Without AirBeam)", style="CardHeader.TLabel").pack(side="left")

        ttk.Label(
            web_card,
            text="If the second PC doesn't have AirBeam installed yet, open this URL in Chrome, Edge, or Firefox on that PC to drag-and-drop send or download files at full Wi-Fi speed:",
            style="CardBody.TLabel"
        ).pack(anchor="w", pady=(2, 8))

        web_mid_row = tk.Frame(web_card, bg="#1e293b")
        web_mid_row.pack(fill="x")

        left_web_box = tk.Frame(web_mid_row, bg="#1e293b")
        left_web_box.pack(side="left", fill="x", expand=True, padx=(0, 10))

        web_url = f"http://{self.local_ip}:{self.iphone_portal_port}/index.html"
        self.lbl_pc_web_url = tk.Label(
            left_web_box, text=f"🌐 Web Portal: {web_url}",
            bg="#0f172a", fg="#38bdf8", font=("Consolas", 10, "bold"),
            padx=10, pady=8, highlightthickness=1, highlightbackground="#334155"
        )
        self.lbl_pc_web_url.pack(fill="x", pady=(0, 8))

        web_btn_row = tk.Frame(left_web_box, bg="#1e293b")
        web_btn_row.pack(fill="x")

        self.btn_copy_pc_web_url = ttk.Button(web_btn_row, text="📋 Copy Web Link", style="Primary.TButton", command=self.copy_pc_web_url)
        self.btn_copy_pc_web_url.pack(side="left", padx=(0, 4))

        self.btn_open_pc_web = ttk.Button(web_btn_row, text="🌐 Open Browser", style="Secondary.TButton", command=self.open_pc_web_browser)
        self.btn_open_pc_web.pack(side="left", padx=4)

        self.btn_share_installer = ttk.Button(web_btn_row, text="💾 Share Setup (.exe)", style="Secondary.TButton", command=self.open_setup_folder_to_share)
        self.btn_share_installer.pack(side="left", padx=4)

        img_qr = self.generate_qr_image(web_url, box_size=3, border=2)
        qr_card = tk.Frame(web_mid_row, bg="#0f172a", padx=8, pady=6, highlightthickness=1, highlightbackground="#334155")
        qr_card.pack(side="right")
        tk.Label(qr_card, text="🌐 Web Portal Link", bg="#0f172a", fg="#38bdf8", font=("Segoe UI", 8, "bold")).pack()
        self.qr_pc_web_label = tk.Label(qr_card, bg="#0f172a")
        self.qr_pc_web_label.pack(pady=2)
        tk.Label(qr_card, text="Scan with 2nd PC camera or phone", bg="#0f172a", fg="#64748b", font=("Segoe UI", 7)).pack()
        if img_qr:
            self.qr_pc_web_label.config(image=img_qr)
            self.qr_pc_web_label.image = img_qr

        self.update_pc_received_summary()

    def add_pc_files(self):
        files = filedialog.askopenfilenames(title="Select files to beam to PC")
        if files:
            for f in files:
                if f not in self.pc_selected_files:
                    self.pc_selected_files.append(f)
            self.update_pc_file_listbox()

    def add_pc_folder(self):
        folder = filedialog.askdirectory(title="Select folder to beam to PC")
        if folder:
            for root, _, filenames in os.walk(folder):
                for fn in filenames:
                    full = os.path.join(root, fn)
                    if full not in self.pc_selected_files:
                        self.pc_selected_files.append(full)
            self.update_pc_file_listbox()

    def clear_pc_files(self):
        self.pc_selected_files.clear()
        self.update_pc_file_listbox()

    def update_pc_file_listbox(self):
        if hasattr(self, "listbox_pc_files") and self.listbox_pc_files.winfo_exists():
            self.listbox_pc_files.delete(0, tk.END)
        total_bytes = 0
        for f in self.pc_selected_files:
            if os.path.exists(f):
                sz = os.path.getsize(f)
                total_bytes += sz
                if hasattr(self, "listbox_pc_files") and self.listbox_pc_files.winfo_exists():
                    self.listbox_pc_files.insert(tk.END, f"{os.path.basename(f)} ({format_bytes(sz)})")
        count = len(self.pc_selected_files)
        size_str = format_bytes(total_bytes)
        if hasattr(self, "lbl_pc_total_size") and self.lbl_pc_total_size.winfo_exists():
            self.lbl_pc_total_size.config(
                text=f"{count} file(s) selected ({size_str}) — Drag & drop files anywhere in window or click '+ Add Files' above"
            )

    def start_pc_send_thread(self):
        target = self.target_pc_ip.get().strip()
        if not target:
            messagebox.showwarning("Target PC Required", "Please enter the Target PC IP or click one of the discovered PCs above!")
            return
        if not self.pc_selected_files:
            messagebox.showwarning("No Files", "Please select one or more files to beam to the target PC!")
            return
        if self.is_pc_sending:
            return

        self.is_pc_sending = True
        self.pc_pause_event.set()
        self.pc_cancel_event.clear()

        self.btn_send_pc.config(state="disabled", text="Beaming to PC (50-100+ MB/s)...")
        self.btn_pause_pc.config(state="normal", text="⏸ Pause")
        self.btn_cancel_pc.config(state="normal")

        engine = HighSpeedTransferEngine(
            target, self.pc_selected_files,
            self.on_pc_transfer_progress,
            self.on_pc_transfer_complete,
            self.pc_pause_event,
            self.pc_cancel_event
        )
        threading.Thread(target=engine.execute, daemon=True).start()

    def toggle_pc_pause(self):
        if self.pc_pause_event.is_set():
            self.pc_pause_event.clear()
            self.btn_pause_pc.config(text="▶ Resume")
            self.lbl_pc_speed.config(text="⏸ Transfer Paused")
        else:
            self.pc_pause_event.set()
            self.btn_pause_pc.config(text="⏸ Pause")

    def cancel_pc_transfer(self):
        if messagebox.askyesno("Cancel Transfer", "Are you sure you want to cancel beaming files to the target PC?"):
            self.pc_cancel_event.set()
            self.btn_pause_pc.config(state="disabled")
            self.btn_cancel_pc.config(state="disabled")
            self.lbl_pc_progress.config(text="Cancelling transfer...")

    def on_pc_transfer_progress(self, file_idx, total_files, filename, pct, cur_spd, avg_spd=0.0, eta_sec=0):
        if cur_spd > 0:
            self.pc_last_valid_speed = cur_spd
            live_str = format_speed_with_mbps(cur_spd)
        elif getattr(self, "pc_last_valid_speed", 0) > 0:
            live_str = format_speed_with_mbps(self.pc_last_valid_speed)
        else:
            live_str = "0.0 MB/s (0 Mbps)"

        avg_str = format_speed(avg_spd)
        eta_str = format_eta(eta_sec)
        spd_display = f"⚡ {live_str}  |  Avg: {avg_str}  |  ETA: {eta_str}"

        self.after(0, lambda: (
            self.lbl_pc_progress.config(text=f"Sending {file_idx}/{total_files}: {filename} ({pct}%)"),
            self.pc_progress_bar.config(value=pct),
            self.lbl_pc_speed.config(text=spd_display)
        ))

    def on_pc_transfer_complete(self, total, error_count, errors, total_bytes=0, duration=0.0, avg_spd=0.0, peak_spd=0.0):
        self.is_pc_sending = False
        avg_str = format_speed_with_mbps(avg_spd)
        peak_str = format_speed(peak_spd)
        final_summary = f"⚡ Completed: Avg {avg_str} | Peak {peak_str}" if avg_spd > 0 else "⚡ Completed"

        def update_ui():
            self.btn_send_pc.config(state="normal", text="⚡ Beam Files to PC (50-100+ MB/s)")
            self.btn_pause_pc.config(state="disabled", text="⏸ Pause")
            self.btn_cancel_pc.config(state="disabled")
            self.lbl_pc_speed.config(text=final_summary)
            self.pc_progress_bar.config(value=100)
            if error_count == 0:
                messagebox.showinfo("PC Transfer Complete", f"Successfully beamed {total} file(s) ({format_bytes(total_bytes)})\nin {duration:.1f}s at {avg_str}!")
            else:
                messagebox.showwarning("Transfer Issues", f"Beamed with {error_count} error(s):\n" + "\n".join(errors[:4]))
        self.after(0, update_ui)

    def scan_for_nearby_pcs(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        my_host = socket.gethostname()
        msg = f"AIRBEAM_PC_PING|{self.session_node_id}|{my_host}|{self.local_ip}".encode("utf-8")
        try:
            sock.sendto(msg, ("255.255.255.255", UDP_PORT))
            sock.sendto(msg, ("192.168.137.255", UDP_PORT))
            if self.local_ip and "." in self.local_ip:
                subnet_bcast = self.local_ip.rsplit(".", 1)[0] + ".255"
                sock.sendto(msg, (subnet_bcast, UDP_PORT))
        except Exception:
            pass
        sock.close()

        # Check connected hotspot clients
        try:
            hotspot_clients = get_connected_hotspot_client_ips()
            now = time.time()
            all_local = get_all_local_ips()
            all_local.add(self.local_ip)
            for hip in hotspot_clients:
                if hip not in all_local and not hip.startswith("127."):
                    self.discovered_pcs[hip] = {
                        "hostname": f"AirBeam Peer ({hip})",
                        "ip": hip,
                        "time": now
                    }
                    if not self.target_pc_ip.get().strip():
                        self.target_pc_ip.set(hip)
        except Exception:
            pass

        now = time.time()
        self.discovered_pcs = {k: v for k, v in self.discovered_pcs.items() if (now - v["time"]) < 30.0}
        self.update_discovered_pcs_ui()

    def update_discovered_pcs_ui(self):
        if not hasattr(self, "pc_discovered_chips_frame"):
            return
        for w in self.pc_discovered_chips_frame.winfo_children():
            w.destroy()

        if not self.discovered_pcs:
            lbl = tk.Label(
                self.pc_discovered_chips_frame,
                text="🔍 Listening for nearby AirBeam PCs... (Open AirBeam on the other PC to auto-connect)",
                bg="#1e293b", fg="#64748b", font=("Segoe UI", 9, "italic")
            )
            lbl.pack(anchor="w")
            return

        for ip, info in list(self.discovered_pcs.items()):
            hostname = info.get("hostname", "AirBeam PC")
            chip = tk.Frame(self.pc_discovered_chips_frame, bg="#0f172a", padx=8, pady=4, highlightthickness=1, highlightbackground="#10b981")
            chip.pack(side="left", padx=(0, 8), pady=2)

            tk.Label(
                chip, text=f"💻 {hostname} ({ip})",
                bg="#0f172a", fg="#f8fafc", font=("Segoe UI", 9, "bold")
            ).pack(side="left", padx=(0, 6))

            btn_select = tk.Button(
                chip, text="⚡ Select", bg="#10b981", fg="#0f172a",
                font=("Segoe UI", 8, "bold"), relief="flat", bd=0, padx=6, pady=2,
                cursor="hand2", command=lambda target_ip=ip: self.select_target_pc(target_ip)
            )
            btn_select.pack(side="left")

    def select_target_pc(self, ip):
        self.target_pc_ip.set(ip)
        if hasattr(self, "lbl_pc_ping_result"):
            self.lbl_pc_ping_result.config(text=f"Selected: {ip} ✅", fg="#10b981")

    def ping_target_pc(self):
        target = self.target_pc_ip.get().strip()
        if not target:
            messagebox.showwarning("Enter IP", "Please select a discovered PC or enter a target PC IP address.")
            return
        def _test():
            try:
                t0 = time.time()
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.0)
                s.connect((target, NIO_PORT))
                rtt = (time.time() - t0) * 1000.0
                s.close()
                self.after(0, lambda: self.lbl_pc_ping_result.config(text=f"Connected! RTT: {rtt:.1f} ms ✅", fg="#10b981"))
                self.after(0, lambda: messagebox.showinfo(
                    "Connection OK",
                    f"Successfully connected to AirBeam PC at {target}:7777!\n\n"
                    f"Latency (RTT): {rtt:.1f} ms\n"
                    f"High-speed NIO transfer link ready!"
                ))
            except Exception as e:
                self.after(0, lambda: self.lbl_pc_ping_result.config(text="Connection Failed ❌", fg="#ef4444"))
                self.after(0, lambda: messagebox.showerror(
                    "Connection Failed",
                    f"Could not connect to {target}:{NIO_PORT}.\n\n"
                    f"Error: {e}\n\n"
                    f"Troubleshooting:\n"
                    f"1. Make sure AirBeam is running on the target PC.\n"
                    f"2. Ensure both PCs are connected to the same Wi-Fi or Hotspot.\n"
                    f"3. Run 'Fix-AirBeam-Firewall.bat' if Windows Firewall is blocking port 7777."
                ))
        threading.Thread(target=_test, daemon=True).start()

    def open_pc_received_folder(self):
        os.makedirs(PC_RECEIVED_DIR, exist_ok=True)
        try:
            os.startfile(PC_RECEIVED_DIR)
        except Exception:
            try:
                subprocess.Popen(["explorer.exe", PC_RECEIVED_DIR])
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open folder: {e}")

    def update_pc_received_summary(self):
        if not os.path.exists(PC_RECEIVED_DIR):
            return
        files = [f for f in os.listdir(PC_RECEIVED_DIR) if not f.endswith(".part") and os.path.isfile(os.path.join(PC_RECEIVED_DIR, f))]
        tot_sz = sum(os.path.getsize(os.path.join(PC_RECEIVED_DIR, f)) for f in files)
        if hasattr(self, "lbl_pc_received_summary"):
            self.lbl_pc_received_summary.config(text=f"📥 Received from PC: {len(files)} file(s) ({format_bytes(tot_sz)})")
        if hasattr(self, "update_pc_received_history_ui"):
            self.update_pc_received_history_ui()

    def update_pc_received_history_ui(self):
        if not hasattr(self, "listbox_pc_history"):
            return
        self.listbox_pc_history.delete(0, tk.END)
        if not os.path.exists(PC_RECEIVED_DIR):
            self.listbox_pc_history.insert(tk.END, "  (No files received from other PCs yet)")
            return
        files = [f for f in os.listdir(PC_RECEIVED_DIR) if not f.endswith(".part") and os.path.isfile(os.path.join(PC_RECEIVED_DIR, f))]
        if not files:
            self.listbox_pc_history.insert(tk.END, "  (No files received from other PCs yet)")
            return
        files.sort(key=lambda f: os.path.getmtime(os.path.join(PC_RECEIVED_DIR, f)), reverse=True)
        for f in files:
            fp = os.path.join(PC_RECEIVED_DIR, f)
            sz = os.path.getsize(fp)
            mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(fp)))
            self.listbox_pc_history.insert(tk.END, f"  📄 {f}  ({format_bytes(sz)})  —  {mtime}")

    def open_selected_pc_received_file(self):
        if not hasattr(self, "listbox_pc_history"):
            return
        sel = self.listbox_pc_history.curselection()
        if not sel:
            return
        idx = sel[0]
        files = [f for f in os.listdir(PC_RECEIVED_DIR) if not f.endswith(".part") and os.path.isfile(os.path.join(PC_RECEIVED_DIR, f))]
        files.sort(key=lambda f: os.path.getmtime(os.path.join(PC_RECEIVED_DIR, f)), reverse=True)
        if 0 <= idx < len(files):
            target = os.path.join(PC_RECEIVED_DIR, files[idx])
            try:
                os.startfile(target)
            except Exception:
                try:
                    subprocess.Popen(["explorer.exe", f"/select,{target}"])
                except Exception:
                    pass

    def clear_pc_received_folder(self):
        if not os.path.exists(PC_RECEIVED_DIR):
            messagebox.showinfo("Folder Empty", "The 'Received_From_PC' folder is already empty!")
            return
        files = [os.path.join(PC_RECEIVED_DIR, f) for f in os.listdir(PC_RECEIVED_DIR) if not f.endswith(".part") and os.path.isfile(os.path.join(PC_RECEIVED_DIR, f))]
        if not files:
            messagebox.showinfo("Folder Empty", "The 'Received_From_PC' folder is already empty!")
            return
        tot_sz = sum(os.path.getsize(f) for f in files)
        if not messagebox.askyesno("Confirm Clear", f"Permanently delete all {len(files)} received file(s) ({format_bytes(tot_sz)}) from 'Received_From_PC'?"):
            return
        deleted = 0
        for f in files:
            try:
                os.remove(f)
                deleted += 1
            except Exception:
                pass
        self.update_pc_received_summary()
        messagebox.showinfo("Cleared", f"Deleted {deleted} file(s) from 'Received_From_PC'.")

    def _on_pc_files_dropped(self, files):
        if not files:
            return
        for f in files:
            path = f.decode('utf-8', errors='replace') if isinstance(f, bytes) else str(f)
            path = os.path.abspath(path)
            if os.path.isfile(path):
                if path not in self.pc_selected_files:
                    self.pc_selected_files.append(path)
            elif os.path.isdir(path):
                for root, _, filenames in os.walk(path):
                    for fn in filenames:
                        full = os.path.join(root, fn)
                        if full not in self.pc_selected_files:
                            self.pc_selected_files.append(full)
        self.update_pc_file_listbox()

    def _on_main_files_dropped(self, files):
        if not files:
            return
        for f in files:
            path = f.decode('utf-8', errors='replace') if isinstance(f, bytes) else str(f)
            path = os.path.abspath(path)
            if os.path.isfile(path):
                if path not in self.selected_files:
                    self.selected_files.append(path)
            elif os.path.isdir(path):
                for root, _, filenames in os.walk(path):
                    for fn in filenames:
                        full = os.path.join(root, fn)
                        if full not in self.selected_files:
                            self.selected_files.append(full)
        self.refresh_file_list()

    def on_pc_receiver_ready(self, port, success, err=""):
        if hasattr(self, "lbl_pc_rx_badge"):
            if success:
                self.lbl_pc_rx_badge.config(text=f"🟢 PC Receiver Active | Port {port}", bg="#064e3b", fg="#34d399")
            else:
                self.lbl_pc_rx_badge.config(text=f"⚠️ Port {port} Conflict", bg="#7f1d1d", fg="#fca5a5")

    def on_pc_receive_start(self, filename, filesize, sender_ip):
        if hasattr(self, "lbl_pc_incoming_title"):
            self.lbl_pc_incoming_title.config(
                text=f"📥 Receiving: '{filename}' ({format_bytes(filesize)}) from {sender_ip}...",
                fg="#38bdf8"
            )
            self.pc_incoming_bar.config(value=0)
            self.lbl_pc_incoming_spd.config(text="Connecting streams...")

    def on_pc_receive_progress(self, filename, cur_bytes, total_bytes, speed):
        if hasattr(self, "pc_incoming_bar"):
            pct = int((cur_bytes * 100) / total_bytes) if total_bytes > 0 else 0
            spd_str = format_speed_with_mbps(speed)
            self.pc_incoming_bar.config(value=pct)
            self.lbl_pc_incoming_spd.config(text=f"⚡ {spd_str} ({pct}%)")

    def on_pc_receive_complete(self, filename, total_bytes, duration, avg_speed, dest_path):
        if hasattr(self, "lbl_pc_incoming_title"):
            spd_str = format_speed_with_mbps(avg_speed)
            self.pc_incoming_bar.config(value=100)
            self.lbl_pc_incoming_title.config(
                text=f"✅ Received: '{filename}' ({format_bytes(total_bytes)}) in {duration:.1f}s!",
                fg="#10b981"
            )
            self.lbl_pc_incoming_spd.config(text=f"⚡ Avg: {spd_str}")
            self.update_pc_received_summary()

    def copy_pc_web_url(self):
        url = f"http://{self.local_ip}:{self.iphone_portal_port}/index.html"
        self.clipboard_clear()
        self.clipboard_append(url)
        self.btn_copy_pc_web_url.config(text="Copied! ✅")
        self.after(2000, lambda: self.btn_copy_pc_web_url.config(text="📋 Copy Web Link"))

    def open_pc_web_browser(self):
        url = f"http://127.0.0.1:{self.iphone_portal_port}/index.html"
        try:
            webbrowser.open(url)
        except Exception:
            pass

    def open_setup_folder_to_share(self):
        setup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "setup-output")
        if not os.path.exists(setup_dir):
            setup_dir = os.path.join(APP_ROOT, "setup-output")
        if os.path.exists(setup_dir):
            try:
                os.startfile(setup_dir)
            except Exception:
                pass
        else:
            messagebox.showinfo("Setup Folder", f"Setup files are located in:\n{setup_dir}")

    def set_pc_connection_mode(self, mode):
        self.pc_connection_mode.set(mode)
        if mode == "HOME_WIFI":
            self.btn_pc_mode_wifi.config(bg="#0284c7", fg="#ffffff")
            self.btn_pc_mode_hotspot.config(bg="#334155", fg="#94a3b8")
            self.pc_wifi_mode_panel.pack(fill="x", pady=(6, 0))
            self.pc_hotspot_mode_panel.pack_forget()
            web_url = f"http://{self.local_ip}:{self.iphone_portal_port}/index.html"
            if hasattr(self, "lbl_pc_web_url"):
                self.lbl_pc_web_url.config(text=f"🌐 Web Portal: {web_url}")
            img_qr = self.generate_qr_image(web_url, box_size=3, border=2)
            if img_qr and hasattr(self, "qr_pc_web_label"):
                self.qr_pc_web_label.config(image=img_qr)
                self.qr_pc_web_label.image = img_qr
        else:
            self.btn_pc_mode_wifi.config(bg="#334155", fg="#94a3b8")
            self.btn_pc_mode_hotspot.config(bg="#0284c7", fg="#ffffff")
            self.pc_wifi_mode_panel.pack_forget()
            self.pc_hotspot_mode_panel.pack(fill="x", pady=(6, 0))
            hotspot_ip = "192.168.137.1"
            web_url = f"http://{hotspot_ip}:{self.iphone_portal_port}/index.html"
            if hasattr(self, "lbl_pc_web_url"):
                self.lbl_pc_web_url.config(text=f"🌐 Web Portal: {web_url}")
            img_qr = self.generate_qr_image(web_url, box_size=3, border=2)
            if img_qr and hasattr(self, "qr_pc_web_label"):
                self.qr_pc_web_label.config(image=img_qr)
                self.qr_pc_web_label.image = img_qr
            self.scan_for_nearby_pcs()

    def toggle_windows_hotspot_for_pc(self, target_state):
        if target_state:
            self.lbl_pc_hotspot_state.config(text="Starting Windows 5 GHz Hotspot...", fg="#f59e0b")
            def worker():
                res = WindowsHotspotController.ensure_hotspot_active("5GHz")
                if res and res.get("enabled"):
                    self.pc_hotspot_active = True
                    ssid = res.get("ssid", "airbeam").strip()
                    pwd = res.get("passphrase", "airbeam123").strip()
                    host_ip = res.get("host_ip", "192.168.137.1").strip()
                    wifi_qr = f"WIFI:T:WPA;S:{ssid};P:{pwd};;"
                    portal_url = f"http://{host_ip}:{self.iphone_portal_port}/index.html"
                    img_wifi = self.generate_qr_image(wifi_qr, box_size=3, border=2)
                    img_portal = self.generate_qr_image(portal_url, box_size=3, border=2)
                    def update_ui():
                        self.lbl_pc_hotspot_state.config(text=f"ON — Active at {host_ip} (5 GHz)", fg="#10b981")
                        self.lbl_pc_hotspot_creds.config(
                            text=f"Network: {ssid}  •  Password: {pwd}  •  Hotspot IP: {host_ip}\nSecond PC: Connect to '{ssid}', then open AirBeam or {portal_url}",
                            fg="#38bdf8"
                        )
                        if img_wifi and hasattr(self, "qr_pc_hotspot_wifi_label"):
                            self.qr_pc_hotspot_wifi_label.config(image=img_wifi)
                            self.qr_pc_hotspot_wifi_label.image = img_wifi
                        if img_portal and hasattr(self, "qr_pc_hotspot_portal_label"):
                            self.qr_pc_hotspot_portal_label.config(image=img_portal)
                            self.qr_pc_hotspot_portal_label.image = img_portal
                        if hasattr(self, "lbl_pc_web_url"):
                            self.lbl_pc_web_url.config(text=f"🌐 Web Portal: {portal_url}")
                        if hasattr(self, "qr_pc_web_label") and img_portal:
                            self.qr_pc_web_label.config(image=img_portal)
                            self.qr_pc_web_label.image = img_portal
                        self.scan_for_nearby_pcs()
                    self.after(0, update_ui)
                else:
                    def on_fail():
                        self.pc_hotspot_switch.set_state(False, trigger_callback=False)
                        self.lbl_pc_hotspot_state.config(text="Failed to start Windows Hotspot. Check Wi-Fi adapter.", fg="#ef4444")
                    self.after(0, on_fail)
            threading.Thread(target=worker, daemon=True).start()
        else:
            self.lbl_pc_hotspot_state.config(text="Stopping Windows Hotspot...", fg="#f59e0b")
            def stop_worker():
                WindowsHotspotController.stop_hotspot()
                self.pc_hotspot_active = False
                def update_stop():
                    self.lbl_pc_hotspot_state.config(text="OFF (Click switch to enable Windows 5 GHz Hotspot)", fg="#94a3b8")
                    self.lbl_pc_hotspot_creds.config(text="Turn ON switch above to start 5 GHz Hotspot and generate connection credentials.", fg="#94a3b8")
                    self.reset_pc_hotspot_qr_placeholders()
                    web_url = f"http://{self.local_ip}:{self.iphone_portal_port}/index.html"
                    if hasattr(self, "lbl_pc_web_url"):
                        self.lbl_pc_web_url.config(text=f"🌐 Web Portal: {web_url}")
                    img_qr = self.generate_qr_image(web_url, box_size=3, border=2)
                    if hasattr(self, "qr_pc_web_label") and img_qr:
                        self.qr_pc_web_label.config(image=img_qr)
                        self.qr_pc_web_label.image = img_qr
                self.after(0, update_stop)
            threading.Thread(target=stop_worker, daemon=True).start()

    def reset_pc_hotspot_qr_placeholders(self):
        dummy_wifi = self.generate_qr_image("WIFI:T:WPA;S:airbeam;P:airbeam123;;", box_size=3, border=2)
        dummy_portal = self.generate_qr_image(f"http://192.168.137.1:{self.iphone_portal_port}/index.html", box_size=3, border=2)
        if dummy_wifi and hasattr(self, "qr_pc_hotspot_wifi_label"):
            self.qr_pc_hotspot_wifi_label.config(image=dummy_wifi)
            self.qr_pc_hotspot_wifi_label.image = dummy_wifi
        if dummy_portal and hasattr(self, "qr_pc_hotspot_portal_label"):
            self.qr_pc_hotspot_portal_label.config(image=dummy_portal)
            self.qr_pc_hotspot_portal_label.image = dummy_portal

    def copy_pc_hotspot_url(self):
        url = f"http://192.168.137.1:{self.iphone_portal_port}/index.html"
        self.clipboard_clear()
        self.clipboard_append(url)
        if hasattr(self, "btn_copy_pc_hotspot_url"):
            self.btn_copy_pc_hotspot_url.config(text="Copied! ✅")
            self.after(2000, lambda: self.btn_copy_pc_hotspot_url.config(text="📋 Copy Hotspot Web URL"))

    def build_apk_tab(self, parent):
        scroll_frame = ScrollableFrame(parent, bg="#0f172a")
        scroll_frame.pack(fill="both", expand=True)
        container = ttk.Frame(scroll_frame.scrollable_window, style="Card.TFrame", padding=20)
        container.pack(fill="both", expand=True)

        apk_filename = os.path.basename(self.apk_path) if self.apk_path else "AirBeam-v2.7-Receiver.apk"
        ttk.Label(container, text=f"Install {apk_filename} on Android", style="CardHeader.TLabel").pack(anchor="center")
        ttk.Label(container, text="Scan with your tablet camera or browser to download the updated APK with App Hotspot & Mode Selector!", style="CardBody.TLabel").pack(anchor="center", pady=(4, 16))

        self.qr_label = tk.Label(container, bg="#1e293b")
        self.qr_label.pack(anchor="center", pady=10)

        apk_url = f"http://{self.local_ip}:{APK_SERVER_PORT}/download"
        self.lbl_apk_url = tk.Label(container, text=f"Direct Link: {apk_url}\nFile: {apk_filename}", bg="#1e293b", fg="#38bdf8", font=("Segoe UI", 10, "bold"), justify="center")
        self.lbl_apk_url.pack(anchor="center", pady=8)

        self.generate_qr_code(apk_url)

        instructions = (
            "AirBeam v2.7 Update Features:\n"
            "• Interactive Hotspot Toggle Switch: 1-click connect/disconnect with home Wi-Fi auto-restore.\n"
            "• Pipelined 6-Stream Turbo Engine: Zero stop-and-wait stalls with 8 MB socket buffer.\n"
            "• Precision Speedometer: Receiver-confirmed rolling window EMA & pause-aware timer.\n"
            "• Live Wi-Fi Telemetry Badge: Shows real-time link rate, band, channel & 5 GHz tip.\n"
            "• Instant Clipboard Beam: Beam copied text & URLs from PC to Android with 1-click open."
        )
        lbl_instruct = tk.Label(container, text=instructions, justify="left", bg="#0f172a", fg="#cbd5e1", font=("Segoe UI", 9), padx=14, pady=12)
        lbl_instruct.pack(fill="x", pady=14)

    def generate_qr_code(self, data):
        try:
            qr = qrcode.QRCode(box_size=6, border=2)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
            photo = ImageTk.PhotoImage(img)
            self.qr_label.config(image=photo)
            self.qr_label.image = photo
        except Exception:
            pass

    def generate_qr_image(self, data, box_size=4, border=2):
        try:
            qr = qrcode.QRCode(box_size=box_size, border=border)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    def build_ios_tab(self, parent):
        scroll_frame = ScrollableFrame(parent, bg="#0f172a")
        scroll_frame.pack(fill="both", expand=True)
        container = scroll_frame.scrollable_window

        # Header Info Card
        header_card = ttk.Frame(container, style="Card.TFrame", padding=14)
        header_card.pack(fill="x", padx=10, pady=(6, 10))
        ttk.Label(header_card, text="📱 iPhone & iPad Ultra-Speed Wireless Transfer (iOS Portal v5.0)", style="CardHeader.TLabel").pack(anchor="w")
        ttk.Label(header_card, text="Zero app installation required on iOS! Use Option 1 below for instant transfer over Home Wi-Fi, or Options 2 & 3 for direct router-bypass speeds (50–95+ MB/s).", style="CardBody.TLabel").pack(anchor="w", pady=(2, 0))

        # --- OPTION 1: Transfer Over Home Wi-Fi Router (Zero Hotspot Required) ---
        opt3_card = ttk.Frame(container, style="Card.TFrame", padding=14)
        opt3_card.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Label(opt3_card, text="Option 1 (Recommended — Zero Setup): 🏠 Transfer Over Home Wi-Fi Router", style="CardHeader.TLabel").pack(anchor="w")
        home_name = get_best_home_wifi_profile(self) or "Home Wi-Fi"
        ttk.Label(
            opt3_card,
            text=f"Instant transfer! Both your PC and iPhone stay connected to your home Wi-Fi ('{home_name}'). No hotspot toggling or disconnecting.",
            style="CardBody.TLabel"
        ).pack(anchor="w", pady=(2, 8))

        self.opt3_action_frame = tk.Frame(opt3_card, bg="#0f172a", padx=12, pady=10, highlightthickness=1, highlightbackground="#334155")
        self.opt3_action_frame.pack(fill="x", pady=(4, 0))
        self.active_opt3_portal_url = None
        self.build_opt3_view()

        # --- OPTION 2: Windows 5 GHz Mobile Hotspot (1-Tap Auto-Join) ---
        opt1_card = ttk.Frame(container, style="Card.TFrame", padding=14)
        opt1_card.pack(fill="x", padx=10, pady=(0, 10))

        opt1_top = tk.Frame(opt1_card, bg="#1e293b")
        opt1_top.pack(fill="x", pady=(0, 8))
        ttk.Label(opt1_top, text="Option 2: 📡 Windows 5 GHz Mobile Hotspot (PC Hotspot ➔ iPhone)", style="CardHeader.TLabel").pack(side="left")

        # Toggle Switch for Option 2
        sw1_frame = tk.Frame(opt1_card, bg="#1e293b")
        sw1_frame.pack(fill="x", pady=(0, 8))
        self.ios_win_hotspot_switch = HotspotToggleSwitch(sw1_frame, command=self.toggle_windows_hotspot_for_ios, width=54, height=26, bg="#1e293b")
        self.ios_win_hotspot_switch.pack(side="left", padx=(0, 10))

        self.lbl_ios_win_hotspot_state = tk.Label(
            sw1_frame, text="OFF (Click switch to enable Windows Hotspot for iPhone)",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold")
        )
        self.lbl_ios_win_hotspot_state.pack(side="left")

        # Side-by-Side QR Codes Frame
        self.qr_dual_frame = tk.Frame(opt1_card, bg="#1e293b")
        self.qr_dual_frame.pack(fill="x", pady=(6, 8))

        # Left QR: Step 1 Wi-Fi Auto-Join
        step1_box = tk.Frame(self.qr_dual_frame, bg="#0f172a", padx=12, pady=10, highlightbackground="#334155", highlightthickness=1)
        step1_box.pack(side="left", fill="both", expand=True, padx=(0, 6))
        tk.Label(step1_box, text="STEP 1: Join Wi-Fi Hotspot", bg="#0f172a", fg="#10b981", font=("Segoe UI", 10, "bold")).pack()
        tk.Label(step1_box, text="Point iPhone Camera here → Tap 'Join Network'", bg="#0f172a", fg="#94a3b8", font=("Segoe UI", 8)).pack(pady=(2, 6))
        self.qr_ios_wifi_label = tk.Label(step1_box, bg="#0f172a")
        self.qr_ios_wifi_label.pack(pady=4)

        # Right QR: Step 2 Open AirBeam Portal
        step2_box = tk.Frame(self.qr_dual_frame, bg="#0f172a", padx=12, pady=10, highlightbackground="#334155", highlightthickness=1)
        step2_box.pack(side="right", fill="both", expand=True, padx=(6, 0))
        tk.Label(step2_box, text="STEP 2: Open AirBeam Web Portal", bg="#0f172a", fg="#38bdf8", font=("Segoe UI", 10, "bold")).pack()
        tk.Label(step2_box, text="Point iPhone Camera here → Tap 'Open in Safari'", bg="#0f172a", fg="#94a3b8", font=("Segoe UI", 8)).pack(pady=(2, 6))
        self.qr_ios_portal_label = tk.Label(step2_box, bg="#0f172a")
        self.qr_ios_portal_label.pack(pady=4)

        self.lbl_ios_win_hotspot_creds = tk.Label(
            opt1_card, text="Turn ON switch above to generate Wi-Fi Auto-Join & Safari Portal QR codes.",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9)
        )
        self.lbl_ios_win_hotspot_creds.pack(anchor="w", pady=(4, 0))
        opt1_card.bind("<Configure>", lambda e: self.lbl_ios_win_hotspot_creds.config(wraplength=max(200, e.width - 28)))

        # Action Buttons Row for Option 2
        btn_win_row = tk.Frame(opt1_card, bg="#1e293b")
        btn_win_row.pack(fill="x", pady=(6, 6))

        self.btn_copy_win_portal_url = tk.Button(
            btn_win_row, text="📋 Copy Portal URL", bg="#334155", fg="#f8fafc",
            font=("Segoe UI", 8, "bold"), relief="flat", bd=0, padx=8, pady=4, cursor="hand2",
            command=self.copy_win_hotspot_portal_url
        )
        self.btn_copy_win_portal_url.pack(side="left", padx=(0, 6))

        self.btn_ref_win_hotspot = tk.Button(
            btn_win_row, text="🔄 Refresh IP / QR", bg="#1e293b", fg="#38bdf8",
            font=("Segoe UI", 8, "bold"), relief="flat", bd=0, padx=8, pady=4, cursor="hand2",
            highlightthickness=1, highlightbackground="#38bdf8",
            command=self.refresh_win_hotspot_qr
        )
        self.btn_ref_win_hotspot.pack(side="left", padx=(0, 6))

        self.btn_switch_port = tk.Button(
            btn_win_row, text=f"🔀 Port: {self.iphone_portal_port}", bg="#1e293b", fg="#a855f7",
            font=("Segoe UI", 8, "bold"), relief="flat", bd=0, padx=8, pady=4, cursor="hand2",
            highlightthickness=1, highlightbackground="#a855f7",
            command=self.toggle_portal_port
        )
        self.btn_switch_port.pack(side="left", padx=(0, 6))

        self.btn_fix_win_firewall = tk.Button(
            btn_win_row, text="🛡️ Fix Firewall", bg="#7f1d1d", fg="#fca5a5",
            font=("Segoe UI", 8, "bold"), relief="flat", bd=0, padx=8, pady=4, cursor="hand2",
            command=self.launch_firewall_fix
        )
        self.btn_fix_win_firewall.pack(side="left")

        # 3-Step Troubleshooting Guide for Option 2
        win_guide_box = tk.Frame(opt1_card, bg="#162032", padx=10, pady=8, highlightthickness=1, highlightbackground="#334155")
        win_guide_box.pack(fill="x", pady=(6, 0))

        tk.Label(win_guide_box, text="💡 If Safari on iPhone says 'Site can't be reached' or forces HTTPS:", bg="#162032", fg="#f59e0b", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
        tk.Label(win_guide_box, text="1️⃣ Join Wi-Fi First: Scan STEP 1 QR code with Camera to connect to the PC Hotspot.", bg="#162032", fg="#cbd5e1", font=("Segoe UI", 8), justify="left").pack(anchor="w")
        tk.Label(win_guide_box, text="2️⃣ Turn OFF Mobile Data: In iPhone Control Center, turn off Mobile Data so iOS doesn't divert Safari to 5G/LTE.", bg="#162032", fg="#38bdf8", font=("Segoe UI", 8, "bold"), justify="left").pack(anchor="w", pady=2)
        tk.Label(win_guide_box, text="3️⃣ Click '🔀 Port' to Switch: If Safari cached HTTPS on 8090, click '🔀 Port' above to switch to Port 8080 (clean with NO HTTPS cache!).", bg="#162032", fg="#a855f7", font=("Segoe UI", 8, "bold"), justify="left").pack(anchor="w", pady=2)
        tk.Label(win_guide_box, text="4️⃣ Safari Private Tab: Open a Private tab in Safari or scan the STEP 2 QR code (includes /index.html).", bg="#162032", fg="#cbd5e1", font=("Segoe UI", 8), justify="left").pack(anchor="w")
        tk.Label(win_guide_box, text="5️⃣ Instant Alternative: Use Option 1 at the top! It connects instantly over Home Wi-Fi with ZERO hotspot toggling.", bg="#162032", fg="#10b981", font=("Segoe UI", 8, "bold"), justify="left").pack(anchor="w", pady=(2, 0))

        # --- OPTION 3: Connect PC to iPhone Personal Hotspot ---
        opt2_card = ttk.Frame(container, style="Card.TFrame", padding=14)
        opt2_card.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Label(opt2_card, text="Option 3: 📶 Connect PC to iPhone 5 GHz Personal Hotspot (iPhone Hotspot ➔ PC)", style="CardHeader.TLabel").pack(anchor="w")
        ttk.Label(opt2_card, text="Turn ON Personal Hotspot in iPhone Settings (5 GHz). Toggle switch below or connect directly via Windows Wi-Fi flyout.", style="CardBody.TLabel").pack(anchor="w", pady=(2, 8))

        fields_frame = tk.Frame(opt2_card, bg="#1e293b")
        fields_frame.pack(fill="x", pady=(0, 10))

        tk.Label(fields_frame, text="iPhone SSID:", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.entry_iphone_ssid = tk.Entry(
            fields_frame, width=18,
            bg="#0f172a", fg="#ffffff",
            insertbackground="#38bdf8",
            font=("Segoe UI", 10, "bold"),
            relief="flat", bd=0,
            highlightthickness=1, highlightbackground="#475569", highlightcolor="#38bdf8"
        )
        self.entry_iphone_ssid.grid(row=0, column=1, sticky="w", padx=(0, 16), ipady=3)
        self.entry_iphone_ssid.insert(0, self.iphone_hotspot_ssid)

        tk.Label(fields_frame, text="Hotspot Password:", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w", padx=(0, 6))
        self.entry_iphone_pwd = tk.Entry(
            fields_frame, width=18, show="*",
            bg="#0f172a", fg="#ffffff",
            insertbackground="#38bdf8",
            font=("Segoe UI", 10, "bold"),
            relief="flat", bd=0,
            highlightthickness=1, highlightbackground="#475569", highlightcolor="#38bdf8"
        )
        self.entry_iphone_pwd.grid(row=0, column=3, sticky="w", padx=(0, 6), ipady=3)
        self.entry_iphone_pwd.insert(0, self.iphone_hotspot_password)

        self.btn_toggle_pwd_view = tk.Button(
            fields_frame, text="👁", bg="#334155", fg="#f8fafc", font=("Segoe UI", 9, "bold"),
            relief="flat", bd=0, padx=6, pady=2, cursor="hand2", command=self.toggle_pwd_visibility
        )
        self.btn_toggle_pwd_view.grid(row=0, column=4, sticky="w", padx=(0, 10))

        sw2_frame = tk.Frame(opt2_card, bg="#1e293b")
        sw2_frame.pack(fill="x", pady=(2, 8))
        self.ios_connect_hotspot_switch = HotspotToggleSwitch(sw2_frame, command=self.toggle_connect_to_iphone_hotspot, width=54, height=26, bg="#1e293b")
        self.ios_connect_hotspot_switch.pack(side="left", padx=(0, 10))

        self.lbl_ios_connect_hotspot_state = tk.Label(
            sw2_frame, text="OFF (Click switch or connect via Windows Wi-Fi flyout)",
            bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 9, "bold")
        )
        self.lbl_ios_connect_hotspot_state.pack(side="left")

        # Option 3 Next-Steps Guidance & QR Container
        self.opt2_action_frame = tk.Frame(opt2_card, bg="#0f172a", padx=12, pady=10, highlightthickness=1, highlightbackground="#334155")
        self.opt2_action_frame.pack(fill="x", pady=(4, 0))
        self.active_opt2_portal_url = None
        self.build_opt2_disconnected_view()

        # --- CARD 4: Files Staged for iPhone & iPad (Web Portal) ---
        ios_files_card = ttk.Frame(container, style="Card.TFrame", padding=14)
        ios_files_card.pack(fill="x", padx=10, pady=(0, 10))

        top_ios_bar = tk.Frame(ios_files_card, bg="#1e293b")
        top_ios_bar.pack(fill="x", pady=(0, 8))

        ttk.Label(top_ios_bar, text="📁 Files Staged for iPhone & iPad (Web Portal)", style="CardHeader.TLabel").pack(side="left")

        btn_ios_clear = ttk.Button(top_ios_bar, text="Clear", style="Secondary.TButton", command=self.clear_ios_staged_files)
        btn_ios_clear.pack(side="right")

        btn_ios_add_folder = ttk.Button(top_ios_bar, text="+ Add Folder", style="Secondary.TButton", command=self.add_folder)
        btn_ios_add_folder.pack(side="right", padx=4)

        btn_ios_add_files = ttk.Button(top_ios_bar, text="+ Add Files", style="Primary.TButton", command=self.add_files)
        btn_ios_add_files.pack(side="right", padx=4)

        btn_ios_clip = ttk.Button(top_ios_bar, text="📋 Send Clipboard", style="Secondary.TButton", command=self.beam_clipboard_to_ios)
        btn_ios_clip.pack(side="right", padx=(4, 0))

        ios_list_frame = tk.Frame(ios_files_card, bg="#0f172a")
        ios_list_frame.pack(fill="x", expand=True)

        ios_scrollbar = tk.Scrollbar(ios_list_frame)
        ios_scrollbar.pack(side="right", fill="y")

        self.listbox_ios_files = tk.Listbox(
            ios_list_frame,
            height=6,
            bg="#0f172a",
            fg="#f8fafc",
            selectbackground="#2563eb",
            selectforeground="#ffffff",
            font=("Segoe UI", 10),
            bd=0,
            highlightthickness=0,
            yscrollcommand=ios_scrollbar.set
        )
        self.listbox_ios_files.pack(fill="both", expand=True, padx=4, pady=4)
        ios_scrollbar.config(command=self.listbox_ios_files.yview)

        self.register_drop_target(ios_files_card)
        self.register_drop_target(self.listbox_ios_files)

        self.lbl_ios_total_size = tk.Label(
            ios_files_card,
            text="0 files selected (0 B) — Drag & drop files anywhere in window or click '+ Add Files' above",
            bg="#1e293b",
            fg="#94a3b8",
            font=("Segoe UI", 9)
        )
        self.lbl_ios_total_size.pack(anchor="w", pady=(6, 0))

        # --- CARD 5: iPhone Portal Received Files & Live Telemetry ---
        tools_card = ttk.Frame(container, style="Card.TFrame", padding=14)
        tools_card.pack(fill="x", padx=10, pady=(0, 14))

        ttk.Label(tools_card, text="iPhone Portal Received Files & Live Telemetry", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 8))

        btn_bar = tk.Frame(tools_card, bg="#1e293b")
        btn_bar.pack(fill="x", pady=(0, 8))

        btn_open_recv = ttk.Button(btn_bar, text="📂 Open Received Folder", style="Secondary.TButton", command=self.open_iphone_received_folder)
        btn_open_recv.pack(side="left", padx=(0, 6))

        btn_clear_recv = ttk.Button(btn_bar, text="🧹 Clear Uploaded Files", style="Secondary.TButton", command=self.clear_iphone_received_folder)
        btn_clear_recv.pack(side="left", padx=(0, 6))

        btn_ref_qr = ttk.Button(btn_bar, text="🔄 Refresh QR", style="Secondary.TButton", command=self.refresh_ios_qr_codes)
        btn_ref_qr.pack(side="left")

        # Live file counts summary
        self.lbl_ios_files_summary = tk.Label(
            tools_card, text="📤 Staged for iPhone: 0 file(s) (0 B)  •  📥 Received from iPhone: 0 file(s) (0 B)",
            bg="#1e293b", fg="#38bdf8", font=("Segoe UI", 9), anchor="w"
        )
        self.lbl_ios_files_summary.pack(fill="x", pady=(8, 8))
        tools_card.bind("<Configure>", lambda e: self.lbl_ios_files_summary.config(wraplength=max(200, e.width - 28)))
        self.update_ios_files_summary()

        # Live Speedometer readout on Tab 3
        self.lbl_ios_live_speed = tk.Label(
            tools_card, text=f"⚡ iOS Portal Status: Active on Port {self.iphone_portal_port} | Live Speed: 0.0 MB/s",
            bg="#0f172a", fg="#10b981", font=("Segoe UI", 10, "bold"), padx=12, pady=8
        )
        self.lbl_ios_live_speed.pack(fill="x")

        # Initialize default placeholder QR codes
        self.reset_ios_qr_placeholders()

    def toggle_windows_hotspot_for_ios(self, target_state):
        if target_state:
            self.lbl_ios_win_hotspot_state.config(text="Starting Windows 5 GHz Hotspot...", fg="#f59e0b")
            def worker():
                res = WindowsHotspotController.ensure_hotspot_active("5GHz")
                if res and res.get("enabled"):
                    self.win_hotspot_for_iphone_active = True
                    ssid = res.get("ssid", "WindowsHotspot").strip()
                    pwd = res.get("passphrase", "").strip()
                    host_ip = res.get("host_ip", "192.168.137.1").strip()

                    wifi_qr = f"WIFI:T:WPA;S:{ssid};P:{pwd};;"
                    portal_url = f"http://{host_ip}:{self.iphone_portal_port}/index.html"
                    self.active_win_hotspot_portal_url = portal_url

                    img_wifi = self.generate_qr_image(wifi_qr, box_size=4, border=2)
                    img_portal = self.generate_qr_image(portal_url, box_size=4, border=2)

                    def update_ui():
                        self.lbl_ios_win_hotspot_state.config(text=f"ON — Active at {host_ip} (5 GHz)", fg="#10b981")
                        self.lbl_ios_win_hotspot_creds.config(
                            text=f"SSID: {ssid}  •  Password: {pwd}  •  Direct URL: {portal_url}",
                            fg="#38bdf8"
                        )
                        if img_wifi:
                            self.qr_ios_wifi_label.config(image=img_wifi)
                            self.qr_ios_wifi_label.image = img_wifi
                        if img_portal:
                            self.qr_ios_portal_label.config(image=img_portal)
                            self.qr_ios_portal_label.image = img_portal
                    self.after(0, update_ui)
                else:
                    def on_fail():
                        self.ios_win_hotspot_switch.set_state(False, trigger_callback=False)
                        self.lbl_ios_win_hotspot_state.config(text="Failed to start Windows Hotspot. Check Wi-Fi adapter.", fg="#ef4444")
                    self.after(0, on_fail)
            threading.Thread(target=worker, daemon=True).start()
        else:
            self.lbl_ios_win_hotspot_state.config(text="Stopping Windows Hotspot...", fg="#f59e0b")
            def stop_worker():
                WindowsHotspotController.stop_hotspot()
                self.win_hotspot_for_iphone_active = False
                def update_stop():
                    self.lbl_ios_win_hotspot_state.config(text="OFF (Click switch to enable Windows Hotspot)", fg="#94a3b8")
                    self.lbl_ios_win_hotspot_creds.config(text="Turn ON switch above to generate Wi-Fi & Portal QR codes.", fg="#94a3b8")
                    self.reset_ios_qr_placeholders()
                self.after(0, update_stop)
            threading.Thread(target=stop_worker, daemon=True).start()

    def toggle_pwd_visibility(self):
        if self.entry_iphone_pwd.cget("show") == "*":
            self.entry_iphone_pwd.config(show="")
            self.btn_toggle_pwd_view.config(text="🔒")
        else:
            self.entry_iphone_pwd.config(show="*")
            self.btn_toggle_pwd_view.config(text="👁")

    def copy_opt2_portal_url(self):
        if getattr(self, "active_opt2_portal_url", None):
            self.clipboard_clear()
            self.clipboard_append(self.active_opt2_portal_url)
            if hasattr(self, "btn_copy_portal_url"):
                self.btn_copy_portal_url.config(text="Copied! ✅", fg="#10b981")
                self.after(2000, lambda: self.btn_copy_portal_url.config(text="📋 Copy Portal URL", fg="#f8fafc"))

    def toggle_portal_port(self):
        self.iphone_portal_port = 8090 if self.iphone_portal_port == 8080 else 8080
        if hasattr(self, "btn_switch_port"):
            self.btn_switch_port.config(text=f"🔀 Port: {self.iphone_portal_port}")
        if hasattr(self, "lbl_ios_live_speed"):
            self.lbl_ios_live_speed.config(text=f"⚡ iOS Portal Status: Active on Ports 8080 & 8090 | Current: {self.iphone_portal_port}")
        if getattr(self, "win_hotspot_for_iphone_active", False):
            self.refresh_win_hotspot_qr()
        elif getattr(self, "connected_to_iphone_hotspot", False):
            self.refresh_ios_qr_codes()
        else:
            self.refresh_opt3_home_portal()

    def open_opt2_portal_browser(self):
        url = getattr(self, "active_opt2_portal_url", None) or f"http://127.0.0.1:{self.iphone_portal_port}/index.html"
        try:
            webbrowser.open(url)
        except Exception:
            pass

    def copy_win_hotspot_portal_url(self):
        url = getattr(self, "active_win_hotspot_portal_url", None)
        if url:
            self.clipboard_clear()
            self.clipboard_append(url)
            if hasattr(self, "btn_copy_win_portal_url"):
                self.btn_copy_win_portal_url.config(text="Copied! ✅", fg="#10b981")
                self.after(2000, lambda: self.btn_copy_win_portal_url.config(text="📋 Copy Portal URL", fg="#f8fafc"))
        else:
            messagebox.showinfo("Hotspot Inactive", "Please turn ON the Windows Hotspot switch above first.")

    def refresh_win_hotspot_qr(self):
        if not getattr(self, "win_hotspot_for_iphone_active", False):
            messagebox.showinfo("Hotspot Inactive", "Please turn ON the Windows Hotspot switch above first.")
            return
        host_ip = "192.168.137.1"
        try:
            cmd = ["powershell", "-NoProfile", "-Command", "Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -like '192.168.137.*' -or (($_.InterfaceAlias -like '*Wi-Fi Direct*' -or $_.InterfaceAlias -like '*Local Area Connection*') -and $_.IPAddress -notlike '169.254.*' -and $_.IPAddress -ne '127.0.0.1') } | Select-Object -ExpandProperty IPAddress -First 1"]
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
            if out:
                host_ip = out.splitlines()[0].strip()
        except Exception:
            pass

        portal_url = f"http://{host_ip}:{self.iphone_portal_port}/index.html"
        self.active_win_hotspot_portal_url = portal_url
        img = self.generate_qr_image(portal_url, box_size=4, border=2)
        if img:
            self.qr_ios_portal_label.config(image=img)
            self.qr_ios_portal_label.image = img
            self.lbl_ios_win_hotspot_creds.config(text=f"Direct URL: {portal_url}")
        messagebox.showinfo("Hotspot Refreshed", f"Windows Hotspot Portal refreshed at:\n{portal_url}")

    def build_opt2_disconnected_view(self):
        for widget in self.opt2_action_frame.winfo_children():
            widget.destroy()

        h_frame = tk.Frame(self.opt2_action_frame, bg="#0f172a")
        h_frame.pack(fill="x", pady=(0, 6))

        tk.Label(
            h_frame, text="📱 How Option 3 Works (iPhone Personal Hotspot ➔ PC):",
            bg="#0f172a", fg="#38bdf8", font=("Segoe UI", 9, "bold")
        ).pack(side="left")

        steps = [
            "1️⃣  On your iPhone: Open Settings ➔ Personal Hotspot ➔ Turn ON 'Allow Others to Join'.",
            "2️⃣  Enter your iPhone Hotspot SSID & Password above, then flip the toggle switch to ON (or connect via Windows Wi-Fi flyout).",
            "3️⃣  Windows connects directly to your iPhone. Once connected, your AirBeam Portal QR code and direct link appear right here to start ultra-fast transfers!"
        ]
        step_labels = []
        for s in steps:
            lbl = tk.Label(
                self.opt2_action_frame, text=s,
                bg="#0f172a", fg="#94a3b8", font=("Segoe UI", 8), anchor="w", justify="left"
            )
            lbl.pack(fill="x", pady=1)
            step_labels.append(lbl)

        def _adjust_opt2_disc_wrap(e):
            w = max(240, e.width - 24)
            for l in step_labels:
                if l.winfo_exists():
                    l.config(wraplength=w)
        self.opt2_action_frame.bind("<Configure>", _adjust_opt2_disc_wrap)

    def build_opt2_failed_view(self, target_ssid, restored_net):
        for widget in self.opt2_action_frame.winfo_children():
            widget.destroy()

        h_frame = tk.Frame(self.opt2_action_frame, bg="#0f172a")
        h_frame.pack(fill="x", pady=(0, 6))

        tk.Label(
            h_frame, text=f"⚠️ Could Not Connect to '{target_ssid}' — Connection Restored to '{restored_net}'",
            bg="#0f172a", fg="#f59e0b", font=("Segoe UI", 9, "bold")
        ).pack(side="left")

        box = tk.Frame(self.opt2_action_frame, bg="#162032", padx=10, pady=8, highlightthickness=1, highlightbackground="#f59e0b")
        box.pack(fill="x", pady=(0, 4))

        steps = [
            ("1️⃣ Keep iPhone Screen Active:", "Open Settings ➔ Personal Hotspot on iPhone and STAY on that screen. (iOS only accepts connections while this screen is open!)."),
            ("2️⃣ Toggle Personal Hotspot:", "Toggle 'Allow Others to Join' OFF and back ON on your iPhone, then click the switch here again."),
            ("3️⃣ Easiest Way (Windows Taskbar):", f"Click the Wi-Fi icon in your Windows taskbar, click '{target_ssid}', and connect. AirBeam will auto-detect it immediately!"),
            ("💡 Instant Alternative:", f"Use Option 1 at the top of this tab! Both PC and iPhone work instantly over '{restored_net}' with ZERO hotspot setup.")
        ]
        failed_labels = []
        for title, desc in steps:
            r = tk.Frame(box, bg="#162032")
            r.pack(fill="x", pady=2)
            tk.Label(r, text=title, bg="#162032", fg="#38bdf8", font=("Segoe UI", 8, "bold")).pack(anchor="w")
            dl = tk.Label(r, text=desc, bg="#162032", fg="#cbd5e1", font=("Segoe UI", 8), justify="left")
            dl.pack(anchor="w", padx=(14, 0))
            failed_labels.append(dl)

        def _adjust_failed_wrap(e):
            w = max(240, e.width - 36)
            for l in failed_labels:
                if l.winfo_exists():
                    l.config(wraplength=w)
        box.bind("<Configure>", _adjust_failed_wrap)

    def build_opt2_connected_view(self, portal_url, pc_ip, ssid, img_portal):
        for widget in self.opt2_action_frame.winfo_children():
            widget.destroy()

        self.active_opt2_portal_url = portal_url

        # Top row: Left = QR code, Right = Actions & Instructions
        top_row = tk.Frame(self.opt2_action_frame, bg="#0f172a")
        top_row.pack(fill="x", pady=(0, 4))

        # Left Column: Dedicated High-Res QR Code Card
        qr_box = tk.Frame(top_row, bg="#1e293b", padx=10, pady=8, highlightthickness=1, highlightbackground="#38bdf8")
        qr_box.pack(side="left", padx=(0, 12))

        tk.Label(qr_box, text="📲 Scan with iPhone Camera", bg="#1e293b", fg="#10b981", font=("Segoe UI", 9, "bold")).pack(pady=(0, 2))
        self.qr_opt2_label = tk.Label(qr_box, bg="#1e293b")
        self.qr_opt2_label.pack(pady=2)
        if img_portal:
            self.qr_opt2_label.config(image=img_portal)
            self.qr_opt2_label.image = img_portal
        tk.Label(qr_box, text="Tap yellow banner to open Safari", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 8)).pack(pady=(2, 0))

        # Right Column: Live Status & Next Actions
        info_box = tk.Frame(top_row, bg="#0f172a")
        info_box.pack(side="left", fill="both", expand=True)

        tk.Label(
            info_box, text=f"🎉 Connected to '{ssid}' Hotspot!",
            bg="#0f172a", fg="#10b981", font=("Segoe UI", 10, "bold"), anchor="w"
        ).pack(fill="x", pady=(0, 3))

        url_badge = tk.Frame(info_box, bg="#1e293b", padx=8, pady=5, highlightthickness=1, highlightbackground="#0284c7")
        url_badge.pack(fill="x", pady=(0, 6))
        tk.Label(
            url_badge, text=f"🌐 Safari Portal URL: {portal_url}",
            bg="#1e293b", fg="#38bdf8", font=("Segoe UI", 9, "bold"), anchor="w"
        ).pack(side="left")

        # Action Buttons Row (2-column responsive grid)
        btn_act_row = tk.Frame(info_box, bg="#0f172a")
        btn_act_row.pack(fill="x", pady=(0, 6))
        btn_act_row.grid_columnconfigure(0, weight=1)
        btn_act_row.grid_columnconfigure(1, weight=1)

        self.btn_copy_portal_url = tk.Button(
            btn_act_row, text="📋 Copy Portal URL", bg="#334155", fg="#f8fafc",
            font=("Segoe UI", 8, "bold"), relief="flat", bd=0, padx=6, pady=4, cursor="hand2",
            command=self.copy_opt2_portal_url
        )
        self.btn_copy_portal_url.grid(row=0, column=0, sticky="ew", padx=(0, 3), pady=2)

        self.btn_open_portal_pc = tk.Button(
            btn_act_row, text="🌐 Open in PC Browser", bg="#0284c7", fg="#ffffff",
            font=("Segoe UI", 8, "bold"), relief="flat", bd=0, padx=6, pady=4, cursor="hand2",
            command=self.open_opt2_portal_browser
        )
        self.btn_open_portal_pc.grid(row=0, column=1, sticky="ew", padx=(3, 0), pady=2)

        # Numbered 4-Step Checklist: Adaptive text wrapping
        guide_box = tk.Frame(info_box, bg="#162032", padx=8, pady=5, highlightthickness=1, highlightbackground="#334155")
        guide_box.pack(fill="x")

        guide_steps = [
            ("📸 Step 1:", "Open Camera on your iPhone and point it at the QR code, then tap 'Open in Safari'."),
            ("📥 Step 2 (PC ➔ iPhone):", "Click '+ Add Files for iPhone' below on PC; they appear in Safari to Download."),
            ("📤 Step 3 (iPhone ➔ PC):", "In Safari on iPhone, tap 'Upload Photos/Files' — they stream to 'Received_From_iPhone/'!"),
            ("📋 Step 4 (Clipboard):", "Sync copied text or links between devices with one tap using clipboard buttons.")
        ]
        opt2_desc_labels = []
        for tag, desc in guide_steps:
            row = tk.Frame(guide_box, bg="#162032")
            row.pack(fill="x", pady=1)
            tk.Label(row, text=tag, bg="#162032", fg="#38bdf8", font=("Segoe UI", 8, "bold")).pack(side="left", anchor="n")
            dl = tk.Label(row, text=" " + desc, bg="#162032", fg="#cbd5e1", font=("Segoe UI", 8), justify="left", anchor="w")
            dl.pack(side="left", fill="x", expand=True)
            opt2_desc_labels.append(dl)

        def _adjust_opt2_conn_wrap(e):
            w = max(180, e.width - 70)
            for l in opt2_desc_labels:
                if l.winfo_exists():
                    l.config(wraplength=w)
        guide_box.bind("<Configure>", _adjust_opt2_conn_wrap)

    def build_opt3_view(self):
        for widget in self.opt3_action_frame.winfo_children():
            widget.destroy()

        ip = get_local_ip()
        portal_url = f"http://{ip}:{self.iphone_portal_port}/index.html"
        self.active_opt3_portal_url = portal_url
        img_portal = self.generate_qr_image(portal_url, box_size=4, border=2)
        cur_wifi = get_current_wifi_profile() or get_best_home_wifi_profile(self) or "Home Wi-Fi"

        top_row = tk.Frame(self.opt3_action_frame, bg="#0f172a")
        top_row.pack(fill="x", pady=(0, 4))

        # Left Column: Dedicated High-Res QR Code Card
        qr_box = tk.Frame(top_row, bg="#1e293b", padx=10, pady=8, highlightthickness=1, highlightbackground="#10b981")
        qr_box.pack(side="left", padx=(0, 12))

        tk.Label(qr_box, text="📲 Scan with iPhone Camera", bg="#1e293b", fg="#10b981", font=("Segoe UI", 9, "bold")).pack(pady=(0, 2))
        self.qr_opt3_label = tk.Label(qr_box, bg="#1e293b")
        self.qr_opt3_label.pack(pady=2)
        if img_portal:
            self.qr_opt3_label.config(image=img_portal)
            self.qr_opt3_label.image = img_portal
        tk.Label(qr_box, text="Tap yellow banner to open Safari", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 8)).pack(pady=(2, 0))

        # Right Column: Live Status & Actions
        info_box = tk.Frame(top_row, bg="#0f172a")
        info_box.pack(side="left", fill="both", expand=True)

        status_txt = f"✅ Active on Wi-Fi: {cur_wifi}  •  PC IP: {ip}"
        self.lbl_opt3_status = tk.Label(
            info_box, text=status_txt,
            bg="#0f172a", fg="#10b981", font=("Segoe UI", 10, "bold"), anchor="w"
        )
        self.lbl_opt3_status.pack(fill="x", pady=(0, 4))

        url_badge = tk.Frame(info_box, bg="#1e293b", padx=8, pady=5, highlightthickness=1, highlightbackground="#0284c7")
        url_badge.pack(fill="x", pady=(0, 6))
        self.lbl_opt3_url = tk.Label(
            url_badge, text=f"🌐 Safari Portal URL: {portal_url}",
            bg="#1e293b", fg="#38bdf8", font=("Segoe UI", 9, "bold"), anchor="w"
        )
        self.lbl_opt3_url.pack(side="left")

        # Action Buttons Row (2x2 responsive grid)
        btn_row = tk.Frame(info_box, bg="#0f172a")
        btn_row.pack(fill="x", pady=(0, 6))
        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=1)

        self.btn_copy_opt3_url = tk.Button(
            btn_row, text="📋 Copy Portal URL", bg="#334155", fg="#f8fafc",
            font=("Segoe UI", 8, "bold"), relief="flat", bd=0, padx=6, pady=4, cursor="hand2",
            command=self.copy_opt3_portal_url
        )
        self.btn_copy_opt3_url.grid(row=0, column=0, sticky="ew", padx=(0, 3), pady=2)

        self.btn_open_opt3_pc = tk.Button(
            btn_row, text="🌐 Open in PC Browser", bg="#0284c7", fg="#ffffff",
            font=("Segoe UI", 8, "bold"), relief="flat", bd=0, padx=6, pady=4, cursor="hand2",
            command=self.open_opt3_portal_browser
        )
        self.btn_open_opt3_pc.grid(row=0, column=1, sticky="ew", padx=(3, 0), pady=2)

        self.btn_ref_opt3 = tk.Button(
            btn_row, text="🔄 Refresh IP / QR", bg="#1e293b", fg="#38bdf8",
            font=("Segoe UI", 8, "bold"), relief="flat", bd=0, padx=6, pady=4, cursor="hand2",
            highlightthickness=1, highlightbackground="#38bdf8",
            command=self.refresh_opt3_home_portal
        )
        self.btn_ref_opt3.grid(row=1, column=0, sticky="ew", padx=(0, 3), pady=2)

        self.btn_fix_firewall = tk.Button(
            btn_row, text="🛡️ Fix Firewall", bg="#7f1d1d", fg="#fca5a5",
            font=("Segoe UI", 8, "bold"), relief="flat", bd=0, padx=6, pady=4, cursor="hand2",
            command=self.launch_firewall_fix
        )
        self.btn_fix_firewall.grid(row=1, column=1, sticky="ew", padx=(3, 0), pady=2)

        # 3-Step Guide with Adaptive Text Wrapping
        guide_box = tk.Frame(info_box, bg="#162032", padx=8, pady=5, highlightthickness=1, highlightbackground="#334155")
        guide_box.pack(fill="x")

        guide_steps = [
            ("📸 Step 1:", f"Ensure iPhone is on '{cur_wifi}'. Scan QR code with Camera → Tap yellow banner."),
            ("📥 Step 2 (PC ➔ iPhone):", "Click '+ Add Files for iPhone' below on PC; they appear instantly in Safari!"),
            ("📤 Step 3 (iPhone ➔ PC):", "In Safari on iPhone, tap 'Upload Photos/Files' — saves to 'Received_From_iPhone/'!"),
            ("🛡️ Tip:", "If Safari says 'Can't reach site', click '🛡️ Fix Firewall' above (runs once as Admin).")
        ]
        desc_labels = []
        for tag, desc in guide_steps:
            row = tk.Frame(guide_box, bg="#162032")
            row.pack(fill="x", pady=1)
            tk.Label(row, text=tag, bg="#162032", fg="#38bdf8", font=("Segoe UI", 8, "bold")).pack(side="left", anchor="n")
            dl = tk.Label(row, text=" " + desc, bg="#162032", fg="#cbd5e1", font=("Segoe UI", 8), justify="left", anchor="w")
            dl.pack(side="left", fill="x", expand=True)
            desc_labels.append(dl)

        def _adjust_opt3_wrap(e):
            w = max(180, e.width - 70)
            for l in desc_labels:
                if l.winfo_exists():
                    l.config(wraplength=w)
        guide_box.bind("<Configure>", _adjust_opt3_wrap)

    def copy_opt3_portal_url(self):
        if getattr(self, "active_opt3_portal_url", None):
            self.clipboard_clear()
            self.clipboard_append(self.active_opt3_portal_url)
            if hasattr(self, "btn_copy_opt3_url"):
                self.btn_copy_opt3_url.config(text="Copied! ✅", fg="#10b981")
                self.after(2000, lambda: self.btn_copy_opt3_url.config(text="📋 Copy Portal URL", fg="#f8fafc"))

    def open_opt3_portal_browser(self):
        url = getattr(self, "active_opt3_portal_url", None) or f"http://127.0.0.1:{self.iphone_portal_port}/index.html"
        try:
            webbrowser.open(url)
        except Exception:
            pass

    def refresh_opt3_home_portal(self):
        self.local_ip = get_local_ip()
        self.build_opt3_view()
        if hasattr(self, "btn_ref_opt3"):
            self.btn_ref_opt3.config(text="Updated! ✅", fg="#10b981")
            self.after(2000, lambda: self.btn_ref_opt3.config(text="🔄 Refresh IP / QR", fg="#38bdf8"))

    def launch_firewall_fix(self):
        bat_candidates = [
            os.path.join(APP_ROOT, "Fix-AirBeam-Firewall.bat"),
            os.path.join(BUNDLE_DIR, "Fix-AirBeam-Firewall.bat"),
            os.path.join(os.path.dirname(APP_ROOT), "Fix-AirBeam-Firewall.bat"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Fix-AirBeam-Firewall.bat")),
        ]
        bat = next((b for b in bat_candidates if os.path.exists(b)), None)
        if os.path.exists(bat):
            try:
                import ctypes
                ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", bat, None, None, 1)
                if ret <= 32:
                    subprocess.Popen([bat], shell=True)
            except Exception:
                try:
                    subprocess.Popen([bat], shell=True)
                except Exception as e:
                    messagebox.showerror("Firewall Error", f"Failed to run Fix-AirBeam-Firewall.bat: {e}")
        else:
            messagebox.showinfo("Firewall", "Please run Fix-AirBeam-Firewall.bat in your AirBeam v5.0 folder.")

    def toggle_connect_to_iphone_hotspot(self, target_state):
        if target_state:
            ssid = self.entry_iphone_ssid.get().strip()
            pwd = self.entry_iphone_pwd.get().strip()
            if not ssid:
                messagebox.showerror("Error", "Please enter your iPhone Personal Hotspot SSID name!")
                self.ios_connect_hotspot_switch.set_state(False, trigger_callback=False)
                return

            self.iphone_hotspot_ssid = ssid
            self.iphone_hotspot_password = pwd
            self.save_iphone_hotspot_config()

            self.lbl_ios_connect_hotspot_state.config(text=f"Connecting to '{ssid}'...", fg="#f59e0b")

            def connect_worker():
                # 1. Capture current home Wi-Fi profile before disconnecting
                home_profile = get_best_home_wifi_profile(self)
                cur = get_current_wifi_profile()
                if cur and not is_hotspot_profile_name(cur):
                    home_profile = cur
                    self.previous_wifi_ssid = cur
                    save_last_home_wifi(cur)

                # 2. Check if a profile already exists in Windows for this iPhone
                matched_profile = find_matching_saved_wifi_profile(ssid)
                if not matched_profile:
                    hex_ssid = "".join(f"{ord(c):02X}" for c in ssid)
                    xml_content = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig>
        <SSID>
            <hex>{hex_ssid}</hex>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>manual</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{pwd}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>"""
                    tmp_path = os.path.join(APP_ROOT, f"_tmp_prof_{int(time.time())}.xml")
                    try:
                        with open(tmp_path, "w", encoding="utf-8") as f:
                            f.write(xml_content)
                        subprocess.run(["netsh", "wlan", "add", "profile", f"filename={tmp_path}", "user=current"], capture_output=True)
                    finally:
                        if os.path.exists(tmp_path):
                            try: os.remove(tmp_path)
                            except: pass
                    matched_profile = ssid

                # 3. Temporarily set home Wi-Fi to manual so Windows doesn't abort early to it
                if home_profile:
                    try:
                        subprocess.run(["netsh", "wlan", "set", "profileparameter", f"name={home_profile}", "connectionmode=manual"], capture_output=True, timeout=2)
                    except Exception:
                        pass

                # 4. Disconnect current Wi-Fi and allow Intel settling pause
                native_wlan_disconnect()
                time.sleep(1.5)

                # 5. Connect natively using wlanapi.dll and netsh
                ok, ret_code = native_wlan_connect(matched_profile)
                try:
                    subprocess.run(["netsh", "wlan", "connect", f"name={matched_profile}"], capture_output=True, timeout=2)
                except Exception:
                    pass

                # 6. Poll for connection & verify STRICTLY that Windows is connected to iPhone
                connected_ok = False
                pc_ip = None
                for _ in range(12):
                    time.sleep(1.0)
                    cur_net = get_current_wifi_profile()
                    telem = parse_wifi_telemetry()
                    cur_ssid = telem.get("ssid", "") or cur_net or ""

                    is_on_iphone = bool(
                        cur_ssid and (
                            cur_ssid.strip().lower() == matched_profile.lower() or
                            "iphone" in cur_ssid.strip().lower() or
                            (ssid and cur_ssid.strip().lower() == ssid.lower())
                        )
                    )

                    ip_cand = get_local_ip()
                    if is_on_iphone and ip_cand and not ip_cand.startswith("127.") and not ip_cand.startswith("169.254."):
                        pc_ip = ip_cand
                        connected_ok = True
                        break

                if connected_ok and pc_ip:
                    self.connected_to_iphone_hotspot = True
                    portal_url = f"http://{pc_ip}:{self.iphone_portal_port}/index.html"
                    img_portal = self.generate_qr_image(portal_url, box_size=4, border=2)

                    def update_conn_ui():
                        self.lbl_ios_connect_hotspot_state.config(text=f"ON — Connected to '{matched_profile}' at {pc_ip}", fg="#10b981")
                        self.build_opt2_connected_view(portal_url, pc_ip, matched_profile, img_portal)
                    self.after(0, update_conn_ui)
                else:
                    self.connected_to_iphone_hotspot = False
                    # Restore home Wi-Fi auto-connect and reconnect
                    if home_profile:
                        try:
                            subprocess.run(["netsh", "wlan", "set", "profileparameter", f"name={home_profile}", "connectionmode=auto"], capture_output=True, timeout=2)
                            for _ in range(4):
                                native_wlan_connect(home_profile)
                                time.sleep(1.0)
                                if get_current_wifi_profile() == home_profile:
                                    break
                        except Exception:
                            pass

                    def update_fail_ui():
                        self.ios_connect_hotspot_switch.set_state(False, trigger_callback=False)
                        restored = get_current_wifi_profile() or home_profile or "Home Wi-Fi"
                        self.lbl_ios_connect_hotspot_state.config(
                            text=f"Timed out. PC reconnected to '{restored}'.", fg="#ef4444"
                        )
                        self.build_opt2_failed_view(matched_profile, restored)
                    self.after(0, update_fail_ui)

            threading.Thread(target=connect_worker, daemon=True).start()
        else:
            self.lbl_ios_connect_hotspot_state.config(text="Disconnecting and restoring home Wi-Fi...", fg="#f59e0b")
            def disconnect_worker():
                self.connected_to_iphone_hotspot = False
                native_wlan_disconnect()
                time.sleep(1.5)

                home_profile = get_best_home_wifi_profile(self)
                if home_profile:
                    try:
                        subprocess.run(["netsh", "wlan", "set", "profileparameter", f"name={home_profile}", "connectionmode=auto"], capture_output=True, timeout=2)
                    except Exception:
                        pass
                    for _ in range(4):
                        native_wlan_connect(home_profile)
                        time.sleep(1.5)
                        cur = get_current_wifi_profile()
                        if cur and cur.lower() == home_profile.lower():
                            break

                def on_disc_ui():
                    restored = get_current_wifi_profile() or home_profile or "Home Wi-Fi"
                    self.lbl_ios_connect_hotspot_state.config(text=f"OFF — Reconnected to {restored}", fg="#94a3b8")
                    self.build_opt2_disconnected_view()
                self.after(0, on_disc_ui)
            threading.Thread(target=disconnect_worker, daemon=True).start()

    def load_iphone_hotspot_config(self):
        if os.path.exists(IPHONE_CONFIG_FILE):
            try:
                with open(IPHONE_CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.iphone_hotspot_ssid = data.get("ssid", "iPhone")
                    self.iphone_hotspot_password = data.get("password", "")
            except Exception:
                pass

    def save_iphone_hotspot_config(self):
        try:
            with open(IPHONE_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"ssid": self.iphone_hotspot_ssid, "password": self.iphone_hotspot_password}, f, indent=2)
        except Exception:
            pass

    def open_iphone_received_folder(self):
        os.makedirs(self.iphone_received_dir, exist_ok=True)
        try:
            os.startfile(self.iphone_received_dir)
        except Exception:
            subprocess.Popen(["explorer.exe", self.iphone_received_dir])

    def clear_ios_staged_files(self):
        if getattr(self, "is_sending", False):
            return
        count = len(getattr(self, "selected_files", []))
        if count == 0:
            messagebox.showinfo("No Files", "There are no staged files for iPhone to clear.")
            return
        self.selected_files.clear()
        self.refresh_file_list()
        self.update_ios_files_summary()
        messagebox.showinfo("Files Cleared", f"Cleared {count} staged file(s). iPhone Safari will now show 0 files.")

    def clear_iphone_received_folder(self):
        os.makedirs(self.iphone_received_dir, exist_ok=True)
        try:
            items = os.listdir(self.iphone_received_dir)
        except Exception:
            items = []

        if not items:
            messagebox.showinfo("Folder Empty", "The 'Received_From_iPhone' folder is already empty! No uploaded files to clear.")
            return

        total_bytes = 0
        file_paths = []
        for name in items:
            fp = os.path.join(self.iphone_received_dir, name)
            if os.path.isfile(fp):
                total_bytes += os.path.getsize(fp)
                file_paths.append(fp)
            elif os.path.isdir(fp):
                file_paths.append(fp)

        ans = messagebox.askyesno(
            "Clear Uploaded Files",
            f"Are you sure you want to permanently delete all {len(file_paths)} uploaded file(s) ({format_bytes(total_bytes)}) in 'Received_From_iPhone'?"
        )
        if not ans:
            return

        deleted = 0
        for fp in file_paths:
            try:
                if os.path.isfile(fp):
                    os.remove(fp)
                    deleted += 1
                elif os.path.isdir(fp):
                    shutil.rmtree(fp, ignore_errors=True)
                    deleted += 1
            except Exception:
                pass

        self.update_ios_files_summary()
        messagebox.showinfo("Files Deleted", f"Successfully cleared {deleted} uploaded file(s) from 'Received_From_iPhone'.")

    def update_ios_files_summary(self):
        if not hasattr(self, "lbl_ios_files_summary"):
            return
        staged_count = len(getattr(self, "selected_files", []))
        staged_bytes = sum(os.path.getsize(f) for f in self.selected_files if os.path.isfile(f))

        recv_count = 0
        recv_bytes = 0
        try:
            if os.path.exists(self.iphone_received_dir):
                for name in os.listdir(self.iphone_received_dir):
                    fp = os.path.join(self.iphone_received_dir, name)
                    if os.path.isfile(fp):
                        recv_count += 1
                        recv_bytes += os.path.getsize(fp)
        except Exception:
            pass

        text = f"📤 Staged for iPhone: {staged_count} file(s) ({format_bytes(staged_bytes)})  •  📥 Received from iPhone: {recv_count} file(s) ({format_bytes(recv_bytes)})"
        self.lbl_ios_files_summary.config(text=text)

    def beam_clipboard_to_ios(self):
        txt = self.get_clipboard_safe()
        if not txt or not txt.strip():
            messagebox.showinfo("Clipboard Empty", "Your Windows clipboard is empty. Copy text or a link first!")
            return
        messagebox.showinfo("Clipboard Ready", f"Windows Clipboard is now live in the iOS Web Portal!\n\nContent:\n{txt[:120]}...\n\nOpen Safari on your iPhone to copy or open the link.")

    def reset_ios_qr_placeholders(self):
        portal_url = f"http://{self.local_ip}:{self.iphone_portal_port}/index.html"
        dummy_wifi = self.generate_qr_image("WIFI:T:WPA;S:AirBeamHotspot;P:airbeam123;;", box_size=4, border=2)
        dummy_portal = self.generate_qr_image(portal_url, box_size=4, border=2)
        if dummy_wifi:
            self.qr_ios_wifi_label.config(image=dummy_wifi)
            self.qr_ios_wifi_label.image = dummy_wifi
        if dummy_portal:
            self.qr_ios_portal_label.config(image=dummy_portal)
            self.qr_ios_portal_label.image = dummy_portal

    def refresh_ios_qr_codes(self):
        ip = get_local_ip()
        portal_url = f"http://{ip}:{self.iphone_portal_port}/index.html"
        img = self.generate_qr_image(portal_url, box_size=4, border=2)
        if img:
            self.qr_ios_portal_label.config(image=img)
            self.qr_ios_portal_label.image = img
            self.lbl_ios_win_hotspot_creds.config(text=f"Direct Portal URL: {portal_url}")
        messagebox.showinfo("Portal Refreshed", f"iOS Portal QR Code refreshed for IP: {ip}\nURL: {portal_url}")

    def get_clipboard_safe(self):
        try:
            return self.clipboard_get()
        except Exception:
            return ""

    def set_clipboard_safe(self, text):
        try:
            self.after(0, lambda: (self.clipboard_clear(), self.clipboard_append(text)))
        except Exception:
            pass

    def record_ios_stream_bytes(self, num_bytes, is_upload=False):
        now = time.time()
        self.ios_bytes_in_window += num_bytes
        dt = now - self.last_ios_sample_time
        if dt >= 0.5:
            cur_speed = self.ios_bytes_in_window / dt
            self.ios_bytes_in_window = 0
            self.last_ios_sample_time = now
            if self.ios_ema_speed <= 0.0:
                self.ios_ema_speed = cur_speed
            else:
                self.ios_ema_speed = 0.3 * cur_speed + 0.7 * self.ios_ema_speed

            spd_mb = self.ios_ema_speed / (1024 * 1024)
            spd_mbps = (self.ios_ema_speed * 8) / (1000 * 1000)
            tag = "⬆️ Uploading from iPhone" if is_upload else "⬇️ Downloading to iPhone"
            spd_text = f"⚡ {tag}: {spd_mb:.1f} MB/s ({spd_mbps:.0f} Mbps)"
            if hasattr(self, "lbl_ios_live_speed"):
                self.after(0, lambda: self.lbl_ios_live_speed.config(text=spd_text))

    def add_files(self):
        files = filedialog.askopenfilenames(title="Select files to beam")
        if files:
            for f in files:
                if f not in self.selected_files:
                    self.selected_files.append(f)
            self.refresh_file_list()

    def add_folder(self):
        folder = filedialog.askdirectory(title="Select folder to beam")
        if folder:
            for root, _, files in os.walk(folder):
                for f in files:
                    full = os.path.join(root, f)
                    if full not in self.selected_files:
                        self.selected_files.append(full)
            self.refresh_file_list()

    def clear_files(self):
        if self.is_sending: return
        self.selected_files.clear()
        self.refresh_file_list()

    def refresh_file_list(self):
        if hasattr(self, "listbox_files") and self.listbox_files.winfo_exists():
            self.listbox_files.delete(0, tk.END)
        if hasattr(self, "listbox_ios_files") and self.listbox_ios_files.winfo_exists():
            self.listbox_ios_files.delete(0, tk.END)

        total_bytes = 0
        for f in self.selected_files:
            try:
                size = os.path.getsize(f)
                total_bytes += size
                item_str = f"{os.path.basename(f)}  ({format_bytes(size)})"
            except Exception:
                item_str = os.path.basename(f)

            if hasattr(self, "listbox_files") and self.listbox_files.winfo_exists():
                self.listbox_files.insert(tk.END, item_str)
            if hasattr(self, "listbox_ios_files") and self.listbox_ios_files.winfo_exists():
                self.listbox_ios_files.insert(tk.END, item_str)

        count = len(self.selected_files)
        size_str = format_bytes(total_bytes)
        status_txt = f"{count} files selected ({size_str}) — Drag & drop files anywhere in window or click '+ Add Files' above"

        if hasattr(self, "lbl_total_size") and self.lbl_total_size.winfo_exists():
            self.lbl_total_size.config(text=status_txt)
        if hasattr(self, "lbl_ios_total_size") and self.lbl_ios_total_size.winfo_exists():
            self.lbl_ios_total_size.config(text=status_txt)

        self.update_ios_files_summary()

    # --- Discovery & Hotspot Handover Coordinator ---
    def start_discovery_coordinator(self):
        def coordinator_loop():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except Exception:
                pass
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(1.5)
            try:
                sock.bind(("", UDP_PORT))
            except Exception as e:
                print(f"UDP discovery coordinator socket bind warning: {e}")

            while getattr(self, "_is_alive", True):
                now = time.time()
                # 1. Fallback / Resend timers (ONLY in LAPTOP_HOTSPOT mode!)
                try:
                    mode = self.connection_mode.get()
                except Exception:
                    break
                if not self.is_sending and mode == "LAPTOP_HOTSPOT":
                    if self.hotspot_state == "WAITING_5GHZ" and (now - self.handover_sent_time) >= 10.0:
                        print("5 GHz handover timed out (10s) with no connection. Auto-falling back to 2.4 GHz hotspot...")
                        self.after(0, self.switch_to_24ghz_hotspot)
                    elif self.hotspot_state == "WAITING_24GHZ" and (now - self.handover_sent_time) >= 8.0:
                        self.handover_sent_time = now
                        target_ip = self.tablet_router_ip or self.entry_ip.get().strip()
                        if self.hotspot_info and target_ip and not target_ip.startswith("Searching") and not target_ip.startswith("192.168.137.") and not target_ip.startswith("192.168.43."):
                            ssid = str(self.hotspot_info["ssid"]).strip()
                            passphrase = str(self.hotspot_info["passphrase"]).strip()
                            host_ip = str(self.hotspot_info.get("host_ip", "192.168.137.1")).strip()
                            re_msg = f"AIRBEAM_HOTSPOT_HANDOVER|{ssid}|{passphrase}|{host_ip}|2.4GHz".encode("utf-8")
                            try:
                                sock.sendto(re_msg, (target_ip, UDP_PORT))
                            except Exception:
                                pass

                # 2. Broadcast discovery across all subnets
                try:
                    sock.sendto(b"AIRBEAM_DISCOVER", ("255.255.255.255", UDP_PORT))
                    sock.sendto(b"AIRBEAM_DISCOVER", ("192.168.43.1", UDP_PORT))
                    sock.sendto(b"AIRBEAM_DISCOVER", ("192.168.43.255", UDP_PORT))
                    sock.sendto(b"AIRBEAM_DISCOVER", ("192.168.137.255", UDP_PORT))
                    if self.local_ip and "." in self.local_ip:
                        subnet_bcast = self.local_ip.rsplit(".", 1)[0] + ".255"
                        sock.sendto(b"AIRBEAM_DISCOVER", (subnet_bcast, UDP_PORT))

                    # Direct unicast probe to candidates if available
                    for target_candidate in (self.tablet_router_ip, self.entry_ip.get().strip()):
                        if target_candidate and not target_candidate.startswith("Searching") and not target_candidate.startswith("192.168.137.") and not target_candidate.startswith("192.168.43."):
                            try:
                                sock.sendto(b"AIRBEAM_DISCOVER", (target_candidate, UDP_PORT))
                            except Exception:
                                pass

                    # Broadcast PC-to-PC discovery announcement
                    pc_ping = f"AIRBEAM_PC_PING|{self.session_node_id}|{socket.gethostname()}|{self.local_ip}".encode("utf-8")
                    sock.sendto(pc_ping, ("255.255.255.255", UDP_PORT))
                    sock.sendto(pc_ping, ("192.168.137.255", UDP_PORT))
                    if self.local_ip and "." in self.local_ip:
                        sock.sendto(pc_ping, (subnet_bcast, UDP_PORT))
                except Exception:
                    pass

                # 3. Receive incoming UDP packets
                try:
                    data, addr = sock.recvfrom(2048)
                    text = data.decode("utf-8", errors="ignore").strip()

                    all_local = get_all_local_ips()
                    all_local.add(self.local_ip)

                    if text.startswith("AIRBEAM_PC_PING"):
                        parts = text.split("|")
                        if len(parts) > 2 and len(parts[1]) == 8:
                            node_id = parts[1]
                            peer_name = parts[2]
                        else:
                            node_id = None
                            peer_name = parts[1] if len(parts) > 1 else "AirBeam PC"
                        peer_ip = addr[0]

                        if node_id != self.session_node_id and peer_ip not in all_local and not peer_ip.startswith("127."):
                            self.discovered_pcs[peer_ip] = {"hostname": peer_name, "ip": peer_ip, "time": time.time()}
                            pong = f"AIRBEAM_PC_PONG|{self.session_node_id}|{socket.gethostname()}|{self.local_ip}".encode("utf-8")
                            try:
                                sock.sendto(pong, (peer_ip, UDP_PORT))
                            except Exception:
                                pass
                            self.after(0, self.update_discovered_pcs_ui)

                    elif text.startswith("AIRBEAM_PC_PONG") or text.startswith("AIRBEAM_PC_ACK"):
                        parts = text.split("|")
                        if len(parts) > 2 and len(parts[1]) == 8:
                            node_id = parts[1]
                            peer_name = parts[2]
                        else:
                            node_id = None
                            peer_name = parts[1] if len(parts) > 1 else "AirBeam PC"
                        peer_ip = addr[0]

                        if node_id != self.session_node_id and peer_ip not in all_local and not peer_ip.startswith("127."):
                            self.discovered_pcs[peer_ip] = {"hostname": peer_name, "ip": peer_ip, "time": time.time()}
                            self.after(0, self.update_discovered_pcs_ui)

                    elif text.startswith("AIRBEAM_ACK"):
                        parts = text.split("|")
                        model = parts[1] if len(parts) > 1 else "Android Tablet"
                        tablet_ip = addr[0]

                        if tablet_ip.startswith("192.168.43."):
                            self.after(0, lambda m=model, ip=tablet_ip: self.on_tablet_hotspot_ready(m, ip))
                        elif tablet_ip.startswith("192.168.137."):
                            self.after(0, lambda m=model, ip=tablet_ip: self.on_hotspot_ready(m, ip))
                        else:
                            self.tablet_router_ip = tablet_ip
                            self.after(0, lambda m=model, ip=tablet_ip: self.on_router_discovered(m, ip))

                    elif text.startswith("AIRBEAM_HOTSPOT_READY"):
                        parts = text.split("|")
                        model = parts[1] if len(parts) > 1 else "Android Tablet"
                        tablet_ip = addr[0]
                        if tablet_ip.startswith("192.168.43."):
                            self.after(0, lambda m=model, ip=tablet_ip: self.on_tablet_hotspot_ready(m, ip))
                        else:
                            self.after(0, lambda m=model, ip=tablet_ip: self.on_hotspot_ready(m, ip))

                    elif text.startswith("AIRBEAM_NEED_24GHZ"):
                        if self.connection_mode.get() == "LAPTOP_HOTSPOT":
                            parts = text.split("|")
                            model = parts[1] if len(parts) > 1 else "Android Tablet"
                            print(f"Received AIRBEAM_NEED_24GHZ from {model} ({addr[0]}). Switching hotspot to 2.4 GHz...")
                            self.after(0, self.switch_to_24ghz_hotspot)

                except socket.timeout:
                    pass
                except Exception:
                    pass

                # 4. Check for connected hotspot tablet on 192.168.43.1 or 192.168.137.*
                if not self.is_sending:
                    try:
                        hip = find_hotspot_device_ip()
                        if hip:
                            current_val = self.entry_ip.get().strip()
                            if current_val != hip or self.hotspot_state != "CONNECTED":
                                if hip == "192.168.43.1":
                                    self.after(0, lambda ip=hip: self.on_tablet_hotspot_ready("samsung SM-T505N", ip))
                                else:
                                    self.after(0, lambda ip=hip: self.on_hotspot_ready("samsung SM-T505N", ip))
                    except Exception:
                        pass

                time.sleep(1.0)

        threading.Thread(target=coordinator_loop, daemon=True).start()

    def on_router_discovered(self, model, ip):
        mode = self.connection_mode.get()
        if mode == "WIFI_ROUTER":
            self.entry_ip.delete(0, tk.END)
            self.entry_ip.insert(0, ip)
            self.lbl_device_status.config(
                text=f"🏠 Home Wi-Fi: Found {model} ({ip}). Ready to beam!",
                style="StatusSuccess.TLabel"
            )
        elif mode == "LAPTOP_HOTSPOT":
            current = self.entry_ip.get().strip()
            if not current.startswith("192.168.137.") and not current.startswith("192.168.43."):
                self.entry_ip.delete(0, tk.END)
                self.entry_ip.insert(0, ip)
                if self.hotspot_state == "IDLE":
                    self.lbl_device_status.config(
                        text=f"Found: {model} on router ({ip}). Upgrading to Laptop Hotspot...",
                        style="StatusPending.TLabel"
                    )
            if not self.is_sending and self.hotspot_state == "IDLE":
                self.tablet_router_ip = ip
                self.negotiate_hotspot_bypass(preferred_band="5GHz")
        elif mode == "TABLET_HOTSPOT":
            # Tablet is on router, but user chose Tablet Hotspot! Do NOT start laptop hotspot!
            current = self.entry_ip.get().strip()
            if not current or current.startswith("Searching"):
                self.entry_ip.delete(0, tk.END)
                self.entry_ip.insert(0, "10.150.131.50")
            if self.hotspot_state != "CONNECTED":
                self.lbl_device_status.config(
                    text=f"📱 Found {model} on router. To use 5 GHz Hotspot: Turn ON Hotspot on tablet & connect PC Wi-Fi to it.",
                    style="StatusPending.TLabel"
                )

    def trigger_hotspot_handover(self, preferred_band=None):
        self.hotspot_state = "IDLE"
        band = preferred_band or "5GHz"
        self.negotiate_hotspot_bypass(preferred_band=band)

    def switch_to_24ghz_hotspot(self):
        if self.hotspot_state in ("SWITCHING_24GHZ", "WAITING_24GHZ", "CONNECTED") or self.is_sending:
            return
        self.hotspot_state = "SWITCHING_24GHZ"
        self.lbl_device_status.config(
            text="Switched to 2.4 GHz direct hotspot (5 GHz not visible on tablet). Connecting...",
            style="StatusPending.TLabel"
        )
        self.negotiate_hotspot_bypass(preferred_band="2.4GHz")

    def negotiate_hotspot_bypass(self, preferred_band="5GHz"):
        if self.connection_mode.get() != "LAPTOP_HOTSPOT":
            return
        if self.is_sending or self.hotspot_state == "CONNECTED":
            return

        def worker():
            with self.hotspot_lock:
                if self.is_negotiating:
                    return
                self.is_negotiating = True

            try:
                target_ip = self.tablet_router_ip or self.entry_ip.get().strip()
                if not target_ip or target_ip.startswith("Searching"):
                    return

                band_str = "5 GHz" if preferred_band == "5GHz" else "2.4 GHz"
                self.after(0, lambda: self.lbl_device_status.config(
                    text=f"Starting Windows {band_str} Mobile Hotspot...", style="StatusPending.TLabel"
                ))

                info = WindowsHotspotController.ensure_hotspot_active(preferred_band=preferred_band)
                if not info or not info.get("enabled"):
                    self.after(0, lambda: self.lbl_device_status.config(
                        text="Hotspot couldn't start automatically. Using standard Wi-Fi.", style="StatusPending.TLabel"
                    ))
                    self.hotspot_state = "IDLE"
                    return

                self.hotspot_info = info
                ssid = str(info["ssid"]).strip()
                passphrase = str(info["passphrase"]).strip()
                host_ip = str(info.get("host_ip", "192.168.137.1")).strip()

                self.current_handover_band = preferred_band
                self.handover_sent_time = time.time()
                self.hotspot_state = "WAITING_5GHZ" if preferred_band == "5GHz" else "WAITING_24GHZ"

                status_msg = (
                    f"Hotspot active ({ssid}). Sending 5 GHz handover to tablet..."
                    if preferred_band == "5GHz"
                    else "Switched to 2.4 GHz direct hotspot (5 GHz not visible on tablet). Connecting..."
                )
                self.after(0, lambda m=status_msg: self.lbl_device_status.config(
                    text=m, style="StatusHotspot.TLabel"
                ))

                # Send AIRBEAM_HOTSPOT_HANDOVER|<ssid>|<passphrase>|<host_ip>|<preferred_band>
                handover_msg = f"AIRBEAM_HOTSPOT_HANDOVER|{ssid}|{passphrase}|{host_ip}|{preferred_band}".encode("utf-8")
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.sendto(handover_msg, (target_ip, UDP_PORT))
                    s.close()
                except Exception as e:
                    print(f"Error sending handover packet: {e}")

            finally:
                with self.hotspot_lock:
                    self.is_negotiating = False

        threading.Thread(target=worker, daemon=True).start()

    def on_hotspot_ready(self, model, ip):
        if ip.startswith("192.168.43."):
            self.on_tablet_hotspot_ready(model, ip)
            return
        self.hotspot_state = "CONNECTED"
        self.entry_ip.delete(0, tk.END)
        self.entry_ip.insert(0, ip)
        band_disp = self.current_handover_band or "Direct"
        self.lbl_device_status.config(
            text=f"🚀 {band_disp} Laptop Hotspot: {model} ({ip}) — Connected!",
            style="StatusHotspot.TLabel"
        )

    def ping_target(self):
        target = self.entry_ip.get().strip()
        mode = self.connection_mode.get()

        def worker():
            # Check current target first if specified
            if target and not target.startswith("Searching"):
                try:
                    t0 = time.time()
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(1.2)
                    s.connect((target, NIO_PORT))
                    s.close()
                    rtt = (time.time() - t0) * 1000
                    if target.startswith("192.168.43."):
                        self.after(0, lambda: self.on_tablet_hotspot_ready("samsung SM-T505N", target))
                    elif target.startswith("192.168.137."):
                        self.after(0, lambda: self.on_hotspot_ready("samsung SM-T505N", target))
                    else:
                        self.after(0, lambda: self.lbl_device_status.config(
                            text=f"Connected to {target} (Home Wi-Fi, {rtt:.1f}ms) — Ready!",
                            style="StatusSuccess.TLabel"
                        ))
                    self.after(0, lambda: messagebox.showinfo("Success", f"Connected to {target}:7777!\nPing: {rtt:.1f} ms\nHigh-speed transfer ready!"))
                    return
                except Exception:
                    pass

            if mode == "TABLET_HOTSPOT":
                self.after(0, lambda: messagebox.showerror(
                    "Tablet Hotspot Not Reachable",
                    f"Could not connect to {target or '10.150.131.50'}:7777.\n\n"
                    "Please check:\n"
                    "1. Is Mobile Hotspot turned ON on your Samsung tablet (5 GHz preferred)?\n"
                    "2. Is your PC Wi-Fi connected to your tablet's hotspot network?\n"
                    "3. Is the AirBeam Receiver app open on your tablet screen?"
                ))
            elif mode == "LAPTOP_HOTSPOT":
                self.after(0, lambda: self.lbl_device_status.config(text="Scanning Laptop Hotspot subnet...", style="StatusPending.TLabel"))
                hip = find_hotspot_device_ip()
                if hip:
                    self.after(0, lambda: self.on_hotspot_ready("samsung SM-T505N", hip))
                    self.after(0, lambda: messagebox.showinfo("Found Hotspot Device", f"Found tablet at {hip}:7777!\nReady to beam."))
                else:
                    self.after(0, lambda: messagebox.showerror(
                        "Device Not Found",
                        f"Could not reach {target}:7777 and no tablet responded on Laptop Hotspot.\n\n"
                        "1. Ensure AirBeam Receiver is opened on your tablet screen.\n"
                        "2. In the tablet app, ensure 'Laptop AP' mode is selected."
                    ))
            else:
                self.after(0, lambda: messagebox.showerror(
                    "Device Not Found",
                    f"Could not reach {target}:7777 on your home Wi-Fi network.\n\n"
                    "1. Ensure both PC and tablet are connected to the same Wi-Fi router.\n"
                    "2. Check the IP shown on your tablet's AirBeam screen and enter it manually."
                ))

        threading.Thread(target=worker, daemon=True).start()

    # --- Transfer Controls ---
    def toggle_pause(self):
        if not self.is_sending: return
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.btn_pause.config(text="▶ Resume")
            self.lbl_progress.config(text="Transfer Paused")
            self.lbl_speed.config(text="Paused")
        else:
            self.pause_event.set()
            self.btn_pause.config(text="⏸ Pause")
            self.lbl_progress.config(text="Resuming...")

    def cancel_transfer(self):
        if not self.is_sending: return
        if messagebox.askyesno("Cancel Transfer", "Cancel active multi-stream transfer?"):
            self.cancel_event.set()
            self.pause_event.set()
            self.lbl_progress.config(text="Cancelling...")
            self.btn_send.config(state="normal", text="⚡ Beam Files (Multi-Stream)")
            self.btn_pause.config(state="disabled", text="⏸ Pause")
            self.btn_cancel.config(state="disabled")
            self.is_sending = False

    def start_send_thread(self):
        if self.is_sending: return
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please select files to beam first.")
            return

        target = self.entry_ip.get().strip()

        # 1. Proactively check if tablet is on the Direct Hotspot
        hip = find_hotspot_device_ip()
        if hip:
            target = hip
            self.entry_ip.delete(0, tk.END)
            self.entry_ip.insert(0, target)
            self.lbl_device_status.config(
                text=f"🚀 Direct Hotspot Active: ({target}) — 50-95+ MB/s Active!",
                style="StatusHotspot.TLabel"
            )

        if not target or target.startswith("Searching"):
            messagebox.showwarning("No Target", "Target device IP not found. Click Scan or enter IP.")
            return

        # 2. Test connectivity before starting transfer
        try:
            test_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_s.settimeout(1.0)
            err = test_s.connect_ex((target, NIO_PORT))
            test_s.close()
            if err != 0:
                # Target IP didn't respond - search hotspot once more
                hip2 = find_hotspot_device_ip()
                if hip2 and hip2 != target:
                    target = hip2
                    self.entry_ip.delete(0, tk.END)
                    self.entry_ip.insert(0, target)
                    self.lbl_device_status.config(
                        text=f"🚀 Direct Hotspot Active: ({target}) — 50-95+ MB/s Active!",
                        style="StatusHotspot.TLabel"
                    )
                else:
                    messagebox.showerror(
                        "Cannot Connect",
                        f"Cannot connect to {target}:7777.\n\n"
                        "1. Make sure AirBeam is OPEN on your tablet screen.\n"
                        "2. Check if the tablet IP shown in AirBeam matches this IP."
                    )
                    return
        except Exception:
            pass

        self.is_sending = True
        self.pause_event.set()
        self.cancel_event.clear()

        self.btn_send.config(state="disabled", text="Beaming 50-95+ MB/s...")
        self.btn_pause.config(state="normal", text="⏸ Pause")
        self.btn_cancel.config(state="normal")

        engine = HighSpeedTransferEngine(
            target, self.selected_files,
            self.on_transfer_progress,
            self.on_transfer_complete,
            self.pause_event,
            self.cancel_event
        )
        threading.Thread(target=engine.execute, daemon=True).start()

    def on_transfer_progress(self, file_idx, total_files, filename, pct, cur_spd, avg_spd=0.0, eta_sec=0):
        if cur_spd > 0:
            self.last_valid_speed = cur_spd
            live_str = format_speed_with_mbps(cur_spd)
        elif getattr(self, "last_valid_speed", 0) > 0:
            live_str = format_speed_with_mbps(self.last_valid_speed)
        else:
            live_str = "0.0 MB/s (0 Mbps)"

        avg_str = format_speed(avg_spd)
        eta_str = format_eta(eta_sec)
        spd_display = f"⚡ {live_str}  |  Avg: {avg_str}  |  ETA: {eta_str}"

        self.after(0, lambda: (
            self.lbl_progress.config(text=f"Sending {file_idx}/{total_files}: {filename} ({pct}%)"),
            self.progress_bar.config(value=pct),
            self.lbl_speed.config(text=spd_display)
        ))

    def on_transfer_complete(self, total, error_count, errors, total_bytes=0, duration=0.0, avg_spd=0.0, peak_spd=0.0):
        self.is_sending = False
        avg_str = format_speed_with_mbps(avg_spd)
        peak_str = format_speed(peak_spd)
        final_summary = f"⚡ Completed: Avg {avg_str} | Peak {peak_str}" if avg_spd > 0 else "⚡ Completed"

        self.after(0, lambda: (
            self.btn_send.config(state="normal", text="⚡ Beam Files (Multi-Stream)"),
            self.btn_pause.config(state="disabled", text="⏸ Pause"),
            self.btn_cancel.config(state="disabled"),
            self.lbl_speed.config(text=final_summary),
            self.progress_bar.config(value=100)
        ))

        # Save stats to last_transfer_stats.json and log to airbeam_sender.log
        if total_bytes > 0:
            stats = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "files_count": total,
                "total_bytes": total_bytes,
                "total_formatted": format_bytes(total_bytes),
                "duration_seconds": round(duration, 2),
                "avg_speed_mb_s": round(avg_spd / (1024 * 1024), 2),
                "avg_speed_mbps": round((avg_spd * 8) / (1000 * 1000), 1),
                "peak_speed_mb_s": round(peak_spd / (1024 * 1024), 2),
                "errors": errors
            }
            try:
                stats_path = os.path.join(APP_ROOT, "last_transfer_stats.json")
                with open(stats_path, "w", encoding="utf-8") as f:
                    json.dump(stats, f, indent=2)
                with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
                    f.write(f"[{stats['timestamp']}] Beam Complete: {total} file(s) ({stats['total_formatted']}) in {stats['duration_seconds']}s — Avg: {stats['avg_speed_mb_s']} MB/s ({stats['avg_speed_mbps']} Mbps) | Peak: {stats['peak_speed_mb_s']} MB/s\n")
            except Exception:
                pass

        if self.cancel_event.is_set():
            self.after(0, lambda: self.lbl_progress.config(text="Transfer was cancelled."))
            return

        if error_count == 0:
            dur_text = f" in {duration:.1f}s" if duration > 0 else ""
            stats_msg = f"Successfully beamed {total} file(s) ({format_bytes(total_bytes)}){dur_text}!\n\n⚡ Average Speed: {avg_str}\n🚀 Peak Speed: {peak_str}" if avg_spd > 0 else f"Successfully beamed {total} files to Android tablet!"
            self.after(0, lambda: (
                self.lbl_progress.config(text=f"All {total} files transferred successfully at max speed!"),
                messagebox.showinfo("Success", stats_msg)
            ))
        else:
            err_msg = "\n".join(errors[:4])
            self.after(0, lambda: messagebox.showerror("Transfer Error", f"{error_count} error(s):\n{err_msg}"))

    def generate_speed_report(self):
        target = self.entry_ip.get().strip()
        is_tablet_hotspot = (
            target.startswith("192.168.43.") or
            target.startswith("10.") or
            getattr(self, "connected_to_airbeam", False) or
            (hasattr(self, "hotspot_switch") and getattr(self.hotspot_switch, "is_on", False)) or
            self.connection_mode.get() == "TABLET_HOTSPOT"
        )
        is_laptop_hotspot = target.startswith("192.168.137.")
        is_direct_hotspot = is_tablet_hotspot or is_laptop_hotspot

        if is_tablet_hotspot:
            mode_desc = "Tablet-Hosted 5 GHz Mobile Hotspot ('airbeam')"
            band_analysis = f"Operating on Tablet 5 GHz Hotspot ('airbeam' at {target}). Full 433–866 Mbps PHY / 60–95+ MB/s. Router bypassed!"
        elif is_laptop_hotspot:
            mode_desc = f"Laptop Direct Hotspot ({self.current_handover_band})"
            band_analysis = f"Operating on Windows Hotspot ({self.current_handover_band}). Router bypassed."
        else:
            mode_desc = "Home Wi-Fi Router Subnet"
            band_analysis = "Operating over home Wi-Fi network."

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "connection_mode": self.connection_mode.get(),
            "hotspot": self.hotspot_info or {"status": "Not active / Handled via Wi-Fi"},
            "active_target_ip": target,
            "is_direct_hotspot_connected": is_direct_hotspot,
            "active_band": self.current_handover_band,
            "parallel_streams": PARALLEL_STREAMS,
            "stripe_size_mb": DEFAULT_STRIPE_SIZE // (1024 * 1024),
            "chunk_slice_kb": CHUNK_SLICE_BYTES // 1024,
            "status": "AirBeam v5.0 Ultra-Speed Multi-Stream Ready",
            "diagnostics": {
                "router_bypassed": is_direct_hotspot,
                "connection_mode_description": mode_desc,
                "band_analysis": band_analysis
            }
        }
        stats_path = os.path.join(APP_ROOT, "last_transfer_stats.json")
        if os.path.exists(stats_path):
            try:
                with open(stats_path, "r", encoding="utf-8") as sf:
                    report["last_transfer"] = json.load(sf)
            except Exception:
                pass
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        report_path = os.path.join(app_dir, "AirBeam_Diagnostic_Report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        messagebox.showinfo("Speed Report", f"AirBeam V2 Telemetry report saved to:\n{report_path}")

if __name__ == "__main__":
    try:
        app = AirBeamSenderApp()
        app.mainloop()
    except Exception as e:
        log_error_to_file("MAIN CRASH", traceback.format_exc())
