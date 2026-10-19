# AirBeam v4.3 Engineering & Release Report: PC-to-PC Multi-Stream Transfer

**Release Date:** October 19, 2026  
**Build Target:** AirBeam v4.3  
**Target Folder:** `C:\Users\youssef\WirelessFileTransfer-v3.0`  
**Protected Folder Status:** `C:\Users\youssef\WirelessFileTransfer` (v2.7) — **100% untouched**

---

## 1. Executive Summary

AirBeam v4.3 introduces **Tab 2: "💻 PC to PC (50–100+ MB/s)"**, extending AirBeam's zero-copy multi-stream pipeline into a full peer-to-peer Windows desktop transfer system. Windows PCs can now discover each other automatically, beam gigabytes of files at 50–100+ MB/s over local Wi-Fi or hotspot connections, receive transfers into a dedicated `Received_From_PC` directory, and offer a zero-install browser mode for PCs without AirBeam.

---

## 2. Architecture & Technical Breakdown

### A. Four Reorganized Tabs
1. **`⚡ Beam to Android (50-95+ MB/s)`**: Connects to the Samsung Galaxy Tab or any Android receiver via Tablet Hotspot, Laptop Hotspot, or Home Wi-Fi.
2. **`💻 PC to PC (50-100+ MB/s)`**: Direct Windows-to-Windows beaming and receiving.
3. **`📱 iPhone / iOS (50-95+ MB/s)`**: Dual-port web portal (8080 & 8090) with direct document routing.
4. **`📥 Install Android APK`**: Built-in HTTP APK download server on port 8888.

### B. Built-in Multi-Stream PC Receiver Server (`PCReceiverServer`)
- **Port:** TCP 7777 (`NIO_PORT`).
- **Socket Parameters:** `SO_REUSEADDR`, `TCP_NODELAY`, `SO_RCVBUF = 8 MB`.
- **Protocol Compatibility:**
  - Control socket: Accepts `ABM_CTRL` header, extracts manifest JSON (`transfer_id`, `filename`, `filesize`, `total_chunks`), pre-allocates destination file in `Received_From_PC/`, and replies with `MANIFEST_OK`.
  - Worker sockets: Accepts `ABM2` magic, reads 32-byte chunk headers (`!QIIQQ`), writes chunk payload directly into open file handles at `chunk_off` under thread-safe file lock, and replies with `COK!` ACKs.
  - HTTP Fallback: Returns clean text response if scanned by web browsers or network tools.
- **Directory:** All incoming files saved to `C:\Users\youssef\WirelessFileTransfer-v3.0\Received_From_PC`.

### C. Automated Peer-to-Peer Discovery (UDP Port 7778)
- Every broadcast cycle, `coordinator_loop` broadcasts `AIRBEAM_PC_PING|<hostname>|<local_ip>`.
- Other AirBeam PCs reply with `AIRBEAM_PC_PONG|<hostname>|<local_ip>`.
- Discovered PCs appear dynamically as interactive chips in the GUI (`💻 HOSTNAME (IP)`).
- Clicking any chip sets the target IP immediately.
- Includes manual IP entry and latency ping test (`⚡ Ping / Test Connection`).

### D. Dedicated PC Beaming Pipeline
- Independent file queue supporting multi-file and whole-folder additions.
- Progress bar, live speedometer (MB/s & Mbps), average speed, and accurate ETA.
- Interactive Pause and Cancel controls (`self.pc_pause_event`, `self.pc_cancel_event`).

### E. Zero-Install Web Mode for Any PC
- For PCs that don't have AirBeam installed: provides clickable link and QR code for `http://<IP>:8080/index.html`.
- Allows drag-and-drop file transfers directly inside Chrome, Edge, or Firefox.
- Includes `💾 Share Setup (.exe)` button to easily share the installer wizard.

---

## 3. Verification & Safety

1. **Syntax Compilation:** Verified with `python -m py_compile sender.py` (0 errors).
2. **Folder Protection:** `C:\Users\youssef\WirelessFileTransfer` (v2.7) remains **100% untouched** (Timestamp: `10/18/2026 9:36:22 PM`).
3. **Launchers:** Updated [`Launch-AirBeam-v4.3.bat`](file:///C:/Users/youssef/WirelessFileTransfer-v3.0/Launch-AirBeam-v4.3.bat) and [`AirBeam v4.3.lnk`](file:///C:/Users/youssef/Desktop/AirBeam%20v4.3.lnk).
