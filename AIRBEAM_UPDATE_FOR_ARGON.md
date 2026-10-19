# ⚡ AirBeam V2.7 — Engineering Update & Technical Report for Argon

**Project:** AirBeam High-Speed Wireless File Transfer (Windows PC ↔ Android)  
**Author / Contributor:** Youssef  
**Target Recipient:** Argon  
**Release Version:** v2.7  
**Date:** October 18, 2026  
**Status:** **File Transmission Succeeded & Verified (v2.7 Turbo Edition)** ✅

---

## 📋 Executive Summary

We have upgraded AirBeam from **v2.6 to v2.7**, pushing real-world throughput to the hardware ceiling of Wi-Fi 6 while introducing major interactive UI and UX enhancements across both the Windows desktop sender and the Samsung Galaxy Tab A7 receiver:

1. **Interactive Hotspot Toggle Switches (PC & Android):**
   * **Android:** Replaced the legacy hotspot settings button with a rounded status card containing a live state subtitle (`"ON — Active at <ip>"` vs `"OFF — Tap switch to enable hotspot"`) and an interactive `SwitchCompat`. A 1.5-second background poller inspects `WifiManager.isWifiApEnabled()` via reflection and scans network interfaces (`swlan0`/`ap0`) to keep the switch synchronized with OS state.
   * **Windows PC:** Replaced the push button with a custom-drawn animated `HotspotToggleSwitch` widget on `tk.Canvas` (Slate Gray `#475569` when OFF, Emerald Green `#10B981` when ON). Toggling ON connects to `airbeam` and auto-detects tablet gateway IP; toggling OFF disconnects and immediately restores home Wi-Fi.
2. **Pipelined Zero-Copy & Adaptive 6-Stream Engine:**
   * **Continuous Pipelined Streaming:** Worker threads stream assigned 16 MB stripes back-to-back without stop-and-wait blocking. An asynchronous ACK collector concurrently gathers `"COK!"` confirmations from disk writes, eliminating inter-stripe pipeline stalls.
   * **Adaptive Stream Count:** Uses 6 parallel TCP streams for files >= 64 MB (4 streams for smaller files) to saturate 5 GHz Wi-Fi 6 A-MPDU frame aggregation.
   * **Socket Buffer Tuning:** `SOCKET_SNDBUF_SIZE = 8 MB` on PC sender, `SOCKET_RCVBUF_SIZE = 16 MB` on Android `ServerSocketChannel`/`SocketChannel`, and `DIRECT_BUFFER_SIZE = 4 MB` off-heap `DirectByteBuffer` per worker.
3. **Precision Speedometer (Receiver-Confirmed Goodput + Rolling Window EMA + Pause-Aware Timer):**
   * Uses a 1.5-second `collections.deque` sliding window smoothed via Exponential Moving Average (`0.30 * window + 0.70 * ema`).
   * Subtracts accumulated pause duration so pausing/resuming never corrupts average speed or ETA.
   * Multi-metric UI readout: `Live Speed (MB/s & Mbps)`, `Average Speed (Avg)`, and `Accurate ETA (MM:SS)`.
4. **Live Wi-Fi Link & Band Telemetry Badge (PC App Header):**
   * Background poller parses `netsh wlan show interfaces` every 3 seconds to display real-time telemetry: `📶 SSID: airbeam | Band: 5 GHz (Ch 149) | Link Rate: 866 Mbps | Signal: 99%`.
   * Automatically warns with an amber tip if the tablet's hotspot is running on 2.4 GHz (Link Rate <= 144 Mbps).
5. **Live Transfer Progress & Speedometer on Android Tablet:**
   * `FileServerService` computes real-time MB/s throughput and broadcasts progress every 200 ms to `MainActivity`, displaying a live progress bar, file name, and speedometer card directly on the tablet screen.
6. **One-Tap [ 📂 Open ] & [ 🔗 Share ] on Android Transfers List:**
   * Every completed transfer item provides instant `[ 📂 Open ]` (`ACTION_VIEW`) and `[ 🔗 Share ]` (`ACTION_SEND`) buttons backed by Android `FileProvider`.
7. **Instant Clipboard / Text & URL Beam (`📋 Beam Clipboard`):**
   * One-click beam of Windows clipboard text or URLs over `ABM_CTRL` (`{"type": "CLIPBOARD", "text": "..."}`).
   * Tablet copies text directly to `ClipboardManager`, and displays an interactive dialog to open URLs in the Android browser.
8. **Strict App-Folder Isolation & Dual V1+V2 Signing:**
   * All binaries, logs, and artifacts are strictly isolated in `C:\Users\youssef\WirelessFileTransfer`. `AirBeam-v2.7-Receiver.apk` is signed with Dual V1+V2 signatures for Knox PackageInstaller compatibility.
9. **Robust Home Wi-Fi Auto-Reconnection & Intel AX201 Handover:**
   * Solved driver deauth race conditions on Intel Wi-Fi 6 AX201 adapters by inserting a 1.5-second settling delay before reconnection.
   * Employs strict anchored regex profile extraction (`get_current_wifi_profile()`), persistent disk caching (`last_home_wifi.txt`), and automated saved-profile fallbacks (`netsh wlan show profiles`).
   * On application exit (clicking the 'X' button or closing the window), synchronously executes `netsh wlan disconnect` in Python (taking ~90ms) before the window closes, ensuring immediate deauthentication from airbeam, while a detached background process with redirected stdio (`DEVNULL`) executes the Intel AX201 settling delay and reconnects to home Wi-Fi.

---

## 🛠️ 1. Detailed Technical Upgrades in Version 2.7

### A. Asynchronous Pipelined Stripe Streaming
* **Legacy Bottleneck (v2.6):** After writing each 16 MB stripe, the sender thread stalled on `sock.recv(4)` waiting for `"COK!"`. Network socket buffers drained to zero between stripes.
* **Pipelined Architecture (v2.7):** Each worker thread initiates a concurrent `ack_reader` thread. The sender pushes 16 MB stripes into the 8 MB socket buffer continuously without blocking. The `ack_reader` verifies disk-write acknowledgments concurrently, maintaining 100% TCP window saturation throughout the transfer.

### B. Adaptive 6-Stream Saturation
* Wi-Fi 6 (802.11ax) and 802.11ac hardware benefit from parallel stream multiplexing.
* Files >= 64 MB automatically scale to **6 parallel TCP worker streams**, bypassing single-core TCP congestion bottlenecks and saturating 80 MHz channel aggregation.

### C. Receiver-Confirmed Precision Speedometer
* Nafve lifetime speed calculations (`sent / elapsed`) distort transfer speed during network stalls or pause events.
* Version 2.7 calculates speed over a sliding 1.5-second sample window with EMA smoothing:
  $$\text{EMA}_{\text{new}} = 0.30 \times \text{Speed}_{\text{window}} + 0.70 \times \text{EMA}_{\text{prev}}$$
* Total paused time is subtracted from elapsed time:
  $$\text{Elapsed}_{\text{active}} = t_{\text{now}} - t_{\text{start}} - t_{\text{paused}}$$
### D. Completed Transfer Metrics Persistence & Speedometer Retention
* **Zero Post-Transfer Data Loss:** In legacy builds, the UI cleared the speed label immediately upon completion (`lbl_speed.config(text="")`), leaving no record of the transfer speed.
* **Persistent Speed Summary:** The completed speed readout remains on-screen (`⚡ Completed: Avg XX.X MB/s (YYY Mbps) | Peak ZZ.Z MB/s`), and the completion popup displays total duration, average speed, and peak speed.
* **Automatic JSON & Log Tracking:** Each completed transfer automatically writes full telemetry to [`last_transfer_stats.json`](file:///C:/Users/youssef/WirelessFileTransfer/last_transfer_stats.json) and logs to [`airbeam_sender.log`](file:///C:/Users/youssef/WirelessFileTransfer/airbeam_sender.log), making transfer speeds permanently verifiable.

---

## 📡 2. Network Architecture & Protocol Specification

```
   ┌────────────────────────────────────────────────────────┐
   │             Windows Desktop Sender (v2.7)              │
   │  (Pipelined 6-Stream Engine, 8MB SNDBUF, 2MB Slices)   │
   └──────────────────────────┬─────────────────────────────┘
                              │
              ┌────────────────┴────────────────┐
              │ High-Throughput Wireless Medium │
              │  (Direct IP: 10.150.131.50 / GW)│
              └────────────────┬────────────────┘
                              │
   ┌──────────────────────────▼─────────────────────────────┐
   │             Android Tablet Receiver (v2.7)             │
   │  (FileServerService - NIO Sparse Channel, 16MB RCVBUF) │
   └────────────────────────────────────────────────────────┘
```

| Component | Port / Protocol | Function |
| :--- | :--- | :--- |
| **Control Socket** | `TCP 7777` | Handshake, JSON file manifest, CANCEL, CLIPBOARD, and FINALIZE (`FINALIZE_OK`) |
| **Worker Sockets** | `TCP 7777 (x6)` | 6 parallel persistent pipelined streams with 16 MB stripes and 2 MB slices |
| **Discovery Beacon** | `UDP 7778` | Broadcast packet `AIRBEAM_DISCOVER` for zero-configuration device pairing |
| **APK Server** | `HTTP 8888` | Built-in HTTP server to deliver v2.7 APK updates over the air via QR code |

---

## 🚀 3. How to Run & Verify

### Step 1: Install Android Receiver (v2.7)
1. Install the APK located in the app folder:
   * File path: `C:\Users\youssef\WirelessFileTransfer\release\AirBeam-v2.7-Receiver.apk` (or scan the QR code in the PC app).
2. Open **AirBeam** on the tablet.
3. Flip the **📡 Mobile Hotspot ('airbeam')** toggle switch to turn ON hotspot.

### Step 2: Launch Windows Sender (v2.7)
1. Double-click the **AirBeam** shortcut on the Desktop or run `Launch-AirBeam-Sender.bat` inside `C:\Users\youssef\WirelessFileTransfer`.
2. Flip the **📶 Connect to 'airbeam' Hotspot** animated toggle switch to ON.
   * PC disconnects from home network, registers WPA2 profile, connects to `airbeam`, and detects the tablet's gateway IP.
   * Telemetry badge shows real-time link rate (e.g., `866 Mbps`) and 5 GHz band confirmation.

### Step 3: Beam Files & Clipboard
1. Add files or folders, and click **`⚡ Beam Files (Multi-Stream)`**.
2. Watch the dual speedometer display live MB/s, average speed, and exact ETA.
3. On tablet, view live progress bar and tap **[ 📂 Open ]** or **[ 🔗 Share ]** once completed.
4. Copy text on Windows and click **`📋 Beam Clipboard`** to send it instantly to the tablet clipboard.
5. Flipping the toggle switch OFF (or closing the PC app) automatically reconnects Windows back to your home Wi-Fi network.

---

## 📦 Deliverables Summary (App Folder Only)

| File | Purpose | Location |
| :--- | :--- | :--- |
| **AirBeam-v2.7-Receiver.apk** | Signed Android receiver app (V1+V2, Toggle Switch, 16MB RCVBUF, Open/Share) | `C:\Users\youssef\WirelessFileTransfer\release\AirBeam-v2.7-Receiver.apk` |
| **AirBeam-v2.7-Receiver.apk** | Root copy for fast access | `C:\Users\youssef\WirelessFileTransfer\AirBeam-v2.7-Receiver.apk` |
| **AirBeam-Receiver.apk** | Release alias | `C:\Users\youssef\WirelessFileTransfer\release\AirBeam-Receiver.apk` |
| **sender.py** | Desktop sender (Pipelined 6-streams, HotspotToggleSwitch, Telemetry, Clipboard) | `C:\Users\youssef\WirelessFileTransfer\desktop-sender\sender.py` |
| **Launch-AirBeam-Sender.bat** | Silent background launcher (pythonw) | `C:\Users\youssef\WirelessFileTransfer\Launch-AirBeam-Sender.bat` |
| **last_home_wifi.txt** | Cached home Wi-Fi profile for instant restore | `C:\Users\youssef\WirelessFileTransfer\last_home_wifi.txt` |
| **AIRBEAM_UPDATE_FOR_ARGON.md** | Complete technical report for Argon (v2.7) | `C:\Users\youssef\WirelessFileTransfer\AIRBEAM_UPDATE_FOR_ARGON.md` |
| **AIRBEAM_PROJECT_CHAT_HISTORY.md** | Complete chronological trajectory & architecture (v1-v2.7) | `C:\Users\youssef\WirelessFileTransfer\AIRBEAM_PROJECT_CHAT_HISTORY.md` |
| **README.md** | Quick start guide & system overview (v2.7) | `C:\Users\youssef\WirelessFileTransfer\README.md` |
| **AirBeam_V2.7_Presentation_and_Architecture.pdf** | Publication-grade 4-page dark-theme presentation with dual-platform UI designs | `C:\Users\youssef\WirelessFileTransfer\AirBeam_V2.7_Presentation_and_Architecture.pdf` (and Desktop) |

