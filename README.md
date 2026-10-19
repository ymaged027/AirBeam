# AirBeam v4.5: Ultra-Speed Wireless Transfer (PC to PC, Android & iPhone / iOS)

AirBeam v4.5 expands ultra-speed wireless transfers across **Windows PCs, Android tablets/phones, and iPhone / iOS devices**, reaching hardware-saturating speeds (**50–100+ MB/s**) with native multi-stream pipelining, dual connection modes for PC-to-PC, auto-hotspot shutdown on exit, labeled QR codes, and zero-install web modes!

---

## ⚡ What's New in v4.5

### 1. 🎨 High-Contrast Target PC IP Input Box
- Replaced system ttk entry with a dark navy background (`#0f172a`), vivid cyan monospace text (`#38bdf8`), cyan insertion cursor, and slate border (`#475569`).
- Completely resolves text visibility issues where text and background were previously the same color.

### 2. 🏷️ Clearly Labeled QR Codes in "PC to PC" Tab
- **📶 Connect Wi-Fi QR Card**: Scan with mobile camera or tablet to automatically connect to the 5 GHz `airbeam` hotspot without typing passwords.
- **🌐 Open Web Portal QR Card**: Scan to immediately load `http://192.168.137.1:8080/index.html` in Chrome, Safari, or Edge for zero-install file transfer.
- **🌐 Web Portal Link Card**: Clearly labeled with subheadings in the Zero-Install Web card for quick peer access.

### 3. 🛑 Automatic Windows Hotspot Shutdown on Exit
- Whenever you close AirBeam (via the title bar `[X]` button or process exit), Windows Mobile Hotspot is automatically stopped in the background.
- Eliminates stranded virtual network adapters and frees your Wi-Fi interface immediately.

### 4. 💻 Dual Connection Modes for PC-to-PC Transfer (Tab 2)
- **🏠 Home / Office Wi-Fi Mode**:
  - Direct peer-to-peer transfer across devices connected to the same local Wi-Fi router.
  - Zero-configuration setup with automatic UDP peer discovery on port 7778.
  - Interactive selection chips for discovered PCs with ping latency measurement.
  - Web Portal at `http://<Local_IP>:8080/index.html` with dynamic QR code generation.
- **💻 Windows 5 GHz Mobile Hotspot Mode (Router-Bypass 50–100+ MB/s)**:
  - Hosts a direct high-bandwidth 5 GHz Wi-Fi hotspot (`airbeam` on `192.168.137.1`), bypassing slow routers, distance bottlenecks, and local network congestion.
  - Features an animated `HotspotToggleSwitch` widget for one-click hotspot activation.
  - Live credentials card displaying SSID, password, and direct URL.
  - Automatic ARP discovery (`get_connected_hotspot_client_ips()`) that auto-detects and populates connected client PCs in real-time.

### 5. 📥 Real-Time Multi-Stream PC Receiver (`PCReceiverServer`)
- Automatically listens on TCP port 7777 with `SO_REUSEADDR`, `TCP_NODELAY`, and 8 MB socket receive buffers across both Home Wi-Fi and Hotspot interfaces.
- Streams incoming files directly into [Received_From_PC](file:///C:/Users/youssef/WirelessFileTransfer-v3.0/Received_From_PC) with live speed reporting and determinate progress bars.
- Dedicated `📂 Open Received Folder` and `🧹 Clear Received` buttons.

---

## 📱 Transfer Modes Across All 4 Tabs

| Tab | Purpose | Connection Modes Available | Max Speed |
| :--- | :--- | :--- | :--- |
| **Tab 1: ⚡ Beam to Android** | Android tablet / phone transfers (NIO 6-Stream) | Tablet Hotspot, Laptop Hotspot, Home Wi-Fi | 50–95+ MB/s |
| **Tab 2: 💻 PC to PC** | Windows PC ↔ Windows PC direct transfer | 🏠 Home Wi-Fi, 💻 Windows 5 GHz Hotspot, Web Portal | 50–100+ MB/s |
| **Tab 3: 📱 iPhone / iOS** | iPhone / iPad Web Portal (Dual Ports 8080/8090) | Home Wi-Fi, Windows Hotspot, iPhone Hotspot | 50–95+ MB/s |
| **Tab 4: 📥 Install Android APK** | AirBeam Android Receiver APK server | Scan QR code or download via port 8888 | 100 Mbps LAN |

---

## 📂 Project Structure

```
C:\Users\youssef\WirelessFileTransfer-v3.0\
├── setup-output\
│   ├── AirBeam-v4.2-Setup.exe        # Standalone Windows Installer Wizard
│   └── AirBeam-v4.2-Portable.zip      # Portable No-Install Archive
├── dist\AirBeam\                      # Compiled standalone runtime directory
├── desktop-sender\
│   ├── sender.py                      # v4.5 Core GUI Application (4 Tabs)
│   └── assets\                        # Icons, logos, and UI graphics
├── android-app\                       # Native Android Receiver project (Java NIO, 6-Stream Turbo)
├── release\                           # AirBeam-v2.7-Receiver.apk (Knox V1+V2 signed)
├── Received_From_PC\                  # Target folder for files received from other PCs
├── Received_From_iPhone\              # Target folder for files uploaded from iOS devices
├── Fix-AirBeam-Firewall.bat           # One-click Admin Firewall fix
├── Launch-AirBeam-v4.5.bat            # v4.5 Local launcher
├── AirBeam-Setup.iss                  # Inno Setup 6 installer script (v4.5 ready)
└── create_shortcut.ps1                # Generates desktop shortcuts
```

> [!NOTE]
> The original `C:\Users\youssef\WirelessFileTransfer` (v2.7) project folder remains **100% untouched and unmodified**.
