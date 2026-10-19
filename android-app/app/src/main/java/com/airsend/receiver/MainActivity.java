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
                tvIpAddress.setText("http://" + ip + ":" + FileServerService.PORT);
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
