# AirBeam: High-Throughput Wireless Transfer & Argon Collaborative Brief

**Target Device:** Windows 11 PC $\rightarrow$ Android Device  
**Current Baseline Throughput:** ~1.0 – 1.1 MB/s  
**Target Throughput:** **50+ MB/s** over local Wi-Fi  
**Status:** Pause/Cancel controls added, 2 MB chunk engine implemented, diagnostic profiling enabled.

---

## 1. System Telemetry & Live Diagnostics (Ground Truth)

Live hardware diagnosis executed on the sender machine (`Windows 11`):
```json
{
  "Adapter": {
    "Name": "Wi-Fi",
    "InterfaceDescription": "Intel(R) Wi-Fi 6 AX201 160MHz",
    "LinkSpeed": "39 Mbps"
  },
  "PhysicalLayerCeiling": "39 Mbps (theoretical max ~4.87 MB/s)",
  "RealWorldTCPThroughput": "~1.0 - 1.2 MB/s (due to 802.11 half-duplex MAC + ACK overhead)"
}
```

### The Primary Hardware Discovery:
The sender's Wi-Fi adapter is an **Intel Wi-Fi 6 AX201 (capable of 2,400 Mbps)**, but it is currently negotiated with the router at **39 Mbps** (connected via 2.4 GHz or low signal).
Because 802.11 Wi-Fi operates in half-duplex mode with CSMA/CA contention:
- A physical link rate of **39 Mbps** yields an effective single-stream TCP application throughput of **~1.0 to 1.2 MB/s**.
- To achieve **50 MB/s** (400 Mbps effective), the link rate must be at least **500–866 Mbps** (which requires 5 GHz 802.11ac/ax, or PC/Phone Mobile Hotspot).

---

## 2. Implemented Features & Architecture

### A. Windows Desktop Sender (`desktop-sender/sender.py`):
- **Controls Added:**
  - `⚡ Beam Files`: Launches high-performance streaming.
  - `⏸ Pause` / `▶ Resume`: Suspends socket transmission without tearing down the TCP stream.
  - `⏹ Cancel`: Aborts the active socket, resets UI, and discards partial data.
  - `📊 Speed Report`: Generates live benchmark & telemetry report (`AirBeam_Diagnostic_Report.json`).
- **Network Engine:**
  - `TCP_NODELAY = 1` (disables Nagle's algorithm).
  - `SO_SNDBUF = 8 MB` (allows full TCP window scaling).
  - 2 MB sequential chunk streaming.
  - Throttled GUI updates (250ms) to prevent Python GIL blocking during large transfers (3.6+ GB).

### B. Android Receiver (`android-app/`):
- **Core Service (`FileServerService.java`):**
  - Foreground Service with active notification (`FOREGROUND_SERVICE_DATA_SYNC`).
  - `serverSocket.setReceiveBufferSize(4 * 1024 * 1024)`.
  - `clientSocket.setReceiveBufferSize(4 * 1024 * 1024)`.
  - `clientSocket.setTcpNoDelay(true)`.
  - 1 MB buffered disk I/O straight into Android's `Downloads/` directory via `MediaStore` / `FileProvider`.
  - UDP Auto-Discovery beacon responder on port 7778 (`AIRBEAM_DISCOVER` $\rightarrow$ `AIRBEAM_ACK`).

---

## 3. How to Reach 50+ MB/s

1. **Bandwidth Band:** Switch from 2.4 GHz to **5 GHz Wi-Fi** on both PC and Android device. The Intel AX201 link rate will jump from 39 Mbps to 866–1200 Mbps.
2. **Wi-Fi Hotspot Alternative (Zero-Router direct link):**
   - Turn on Windows **Mobile Hotspot** (5 GHz band) on PC, and connect the phone directly to it.
   - Or turn on Android Hotspot and connect PC.
   - This bypasses router congestion completely and hits **60–90 MB/s** peer-to-peer.
3. **Multi-Channel Parallel Sockets:**
   - Instead of 1 TCP stream, slice files into 16 MB chunks and transfer across 4 parallel TCP worker connections to saturate available bandwidth.

---

## 4. Questions & Collaboration Directives for Argon

Argon, please review the architecture above and provide recommendations on:

1. **Multi-Stream Protocol:** What is the most resilient protocol specification to split a 3.6 GB file into multi-socket TCP chunks (e.g. 4 parallel workers) with pause/resume support between Python and Android Java?
2. **Zero-Copy Optimization:** Should we switch from Python `sock.sendall()` to `sock.sendfile()` (`TransmitFile` on Windows) for the multi-gigabyte transfer, and how should we handle the chunk headers in that case?
3. **Android NIO Ring Buffer:** Would switching from `BufferedOutputStream` to Java NIO `FileChannel.write(directByteBuffer)` with a ring buffer eliminate any remaining flash memory write stalls on Android 14?
4. **Peer-to-Peer Direct Pairing:** What is the cleanest implementation for initiating Wi-Fi Direct or SoftAP negotiation when the local router is restricted to 2.4 GHz?
