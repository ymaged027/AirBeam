# AirBeam v3.5 — Engineering & Architecture Report

**Date:** October 19, 2026  
**Build:** AirBeam v3.5 Ultra-Speed Wireless Transfer (Android & iPhone / iOS)  
**Target Folder:** `C:\Users\youssef\WirelessFileTransfer-v3.0`  
**Protected Legacy Folder:** `C:\Users\youssef\WirelessFileTransfer` (v2.7) — *100% Untouched*

---

## 1. Executive Summary

AirBeam **v3.5** addresses two critical UI & usability issues reported by the user:
1. **Universal Mouse Wheel Scrolling:** Fixed an underlying Tkinter Windows DPI scaling limitation where `winfo_containing` failed inside canvas windows. Mouse wheel scrolling now works effortlessly across the entire Tab 3 interface without requiring manual slider dragging.
2. **Dynamic Adaptive Responsive Layout:** Resolved horizontal button clipping and text truncation shown in the user's screenshot (`Screenshot 2026-10-19 111324.png`). Card 4 file action buttons and guidance cards now dynamically reflow into balanced grids and adjust text wrapping in real time whenever the application window is resized.
3. **Version Increment to v3.5:** Updated application window titles, taskbar AppUserModelID, web portal HTML templates, launcher scripts, and desktop shortcuts.

---

## 2. Root Cause Analysis & Architectural Fixes

### A. Universal Mouse Wheel Scrolling Fix
- **Root Cause Identified:** In Tkinter on Windows with OS DPI scaling active, widgets embedded inside a canvas via `create_window` are not recognized as children by `winfo_containing(x, y)`. When rolling the mouse wheel over cards or child widgets, `winfo_containing` returned `None`, causing `is_ours` to evaluate to `False` and discarding all scroll events.
- **Architectural Solution:**
  - Replaced `winfo_containing` with direct bounding-box geometry calculation:
    ```python
    rx = self.winfo_rootx()
    ry = self.winfo_rooty()
    rw = self.winfo_width()
    rh = self.winfo_height()
    if rx <= event.x_root <= rx + rw and ry <= event.y_root <= ry + rh:
        delta = int(-1 * (event.delta / 120))
        if delta == 0 and event.delta != 0:
            delta = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(delta * 2, "units")
    ```
  - Added `self.winfo_ismapped()` guard to ensure wheel events only scroll Tab 3 when Tab 3 is active, preventing accidental cross-tab scrolling.

### B. Dynamic Adaptive Responsive Layout (Card 4 & Guides)
- **Root Cause Identified:** In the previous version, Card 4 placed 6 buttons (`+ Add Files for iPhone`, `🗑️ Clear Staged Files`, `📂 Open Received Folder`, `🧹 Clear Uploaded Files`, `📋 Send Clipboard`, `🔄 Refresh QR`) horizontally in a single `pack(side="left")` row. When the window was at default width or narrower, the total button width exceeded available space, cutting off the last two buttons. Additionally, instruction steps had fixed or missing `wraplength` attributes.
- **Architectural Solution:**
  - **Card 4 Dynamic Grid Reflow:** `btn_bar` binds to `<Configure>` to evaluate container width:
    - **Wide Mode ($\ge$ 620px):** Arranges buttons in a 3-column $\times$ 2-row grid (`weight=1`, `sticky="ew"`), with buttons evenly expanding to occupy the full card width.
    - **Narrow Mode ($<$ 620px):** Automatically reflows buttons into a 2-column $\times$ 3-row grid with zero clipping.
  - **Option 1 Home Wi-Fi Buttons:** Refactored into a 2-column $\times$ 2-row grid alongside the QR code card (`📋 Copy Portal URL`, `🌐 Open in PC Browser`, `🔄 Refresh IP / QR`, `🛡️ Fix Firewall`).
  - **Dynamic Text Wrapping:** Guided instruction cards across Options 1, 2, and 3 now listen to parent resize events (`<Configure>`) and dynamically update label `wraplength` to fit available space cleanly.

---

## 3. Verification & Test Suite

| Test Case | Status | Details |
| :--- | :---: | :--- |
| **Python Syntax Compilation** | **PASS** | `python -m py_compile sender.py` completed with 0 errors |
| **iOS Web Portal Runtime** | **PASS** | HTTP GET `http://127.0.0.1:8090/` returned HTTP 200 with `AirBeam v3.5` branding |
| **Desktop Shortcut Generation** | **PASS** | `create_shortcut.ps1` generated `AirBeam v3.5.lnk` and cleaned older links |
| **Launcher Script** | **PASS** | `Launch-AirBeam-v3.5.bat` verified and functional |
| **Legacy v2.7 Folder Integrity** | **PASS** | `C:\Users\youssef\WirelessFileTransfer` timestamp verified (`10/18/2026 9:36:22 PM`), 100% untouched |

---

## 4. How to Launch AirBeam v3.5

- **Desktop Shortcut:** Double-click the **AirBeam v3.5** shortcut on your Desktop.
- **Batch Launcher:** Run [`Launch-AirBeam-v3.5.bat`](file:///C:/Users/youssef/WirelessFileTransfer-v3.0/Launch-AirBeam-v3.5.bat).
