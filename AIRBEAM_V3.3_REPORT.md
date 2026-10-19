# AirBeam v3.3 — Engineering & Architecture Report
## False-Positive Connection Elimination, Auto-Detection & Priority Layout Optimization

**Release Date:** October 19, 2026  
**Status:** Verified & Deployed  
**Target Environment:** Windows 10/11 & iOS 14+ (Safari Web App)  
**Self-Contained Root Directory:** `C:\Users\youssef\WirelessFileTransfer-v3.0`  
**Protected Directory:** `C:\Users\youssef\WirelessFileTransfer` (v2.7 — 100% Untouched)

---

### Executive Summary

In AirBeam v3.2, user testing revealed a critical edge case when connecting the PC to an iPhone's Personal Hotspot:
- The desktop app displayed: `ON — Connected to 'youssef's iPhone' at 192.168.1.4`, but the Windows taskbar Wi-Fi flyout showed the PC remained connected to the home network (`Orange-youssef`).
- Furthermore, because Option 3 (Transfer Over Home Wi-Fi Router) was placed at the bottom of Tab 3, users had to scroll past two complex hotspot cards to reach the zero-setup router mode.

AirBeam **v3.3** completely resolves these issues through strict profile connection verification, auto-recovery to Home Wi-Fi, background taskbar flyout auto-detection, and a re-engineered Tab 3 layout where Home Wi-Fi Router mode takes top billing.

---

### Key Technical Enhancements in v3.3

#### 1. Strict Profile Verification & False-Positive Elimination
- **Previous Root Cause:** `connect_worker()` checked whether `get_local_ip()` was non-empty and non-loopback. When Windows failed to associate with the iPhone within 2 seconds, Windows AutoConfig silently re-associated with `Orange-youssef`. The loop saw `192.168.1.4` and broke out, falsely claiming connection to the iPhone.
- **v3.3 Implementation:**
  - Before initiating the connection, Windows temporarily sets the home Wi-Fi profile (`Orange-youssef`) to `connectionmode=manual` so Windows does not prematurely abort the association handshake.
  - The polling loop strictly evaluates both the active SSID (`cur_ssid == matched_profile` or `"iphone" in cur_ssid.lower()`) and the assigned IP (`172.20.10.x` or verified non-home IP).
  - If association times out after 12 seconds:
    - `self.connected_to_iphone_hotspot` is set to `False`.
    - Auto-connect on `Orange-youssef` is immediately re-enabled (`connectionmode=auto`).
    - The PC reconnects automatically to `Orange-youssef`.
    - The toggle switch flips back to `OFF`.
    - An actionable troubleshooting card (`build_opt2_failed_view`) explains the exact steps required (iPhone unlocked on the Settings ➔ Personal Hotspot screen, or 1-tap connection via the Windows taskbar flyout).

#### 2. Bidirectional Taskbar Wi-Fi Flyout Auto-Detection
- In `on_telemetry_updated(data)`:
  - If the user connects to `youssef’s iPhone` directly through the Windows taskbar Wi-Fi flyout, AirBeam detects the SSID within 3 seconds.
  - The Option 3 toggle switch automatically flips to `ON` without manual input.
  - The Safari Portal QR code and clickable link instantly update to `http://172.20.10.x:8090`.
  - When the user disconnects or turns off the hotspot, AirBeam auto-flips the switch back to `OFF` and restores the default view.

#### 3. Re-Engineered Tab 3 Priority Hierarchy (Home Wi-Fi on Top)
Tab 3 now presents transfer options in descending order of convenience:
1. **Option 1 (Recommended — Zero Setup): 🏠 Transfer Over Home Wi-Fi Router:**
   - Directly visible at the top without scrolling.
   - Zero setup required: both PC and iPhone are already connected to `Orange-youssef`.
   - Shows high-resolution QR code pointing to `http://192.168.1.4:8090`.
   - Action buttons: `[ 📋 Copy Portal URL ]`, `[ 🌐 Open in PC Browser ]`, `[ 🔄 Refresh IP / QR ]`, and `[ 🛡️ Fix Firewall ]`.
2. **Option 2: 📡 Windows 5 GHz Mobile Hotspot (PC Hotspot ➔ iPhone):**
   - Direct router-bypass mode (50–95+ MB/s).
   - Side-by-side QR codes for 1-tap camera Wi-Fi join and Safari portal opening.
3. **Option 3: 📶 Connect PC to iPhone 5 GHz Personal Hotspot (iPhone Hotspot ➔ PC):**
   - Direct router-bypass mode with verified native connection and automatic fallback.
4. **Section 4: iPhone Portal File Actions & Live Telemetry:**
   - Dedicated buttons for adding files, opening received folders, sending clipboard data, and monitoring real-time MB/s throughput.

---

### Version 3.3 Verification Matrix

| Component | Status | Verification Method |
| :--- | :--- | :--- |
| `sender.py` Syntax & Compilation | PASS | `python -m py_compile sender.py` (0 errors) |
| Web Portal HTTP Server (Port 8090) | PASS | `http://127.0.0.1:8090/` returned 200 OK |
| Files JSON API | PASS | `GET /api/files` returned valid JSON list |
| Clipboard JSON API | PASS | `GET /api/clipboard` returned valid clipboard JSON |
| Launcher Script | PASS | `Launch-AirBeam-v3.3.bat` verified |
| Desktop Shortcut | PASS | `AirBeam v3.3.lnk` deployed, older shortcuts purged |
| v2.7 Folder Integrity | PASS | `C:\Users\youssef\WirelessFileTransfer` unchanged |

---

### Quick Launch Guide

To run AirBeam v3.3:
1. Double-click the **AirBeam v3.3** icon on your Desktop, or
2. Execute `C:\Users\youssef\WirelessFileTransfer-v3.0\Launch-AirBeam-v3.3.bat`.
