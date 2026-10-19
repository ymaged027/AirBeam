# AirBeam v3.7 — Engineering & Architecture Report

**Date:** October 19, 2026  
**Build:** AirBeam v3.7 Ultra-Speed Wireless Transfer (Android & iPhone / iOS)  
**Target Folder:** `C:\Users\youssef\WirelessFileTransfer-v3.0`  
**Protected Legacy Folder:** `C:\Users\youssef\WirelessFileTransfer` (v2.7) — *100% Untouched*

---

## 1. Executive Summary

AirBeam **v3.7** resolves the persistent trackpad scrolling issue on modern Windows 11 laptops running Python 3.14 (Tcl/Tk 9.0.4) and provides a fully scrollable experience across both Tab 1 ("⚡ Beam Files") and Tab 3 ("📱 iPhone / iOS"):
1. **Tk 9.0 Native `<TouchpadScroll>` Event Binding:** Uncovered the core reason why physical mice scrolled but laptop trackpads failed: under Tcl/Tk 9.0 (TIP 684), Windows precision touchpads dispatch a dedicated `<TouchpadScroll>` event rather than `<MouseWheel>`. AirBeam v3.7 implements full dual-binding architecture for `<TouchpadScroll>`, `<Shift-TouchpadScroll>`, `<MouseWheel>`, and `<Shift-MouseWheel>`.
2. **Zero-Lag Immediate Delta Scaling:** Small continuous trackpad swipes ($\pm 5$ to $\pm 30$) are mapped directly into responsive 1–2 unit scrolls with zero dead zone and no timer lag.
3. **Scrollable Layout & Slider on Tab 1 (Beam Files):** Tab 1 is now fully wrapped in a `ScrollableFrame` with a vertical scrollbar slider.
4. **Version Increment to v3.7:** Updated application window titles, taskbar AppUserModelID, web portal branding, launcher scripts, and desktop shortcuts.

---

## 2. Technical Root Cause & Architectural Fixes

### A. The Tk 9.0 `<TouchpadScroll>` Discovery (TIP 684)
- **Root Cause:**
  - Python 3.14 bundles Tcl/Tk **9.0.4**.
  - In Tk 9.0, under TIP 684 ("Add Support for Touchpad Scrolling to Tk"), two-finger touchpad scrolling gestures on Windows are delivered via the `<TouchpadScroll>` event, while external mice continue to send `<MouseWheel>`.
  - Because applications traditionally bind only `<MouseWheel>`, physical mice worked perfectly while laptop trackpads were completely dropped by Tkinter.
- **Architectural Solution:**
  - Registered dual global and local bindings:
    ```python
    scroll_events = [
        "<MouseWheel>",
        "<TouchpadScroll>",
        "<Shift-MouseWheel>",
        "<Shift-TouchpadScroll>",
        "<Button-4>",
        "<Button-5>"
    ]
    for ev in scroll_events:
        self.bind_all(ev, ScrollableFrame._on_global_scroll)
        self.canvas.bind(ev, lambda e, inst=self: inst._on_instance_scroll(e))
        self.scrollable_window.bind(ev, lambda e, inst=self: inst._on_instance_scroll(e))
    ```
  - **Dynamic Delta Scaling:**
    ```python
    if delta:
        if abs(delta) >= 120:
            units = int(-1 * (delta / 30))
        else:
            units = int(-1 * (delta / 20))
            if units == 0:
                units = -1 if delta > 0 else 1
    elif num == 4:
        units = -2
    elif num == 5:
        units = 2
    target.canvas.yview_scroll(units, "units")
    ```

### B. Tab 1 (Beam Files) Scrollable Container
- Wrapped `tab_send` inside `ScrollableFrame`, equipping Tab 1 with a native vertical scrollbar slider.
- Structured with uniform 10px padding across the Telemetry, Device Selection, Files to Beam (with 7-row listbox and dedicated inner scrollbar), and Progress & Action cards.
- Configured event awareness so listbox items scroll when hovered, and the main page scrolls when hovering over cards or background.

---

## 3. Verification & Test Suite

| Test Case | Status | Details |
| :--- | :---: | :--- |
| **Python Syntax Compilation** | **PASS** | `python -m py_compile sender.py` completed with 0 errors |
| **Tk 9.0 `<TouchpadScroll>` Engine** | **PASS** | Verified `<TouchpadScroll>` micro-deltas ($\pm 20, \pm 60$) scroll Canvas directly |
| **MouseWheel ($\pm 120$) Engine** | **PASS** | Verified physical mouse wheel events scroll Canvas directly |
| **iOS Web Portal Runtime** | **PASS** | Local HTTP GET on port 8090 returned HTTP 200 with `AirBeam v3.7` branding |
| **Desktop Shortcut Generation** | **PASS** | `create_shortcut.ps1` generated `AirBeam v3.7.lnk` and cleaned older links |
| **Legacy v2.7 Folder Integrity** | **PASS** | `C:\Users\youssef\WirelessFileTransfer` timestamp verified (`10/18/2026 9:36:22 PM`), 100% untouched |

---

## 4. How to Launch AirBeam v3.7

- **Desktop Shortcut:** Double-click the **AirBeam v3.7** shortcut on your Desktop.
- **Batch Launcher:** Run [`Launch-AirBeam-v3.7.bat`](file:///C:/Users/youssef/WirelessFileTransfer-v3.0/Launch-AirBeam-v3.7.bat).
