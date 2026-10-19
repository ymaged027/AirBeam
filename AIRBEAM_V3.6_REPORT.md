# AirBeam v3.6 — Engineering & Architecture Report

**Date:** October 19, 2026  
**Build:** AirBeam v3.6 Ultra-Speed Wireless Transfer (Android & iPhone / iOS)  
**Target Folder:** `C:\Users\youssef\WirelessFileTransfer-v3.0`  
**Protected Legacy Folder:** `C:\Users\youssef\WirelessFileTransfer` (v2.7) — *100% Untouched*

---

## 1. Executive Summary

AirBeam **v3.6** addresses two core user requests regarding scrolling and interface navigation:
1. **Precision Trackpad (Touchpad) Two-Finger Scrolling:** Solved the issue where scrolling operated with a physical mouse but failed on laptop trackpads. Implemented continuous delta accumulation with micro-flick flushing and removed restrictive coordinate bounds that rejected trackpad gesture packets.
2. **Scrollable Layout & Slider on Tab 1 (Beam Files):** Converted the primary Android transfer tab into a `ScrollableFrame` equipped with a native vertical scrollbar slider. All sections (Wi-Fi link telemetry, target device & mode selector, files list, and transfer progress/actions) are now fully scrollable and never truncated on compact screen heights.
3. **Multi-Tab Class Registry:** Introduced central active-tab dispatching so that whichever Notebook tab is currently open receives scroll events seamlessly without cross-tab interference.
4. **Version Increment to v3.6:** Updated window titles, taskbar AppUserModelID, web portal branding, launcher scripts, and desktop shortcuts.

---

## 2. Technical Root Cause & Architectural Fixes

### A. Trackpad vs. Mouse Wheel Gesture Discrepancy
- **Root Cause:**
  - Physical mouse wheels send discrete `WM_MOUSEWHEEL` clicks with `event.delta` = $\pm 120$.
  - Laptop precision trackpads send continuous fine-grained deltas (e.g., 5 to 30 per swipe).
  - Integer division `int(event.delta / 120)` truncated small trackpad deltas to `0`, making the trackpad feel completely dead/stuck.
  - Furthermore, trackpad gesture messages on Windows can report client coordinates or `(0, 0)` rather than screen root coordinates, causing previous `rx <= event.x_root <= rx + rw` bounds checks to reject the event.
- **Architectural Solution:**
  - **Delta Accumulator:**
    ```python
    target._wheel_accum += delta
    step_threshold = 24.0
    if abs(target._wheel_accum) >= step_threshold:
        units = int(target._wheel_accum / step_threshold)
        target._wheel_accum -= units * step_threshold
        target.canvas.yview_scroll(-units, "units")
    ```
  - **Auto-Flush Timer:** An automatic 100ms timer flushes any residual delta $\ge 4.0$ to register single micro-flicks smoothly.
  - **Diagonal Swipe Tolerance:** Bound `<Shift-MouseWheel>` alongside `<MouseWheel>` to support natural two-finger trackpad motion.

### B. Tab 1 (Beam Files) Scrollable Frame & Slider
- **Architecture:** Wrapped `tab_send` inside `ScrollableFrame`, providing a full-height `ttk.Scrollbar` on the right margin.
- **Nested Listbox Coordination:** When the user hovers over the files listbox, mouse wheel and trackpad events scroll the list items. When hovering over cards, buttons, or whitespace, events scroll the main tab container.
- **Consistent Layout:** Telemetry, device card, files card, and action card are cleanly stacked with uniform 10px horizontal padding.

---

## 3. Verification & Test Suite

| Test Case | Status | Details |
| :--- | :---: | :--- |
| **Python Syntax Compilation** | **PASS** | `python -m py_compile sender.py` verified with 0 errors |
| **Dual-Tab Scroll Engine Test** | **PASS** | Verified mouse wheel ($\pm 120$) and trackpad micro-deltas ($\pm 10, \pm 15$) scroll active tab accurately |
| **iOS Web Portal Runtime** | **PASS** | Local HTTP GET on port 8090 returned HTTP 200 with `AirBeam v3.6` branding |
| **Desktop Shortcut Generation** | **PASS** | `create_shortcut.ps1` generated `AirBeam v3.6.lnk` and cleaned older links |
| **Legacy v2.7 Folder Integrity** | **PASS** | `C:\Users\youssef\WirelessFileTransfer` timestamp verified (`10/18/2026 9:36:22 PM`), 100% untouched |

---

## 4. How to Launch AirBeam v3.6

- **Desktop Shortcut:** Double-click the **AirBeam v3.6** shortcut on your Desktop.
- **Batch Launcher:** Run [`Launch-AirBeam-v3.6.bat`](file:///C:/Users/youssef/WirelessFileTransfer-v3.0/Launch-AirBeam-v3.6.bat).
