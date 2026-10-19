# AirBeam v3.8 Engineering & Release Report

**Release Date:** October 19, 2026  
**Build Target:** AirBeam v3.8  
**Target Folder:** `C:\Users\youssef\WirelessFileTransfer-v3.0`  
**Protected Folder Status:** `C:\Users\youssef\WirelessFileTransfer` (v2.7) — **100% untouched**

---

## 1. Deep Root Cause Analysis: Laptop Trackpad Scrolling Failure

### Why Physical Mice Worked but Laptop Trackpads Failed:
1. **Python 3.14 & Tcl/Tk 9.0 (TIP 684 Specification):**
   - In modern Tcl/Tk 9.0 on Windows, laptop Precision Touchpads send two-finger scroll gestures as native `<TouchpadScroll>` events rather than standard `<MouseWheel>` events.
2. **The 32-bit Packed Signed Integer Bug:**
   - Under TIP 684, Tk stores horizontal and vertical touchpad delta values packed together into a 32-bit keycode field:
     - High 16 bits = $\Delta x$ (signed 16-bit)
     - Low 16 bits = $\Delta y$ (signed 16-bit)
   - When a user performs a two-finger scroll downwards (swiping fingers up to scroll down), Windows produces a negative delta (e.g. $\Delta y = -5$).
   - When stored in the low 16 bits of a 32-bit integer, `-5` becomes `0xFFFB` (`65531`).
   - When treated as a plain integer delta without 16-bit signed extraction, `delta` evaluated to `+65531`.
   - The scroll calculator performed `units = int(-1 * (65531 / 30)) = -2184 units`!
   - This instructed the canvas to scroll violently upwards by 2,184 units towards `0.0`. Because the user was already at the top of the page, this kept the scroll position firmly pinned at `0.0` (frozen at the top)!
3. **Canvas Step Resolution Mismatch (`yscrollincrement`):**
   - By default, Tk Canvas has `yscrollincrement=0`, which means 1 unit = 1/10th of the canvas height (~60–75 pixels).
   - High-frequency touchpad events (~60 per second) need fine pixel resolution rather than discrete 60-pixel chunk jumps.

---

## 2. Technical Implementation in v3.8

### A. Mathematical 16-Bit Signed Unpack & Normalization
The event handler now unpacks `delta` according to the official Tk 9.0 TIP 684 specification:
```python
if ev_type in ("39", "TouchpadScroll") or abs(delta) > 32767:
    u32 = int(delta) & 0xFFFFFFFF
    raw_dy = u32 & 0xFFFF
    dy = raw_dy if raw_dy < 0x8000 else raw_dy - 0x10000
    pixels = int(-dy)
```
- A downward swipe ($\Delta y = -15$) unpacks correctly to `dy = -15`, producing `pixels = +15` (scrolling content smoothly down).
- An upward swipe ($\Delta y = +10$) unpacks correctly to `dy = +10`, producing `pixels = -10` (scrolling content smoothly up).

### B. Pixel-Level Precision Scrolling (`yscrollincrement=1`)
```python
self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, yscrollincrement=1)
```
Setting `yscrollincrement=1` ensures that calling `canvas.yview_scroll(pixels, "units")` scrolls by exactly that number of screen pixels, delivering fluid 60fps tracking.

### C. Unified Mouse Wheel & Linux Button Support
- **Discrete Mouse Wheels:** `abs(delta) >= 120` $\rightarrow$ `int(-1 * (delta / 120) * 35)` pixels per notch.
- **Micro-Deltas / Continuous Wheels:** `abs(delta) < 120` $\rightarrow$ scaled directly to pixels.
- **Linux:** `<Button-4>` / `<Button-5>` scroll $\pm 35$ pixels.

### D. Universal Multi-Tab Coverage & Hover Isolation
- All tabs (Tab 1 "⚡ Beam Files", Tab 2 "Install APK", and Tab 3 "📱 iPhone / iOS") are hosted in `ScrollableFrame`.
- Hovering over `self.file_listbox` scrolls the list items directly. Hovering over cards, badges, buttons, or background scrolls the tab smoothly.

---

## 3. Verification & Test Matrix

| Test Case | Event / Input | Expected Action | Result |
| :--- | :--- | :--- | :--- |
| **Trackpad Swipe Down** | `<TouchpadScroll>`, $\Delta y = -15$ (packed `65521`) | Moves view down by +15 px | **PASS (`v1 = 0.00714 > v0`)** |
| **Trackpad Swipe Up** | `<TouchpadScroll>`, $\Delta y = +10$ (packed `10`) | Moves view up by -10 px | **PASS (`v2 = 0.00238 < v1`)** |
| **Physical Mouse Down** | `<MouseWheel>`, $\Delta = -120$ | Moves view down by +35 px | **PASS (`v3 = 0.01905 > v2`)** |
| **Physical Mouse Up** | `<MouseWheel>`, $\Delta = +120$ | Moves view up by -35 px | **PASS (`v4 = 0.00238 < v3`)** |
| **Precision Micro-Delta** | `<MouseWheel>`, $\Delta = -18$ | Moves view down by +18 px | **PASS (`v5 = 0.01095 > v4`)** |
| **File Listbox Hover** | Cursor over `file_listbox` | Listbox scrolls internally; tab canvas stays stationary | **PASS** |
| **Desktop Shortcut** | `create_shortcut.ps1` | `AirBeam v3.8.lnk` created on Desktop; older links removed | **PASS** |
| **Protected Folder** | `C:\Users\youssef\WirelessFileTransfer` (v2.7) | Unmodified (`10/18/2026 9:36:22 PM`) | **100% UNTOUCHED** |

---

## 4. How to Launch AirBeam v3.8
Double-click the **AirBeam v3.8** icon on your Desktop, or run:
```cmd
C:\Users\youssef\WirelessFileTransfer-v3.0\Launch-AirBeam-v3.8.bat
```
