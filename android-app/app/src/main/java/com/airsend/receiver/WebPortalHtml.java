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
"    <!-- iOS AirDrop Share Sheet Card -->\n" +
"    <div class=\"card\">\n" +
"        <div class=\"card-header\">\n" +
"            <div class=\"card-title\">⚡ iOS AirDrop Share Sheet</div>\n" +
"            <span class=\"badge\" style=\"margin-top:0;background:rgba(139,92,246,0.18);color:#A78BFA;border-color:rgba(139,92,246,0.3);\">AirDrop Mode</span>\n" +
"        </div>\n" +
"        <p style=\"font-size:13px;color:var(--text-secondary);margin:0 0 14px;\">\n" +
"            Beam photos, 4K videos, and files directly from your iPhone's native <b>Share</b> menu without opening Safari every time!\n" +
"        </p>\n" +
"        <a href=\"" + ICLOUD_SHORTCUT_URL + "\" class=\"btn btn-shortcut\">⚡ Download iOS Shortcut (1-Click)</a>\n" +
"        <button id=\"btnCopyEndpoint\" onclick=\"copyUploadEndpoint()\" class=\"btn btn-secondary\">📋 Copy Upload URL</button>\n" +
"        <div style=\"background:#162032;border-radius:12px;padding:12px;margin-top:12px;font-size:12px;color:#94A3B8;line-height:1.5;\">\n" +
"            <b>💡 Easy Setup:</b><br>\n" +
"            1. Tap <b>Download iOS Shortcut</b> above to install with Apple ID signing.<br>\n" +
"            2. In iPhone <b>Photos</b> or <b>Files</b>, select media & tap <b>Share ➔ AirBeam to PC / Android</b>.<br>\n" +
"            3. Works seamlessly over Wi-Fi or Hotspot!\n" +
"        </div>\n" +
"    </div>\n" +
"\n" +
"    <!-- Staged Files for iPhone -->\n" +
"    <div class=\"card\">\n" +
"        <div class=\"card-header\">\n" +
"            <div class=\"card-title\">📥 Files from Android</div>\n" +
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
"            <div class=\"card-title\">📤 Send Files to Android</div>\n" +
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
"                <button id=\"btnUploadPauseResume\" onclick=\"toggleUploadPauseResume()\" class=\"btn\" style=\"flex:1;padding:10px;font-size:13px;background:#F59E0B;color:#fff;border-radius:10px;margin-bottom:0;\">⏸️ Pause</button>\n" +
"                <button id=\"btnUploadCancel\" onclick=\"cancelUpload()\" class=\"btn\" style=\"flex:1;padding:10px;font-size:13px;background:#EF4444;color:#fff;border-radius:10px;margin-bottom:0;\">❌ Cancel</button>\n" +
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
"                const res = await fetch('/api/files');\n" +
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
"                        <a href=\"/download?id=${f.index}\" class=\"btn-download\" download=\"${f.name}\">⬇️ Download</a>\n" +
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
"                const res = await fetch('/api/clipboard');\n" +
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
"                const res = await fetch('/api/clipboard', {\n" +
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
"            window.location.href = '/download-all.zip';\n" +
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
"                if (speedEl) speedEl.innerText = '⏸️ Paused';\n" +
"                showToast('⏸️ Upload paused');\n" +
"            } else {\n" +
"                if (btn) { btn.innerText = '⏸️ Pause'; btn.style.background = '#F59E0B'; }\n" +
"                showToast('▶️ Upload resumed');\n" +
"            }\n" +
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
"                    fetch('/upload?action=cancel&filename=' + encodeURIComponent(curFile.name), { method: 'POST' });\n" +
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
"                btnPause.innerText = '⏸️ Pause';\n" +
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
"                        const url = '/upload?filename=' + encodeURIComponent(file.name) + '&offset=' + offset + '&total=' + file.size + (isLast ? '&last=1' : '');\n" +
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
"        fetchFiles();\n" +
"        fetchClipboard();\n" +
"        setInterval(fetchFiles, 3000);\n" +
"        setInterval(fetchClipboard, 5000);\n" +
"    </script>\n" +
"</body>\n" +
"</html>";
    }
}
