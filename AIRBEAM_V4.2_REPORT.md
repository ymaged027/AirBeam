# AirBeam v4.2 Engineering & Release Report

**Release Date:** October 19, 2026  
**Build Target:** AirBeam v4.2  
**Target Folder:** `C:\Users\youssef\WirelessFileTransfer-v3.0`  
**Protected Folder Status:** `C:\Users\youssef\WirelessFileTransfer` (v2.7) — **100% untouched**

---

## 1. Executive Summary

AirBeam v4.2 resolves the persistent iOS Safari `https` auto-reversion issue in Windows Hotspot mode, enhances the iOS transfer subsystem with a concurrent dual-port engine (8080 & 8090), adds an in-GUI port switcher, and updates the standalone distribution setup (`AirBeam-v4.2-Setup.exe` and `AirBeam-v4.2-Portable.zip`).

---

## 2. Root Cause Analysis: Safari Automatic HTTPS Reversion

### The Problem:
When connecting an iPhone to the Windows Hotspot (Option 2), Safari refused to load `http://192.168.137.1:8090`. When the user changed `https://` to `http://` in the address bar and pressed Enter, Safari instantly reverted the URL back to `https://192.168.137.1:8090`, failing with `400 Bad request version` or connection timeout.

### Root Causes:
1. **Predictive Autocomplete & Top Hit HSTS Poisoning:**
   - When a user previously navigated to `192.168.137.1:8090` without an explicit scheme, iOS Safari attempted HTTPS first and saved the host:port combination into its internal Top Hit autocomplete cache.
   - Even when typing `http://`, Safari's autocomplete overrides the input with the cached HTTPS entry upon pressing Enter.
2. **Local Network HTTPS-First Heuristic:**
   - Modern iOS Safari applies an aggressive HTTPS-First heuristic to bare hostnames without concrete document paths (e.g. `192.168.137.1:8090` instead of `192.168.137.1:8090/index.html`).

---

## 3. Engineering Implementation

### A. Concurrent Dual-Port iOS Portal Engine
`IPhonePortalServer` now binds and runs workers on dual ports concurrently:
```python
IPHONE_PORTAL_PORTS = (8080, 8090)
```
- **Port 8080 is Primary:** Since Safari has never visited port 8080 on `192.168.137.1`, it has zero cached history or autocomplete records, allowing an immediate, clean HTTP connection.
- **Port 8090 Remains Active:** Sockets listen on both ports simultaneously so either port functions seamlessly.

### B. Direct Document Path Routing (`/index.html`)
All portal URLs across Option 1, Option 2, and Option 3 now explicitly include `/index.html`:
```python
portal_url = f"http://{cur_ip}:{self.iphone_portal_port}/index.html"
```
Providing an explicit file path signals to Safari that this is a concrete resource request, preventing Safari from applying domain-level HTTPS promotion.

### C. In-GUI Dynamic Port Switcher
Added `[ 🔀 Port: 8080 ]` toggle button directly inside Option 2. Clicking the button:
- Swaps active port between `8080` and `8090`.
- Regenerates the high-resolution QR code in real time.
- Updates clipboard and live link display without needing to restart the server.

### D. Native Self-Elevating Firewall Script
`Fix-AirBeam-Firewall.bat` was completely rewritten using native batch commands and `Start-Process cmd.exe -Verb RunAs`, opening inbound ports:
- **TCP 8090 & 8080** (iOS Web Portal dual engine)
- **TCP 7777** (AirBeam High-Speed Transfer)
- **TCP 8888** (APK Download Server)
- **UDP 7778** (Zero-Config UDP Discovery)
- `pythonw.exe` & `python.exe` runtimes across **all network profiles** (Private, Public, Domain).

---

## 4. Distribution Packages & Verification

1. **Standalone Installer Wizard:**
   - Path: [`setup-output\AirBeam-v4.2-Setup.exe`](file:///C:/Users/youssef/WirelessFileTransfer-v3.0/setup-output/AirBeam-v4.2-Setup.exe) (29.5 MB)
   - Built with Inno Setup 6.7.3 (`lzma2/ultra64` compression).
2. **Portable ZIP Archive:**
   - Path: [`setup-output\AirBeam-v4.2-Portable.zip`](file:///C:/Users/youssef/WirelessFileTransfer-v3.0/setup-output/AirBeam-v4.2-Portable.zip) (38.2 MB)
3. **Desktop Shortcut:**
   - Path: [`AirBeam v4.2.lnk`](file:///C:/Users/youssef/Desktop/AirBeam%20v4.2.lnk)
4. **Project History & Docs:**
   - [`AIRBEAM_PROJECT_CHAT_HISTORY.md`](file:///C:/Users/youssef/WirelessFileTransfer-v3.0/AIRBEAM_PROJECT_CHAT_HISTORY.md) (Section 20 added).
   - [`README.md`](file:///C:/Users/youssef/WirelessFileTransfer-v3.0/README.md) (Updated to v4.2).
   - [`AIRBEAM_V4.2_SETUP_GUIDE.md`](file:///C:/Users/youssef/WirelessFileTransfer-v3.0/AIRBEAM_V4.2_SETUP_GUIDE.md) (Sharing guide).
5. **Folder Protection:**
   - `C:\Users\youssef\WirelessFileTransfer` (v2.7) remains **100% untouched** (Timestamp: `10/18/2026 9:36:22 PM`).
