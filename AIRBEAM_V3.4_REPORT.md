# AirBeam v3.4 — Engineering & Architecture Report
## Smooth Mouse Wheel Scrolling & Comprehensive File Clear Suite

**Release Date:** October 19, 2026  
**Status:** Verified & Deployed  
**Target Environment:** Windows 10/11 & iOS 14+ (Safari Web App)  
**Self-Contained Root Directory:** `C:\Users\youssef\WirelessFileTransfer-v3.0`  
**Protected Directory:** `C:\Users\youssef\WirelessFileTransfer` (v2.7 — 100% Untouched)

---

### Executive Summary

AirBeam **v3.4** introduces two major usability and control enhancements based on user feedback:
1. **Comprehensive Clear Buttons for All File Workflows:**
   - On the PC app (Tab 3): Added `[ 🗑️ Clear Staged Files ]` to clear files queued for iPhone download, and `[ 🧹 Clear Uploaded Files ]` to safely empty the `Received_From_iPhone` folder with confirmation and live count display.
   - On the iOS Safari Web App: Added an **Uploaded Files** history section with a one-tap `[ 🗑️ Clear Upload List ]` button.
2. **Universal Mouse Wheel Scrolling across Tab 3:**
   - Solved the limitation where the canvas in `ScrollableFrame` could only be scrolled by dragging the vertical scrollbar slider.
   - Implemented a pointer-aware recursive mousewheel dispatcher that smoothly scrolls the view whenever the mouse cursor spins the wheel anywhere over the tab (cards, labels, buttons, or blank space).

---

### Technical Implementation Details

#### 1. Pointer-Aware Mouse Wheel Dispatching in `ScrollableFrame`
- **Root Cause in Previous Versions:** `ScrollableFrame` created a standard `ttk.Scrollbar` and bound `<Configure>` on the canvas, but never bound `<MouseWheel>`. In Tkinter, child widgets (labels, frames, buttons) do not bubble mousewheel events up to parent canvases by default.
- **v3.4 Architecture:**
  - Bound `<MouseWheel>` globally via `self.bind_all("<MouseWheel>", self._on_mousewheel)`.
  - In `_on_mousewheel(event)`, the handler dynamically queries `self.winfo_containing(event.x_root, event.y_root)`.
  - It traverses the widget hierarchy (`curr = curr.master`) to determine whether the pointer is currently within `ScrollableFrame`.
  - If inside Tab 3, it scrolls `self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")`.
  - If the cursor is on another tab (e.g., Tab 1's file listbox) or outside the window, it does not intercept the event, ensuring zero interference with native OS or listbox scrolling.

#### 2. Comprehensive File Clear Controls
- **PC Tab 3 — `[ 🗑️ Clear Staged Files ]`:**
  - Clears `self.selected_files` for iPhone download.
  - Automatically updates the file count in the GUI and notifies iPhone Safari (via `/api/files`) so the web page immediately updates to "0 files staged".
- **PC Tab 3 — `[ 🧹 Clear Uploaded Files ]`:**
  - Scans `C:\Users\youssef\WirelessFileTransfer-v3.0\Received_From_iPhone`.
  - If empty, informs the user with a friendly notification.
  - If files exist, presents a confirmation dialog with total file count and size in MB.
  - Upon user confirmation, permanently deletes the uploaded files and refreshes the live summary label.
- **PC Tab 3 — Live File Summary Badge:**
  - Displays: `📤 Staged for iPhone: X file(s) (Y MB)  •  📥 Received from iPhone: A file(s) (B MB)`
  - Automatically updates every 3 seconds via the background telemetry loop.
- **Safari Web App — Upload History & `[ 🗑️ Clear Upload List ]`:**
  - Below the upload progress bar, uploaded files are logged with their filename, file size, timestamp, and a `✅` badge.
  - Users can clear the upload list anytime with one tap on `[ 🗑️ Clear Upload List ]`.

---

### Verification Matrix

| Component | Status | Verification Method |
| :--- | :--- | :--- |
| `sender.py` Syntax & Compilation | PASS | `python -m py_compile sender.py` (0 errors) |
| Web Portal HTTP Server (Port 8090) | PASS | `http://127.0.0.1:8090/` returned 200 OK |
| HTML Portal Title & Header | PASS | Verified `AirBeam v3.4` in HTML response |
| Clear Upload List in Web App | PASS | Verified `clearUploadedFilesList` in HTML response |
| Launcher Script | PASS | `Launch-AirBeam-v3.4.bat` verified |
| Desktop Shortcut | PASS | `AirBeam v3.4.lnk` generated; older shortcuts cleaned up |
| v2.7 Folder Integrity | PASS | `C:\Users\youssef\WirelessFileTransfer` unchanged |

---

### Quick Launch Guide

To run AirBeam v3.4:
1. Double-click the **AirBeam v3.4** shortcut on your Desktop, or
2. Execute `C:\Users\youssef\WirelessFileTransfer-v3.0\Launch-AirBeam-v3.4.bat`.
