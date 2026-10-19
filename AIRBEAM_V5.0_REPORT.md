# AirBeam v5.0 Engineering Report: Window-Wide Drag-and-Drop & File Queue Unification

**Date:** October 19, 2026  
**Version:** AirBeam v5.0  
**Working Directory:** `C:\Users\youssef\WirelessFileTransfer-v3.0`  
**Target Repository:** `https://github.com/ymaged027/AirBeam` (Private)

---

## 🚀 Overview & Objectives

In response to the user's requirements:
1. *"when i drag a file and drop it the app closes"*
2. *"add the drag and drop to be any where in the app not just a box"*
3. *"add the box of selected files to all the tabs execpt the qr"*

**AirBeam v5.0** resolves these issues with the following architectural upgrades:

1. **Root Cause Resolution for Application Crash on Drag-and-Drop**:
   - Replaced broken third-party library `windnd` (which suffered from 64-bit function pointer truncation in ctypes `GetWindowLongPtrA` leading to `EXCEPTION_ACCESS_VIOLATION 0xC0000005`) with an internal `NativeWindowsDropTarget` using explicit 64-bit ctypes prototypes and Unicode buffers.
2. **Window-Wide Drag & Drop Interception**:
   - Enabled `DragAcceptFiles` across the top-level window, client window, and all child widgets recursively via Win32 `EnumChildWindows`. Dropping files anywhere in the window (headers, cards, buttons, backgrounds, or listboxes) seamlessly captures and routes files to the currently active tab's staging queue.
3. **Selected Files Queue on All Tabs (Except QR Tab)**:
   - Added a unified **`📁 Files Staged for iPhone & iPad (Web Portal)`** card to Tab 3 (`build_ios_tab`), matching Tab 1 (Android) and Tab 2 (PC to PC).
   - Preserved Tab 4 (`Install Android APK`) as a clean QR code scanner tab without a file box.
4. **Clean Monotonic Version Bump to v5.0**:
   - Updated `sender.py`, window titles, Web Portal headers, AppUserModelID, launcher scripts (`Launch-AirBeam-v5.0.bat`), desktop shortcuts (`AirBeam v5.0.lnk`), `README.md`, and project chat history.
   - Kept `C:\Users\youssef\WirelessFileTransfer` (v2.7) 100% untouched.

---

## 🛠️ Detailed Engineering Actions

### 1. Native 64-Bit Drop Target Implementation (`NativeWindowsDropTarget`)
- **Root Cause Analysis**:
  `windnd-1.0.7` assigned `GetWindowLong = ctypes.windll.user32.GetWindowLongPtrA` without declaring `restype = ctypes.c_ssize_t`. On 64-bit Python on Windows, ctypes defaults return types to 32-bit signed integers. When subclassing Tkinter's native `WndProc`, the 64-bit pointer was sign-extended or truncated into invalid memory. Calling `CallWindowProcW` triggered an instant hardware access violation (`0xC0000005`) crashing Python before any exception handling could catch it.
- **Native Implementation**:
  - Defined explicit 64-bit prototypes:
    ```python
    SetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    SetWindowLongPtr.restype = ctypes.c_ssize_t
    GetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int]
    GetWindowLongPtr.restype = ctypes.c_ssize_t
    CallWindowProc.argtypes = [ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    CallWindowProc.restype = ctypes.c_ssize_t
    ```
  - Intercepted `WM_DROPFILES (0x0233)` using `DragQueryFileW` with dynamic Unicode buffer sizing and `DragFinish(hDrop)`.
  - Dispatched file paths asynchronously via `root.after(0, ...)` to ensure the Win32 window procedure returns immediately without re-entrancy latency.

### 2. Window-Wide Drop Capture & Routing
- Hooked `parent_hwnd = user32.GetParent(root.winfo_id())`, `client_hwnd = root.winfo_id()`, and child windows via `EnumChildWindows(parent_hwnd)`.
- Re-enumerates and attaches hooks on `<<NotebookTabChanged>>` to capture any newly created child widgets.
- `on_global_files_dropped(files)` inspects the active tab:
  - **Tab 0 (`Beam to Android`)**: Appends to `self.selected_files` and calls `self.refresh_file_list()`.
  - **Tab 1 (`PC to PC`)**: Appends to `self.pc_selected_files` and calls `self.update_pc_file_listbox()`.
  - **Tab 2 (`iPhone / iOS`)**: Appends to `self.selected_files` (staged for Web Portal) and calls `self.refresh_file_list()`.
  - **Tab 3 (`Install Android APK` - QR Tab)**: Safely stages files to `self.selected_files` without errors.

### 3. Tab 3 Staged Files Card (`build_ios_tab`)
- Added card matching Tabs 1 & 2:
  - Header: `📁 Files Staged for iPhone & iPad (Web Portal)`
  - Action buttons: `+ Add Files`, `+ Add Folder`, `Clear`, `📋 Send Clipboard`
  - Listbox: `self.listbox_ios_files` with vertical scrollbar
  - Live summary label: `self.lbl_ios_total_size`
- Updated `refresh_file_list()` to populate both `listbox_files` and `listbox_ios_files` synchronously.
- Streamlined `tools_card` to focus on received files management (`Open Received Folder`, `Clear Uploaded Files`, `Refresh QR`) and live telemetry.

---

## 🔒 Verification & Quality Assurance

1. **Python Compilation**:
   - `python -m py_compile desktop-sender/sender.py` passed with code 0 (zero syntax errors).
2. **Headless Execution & Drop Test**:
   - Tested drops across Tab 0, Tab 1, and Tab 2 programmatically.
   - Verified that `selected_files`, `pc_selected_files`, `listbox_files`, `listbox_pc_files`, and `listbox_ios_files` updated correctly and cleanly closed without crash.
3. **v2.7 Isolation**:
   - Verified `C:\Users\youssef\WirelessFileTransfer` (v2.7) remains 100% untouched (`10/18/2026 9:36:22 PM`).
4. **Desktop Shortcuts**:
   - `AirBeam v5.0.lnk` and `AirBeam.lnk` verified on `C:\Users\youssef\Desktop`.
