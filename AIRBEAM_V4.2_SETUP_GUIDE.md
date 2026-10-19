# AirBeam v4.2 Setup & Sharing Guide

**Release:** AirBeam v4.2 Setup & Portable Distribution  
**Location on Disk:** `C:\Users\youssef\WirelessFileTransfer-v3.0\setup-output`  
**Desktop Shortcut:** `AirBeam v4.2.lnk` on your Desktop  

---

## 🎁 Two Ready-to-Share Packages

You have two pre-compiled, self-contained options to share with friends, colleagues, or other PCs:

### Option A: The Full Installer (`AirBeam-v4.2-Setup.exe` — 29.5 MB) 🌟 Recommended
- **Best for:** Anyone who wants a standard Windows installation with zero setup.
- **How to use:**
  1. Share `AirBeam-v4.2-Setup.exe` via Google Drive, Telegram, USB flash drive, or WhatsApp Web.
  2. The recipient double-clicks `AirBeam-v4.2-Setup.exe`.
  3. The Inno Setup wizard:
     - Installs AirBeam into `%LocalAppData%\Programs\AirBeam` (No admin prompt required!).
     - Automatically creates Desktop and Start Menu shortcuts with the custom icon.
     - Adds Windows Defender Firewall inbound rules for transfer (TCP 8090, 8080, 7777, 8888) and discovery (UDP 7778).
     - Registers a clean uninstaller in Windows Settings / Apps.
     - Launches AirBeam v4.2 immediately!

---

### Option B: The Portable ZIP (`AirBeam-v4.2-Portable.zip` — 38.2 MB)
- **Best for:** Running directly from a USB stick or for users who cannot or do not want to run an installer.
- **How to use:**
  1. Share `AirBeam-v4.2-Portable.zip`.
  2. The recipient extracts the ZIP file to any folder or USB drive.
  3. Double-click `AirBeam.exe` to launch immediately!

---

## ⚡ What's New in v4.2

1. **Safari HTTPS Auto-Reversion Bypass:**
   - Safari on iOS previously remembered `192.168.137.1:8090` and forced `http://` to revert back to `https://`.
   - **Port 8080 is now the primary port**, bypassing Safari's contaminated cache completely.
   - **`/index.html` document routing** ensures Safari never executes its domain HTTPS-First upgrade.
2. **Concurrent Dual-Port Engine (8080 & 8090):**
   - The iOS Web Portal listens on **both port 8080 and 8090 simultaneously**.
   - An interactive `[ 🔀 Port: 8080 ]` button inside Option 2 lets you switch ports anytime with one click.
3. **Firewall & UAC Self-Elevation:**
   - Includes `Fix-AirBeam-Firewall.bat` with native elevation, opening ports 8080, 8090, 7777, 8888, and 7778 across all network adapters.
4. **Precision Trackpad & Mouse Scrolling:**
   - Full 16-bit signed unpack for laptop trackpad two-finger scrolling on all tabs.

---

## 🔒 Recipient System Requirements
- **Operating System:** Windows 10 or Windows 11 (64-bit).
- **Python Required:** **NONE!** Python 3.14, Tkinter, Pillow, and all dependencies are fully frozen into the executable.
- **Android APK Included:** Bundles `AirBeam-v2.7-Receiver.apk` (Java NIO 6-Stream Turbo) so Android users can install offline.
- **iPhone / iOS Transfer:** Zero apps required! iPhone users scan the QR code to open the web portal on port 8080 or 8090 in Safari.

---

## 📁 Exact File Locations
- **Setup Folder:** [`C:\Users\youssef\WirelessFileTransfer-v3.0\setup-output`](file:///C:/Users/youssef/WirelessFileTransfer-v3.0/setup-output)
- **Installer:** [`AirBeam-v4.2-Setup.exe`](file:///C:/Users/youssef/WirelessFileTransfer-v3.0/setup-output/AirBeam-v4.2-Setup.exe) (29.5 MB)
- **Portable ZIP:** [`AirBeam-v4.2-Portable.zip`](file:///C:/Users/youssef/WirelessFileTransfer-v3.0/setup-output/AirBeam-v4.2-Portable.zip) (38.2 MB)
