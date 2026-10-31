package com.airsend.receiver;

public class WebPortalHtml {
    public static final String ICLOUD_SHORTCUT_URL = "https://www.icloud.com/shortcuts/64fb6a4308124708937953f6fd8f9f62";

    public static String getHtml(String deviceModel, String serverPort) {
        return "<!DOCTYPE html>\n" +
"<html lang=\"en\">\n" +
"<head>\n" +
"    <meta charset=\"UTF-8\">\n" +
"    <meta name=\"apple-mobile-web-app-capable\" content=\"yes\">\n" +
"    <meta name=\"apple-mobile-web-app-status-bar-style\" content=\"black-translucent\">\n" +
"    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover, user-scalable=no\">\n" +
"    <meta name=\"theme-color\" content=\"#0B1120\">\n" +
"    <title>AirBeam Web Portal</title>\n" +
"    <style>\n" +
"        :root {\n" +
"            --bg: #0B1120;\n" +
"            --card-bg: rgba(30, 41, 59, 0.78);\n" +
"            --card-border: rgba(71, 85, 105, 0.45);\n" +
"            --text-primary: #F8FAFC;\n" +
"            --text-secondary: #94A3B8;\n" +
"            --accent-cyan: #38BDF8;\n" +
"            --accent-green: #10B981;\n" +
"            --accent-purple: #8B5CF6;\n" +
"        }\n" +
"        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }\n" +
"        body {\n" +
"            margin: 0;\n" +
"            padding: env(safe-area-inset-top, 20px) 16px env(safe-area-inset-bottom, 20px);\n" +
"            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;\n" +
"            background: var(--bg);\n" +
"            color: var(--text-primary);\n" +
"            min-height: 100vh;\n" +
"        }\n" +
"        .header {\n" +
"            text-align: center;\n" +
"            padding: 16px 0 20px;\n" +
"        }\n" +
"        .header h1 {\n" +
"            margin: 0;\n" +
"            font-size: 24px;\n" +
"            font-weight: 700;\n" +
"            display: flex;\n" +
"            align-items: center;\n" +
"            justify-content: center;\n" +
"            gap: 8px;\n" +
"        }\n" +
"        .header p {\n" +
"            margin: 6px 0 0;\n" +
"            font-size: 13px;\n" +
"            color: var(--text-secondary);\n" +
"        }\n" +
"        .badge {\n" +
"            display: inline-flex;\n" +
"            align-items: center;\n" +
"            gap: 6px;\n" +
"            padding: 4px 12px;\n" +
"            border-radius: 9999px;\n" +
"            font-size: 11px;\n" +
"            font-weight: 600;\n" +
"            margin-top: 10px;\n" +
"            background: rgba(16, 185, 129, 0.15);\n" +
"            color: var(--accent-green);\n" +
"            border: 1px solid rgba(16, 185, 129, 0.3);\n" +
"        }\n" +
"        .card {\n" +
"            background: var(--card-bg);\n" +
"            border: 1px solid var(--card-border);\n" +
"            border-radius: 20px;\n" +
"            padding: 20px;\n" +
"            margin-bottom: 16px;\n" +
"            backdrop-filter: blur(20px);\n" +
"            -webkit-backdrop-filter: blur(20px);\n" +
"            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);\n" +
"        }\n" +
"        .card-header {\n" +
"            display: flex;\n" +
"            align-items: center;\n" +
"            justify-content: space-between;\n" +
"            margin-bottom: 14px;\n" +
"        }\n" +
"        .card-title {\n" +
"            font-size: 17px;\n" +
"            font-weight: 600;\n" +
"            display: flex;\n" +
"            align-items: center;\n" +
"            gap: 8px;\n" +
"        }\n" +
"        .btn {\n" +
"            display: block;\n" +
"            width: 100%;\n" +
"            padding: 14px 16px;\n" +
"            border-radius: 12px;\n" +
"            font-size: 15px;\n" +
"            font-weight: 600;\n" +
"            text-align: center;\n" +
"            text-decoration: none;\n" +
"            cursor: pointer;\n" +
"            border: none;\n" +
"            transition: transform 0.1s ease, filter 0.1s ease;\n" +
"        }\n" +
"        .btn:active { transform: scale(0.98); filter: brightness(0.9); }\n" +
"        .btn-shortcut {\n" +
"            background: linear-gradient(135deg, #8B5CF6, #6D28D9);\n" +
"            color: #fff;\n" +
"            box-shadow: 0 4px 18px rgba(139, 92, 246, 0.45);\n" +
"            margin-bottom: 10px;\n" +
"        }\n" +
"        .btn-secondary {\n" +
"            background: rgba(51, 65, 85, 0.6);\n" +
"            color: var(--text-primary);\n" +
"            border: 1px solid rgba(255, 255, 255, 0.1);\n" +
"        }\n" +
"        .dropzone {\n" +
"            border: 2px dashed rgba(56, 189, 248, 0.4);\n" +
"            border-radius: 16px;\n" +
"            padding: 28px 16px;\n" +
"            text-align: center;\n" +
"            background: rgba(56, 189, 248, 0.04);\n" +
"            cursor: pointer;\n" +
"            transition: border-color 0.2s;\n" +
"        }\n" +
"        .dropzone:active { border-color: var(--accent-cyan); background: rgba(56, 189, 248, 0.08); }\n" +
"        .file-item {\n" +
"            display: flex;\n" +
"            align-items: center;\n" +
"            justify-content: space-between;\n" +
"            padding: 12px 14px;\n" +
"            background: rgba(15, 23, 42, 0.6);\n" +
"            border: 1px solid rgba(255, 255, 255, 0.07);\n" +
"            border-radius: 12px;\n" +
"            margin-bottom: 8px;\n" +
"        }\n" +
"        .file-info {\n" +
"            overflow: hidden;\n" +
"            padding-right: 12px;\n" +
"        }\n" +
"        .file-name {\n" +
"            font-size: 14px;\n" +
"            font-weight: 500;\n" +
"            white-space: nowrap;\n" +
"            overflow: hidden;\n" +
"            text-overflow: ellipsis;\n" +
"        }\n" +
"        .file-size {\n" +
"            font-size: 12px;\n" +
"            color: var(--text-secondary);\n" +
"            margin-top: 2px;\n" +
"        }\n" +
"        .btn-download {\n" +
"            background: linear-gradient(135deg, #2563EB, #1D4ED8);\n" +
"            color: #fff;\n" +
"            padding: 8px 14px;\n" +
"            border-radius: 8px;\n" +
"            font-size: 12px;\n" +
"            font-weight: 600;\n" +
"            text-decoration: none;\n" +
"            flex-shrink: 0;\n" +
"        }\n" +
"        .device-switcher-box {\n" +
"            background: rgba(30, 41, 59, 0.7);\n" +
"            border: 1px solid rgba(56, 189, 248, 0.3);\n" +
"            border-radius: 14px;\n" +
"            padding: 10px 14px;\n" +
"            margin-bottom: 16px;\n" +
"            display: flex;\n" +
"            flex-direction: column;\n" +
"            gap: 8px;\n" +
"        }\n" +
"        .switcher-header {\n" +
"            font-size: 11px;\n" +
"            text-transform: uppercase;\n" +
"            letter-spacing: 0.5px;\n" +
"            color: var(--text-secondary);\n" +
"            font-weight: 700;\n" +
"            display: flex;\n" +
"            align-items: center;\n" +
"            justify-content: space-between;\n" +
"        }\n" +
"        .pill-group {\n" +
"            display: flex;\n" +
"            gap: 8px;\n" +
"        }\n" +
"        .device-pill {\n" +
"            flex: 1;\n" +
"            padding: 10px 8px;\n" +
"            border-radius: 10px;\n" +
"            border: 1px solid rgba(255, 255, 255, 0.1);\n" +
"            background: rgba(15, 23, 42, 0.6);\n" +
"            color: var(--text-secondary);\n" +
"            font-size: 13px;\n" +
"            font-weight: 600;\n" +
"            cursor: pointer;\n" +
"            display: flex;\n" +
"            align-items: center;\n" +
"            justify-content: center;\n" +
"            gap: 6px;\n" +
"            transition: all 0.2s ease;\n" +
"        }\n" +
"        .device-pill.active {\n" +
"            background: rgba(56, 189, 248, 0.15);\n" +
"            border-color: var(--accent-cyan);\n" +
"            color: #fff;\n" +
"            box-shadow: 0 0 12px rgba(56, 189, 248, 0.25);\n" +
"        }\n" +
"        .progress-box {\n" +
"            display: none;\n" +
"            background: rgba(15, 23, 42, 0.8);\n" +
"            border-radius: 12px;\n" +
"            padding: 12px;\n" +
"            margin-top: 14px;\n" +
"            border: 1px solid rgba(56, 189, 248, 0.3);\n" +
"        }\n" +
"        .progress-bar-bg {\n" +
"            background: rgba(255, 255, 255, 0.1);\n" +
"            border-radius: 6px;\n" +
"            height: 8px;\n" +
"            overflow: hidden;\n" +
"            margin: 8px 0;\n" +
"        }\n" +
"        .progress-bar-fill {\n" +
"            background: linear-gradient(90deg, #38BDF8, #10B981);\n" +
"            height: 100%;\n" +
"            width: 0%;\n" +
"            transition: width 0.15s ease;\n" +
"        }\n" +
"        .toast {\n" +
"            position: fixed;\n" +
"            bottom: 30px;\n" +
"            left: 50%;\n" +
"            transform: translateX(-50%);\n" +
"            background: #10B981;\n" +
"            color: #fff;\n" +
"            padding: 10px 20px;\n" +
"            border-radius: 30px;\n" +
"            font-size: 13px;\n" +
"            font-weight: 600;\n" +
"            display: none;\n" +
"            z-index: 1000;\n" +
"            box-shadow: 0 4px 15px rgba(0,0,0,0.4);\n" +
"        }\n" +
"        .clipboard-box {\n" +
"            background: rgba(15, 23, 42, 0.6);\n" +
"            border-radius: 12px;\n" +
"            padding: 12px;\n" +
"            margin-bottom: 10px;\n" +
"            font-family: monospace;\n" +
"            font-size: 12px;\n" +
"            color: #38BDF8;\n" +
"            word-break: break-all;\n" +
"            max-height: 80px;\n" +
"            overflow-y: auto;\n" +
"        }\n" +
"        textarea {\n" +
"            width: 100%;\n" +
"            border-radius: 10px;\n" +
"            background: rgba(15, 23, 42, 0.6);\n" +
"            border: 1px solid rgba(255,255,255,0.1);\n" +
"            color: #fff;\n" +
"            padding: 10px;\n" +
"            font-size: 13px;\n" +
"            resize: none;\n" +
"            margin-bottom: 10px;\n" +
"        }\n" +
"    </style>\n" +
"</head>\n" +
"<body>\n" +
"    <div class=\"header\">\n" +
"        <h1>⚡ AirBeam v6.0</h1>\n" +
"        <p>Receiver: " + deviceModel + "</p>\n" +
"        <div class=\"badge\">● DIRECT 5GHz WI-FI PIPE (50-95+ MB/s)</div>\n" +
"    </div>\n" +
"\n" +
"    <!-- ⚡ AirBeam Multi-Device Switcher -->\n" +
"    <div id=\"deviceSwitcherBar\" class=\"device-switcher-box\" style=\"display:none;\">\n" +
"        <div class=\"switcher-header\">\n" +
"            <span>AirBeam Connected Devices</span>\n" +
"            <span id=\"targetStatusText\" style=\"color:var(--accent-cyan);\">● Direct Wi-Fi</span>\n" +
"        </div>\n" +
"        <div class=\"pill-group\">\n" +
"            <button id=\"pillTablet\" class=\"device-pill active\" onclick=\"switchTargetDevice('tablet')\">\n" +
"                <span>📱</span>\n" +
"                <span id=\"pillTabletLabel\">Samsung Tablet</span>\n" +
"            </button>\n" +
"            <button id=\"pillPC\" class=\"device-pill\" onclick=\"switchTargetDevice('pc')\">\n" +
"                <span>💻</span>\n" +
"                <span id=\"pillPCLabel\">Windows PC</span>\n" +
"            </button>\n" +
"        </div>\n" +
"    </div>\n" +
"\n" +
"    <!-- ⚡ Live Active Transfer Card with STOP / RESUME and CANCEL -->\n" +
"    <div id=\"liveTransferCard\" class=\"card\" style=\"display:none;border:1.5px solid #38BDF8;background:linear-gradient(180deg, rgba(15,23,42,0.95) 0%, rgba(30,41,59,0.95) 100%);box-shadow:0 8px 24px rgba(56,189,248,0.2);\">\n" +
"        <div class=\"card-header\" style=\"margin-bottom:8px;\">\n" +
"            <div class=\"card-title\" style=\"color:#38BDF8;display:flex;align-items:center;gap:8px;\">\n" +
"                <span class=\"pulse-dot\"></span> ⚡ Live Active Transfer\n" +
"            </div>\n" +
"            <span id=\"liveTransferPercent\" class=\"badge\" style=\"margin-top:0;background:rgba(56,189,248,0.2);color:#38BDF8;font-size:13px;font-weight:700;\">0%</span>\n" +
"        </div>\n" +
"        <div id=\"liveTransferFilename\" style=\"font-weight:600;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-bottom:8px;color:#F8FAFC;\">Receiving file...</div>\n" +
"        <div class=\"progress-bar-bg\" style=\"height:10px;border-radius:5px;background:#334155;overflow:hidden;\">\n" +
"            <div id=\"liveTransferFill\" class=\"progress-bar-fill\" style=\"width:0%;height:100%;background:linear-gradient(90deg,#38BDF8,#818CF8);transition:width 0.2s ease;\"></div>\n" +
"        </div>\n" +
"        <div style=\"display:flex;justify-content:space-between;font-size:11px;color:var(--text-secondary);margin-top:6px;\">\n" +
"            <span id=\"liveTransferBytes\">0 MB / 0 MB</span>\n" +
"            <span id=\"liveTransferSpeed\">⚡ 0.0 MB/s</span>\n" +
"        </div>\n" +
"        <div style=\"display:flex;gap:10px;margin-top:14px;\">\n" +
"            <button id=\"btnLiveTransferStop\" onclick=\"toggleServerTransfer()\" class=\"btn\" style=\"flex:1;padding:12px;font-size:14px;font-weight:700;background:#F59E0B;color:#fff;border-radius:10px;margin-bottom:0;cursor:pointer;\">\n" +
"                ⏹️ Stop\n" +
"            </button>\n" +
"            <button id=\"btnLiveTransferCancel\" onclick=\"cancelServerTransfer()\" class=\"btn\" style=\"flex:1;padding:12px;font-size:14px;font-weight:700;background:#EF4444;color:#fff;border-radius:10px;margin-bottom:0;cursor:pointer;\">\n" +
"                ❌ Cancel\n" +
"            </button>\n" +
"        </div>\n" +
"    </div>\n" +
"\n" +
"    <!-- iOS AirDrop Share Sheet Card -->\n" +
"    <div class=\"card\" style=\"border:1px solid rgba(139,92,246,0.45);background:linear-gradient(180deg, rgba(30,41,59,0.85) 0%, rgba(20,24,45,0.9) 100%);\">\n" +
"        <div class=\"card-header\">\n" +
"            <div class=\"card-title\" style=\"display:flex;align-items:center;gap:8px;\"><span>⚡</span><span style=\"color:#C084FC;font-weight:700;\">iOS AirDrop Share Sheet</span></div>\n" +
"            <span class=\"badge\" style=\"margin-top:0;background:rgba(139,92,246,0.25);color:#C084FC;\">AirDrop Mode</span>\n" +
"        </div>\n" +
"        <p style=\"font-size:13px;color:var(--text-secondary);margin:0 0 14px;line-height:1.5;\">\n" +
"            Beam photos, 4K videos, and files directly from your iPhone's native <b>Share</b> menu without opening Safari every time!\n" +
"        </p>\n" +
"        <a href=\"" + ICLOUD_SHORTCUT_URL + "\" class=\"btn\" style=\"background:linear-gradient(135deg, #8B5CF6, #6D28D9);color:#fff;font-weight:700;box-shadow:0 4px 18px rgba(139,92,246,0.45);font-size:15px;padding:14px 16px;text-align:center;text-decoration:none;display:block;border-radius:12px;\">\n" +
"            📥 Download AirBeam Shortcut\n" +
"        </a>\n" +
"    </div>\n" +
"\n" +
"    <!-- Staged Files for iPhone -->\n" +
"    <div class=\"card\">\n" +
"        <div class=\"card-header\">\n" +
"            <div id=\"stagedCardTitle\" class=\"card-title\">📥 Files from Android</div>\n" +
"            <span id=\"fileCountBadge\" class=\"badge\" style=\"margin-top:0;\">0 files</span>\n" +
"        </div>\n" +
"        <div id=\"fileListContainer\">\n" +
"            <p style=\"color:var(--text-secondary);font-size:13px;text-align:center;margin:8px 0;\">No files staged on Android yet. Tap 'Send Files to iPhone' in the Android app.</p>\n" +
"        </div>\n" +
"        <button id=\"btnDownloadAll\" onclick=\"downloadAllFiles()\" class=\"btn btn-secondary\" style=\"display:none;margin-top:10px;\">📦 Download All (ZIP)</button>\n" +
"    </div>\n" +
"\n" +
"    <!-- Upload Dropzone (iPhone to Android) -->\n" +
"    <div class=\"card\">\n" +
"        <div class=\"card-header\">\n" +
"            <div id=\"uploadCardTitle\" class=\"card-title\">📤 Send Files to Android</div>\n" +
"        </div>\n" +
"        <div class=\"dropzone\" onclick=\"document.getElementById('fileInput').click()\">\n" +
"            <div style=\"font-size:36px;margin-bottom:8px;\">📁</div>\n" +
"            <div style=\"font-size:15px;font-weight:600;\">Tap to Choose Photos or Files</div>\n" +
"            <div style=\"font-size:12px;color:var(--text-secondary);margin-top:4px;\">Transfers straight to Android's Downloads folder</div>\n" +
"            <input type=\"file\" id=\"fileInput\" multiple style=\"display:none;\" onchange=\"handleFileSelect(this.files)\">\n" +
"        </div>\n" +
"\n" +
"        <div id=\"uploadProgressBox\" class=\"progress-box\">\n" +
"            <div style=\"display:flex;justify-content:space-between;font-size:13px;font-weight:600;\">\n" +
"                <span id=\"uploadFileName\" style=\"overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:200px;\">Uploading...</span>\n" +
"                <span id=\"uploadPercent\" style=\"color:var(--accent-cyan);\">0%</span>\n" +
"            </div>\n" +
"            <div class=\"progress-bar-bg\"><div id=\"uploadBarFill\" class=\"progress-bar-fill\"></div></div>\n" +
"            <div style=\"display:flex;justify-content:space-between;font-size:11px;color:var(--text-secondary);\">\n" +
"                <span id=\"uploadDetail\">0 MB / 0 MB</span>\n" +
"                <span id=\"uploadSpeed\">⚡ 0.0 MB/s</span>\n" +
"            </div>\n" +
"            <div style=\"display:flex;gap:10px;margin-top:12px;\">\n" +
"                <button id=\"btnUploadPauseResume\" onclick=\"toggleUploadPauseResume()\" class=\"btn\" style=\"flex:1;padding:12px;font-size:14px;font-weight:700;background:#F59E0B;color:#fff;border-radius:10px;margin-bottom:0;\">⏹️ Stop</button>\n" +
"                <button id=\"btnUploadCancel\" onclick=\"cancelUpload()\" class=\"btn\" style=\"flex:1;padding:12px;font-size:14px;font-weight:700;background:#EF4444;color:#fff;border-radius:10px;margin-bottom:0;\">❌ Cancel</button>\n" +
"            </div>\n" +
"        </div>\n" +
"    </div>\n" +
"\n" +
"    <!-- Clipboard Sync -->\n" +
"    <div class=\"card\">\n" +
"        <div class=\"card-header\">\n" +
"            <div class=\"card-title\">📋 Clipboard Sync</div>\n" +
"        </div>\n" +
"        <div style=\"font-size:12px;color:var(--text-secondary);margin-bottom:4px;\">Android Clipboard:</div>\n" +
"        <div id=\"androidClipboardText\" class=\"clipboard-box\">(empty)</div>\n" +
"        <button onclick=\"copyAndroidClipboard()\" class=\"btn btn-secondary\" style=\"margin-bottom:12px;\">📋 Copy to iPhone</button>\n" +
"        <textarea id=\"txtSendClipboard\" rows=\"2\" placeholder=\"Type text or paste link to send to Android...\"></textarea>\n" +
"        <button onclick=\"sendToAndroidClipboard()\" class=\"btn btn-secondary\">📤 Send to Android Clipboard</button>\n" +
"    </div>\n" +
"\n" +
"    <div id=\"toast\" class=\"toast\">Copied!</div>\n" +
"\n" +
"    <script>\n" +
"        let stagedFiles = [];\n" +
"        let currentAndroidClipboard = '';\n" +
"        let currentTargetDevice = 'tablet';\n" +
"        let detectedDevices = null;\n" +
"\n" +
"        function getTargetBaseUrl() {\n" +
"            if (!detectedDevices || !detectedDevices.peer) return '';\n" +
"            if (detectedDevices.current && detectedDevices.current.type === 'tablet' && currentTargetDevice === 'pc') {\n" +
"                return 'http://' + detectedDevices.peer.ip + ':' + (detectedDevices.peer.port || 8080);\n" +
"            }\n" +
"            if (detectedDevices.current && detectedDevices.current.type === 'pc' && currentTargetDevice === 'tablet') {\n" +
"                return 'http://' + detectedDevices.peer.ip + ':' + (detectedDevices.peer.port || 8080);\n" +
"            }\n" +
"            return '';\n" +
"        }\n" +
"\n" +
"        async function loadDevices() {\n" +
"            try {\n" +
"                const res = await fetch('/api/devices');\n" +
"                if (!res.ok) return;\n" +
"                detectedDevices = await res.json();\n" +
"                const bar = document.getElementById('deviceSwitcherBar');\n" +
"                if (detectedDevices && detectedDevices.peer) {\n" +
"                    bar.style.display = 'flex';\n" +
"                    const tabletName = (detectedDevices.current && detectedDevices.current.type === 'tablet') ? detectedDevices.current.name : (detectedDevices.peer.name || 'Samsung Tablet');\n" +
"                    const pcName = (detectedDevices.current && detectedDevices.current.type === 'pc') ? detectedDevices.current.name : (detectedDevices.peer.name || 'Windows PC');\n" +
"                    document.getElementById('pillTabletLabel').innerText = tabletName;\n" +
"                    document.getElementById('pillPCLabel').innerText = pcName;\n" +
"                    const saved = localStorage.getItem('airbeam_target_device');\n" +
"                    if (saved === 'pc' || saved === 'tablet') {\n" +
"                        switchTargetDevice(saved, false);\n" +
"                    }\n" +
"                }\n" +
"            } catch (e) {}\n" +
"        }\n" +
"\n" +
"        function switchTargetDevice(target, save) {\n" +
"            if (save === undefined) save = true;\n" +
"            currentTargetDevice = target;\n" +
"            if (save) {\n" +
"                try { localStorage.setItem('airbeam_target_device', target); } catch (e) {}\n" +
"            }\n" +
"            const pillTablet = document.getElementById('pillTablet');\n" +
"            const pillPC = document.getElementById('pillPC');\n" +
"            const uploadTitle = document.getElementById('uploadCardTitle');\n" +
"            const stagedTitle = document.getElementById('stagedCardTitle');\n" +
"            const targetStatusText = document.getElementById('targetStatusText');\n" +
"\n" +
"            if (target === 'pc') {\n" +
"                if (pillTablet) pillTablet.classList.remove('active');\n" +
"                if (pillPC) pillPC.classList.add('active');\n" +
"                if (uploadTitle) uploadTitle.innerText = '📤 Send Files to Windows PC';\n" +
"                if (stagedTitle) stagedTitle.innerText = '📥 Files from Windows PC';\n" +
"                if (targetStatusText) targetStatusText.innerText = '● Windows PC Selected';\n" +
"                showToast('Target: Windows PC');\n" +
"            } else {\n" +
"                if (pillTablet) pillTablet.classList.add('active');\n" +
"                if (pillPC) pillPC.classList.remove('active');\n" +
"                if (uploadTitle) uploadTitle.innerText = '📤 Send Files to Android';\n" +
"                if (stagedTitle) stagedTitle.innerText = '📥 Files from Android';\n" +
"                if (targetStatusText) targetStatusText.innerText = '● Android Tablet Selected';\n" +
"                showToast('Target: Samsung Tablet');\n" +
"            }\n" +
"            fetchFiles();\n" +
"            fetchClipboard();\n" +
"            checkServerTransferStatus();\n" +
"        }\n" +
"\n" +
"        function showToast(msg) {\n" +
"            const t = document.getElementById('toast');\n" +
"            t.innerText = msg;\n" +
"            t.style.display = 'block';\n" +
"            setTimeout(() => { t.style.display = 'none'; }, 2500);\n" +
"        }\n" +
"\n" +
"        async function fetchFiles() {\n" +
"            try {\n" +
"                const res = await fetch(getTargetBaseUrl() + '/api/files');\n" +
"                stagedFiles = await res.json();\n" +
"                renderFiles();\n" +
"            } catch (e) {}\n" +
"        }\n" +
"\n" +
"        function renderFiles() {\n" +
"            const container = document.getElementById('fileListContainer');\n" +
"            const badge = document.getElementById('fileCountBadge');\n" +
"            const btnAll = document.getElementById('btnDownloadAll');\n" +
"            badge.innerText = `${stagedFiles.length} file${stagedFiles.length === 1 ? '' : 's'}`;\n" +
"            if (stagedFiles.length === 0) {\n" +
"                container.innerHTML = '<p style=\"color:var(--text-secondary);font-size:13px;text-align:center;margin:8px 0;\">No files staged on Android yet. Tap \"Send Files to iPhone\" in the Android app.</p>';\n" +
"                btnAll.style.display = 'none';\n" +
"                return;\n" +
"            }\n" +
"            btnAll.style.display = stagedFiles.length > 1 ? 'block' : 'none';\n" +
"            let html = '';\n" +
"            stagedFiles.forEach(f => {\n" +
"                html += `\n" +
"                    <div class=\"file-item\">\n" +
"                        <div class=\"file-info\">\n" +
"                            <div class=\"file-name\">${f.name}</div>\n" +
"                            <div class=\"file-size\">${f.formatted_size}</div>\n" +
"                        </div>\n" +
"                        <a href=\"${getTargetBaseUrl()}/download?id=${f.index}\" class=\"btn-download\" download=\"${f.name}\">⬇️ Download</a>\n" +
"                    </div>\n" +
"                `;\n" +
"            });\n" +
"            container.innerHTML = html;\n" +
"        }\n" +
"\n" +
"        function copyUploadEndpoint() {\n" +
"            const url = 'http://airbeam.local:" + serverPort + "/upload';\n" +
"            navigator.clipboard.writeText(url).then(() => showToast('📋 Upload URL copied!')).catch(() => {\n" +
"                fallbackCopy(url);\n" +
"            });\n" +
"        }\n" +
"\n" +
"        async function fetchClipboard() {\n" +
"            try {\n" +
"                const res = await fetch(getTargetBaseUrl() + '/api/clipboard');\n" +
"                const data = await res.json();\n" +
"                currentAndroidClipboard = data.text || '';\n" +
"                const el = document.getElementById('androidClipboardText');\n" +
"                el.innerText = currentAndroidClipboard.trim() ? currentAndroidClipboard : '(empty)';\n" +
"            } catch (e) {}\n" +
"        }\n" +
"\n" +
"        function copyAndroidClipboard() {\n" +
"            if (!currentAndroidClipboard) return;\n" +
"            navigator.clipboard.writeText(currentAndroidClipboard).then(() => showToast('📋 Copied!')).catch(() => fallbackCopy(currentAndroidClipboard));\n" +
"        }\n" +
"\n" +
"        async function sendToAndroidClipboard() {\n" +
"            const txt = document.getElementById('txtSendClipboard').value.trim();\n" +
"            if (!txt) return;\n" +
"            try {\n" +
"                const res = await fetch(getTargetBaseUrl() + '/api/clipboard', {\n" +
"                    method: 'POST',\n" +
"                    headers: { 'Content-Type': 'application/json' },\n" +
"                    body: JSON.stringify({ text: txt })\n" +
"                });\n" +
"                if (res.ok) {\n" +
"                    showToast('📋 Sent to Android!');\n" +
"                    document.getElementById('txtSendClipboard').value = '';\n" +
"                    fetchClipboard();\n" +
"                }\n" +
"            } catch (e) {\n" +
"                showToast('Error sending clipboard');\n" +
"            }\n" +
"        }\n" +
"\n" +
"        function fallbackCopy(text) {\n" +
"            try {\n" +
"                const ta = document.createElement('textarea');\n" +
"                ta.value = text;\n" +
"                document.body.appendChild(ta);\n" +
"                ta.select();\n" +
"                document.execCommand('copy');\n" +
"                document.body.removeChild(ta);\n" +
"                showToast('📋 Copied!');\n" +
"            } catch (e) { showToast('Copied!'); }\n" +
"        }\n" +
"\n" +
"        function downloadAllFiles() {\n" +
"            window.location.href = getTargetBaseUrl() + '/download-all.zip';\n" +
"        }\n" +
"\n" +
"        let currentUploadXhr = null;\n" +
"        let isUploadPaused = false;\n" +
"        let isUploadCancelled = false;\n" +
"        let activeUploadFiles = [];\n" +
"        let activeUploadIndex = 0;\n" +
"\n" +
"        function toggleUploadPauseResume() {\n" +
"            isUploadPaused = !isUploadPaused;\n" +
"            const btn = document.getElementById('btnUploadPauseResume');\n" +
"            const speedEl = document.getElementById('uploadSpeed');\n" +
"            if (isUploadPaused) {\n" +
"                if (btn) { btn.innerText = '▶️ Resume'; btn.style.background = '#10B981'; }\n" +
"                if (speedEl) speedEl.innerText = '⏹️ Stopped';\n" +
"                showToast('⏹️ Upload stopped');\n" +
"            } else {\n" +
"                if (btn) { btn.innerText = '⏹️ Stop'; btn.style.background = '#F59E0B'; }\n" +
"                showToast('▶️ Upload resumed');\n" +
"            }\n" +
"        }\n" +
"\n" +
"        async function checkServerTransferStatus() {\n" +
"            try {\n" +
"                const res = await fetch(getTargetBaseUrl() + '/api/transfer/status');\n" +
"                if (!res.ok) return;\n" +
"                const data = await res.json();\n" +
"                const card = document.getElementById('liveTransferCard');\n" +
"                if (!card) return;\n" +
"                if (data.active) {\n" +
"                    card.style.display = 'block';\n" +
"                    document.getElementById('liveTransferFilename').innerText = data.filename || 'Active Transfer';\n" +
"                    document.getElementById('liveTransferPercent').innerText = (data.percent || 0) + '%';\n" +
"                    document.getElementById('liveTransferFill').style.width = (data.percent || 0) + '%';\n" +
"                    const mbDone = ((data.transferred || 0) / (1024 * 1024)).toFixed(1);\n" +
"                    const mbTotal = ((data.total || 0) / (1024 * 1024)).toFixed(1);\n" +
"                    document.getElementById('liveTransferBytes').innerText = mbDone + ' MB / ' + mbTotal + ' MB';\n" +
"                    const speed = (data.speed_mbps || 0).toFixed(1);\n" +
"                    const btnStop = document.getElementById('btnLiveTransferStop');\n" +
"                    if (data.is_paused) {\n" +
"                        document.getElementById('liveTransferSpeed').innerText = '⏹️ Stopped';\n" +
"                        if (btnStop) { btnStop.innerText = '▶️ Resume'; btnStop.style.background = '#10B981'; }\n" +
"                    } else {\n" +
"                        document.getElementById('liveTransferSpeed').innerText = '⚡ ' + speed + ' MB/s';\n" +
"                        if (btnStop) { btnStop.innerText = '⏹️ Stop'; btnStop.style.background = '#F59E0B'; }\n" +
"                    }\n" +
"                } else {\n" +
"                    card.style.display = 'none';\n" +
"                }\n" +
"            } catch (e) {}\n" +
"        }\n" +
"\n" +
"        async function toggleServerTransfer() {\n" +
"            try {\n" +
"                const res = await fetch(getTargetBaseUrl() + '/api/transfer/toggle_pause', { method: 'POST' });\n" +
"                const data = await res.json();\n" +
"                const btn = document.getElementById('btnLiveTransferStop');\n" +
"                if (data.is_paused) {\n" +
"                    if (btn) { btn.innerText = '▶️ Resume'; btn.style.background = '#10B981'; }\n" +
"                    showToast('⏹️ Transfer stopped');\n" +
"                } else {\n" +
"                    if (btn) { btn.innerText = '⏹️ Stop'; btn.style.background = '#F59E0B'; }\n" +
"                    showToast('▶️ Transfer resumed');\n" +
"                }\n" +
"            } catch (e) { showToast('Action failed'); }\n" +
"        }\n" +
"\n" +
"        async function cancelServerTransfer() {\n" +
"            try {\n" +
"                await fetch(getTargetBaseUrl() + '/api/transfer/cancel', { method: 'POST' });\n" +
"                const card = document.getElementById('liveTransferCard');\n" +
"                if (card) card.style.display = 'none';\n" +
"                showToast('❌ Transfer cancelled');\n" +
"            } catch (e) { showToast('Cancel failed'); }\n" +
"        }\n" +
"\n" +
"        async function cancelUpload() {\n" +
"            isUploadCancelled = true;\n" +
"            isUploadPaused = false;\n" +
"            if (currentUploadXhr) {\n" +
"                try { currentUploadXhr.abort(); } catch (e) {}\n" +
"                currentUploadXhr = null;\n" +
"            }\n" +
"            const curFile = activeUploadFiles[activeUploadIndex];\n" +
"            if (curFile) {\n" +
"                try {\n" +
"                    fetch(getTargetBaseUrl() + '/upload?action=cancel&filename=' + encodeURIComponent(curFile.name), { method: 'POST' });\n" +
"                } catch (e) {}\n" +
"            }\n" +
"            document.getElementById('uploadProgressBox').style.display = 'none';\n" +
"            document.getElementById('fileInput').value = '';\n" +
"            showToast('❌ Upload cancelled');\n" +
"        }\n" +
"\n" +
"        async function handleFileSelect(files) {\n" +
"            if (!files || files.length === 0) return;\n" +
"            activeUploadFiles = Array.from(files);\n" +
"            activeUploadIndex = 0;\n" +
"            isUploadPaused = false;\n" +
"            isUploadCancelled = false;\n" +
"\n" +
"            const progressBox = document.getElementById('uploadProgressBox');\n" +
"            const fileNameEl = document.getElementById('uploadFileName');\n" +
"            const barFill = document.getElementById('uploadBarFill');\n" +
"            const speedEl = document.getElementById('uploadSpeed');\n" +
"            const percentEl = document.getElementById('uploadPercent');\n" +
"            const detailEl = document.getElementById('uploadDetail');\n" +
"            const btnPause = document.getElementById('btnUploadPauseResume');\n" +
"\n" +
"            if (btnPause) {\n" +
"                btnPause.innerText = '⏹️ Stop';\n" +
"                btnPause.style.background = '#F59E0B';\n" +
"            }\n" +
"            progressBox.style.display = 'block';\n" +
"\n" +
"            const CHUNK_SIZE = 2 * 1024 * 1024; // 2MB slice per chunk\n" +
"\n" +
"            for (activeUploadIndex = 0; activeUploadIndex < activeUploadFiles.length; activeUploadIndex++) {\n" +
"                if (isUploadCancelled) break;\n" +
"                const file = activeUploadFiles[activeUploadIndex];\n" +
"                fileNameEl.innerText = file.name;\n" +
"                barFill.style.width = '0%';\n" +
"                percentEl.innerText = '0%';\n" +
"                detailEl.innerText = `0 MB / ${(file.size / (1024*1024)).toFixed(1)} MB`;\n" +
"\n" +
"                let offset = 0;\n" +
"                let lastTime = Date.now();\n" +
"                let lastLoaded = 0;\n" +
"\n" +
"                while (offset < file.size) {\n" +
"                    if (isUploadCancelled) break;\n" +
"                    while (isUploadPaused && !isUploadCancelled) {\n" +
"                        await new Promise(r => setTimeout(r, 200));\n" +
"                    }\n" +
"                    if (isUploadCancelled) break;\n" +
"\n" +
"                    const chunkEnd = Math.min(offset + CHUNK_SIZE, file.size);\n" +
"                    const chunk = file.slice(offset, chunkEnd);\n" +
"                    const isLast = (chunkEnd >= file.size);\n" +
"\n" +
"                    const chunkOk = await new Promise((resolve) => {\n" +
"                        const xhr = new XMLHttpRequest();\n" +
"                        currentUploadXhr = xhr;\n" +
"\n" +
"                        xhr.upload.onprogress = (e) => {\n" +
"                            if (isUploadCancelled || isUploadPaused) return;\n" +
"                            const curTotal = offset + e.loaded;\n" +
"                            const pct = Math.round((curTotal / file.size) * 100);\n" +
"                            barFill.style.width = pct + '%';\n" +
"                            percentEl.innerText = pct + '%';\n" +
"                            detailEl.innerText = `${(curTotal / (1024*1024)).toFixed(1)} MB / ${(file.size / (1024*1024)).toFixed(1)} MB`;\n" +
"\n" +
"                            const now = Date.now();\n" +
"                            const dt = (now - lastTime) / 1000;\n" +
"                            if (dt >= 0.3) {\n" +
"                                const speedMB = ((curTotal - lastLoaded) / (1024 * 1024)) / dt;\n" +
"                                speedEl.innerText = `⚡ ${speedMB.toFixed(1)} MB/s`;\n" +
"                                lastTime = now;\n" +
"                                lastLoaded = curTotal;\n" +
"                            }\n" +
"                        };\n" +
"\n" +
"                        xhr.onload = () => {\n" +
"                            currentUploadXhr = null;\n" +
"                            resolve(xhr.status >= 200 && xhr.status < 300);\n" +
"                        };\n" +
"\n" +
"                        xhr.onerror = () => { currentUploadXhr = null; resolve(false); };\n" +
"                        xhr.onabort = () => { currentUploadXhr = null; resolve(false); };\n" +
"\n" +
"                        const url = getTargetBaseUrl() + '/upload?filename=' + encodeURIComponent(file.name) + '&offset=' + offset + '&total=' + file.size + (isLast ? '&last=1' : '');\n" +
"                        xhr.open('POST', url, true);\n" +
"                        xhr.setRequestHeader('x-file-name', encodeURIComponent(file.name));\n" +
"                        xhr.setRequestHeader('x-file-offset', offset.toString());\n" +
"                        xhr.setRequestHeader('x-file-total', file.size.toString());\n" +
"                        xhr.send(chunk);\n" +
"                    });\n" +
"\n" +
"                    if (isUploadCancelled) break;\n" +
"                    if (!chunkOk) {\n" +
"                        if (!isUploadPaused) {\n" +
"                            showToast(`❌ Upload error: ${file.name}`);\n" +
"                            break;\n" +
"                        }\n" +
"                    } else {\n" +
"                        offset = chunkEnd;\n" +
"                    }\n" +
"                }\n" +
"\n" +
"                if (!isUploadCancelled && offset >= file.size) {\n" +
"                    showToast(`✅ ${file.name} uploaded!`);\n" +
"                }\n" +
"            }\n" +
"\n" +
"            if (!isUploadCancelled) {\n" +
"                setTimeout(() => { progressBox.style.display = 'none'; }, 2000);\n" +
"                document.getElementById('fileInput').value = '';\n" +
"            }\n" +
"        }\n" +
"        loadDevices();\n" +
"        fetchFiles();\n" +
"        fetchClipboard();\n" +
"        checkServerTransferStatus();\n" +
"        setInterval(loadDevices, 5000);\n" +
"        setInterval(fetchFiles, 3000);\n" +
"        setInterval(fetchClipboard, 5000);\n" +
"        setInterval(checkServerTransferStatus, 1000);\n" +
"    </script>\n" +
"</body>\n" +
"</html>";
    }
}
