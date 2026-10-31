package com.airsend.receiver;

import android.Manifest;
import android.app.DownloadManager;
import android.content.BroadcastReceiver;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.ServiceConnection;
import android.content.ClipboardManager;
import android.content.ClipData;
import android.net.Uri;
import android.net.wifi.WifiManager;
import android.os.Handler;
import android.os.Looper;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.IBinder;
import android.view.View;
import android.widget.Button;
import androidx.annotation.Nullable;
import android.util.Log;
import android.widget.ImageView;
import android.graphics.Bitmap;
import com.google.zxing.BarcodeFormat;
import com.google.zxing.qrcode.QRCodeWriter;
import com.google.zxing.common.BitMatrix;
import android.provider.OpenableColumns;
import android.database.Cursor;
import android.widget.TextView;
import android.widget.Toast;

import android.location.LocationManager;
import android.provider.Settings;
import androidx.appcompat.app.AlertDialog;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.widget.SwitchCompat;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class MainActivity extends AppCompatActivity implements FileServerService.OnTransferListener {

    private static final int PERMISSION_REQ_CODE = 101;

    private TextView tvStatus;
    private TextView tvIpAddress;
    private View statusDot;
    private Button btnToggleServer;
    private Button btnOpenDownloads;
    private TextView tvEmpty;
    private RecyclerView rvTransfers;
    private TransferAdapter adapter;

    private FileServerService fileServerService;
    private boolean isBound = false;
    public static final String PREF_MODE = "pref_connection_mode";
    public static final String MODE_TABLET_HOTSPOT = "TABLET_HOTSPOT";
    public static final String MODE_LAPTOP_HOTSPOT = "LAPTOP_HOTSPOT";
    public static final String MODE_ROUTER = "ROUTER";

    private Button btnModeTabletHotspot;
    private Button btnModeLaptopHotspot;
    private Button btnModeRouter;
    private TextView tvModeDescription;
    private TextView tvHotspotSsid;
    private TextView tvHotspotPass;
    private LinearLayout layoutHotspotHelper;
    private String currentMode = MODE_TABLET_HOTSPOT;

    // Hotspot Toggle Switch & Status
    private SwitchCompat switchHotspot;
    private TextView tvHotspotSwitchSubtitle;
    private boolean isUpdatingSwitchFromSystem = false;

    // Active Live Transfer Card
    private LinearLayout cardActiveTransfer;
    private TextView tvActiveFileName;
    private TextView tvActiveSpeed;
    private ProgressBar pbActiveTransfer;
    private TextView tvActiveProgressDetail;
    private TextView tvActivePercent;

    // Web Portal & iOS AirDrop
    private TextView tvPortalUrl;
    private Button btnCopyPortalUrl;
    private ImageView ivPortalQr;
    private TextView tvStagedCount;
    private Button btnStageFiles;
    private Button btnClearStaged;
    private static final int REQUEST_CODE_STAGE_FILES = 202;

    // Hotspot Wi-Fi QR Code Auto-Connect
    private LinearLayout layoutHotspotQrBox;
    private ImageView ivHotspotQr;

    // Active Transfer Controls
    private Button btnActivePauseResume;
    private Button btnActiveCancel;

    private final BroadcastReceiver clipboardReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            String text = intent.getStringExtra("text");
            if (text != null && (text.startsWith("http://") || text.startsWith("https://"))) {
                showOpenUrlDialog(text);
            }
        }
    };

    private final ServiceConnection serviceConnection = new ServiceConnection() {
        @Override
        public void onServiceConnected(ComponentName name, IBinder service) {
            FileServerService.LocalBinder binder = (FileServerService.LocalBinder) service;
            fileServerService = binder.getService();
            fileServerService.setTransferListener(MainActivity.this);
            fileServerService.setConnectionMode(currentMode);
            isBound = true;
            updateServerStatus(true);
        }

        @Override
        public void onServiceDisconnected(ComponentName name) {
            fileServerService = null;
            isBound = false;
            updateServerStatus(false);
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        tvStatus = findViewById(R.id.tvStatus);
        tvIpAddress = findViewById(R.id.tvIpAddress);
        statusDot = findViewById(R.id.statusDot);
        btnToggleServer = findViewById(R.id.btnToggleServer);
        btnOpenDownloads = findViewById(R.id.btnOpenDownloads);
        tvEmpty = findViewById(R.id.tvEmpty);
        rvTransfers = findViewById(R.id.rvTransfers);

        btnModeTabletHotspot = findViewById(R.id.btnModeTabletHotspot);
        btnModeLaptopHotspot = findViewById(R.id.btnModeLaptopHotspot);
        btnModeRouter = findViewById(R.id.btnModeRouter);
        tvModeDescription = findViewById(R.id.tvModeDescription);
        tvHotspotSsid = findViewById(R.id.tvHotspotSsid);
        tvHotspotPass = findViewById(R.id.tvHotspotPass);
        layoutHotspotHelper = findViewById(R.id.layoutHotspotHelper);

        // Toggle Switch Row
        switchHotspot = findViewById(R.id.switchHotspot);
        tvHotspotSwitchSubtitle = findViewById(R.id.tvHotspotSwitchSubtitle);

        // Active Live Transfer Card
        cardActiveTransfer = findViewById(R.id.cardActiveTransfer);
        tvActiveFileName = findViewById(R.id.tvActiveFileName);
        tvActiveSpeed = findViewById(R.id.tvActiveSpeed);
        pbActiveTransfer = findViewById(R.id.pbActiveTransfer);
        tvActiveProgressDetail = findViewById(R.id.tvActiveProgressDetail);
        tvActivePercent = findViewById(R.id.tvActivePercent);

        Button btnCopySsid = findViewById(R.id.btnCopySsid);
        // Web Portal & iOS AirDrop Views
        tvPortalUrl = findViewById(R.id.tvPortalUrl);
        btnCopyPortalUrl = findViewById(R.id.btnCopyPortalUrl);
        ivPortalQr = findViewById(R.id.ivPortalQr);
        tvStagedCount = findViewById(R.id.tvStagedCount);
        btnStageFiles = findViewById(R.id.btnStageFiles);
        btnClearStaged = findViewById(R.id.btnClearStaged);

        if (btnCopyPortalUrl != null) {
            btnCopyPortalUrl.setOnClickListener(v -> copyToClipboard("Web Portal URL", "http://airbeam.local:8080"));
        }
        if (btnStageFiles != null) {
            btnStageFiles.setOnClickListener(v -> openFilePickerToStage());
        }
        if (btnClearStaged != null) {
            btnClearStaged.setOnClickListener(v -> {
                FileServerService.clearStagedFiles();
                updateStagedFilesUi();
                Toast.makeText(this, "Staged files cleared", Toast.LENGTH_SHORT).show();
            });
        }
        generatePortalQrCode();
        updateStagedFilesUi();
        handleShareIntent(getIntent());

        // Hotspot Wi-Fi QR View
        layoutHotspotQrBox = findViewById(R.id.layoutHotspotQrBox);
        ivHotspotQr = findViewById(R.id.ivHotspotQr);

        // Active Transfer Controls
        btnActivePauseResume = findViewById(R.id.btnActivePauseResume);
        btnActiveCancel = findViewById(R.id.btnActiveCancel);

        if (btnActivePauseResume != null) {
            btnActivePauseResume.setOnClickListener(v -> {
                if (fileServerService != null) {
                    boolean paused = fileServerService.togglePauseActiveTransfer();
                    if (paused) {
                        btnActivePauseResume.setText("▶️ Resume");
                        btnActivePauseResume.setBackgroundTintList(android.content.res.ColorStateList.valueOf(0xFF10B981));
                        if (tvActiveSpeed != null) tvActiveSpeed.setText("⏹️ Stopped");
                        Toast.makeText(this, "Transfer stopped", Toast.LENGTH_SHORT).show();
                    } else {
                        btnActivePauseResume.setText("⏹️ Stop");
                        btnActivePauseResume.setBackgroundTintList(android.content.res.ColorStateList.valueOf(0xFFF59E0B));
                        Toast.makeText(this, "Transfer resumed", Toast.LENGTH_SHORT).show();
                    }
                }
            });
        }

        if (btnActiveCancel != null) {
            btnActiveCancel.setOnClickListener(v -> {
                if (fileServerService != null) {
                    fileServerService.cancelActiveTransfer();
                }
                if (cardActiveTransfer != null) {
                    cardActiveTransfer.setVisibility(View.GONE);
                }
                Toast.makeText(this, "❌ Transfer cancelled", Toast.LENGTH_SHORT).show();
            });
        }

        Button btnCopyPass = findViewById(R.id.btnCopyPass);
        if (btnCopySsid != null) {
            btnCopySsid.setOnClickListener(v -> copyToClipboard("SSID", tvHotspotSsid != null ? tvHotspotSsid.getText().toString() : "airbeam"));
        }
        if (btnCopyPass != null) {
            btnCopyPass.setOnClickListener(v -> copyToClipboard("Password", tvHotspotPass != null ? tvHotspotPass.getText().toString() : "airbeam123"));
        }

        currentMode = getSharedPreferences("airbeam_prefs", MODE_PRIVATE).getString(PREF_MODE, MODE_TABLET_HOTSPOT);
        updateModeUi();

        btnModeTabletHotspot.setOnClickListener(v -> setConnectionMode(MODE_TABLET_HOTSPOT));
        btnModeLaptopHotspot.setOnClickListener(v -> setConnectionMode(MODE_LAPTOP_HOTSPOT));
        btnModeRouter.setOnClickListener(v -> setConnectionMode(MODE_ROUTER));

        if (switchHotspot != null) {
            switchHotspot.setOnCheckedChangeListener((buttonView, isChecked) -> {
                if (isUpdatingSwitchFromSystem) return;
                openDefaultHotspotSettings();
                Toast.makeText(this, "Toggle Mobile Hotspot in Samsung Settings, then press Back", Toast.LENGTH_SHORT).show();
            });
        }

        adapter = new TransferAdapter(this);
        rvTransfers.setLayoutManager(new LinearLayoutManager(this));
        rvTransfers.setAdapter(adapter);

        btnOpenDownloads.setOnClickListener(v -> {
            try {
                Intent intent = new Intent(DownloadManager.ACTION_VIEW_DOWNLOADS);
                intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(intent);
            } catch (Exception e) {
                Toast.makeText(MainActivity.this, "Opening file explorer...", Toast.LENGTH_SHORT).show();
            }
        });

        btnToggleServer.setOnClickListener(v -> {
            if (isBound) {
                stopFileService();
            } else {
                startFileService();
            }
        });

        requestPermissionsIfNeeded();
        checkLocationServicesEnabled();
        startFileService();
        syncHotspotState();
    }

    private void showOpenUrlDialog(String url) {
        new AlertDialog.Builder(this)
                .setTitle("🔗 Link Received from PC")
                .setMessage(url)
                .setPositiveButton("Open in Browser", (dialog, which) -> {
                    try {
                        Intent browserIntent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                        browserIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                        startActivity(browserIntent);
                    } catch (Exception e) {
                        Toast.makeText(MainActivity.this, "Cannot open browser: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                    }
                })
                .setNegativeButton("Dismiss", null)
                .show();
    }

    private void syncHotspotState() {
        boolean active = FileServerService.isHotspotActive(this);
        String ip = FileServerService.getHotspotIpAddress(this);

        runOnUiThread(() -> {
            isUpdatingSwitchFromSystem = true;
            if (switchHotspot != null) {
                switchHotspot.setChecked(active);
            }
            if (layoutHotspotQrBox != null) {
                if (active) {
                    layoutHotspotQrBox.setVisibility(View.VISIBLE);
                    generateHotspotQrCode();
                } else {
                    layoutHotspotQrBox.setVisibility(View.GONE);
                }
            }
            if (tvHotspotSwitchSubtitle != null) {
                if (active) {
                    tvHotspotSwitchSubtitle.setText("ON — Active at " + ip);
                    tvHotspotSwitchSubtitle.setTextColor(0xFF10B981);
                } else {
                    tvHotspotSwitchSubtitle.setText("OFF — Tap switch to enable hotspot");
                    tvHotspotSwitchSubtitle.setTextColor(0xFF94A3B8);
                }
            }
            isUpdatingSwitchFromSystem = false;
        });
    }

    private void openDefaultHotspotSettings() {
        Intent intent = new Intent();
        intent.setClassName("com.android.settings", "com.android.settings.TetherSettings");
        try {
            startActivity(intent);
            return;
        } catch (Exception ignored) {}

        try {
            intent = new Intent(Settings.ACTION_WIRELESS_SETTINGS);
            startActivity(intent);
            return;
        } catch (Exception ignored) {}

        try {
            intent = new Intent(Settings.ACTION_SETTINGS);
            startActivity(intent);
        } catch (Exception e) {
            Toast.makeText(this, "Could not open Hotspot settings", Toast.LENGTH_SHORT).show();
        }
    }

    private void copyToClipboard(String label, String text) {
        try {
            ClipboardManager clipboard = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            ClipData clip = ClipData.newPlainText(label, text);
            if (clipboard != null) {
                clipboard.setPrimaryClip(clip);
            }
            Toast.makeText(this, label + " copied: " + text, Toast.LENGTH_SHORT).show();
        } catch (Exception e) {
            Toast.makeText(this, "Copy failed: " + e.getMessage(), Toast.LENGTH_SHORT).show();
        }
    }

    private void setConnectionMode(String mode) {
        currentMode = mode;
        getSharedPreferences("airbeam_prefs", MODE_PRIVATE).edit().putString(PREF_MODE, mode).apply();
        updateModeUi();
        if (fileServerService != null) {
            fileServerService.setConnectionMode(mode);
        }
        updateServerStatus(true);
        syncHotspotState();
    }

    private void updateModeUi() {
        int colorActive = 0xFF0284C7;
        int colorInactive = 0xFF334155;
        int textActive = 0xFFFFFFFF;
        int textInactive = 0xFF94A3B8;

        btnModeTabletHotspot.setEnabled(true);
        btnModeTabletHotspot.setAlpha(1.0f);
        btnModeTabletHotspot.setBackgroundColor(MODE_TABLET_HOTSPOT.equals(currentMode) ? colorActive : colorInactive);
        btnModeTabletHotspot.setTextColor(MODE_TABLET_HOTSPOT.equals(currentMode) ? textActive : textInactive);

        btnModeLaptopHotspot.setEnabled(true);
        btnModeLaptopHotspot.setAlpha(1.0f);
        btnModeLaptopHotspot.setBackgroundColor(MODE_LAPTOP_HOTSPOT.equals(currentMode) ? colorActive : colorInactive);
        btnModeLaptopHotspot.setTextColor(MODE_LAPTOP_HOTSPOT.equals(currentMode) ? textActive : textInactive);

        btnModeRouter.setEnabled(true);
        btnModeRouter.setAlpha(1.0f);
        btnModeRouter.setBackgroundColor(MODE_ROUTER.equals(currentMode) ? colorActive : colorInactive);
        btnModeRouter.setTextColor(MODE_ROUTER.equals(currentMode) ? textActive : textInactive);

        if (MODE_TABLET_HOTSPOT.equals(currentMode)) {
            tvModeDescription.setText("Tablet Hotspot Setup (SSID: airbeam | Pass: airbeam123):");
            if (layoutHotspotHelper != null) layoutHotspotHelper.setVisibility(View.VISIBLE);
        } else if (MODE_LAPTOP_HOTSPOT.equals(currentMode)) {
            tvModeDescription.setText("💻 Laptop Hotspot: On PC, click 'Start Hotspot'. Tablet connects automatically.");
            if (layoutHotspotHelper != null) layoutHotspotHelper.setVisibility(View.GONE);
        } else {
            tvModeDescription.setText("🏠 Home Wi-Fi: Both PC and Tablet on local Wi-Fi router network.");
            if (layoutHotspotHelper != null) layoutHotspotHelper.setVisibility(View.GONE);
        }
    }

    private void checkLocationServicesEnabled() {
        try {
            LocationManager lm = (LocationManager) getSystemService(Context.LOCATION_SERVICE);
            boolean isGps = lm != null && lm.isProviderEnabled(LocationManager.GPS_PROVIDER);
            boolean isNet = lm != null && lm.isProviderEnabled(LocationManager.NETWORK_PROVIDER);
            if (!isGps && !isNet) {
                new AlertDialog.Builder(this)
                        .setTitle("Turn On Location")
                        .setMessage("Android requires Location to be turned ON to detect the Windows Hotspot (joe). Tap Enable to turn on Location.")
                        .setPositiveButton("Enable", (dialog, which) -> {
                            startActivity(new Intent(Settings.ACTION_LOCATION_SOURCE_SETTINGS));
                        })
                        .setNegativeButton("Cancel", null)
                        .show();
            }
        } catch (Exception ignored) {}
    }

    private void requestPermissionsIfNeeded() {
        List<String> neededPermissions = new ArrayList<>();
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            neededPermissions.add(Manifest.permission.ACCESS_FINE_LOCATION);
        }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            neededPermissions.add(Manifest.permission.ACCESS_COARSE_LOCATION);
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                neededPermissions.add(Manifest.permission.POST_NOTIFICATIONS);
            }
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.NEARBY_WIFI_DEVICES) != PackageManager.PERMISSION_GRANTED) {
                neededPermissions.add(Manifest.permission.NEARBY_WIFI_DEVICES);
            }
        }
        if (Build.VERSION.SDK_INT <= Build.VERSION_CODES.Q) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED) {
                neededPermissions.add(Manifest.permission.WRITE_EXTERNAL_STORAGE);
            }
        }
        if (!neededPermissions.isEmpty()) {
            ActivityCompat.requestPermissions(this, neededPermissions.toArray(new String[0]), PERMISSION_REQ_CODE);
        }
    }

    private void startFileService() {
        Intent serviceIntent = new Intent(this, FileServerService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent);
        } else {
            startService(serviceIntent);
        }
        bindService(serviceIntent, serviceConnection, Context.BIND_AUTO_CREATE);
    }

    private void stopFileService() {
        if (isBound) {
            if (fileServerService != null) {
                fileServerService.setTransferListener(null);
            }
            unbindService(serviceConnection);
            isBound = false;
        }
        Intent serviceIntent = new Intent(this, FileServerService.class);
        stopService(serviceIntent);
        updateServerStatus(false);
    }

    private void updateServerStatus(boolean running) {
        runOnUiThread(() -> {
            if (running) {
                String ip = FileServerService.getLocalIpAddress(this);
                if (ip == null || ip.equals("127.0.0.1")) {
                    ip = "10.150.131.50";
                }
                tvIpAddress.setText("http://" + ip + ":" + FileServerService.NIO_PORT);
                if (ip.startsWith("192.168.43.")) {
                    tvStatus.setText("🚀 Tablet Hotspot Active (airbeam) — 50-95+ MB/s");
                    tvStatus.setTextColor(0xFF38BDF8);
                } else if (ip.startsWith("192.168.137.")) {
                    tvStatus.setText("🚀 Connected to Windows Hotspot (50-95+ MB/s)");
                    tvStatus.setTextColor(0xFF38BDF8);
                } else {
                    tvStatus.setText("Ready on Wi-Fi: " + ip);
                    tvStatus.setTextColor(0xFF22C55E);
                }
                statusDot.setBackgroundResource(R.drawable.bg_badge);
                btnToggleServer.setText("Running");
                btnToggleServer.setBackgroundColor(0xFF2563EB);
            } else {
                tvIpAddress.setText("http://10.150.131.50:" + FileServerService.PORT);
                tvStatus.setText("Receiver Inactive");
                tvStatus.setTextColor(0xFFEF4444);
                btnToggleServer.setText("Start");
                btnToggleServer.setBackgroundColor(0xFF64748B);
            }
        });
    }

    @Override
    public void onTransferStart(TransferItem item) {
        runOnUiThread(() -> {
            tvEmpty.setVisibility(View.GONE);
            rvTransfers.setVisibility(View.VISIBLE);
            adapter.addOrUpdate(item);

            if (cardActiveTransfer != null) {
                cardActiveTransfer.setVisibility(View.VISIBLE);
                if (btnActivePauseResume != null) {
                    btnActivePauseResume.setText("⏹️ Stop");
                    btnActivePauseResume.setBackgroundTintList(android.content.res.ColorStateList.valueOf(0xFFF59E0B));
                }
                tvActiveFileName.setText(item.getFileName());
                tvActiveSpeed.setText("⚡ 0.0 MB/s");
                pbActiveTransfer.setProgress(0);
                tvActivePercent.setText("0%");
                tvActiveProgressDetail.setText("0 B / " + formatSize(item.getTotalBytes()));
            }
        });
    }

    @Override
    public void onTransferProgress(TransferItem item) {
        runOnUiThread(() -> {
            adapter.addOrUpdate(item);

            if (cardActiveTransfer != null) {
                cardActiveTransfer.setVisibility(View.VISIBLE);
                tvActiveFileName.setText(item.getFileName());
                double spd = item.getSpeedMBps();
                if (spd > 0) {
                    tvActiveSpeed.setText(String.format(Locale.US, "⚡ %.1f MB/s", spd));
                }
                pbActiveTransfer.setProgress(item.getProgressPercent());
                tvActivePercent.setText(item.getProgressPercent() + "%");
                tvActiveProgressDetail.setText(formatSize(item.getTransferredBytes()) + " / " + formatSize(item.getTotalBytes()));
            }
        });
    }

    @Override
    public void onTransferComplete(TransferItem item) {
        runOnUiThread(() -> {
            adapter.addOrUpdate(item);
            if (cardActiveTransfer != null) {
                cardActiveTransfer.setVisibility(View.GONE);
            }
            Toast.makeText(this, "Received: " + item.getFileName(), Toast.LENGTH_SHORT).show();
        });
    }

    @Override
    public void onTransferFailed(TransferItem item, String error) {
        runOnUiThread(() -> {
            adapter.addOrUpdate(item);
            if (cardActiveTransfer != null) {
                cardActiveTransfer.setVisibility(View.GONE);
            }
            Toast.makeText(this, "Failed: " + item.getFileName() + " (" + error + ")", Toast.LENGTH_SHORT).show();
        });
    }

    private String formatSize(long bytes) {
        if (bytes < 1024) return bytes + " B";
        int exp = (int) (Math.log(bytes) / Math.log(1024));
        char pre = "KMGTPE".charAt(exp - 1);
        return String.format(Locale.US, "%.1f %cB", bytes / Math.pow(1024, exp), pre);
    }

    private final android.os.Handler statusRefreshHandler = new android.os.Handler(android.os.Looper.getMainLooper());
    private final Runnable statusRefreshRunnable = new Runnable() {
        @Override
        public void run() {
            if (isBound) {
                updateServerStatus(true);
            }
            syncHotspotState();
            statusRefreshHandler.postDelayed(this, 1500);
        }
    };

    @Override
    protected void onResume() {
        super.onResume();
        checkLocationServicesEnabled();
        if (isBound) {
            updateServerStatus(true);
        }
        updateStagedFilesUi();
        syncHotspotState();

        IntentFilter filter = new IntentFilter("com.airbeam.CLIPBOARD_RECEIVED");
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(clipboardReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
        } else {
            registerReceiver(clipboardReceiver, filter);
        }

        statusRefreshHandler.removeCallbacks(statusRefreshRunnable);
        statusRefreshHandler.postDelayed(statusRefreshRunnable, 1500);
    }

    @Override
    protected void onPause() {
        statusRefreshHandler.removeCallbacks(statusRefreshRunnable);
        try {
            unregisterReceiver(clipboardReceiver);
        } catch (Exception ignored) {}
        super.onPause();
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleShareIntent(intent);
    }

    private void generateHotspotQrCode() {
        if (ivHotspotQr == null) return;
        new Thread(() -> {
            try {
                String ssid = tvHotspotSsid != null ? tvHotspotSsid.getText().toString().trim() : "airbeam";
                String pass = tvHotspotPass != null ? tvHotspotPass.getText().toString().trim() : "airbeam123";
                // Standard Wi-Fi network QR code format for iPhone / Android native camera scanning
                String wifiPayload = "WIFI:T:WPA;S:" + ssid + ";P:" + pass + ";;";
                QRCodeWriter writer = new QRCodeWriter();
                BitMatrix bitMatrix = writer.encode(
                        wifiPayload,
                        BarcodeFormat.QR_CODE,
                        512,
                        512
                );
                int width = bitMatrix.getWidth();
                int height = bitMatrix.getHeight();
                Bitmap bmp = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
                for (int x = 0; x < width; x++) {
                    for (int y = 0; y < height; y++) {
                        bmp.setPixel(x, y, bitMatrix.get(x, y) ? 0xFF0B1120 : 0xFFFFFFFF);
                    }
                }
                runOnUiThread(() -> {
                    if (ivHotspotQr != null) {
                        ivHotspotQr.setImageBitmap(bmp);
                    }
                });
            } catch (Exception e) {
                Log.e("MainActivity", "Error generating hotspot Wi-Fi QR code", e);
            }
        }).start();
    }

    private void generatePortalQrCode() {
        if (ivPortalQr == null) return;
        new Thread(() -> {
            try {
                String url = "http://airbeam.local:" + FileServerService.PORT;
                QRCodeWriter writer = new QRCodeWriter();
                BitMatrix bitMatrix = writer.encode(
                        url,
                        BarcodeFormat.QR_CODE,
                        512,
                        512
                );
                int width = bitMatrix.getWidth();
                int height = bitMatrix.getHeight();
                Bitmap bmp = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
                for (int x = 0; x < width; x++) {
                    for (int y = 0; y < height; y++) {
                        bmp.setPixel(x, y, bitMatrix.get(x, y) ? 0xFF0B1120 : 0xFFFFFFFF);
                    }
                }
                runOnUiThread(() -> {
                    if (ivPortalQr != null) {
                        ivPortalQr.setImageBitmap(bmp);
                    }
                });
            } catch (Exception e) {
                Log.e("MainActivity", "Error generating QR code", e);
            }
        }).start();
    }

    private void openFilePickerToStage() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("*/*");
        intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
        try {
            startActivityForResult(intent, REQUEST_CODE_STAGE_FILES);
        } catch (Exception e) {
            Toast.makeText(this, "Cannot open file picker: " + e.getMessage(), Toast.LENGTH_SHORT).show();
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, @Nullable Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_CODE_STAGE_FILES && resultCode == RESULT_OK && data != null) {
            int added = 0;
            if (data.getClipData() != null) {
                int count = data.getClipData().getItemCount();
                for (int i = 0; i < count; i++) {
                    Uri uri = data.getClipData().getItemAt(i).getUri();
                    if (stageUri(uri)) added++;
                }
            } else if (data.getData() != null) {
                if (stageUri(data.getData())) added++;
            }
            updateStagedFilesUi();
            if (added > 0) {
                Toast.makeText(this, "Staged " + added + " file(s) for iPhone! Download at http://airbeam.local:8080", Toast.LENGTH_LONG).show();
            }
        }
    }

    private boolean stageUri(Uri uri) {
        if (uri == null) return false;
        String displayName = "file_" + System.currentTimeMillis();
        long fileSize = 0;
        String mime = getContentResolver().getType(uri);

        try (Cursor cursor = getContentResolver().query(uri, null, null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                int nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                int sizeIndex = cursor.getColumnIndex(OpenableColumns.SIZE);
                if (nameIndex != -1) {
                    String n = cursor.getString(nameIndex);
                    if (n != null && !n.isEmpty()) displayName = n;
                }
                if (sizeIndex != -1) {
                    fileSize = cursor.getLong(sizeIndex);
                }
            }
        } catch (Exception ignored) {}

        int index = FileServerService.getStagedFiles().size();
        StagedFile stagedFile = new StagedFile(index, displayName, fileSize, uri, mime);
        FileServerService.addStagedFile(stagedFile);
        return true;
    }

    private void handleShareIntent(Intent intent) {
        if (intent == null) return;
        String action = intent.getAction();
        String type = intent.getType();
        if (Intent.ACTION_SEND.equals(action) && type != null) {
            Uri streamUri = intent.getParcelableExtra(Intent.EXTRA_STREAM);
            if (streamUri != null) {
                stageUri(streamUri);
                updateStagedFilesUi();
                Toast.makeText(this, "Staged 1 file for iPhone! Open http://airbeam.local:8080", Toast.LENGTH_LONG).show();
            }
        } else if (Intent.ACTION_SEND_MULTIPLE.equals(action) && type != null) {
            ArrayList<Uri> uris = intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM);
            if (uris != null && !uris.isEmpty()) {
                int count = 0;
                for (Uri u : uris) {
                    if (stageUri(u)) count++;
                }
                updateStagedFilesUi();
                Toast.makeText(this, "Staged " + count + " files for iPhone! Open http://airbeam.local:8080", Toast.LENGTH_LONG).show();
            }
        }
    }

    private void updateStagedFilesUi() {
        runOnUiThread(() -> {
            int count = FileServerService.getStagedFiles().size();
            if (tvStagedCount != null) {
                if (count == 0) {
                    tvStagedCount.setText("Files staged for iPhone: 0");
                } else {
                    tvStagedCount.setText("Files staged for iPhone: " + count + " file" + (count == 1 ? "" : "s") + " ready");
                }
            }
        });
    }

    @Override
    protected void onDestroy() {
        statusRefreshHandler.removeCallbacks(statusRefreshRunnable);
        try {
            unregisterReceiver(clipboardReceiver);
        } catch (Exception ignored) {}
        if (isBound) {
            if (fileServerService != null) {
                fileServerService.setTransferListener(null);
            }
            unbindService(serviceConnection);
            isBound = false;
        }
        super.onDestroy();
    }
}
