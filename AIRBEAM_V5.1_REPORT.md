# AirBeam v5.1 Engineering Report: Edge-Case Bug Fixes, Ease-of-Use Upgrades & Single-Instance IPC

**Date:** October 20, 2026  
**Version:** AirBeam v5.1  
**Working Directory:** `C:\Users\youssef\WirelessFileTransfer-v3.0`  
**Target Repository:** `https://github.com/ymaged027/AirBeam` (Private)

---

## 🚀 Overview & Objectives

Following the v5.0 milestone, **AirBeam v5.1** addresses 3 critical edge-case bugs identified in the drag-and-drop and ZIP streaming subsystems, delivers 4 high-impact ease-of-use upgrades, implements a robust single-instance IPC forwarding architecture for Windows Explorer right-click integration, and executes a thorough cleanup of legacy v2.7 artifacts.

---

## 🛠️ Key Technical Implementations

### 1. Fix Dropped Folder Crash (`PermissionError: [Errno 13]`)
- **Root Cause**: Windows Explorer drag-and-drop passes folder directory paths to `WM_DROPFILES`. Appending a folder path directly to `selected_files` or `pc_selected_files` caused `open(filepath, "rb")` in the streaming engine or web portal to crash Python with `PermissionError: [Errno 13] Permission denied`.
- **Solution**: In `on_global_files_dropped()`, `_on_pc_files_dropped()`, and `_on_main_files_dropped()`, every path is verified with `os.path.isdir()`. If a directory is dropped, AirBeam displays a live status message (`📦 Packaging dropped folder '<name>'...`), recursively walks the tree, and stages each child file individually. Direct folder path insertion is blocked, and duplicate paths are automatically ignored.

### 2. Guard `NativeWindowsDropTarget` Against Duplicate WndProc Subclassing
- **Root Cause**: Switching tabs triggered `<<NotebookTabChanged>>`, re-running `EnumChildWindows` and `SetWindowLongPtrW(hwnd, GWL_WNDPROC, ...)`. Hooking an HWND more than once overwrote `orig_wndproc` with the already-subclassed callback pointer, causing infinite recursion (`0xC00000FD` stack overflow).
- **Solution**: Defined `NativeWindowsDropTarget` with an explicit `self._hooked_hwnds: Dict[int, int]` registry mapping `hwnd -> original_wndproc`. Skips any HWND already present in `_hooked_hwnds` and verifies `GetWindowLongPtrW(hwnd, GWL_WNDPROC) != self._wndproc_ptr`. Retains a strong instance reference to `self._wndproc_cb = WNDPROC_PROTO(...)` to prevent garbage collection. Provides clean unhooking on window close.

### 3. Deduplicate Filenames Inside `GET /download-all.zip`
- **Root Cause**: When staging multiple files with identical basenames from different folders (e.g., `FolderA\photo.jpg` and `FolderB\photo.jpg`), the ZIP stream wrote conflicting archive entry names, causing the iOS Files app to overwrite earlier files during extraction.
- **Solution**: Added collision tracking in `IPhonePortalHandler.do_GET('/download-all.zip')` via `seen_counts: Dict[str, int]`. Clashing filenames are automatically renamed sequentially as `photo (1).jpg`, `photo (2).jpg`, ensuring zero file loss.

### 4. Ease-of-Use Upgrade #1: Single File Removal & Keyboard Shortcuts
- Bound `<Delete>` and `<BackSpace>` keys to `listbox_files` (Tab 1), `listbox_pc_files` (Tab 2), and `listbox_ios_files` (Tab 3).
- Added `[ ➖ Remove ]` buttons next to `Clear` across all three tabs.
- Users can remove single highlighted files or the last item in the queue without clearing the entire file list.

### 5. Ease-of-Use Upgrade #2: Global Ctrl+V Clipboard & Copied Files Paste
- Bound `<Control-v>` globally across the main window.
- Automatically inspects the Windows clipboard for copied Explorer files (`CF_HDROP`) and stages them into the active tab queue (identical to drag-and-drop).
- If copied content is text or a URL, beams or presents clipboard text seamlessly while preserving native text editing inside Entry/Text widgets.

### 6. Ease-of-Use Upgrade #3: Explorer Right-Click "⚡ Send with AirBeam" Integration
- Updated `sender.py` startup (`sys.argv[1:]`) so files or folders passed as command-line arguments are automatically staged into the queue on launch.
- Added a `[ ⚡ Add to Windows Right-Click Menu ]` toggle button in the top navigation bar.
- Uses `HKCU\Software\Classes\*\shell\AirBeam` and `HKCU\Software\Classes\Directory\shell\AirBeam` (zero Admin rights required).
- Updated launcher batch scripts (`Launch-AirBeam-v5.1.bat` and `Launch-AirBeam.bat`) to forward `%*` arguments.

### 7. Ease-of-Use Upgrade #4: Persistent Auto-Open Folder & Audio Completion Chime
- Added persistent checkbox `[☑ Auto-open folder when files arrive]` on Tab 2 (PC to PC) and Tab 3 (iPhone / iOS).
- Setting is persisted and restored via `airbeam_config.json`.
- When enabled, completing an incoming transfer plays a subtle Windows completion chime (`winsound.MessageBeep`) and opens/highlights the received file in Windows Explorer via `explorer.exe /select,"<dest_path>"`.

### 8. Single-Instance IPC Architecture & Explorer Forward-to-Existing-Window
- **Loopback TCP Server (`SingleInstanceIPCServer` on `127.0.0.1:7779`)**: Runs a lightweight daemon listener inside the primary instance with `SO_EXCLUSIVEADDRUSE` to prevent port-hijacking.
- **Atomic Win32 Mutex Detection**: Secondary launches instantly detect the running instance via `Local\AirBeam_SingleInstance_App_Mutex` (`ERROR_ALREADY_EXISTS = 183`).
- **Seamless File Forwarding (`try_forward_to_running_instance`)**: Forwards file paths over TCP to the primary window, receives `ACK_OK`, and exits immediately with `sys.exit(0)`.
- **Window Elevation (`bring_to_front`)**: Automatically unminimizes (`ShowWindow(SW_RESTORE=9)`) and brings the window to the foreground (`SetForegroundWindow`) using the root HWND from `GetAncestor(hwnd, GA_ROOT=2)`.
- **Duplicate Prevention**: Clicking desktop shortcuts or selecting "Send with AirBeam" on files in Explorer while the app is already open focuses the existing window and queues the files without opening duplicate windows.

---

## 🧹 Legacy Version Cleanup & Disk Pruning

1. **Deleted Legacy Version 2.7 Folder**: Completely deleted `C:\Users\youssef\WirelessFileTransfer` (v2.7 codebase) from disk.
2. **Pruned Legacy Launch Scripts**: Removed `Launch-AirBeam-v4.7.bat`, `Launch-AirBeam-v4.9.bat`, and `Launch-AirBeam-v5.0.bat` (leaving `Launch-AirBeam-v5.1.bat` and `Launch-AirBeam.bat`).
3. **Pruned Legacy APKs**: Removed `AirBeam-v2.7-Receiver.apk` from root, `release/AirBeam-v2.7-Receiver.apk`, and untracked `release/AirBeam-v2.1`..`v2.6`.
4. **Pruned Legacy Presentations**: Removed `AirBeam_V2.7_Presentation_and_Architecture.pdf` from project root and Windows Desktop.
5. **Updated Build Specs**: Updated `desktop-sender/sender.py` APK resolution, `AirBeam.spec` datas, `AirBeam-Setup.iss` version definitions, and `README.md` repository structure.

---

## 📊 Verification Summary

| Test Case | Method | Result | Status |
| :--- | :--- | :--- | :--- |
| **Python Syntax Check** | `python -m py_compile desktop-sender/sender.py` | 0 Syntax Errors | 🟢 PASS |
| **IPC Forwarding Simulation** | Multi-process socket transmission test | Delivered `['test1', 'test2']`, `ACK_OK`, exit 0 | 🟢 PASS |
| **Explorer Mutex Detection** | Win32 `CreateMutexW` duplication test | `ERROR_ALREADY_EXISTS (183)` detected instantly | 🟢 PASS |
| **Folder Drag-and-Drop** | Recursive directory unpack in `_on_main_files_dropped` | Staged files individually, zero PermissionError | 🟢 PASS |
| **Single-File Removal** | `<Delete>` & `[ ➖ Remove ]` queue handlers | Removes target item, preserves queue | 🟢 PASS |
| **v2.7 Folder Deletion** | PowerShell `Test-Path C:\Users\youssef\WirelessFileTransfer` | Returned `False` | 🟢 PASS |
| **Repository Hygiene** | Git status & tree verification | All legacy artifacts pruned | 🟢 PASS |
