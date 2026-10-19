package com.airsend.receiver;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.media.MediaScannerConnection;
import android.net.ConnectivityManager;
import android.net.MacAddress;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.net.wifi.ScanResult;
import android.net.wifi.WifiManager;
import android.net.wifi.WifiNetworkSpecifier;
import android.net.wifi.WifiNetworkSuggestion;
import android.os.Binder;
import android.os.Build;
import android.os.Environment;
import android.os.IBinder;
import android.os.PowerManager;
import android.os.Handler;
import android.os.Looper;
import android.content.ClipboardManager;
import android.content.ClipData;
import android.widget.Toast;
import android.text.format.Formatter;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;

import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.RandomAccessFile;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.NetworkInterface;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.StandardSocketOptions;
import java.net.URLDecoder;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.channels.ServerSocketChannel;
import java.nio.channels.SocketChannel;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

public class FileServerService extends Service {
    private static final String TAG = "FileServerService";
    public static final int PORT = 8080;
    public static final int NIO_PORT = 7777;
    public static final int UDP_PORT = 7778;
    private static final String CHANNEL_ID = "AirSendServiceChannel";
    private static final int NOTIF_ID = 1001;

    private final IBinder binder = new LocalBinder();
    private ServerSocket serverSocket;
    private ServerSocketChannel nioServerChannel;
    private DatagramSocket udpSocket;
    private boolean isRunning = false;
    private ExecutorService threadPool;
    private OnTransferListener transferListener;

    private final AtomicBoolean isConnectingHotspot = new AtomicBoolean(false);
    private ConnectivityManager.NetworkCallback activeNetworkCallback;
    private final ConcurrentHashMap<Long, ActiveTransferSession> activeSessions = new ConcurrentHashMap<>();
    private volatile String connectionMode = "TABLET_HOTSPOT";

    private PowerManager.WakeLock wakeLock;
    private WifiManager.WifiLock wifiLock;
    private final Object lockSync = new Object();

    private void acquireWakeAndWifiLocks() {
        synchronized (lockSync) {
            try {
                if (wakeLock == null) {
                    PowerManager powerManager = (PowerManager) getSystemService(Context.POWER_SERVICE);
                    if (powerManager != null) {
                        wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "AirBeam::TransferWakeLock");
                        wakeLock.setReferenceCounted(false);
                    }
                }
                if (wakeLock != null && !wakeLock.isHeld()) {
                    wakeLock.acquire(15 * 60 * 1000L); // 15 mins timeout safety
                    Log.d(TAG, "Acquired partial WakeLock for transfer");
                }
            } catch (Exception e) {
                Log.w(TAG, "Could not acquire WakeLock", e);
            }

            try {
                if (wifiLock == null) {
                    WifiManager wifiManager = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
                    if (wifiManager != null) {
                        int mode = WifiManager.WIFI_MODE_FULL_HIGH_PERF;
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                            mode = WifiManager.WIFI_MODE_FULL_LOW_LATENCY;
                        }
                        wifiLock = wifiManager.createWifiLock(mode, "AirBeam::TransferWifiLock");
                        wifiLock.setReferenceCounted(false);
                    }
                }
                if (wifiLock != null && !wifiLock.isHeld()) {
                    wifiLock.acquire();
                    Log.d(TAG, "Acquired WifiLock (Low Latency / High Perf) for transfer");
                }
            } catch (Exception e) {
                Log.w(TAG, "Could not acquire WifiLock", e);
            }
        }
    }

    private void releaseWakeAndWifiLocks() {
        synchronized (lockSync) {
            if (!activeSessions.isEmpty()) {
                return;
            }
            try {
                if (wakeLock != null && wakeLock.isHeld()) {
                    wakeLock.release();
                    Log.d(TAG, "Released WakeLock");
                }
            } catch (Exception e) {
                Log.w(TAG, "Could not release WakeLock", e);
            }

            try {
                if (wifiLock != null && wifiLock.isHeld()) {
                    wifiLock.release();
                    Log.d(TAG, "Released WifiLock");
                }
            } catch (Exception e) {
                Log.w(TAG, "Could not release WifiLock", e);
            }
        }
    }

    public void setConnectionMode(String mode) {
        this.connectionMode = mode;
        Log.d(TAG, "Connection mode set to: " + mode);
    }

    public interface OnTransferListener {
        void onTransferStart(TransferItem item);
        void onTransferProgress(TransferItem item);
        void onTransferComplete(TransferItem item);
        void onTransferFailed(TransferItem item, String error);
    }

    public static class ActiveTransferSession {
        public final long transferId;
        public final File partFile;
        public final File targetFile;
        public final RandomAccessFile raf;
        public final FileChannel fileChannel;
        public final long totalBytes;
        public final AtomicLong transferredBytes = new AtomicLong(0);
        public final TransferItem transferItem;
        public volatile long lastProgressUpdate = 0;
        public volatile long lastBytesDone = 0;
        public volatile double speedMBps = 0.0;

        public ActiveTransferSession(long transferId, File partFile, File targetFile, RandomAccessFile raf, FileChannel fileChannel, long totalBytes, TransferItem item) {
            this.transferId = transferId;
            this.partFile = partFile;
            this.targetFile = targetFile;
            this.raf = raf;
            this.fileChannel = fileChannel;
            this.totalBytes = totalBytes;
            this.transferItem = item;
        }
    }

    public class LocalBinder extends Binder {
        public FileServerService getService() {
            return FileServerService.this;
        }
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return binder;
    }

    public void setTransferListener(OnTransferListener listener) {
        this.transferListener = listener;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        startForeground(NOTIF_ID, createNotification("AirBeam V2 Active", "Ready to receive (Port 7777 / 8080)"));
        threadPool = Executors.newCachedThreadPool();
        startHttpServer();
        startNioServer();
        startUdpBeaconListener();
        startPeriodicAnnouncement();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "AirBeam Receiver Service",
                    NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Shows file transfer server status");
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(channel);
            }
        }
    }

    private Notification createNotification(String title, String content) {
        Intent notificationIntent = new Intent(this, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                this, 0, notificationIntent,
                Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0
        );

        return new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle(title)
                .setContentText(content)
                .setSmallIcon(R.drawable.ic_launcher_foreground)
                .setContentIntent(pendingIntent)
                .setOngoing(true)
                .build();
    }

    public void updateNotification(String title, String content) {
        NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager != null) {
            manager.notify(NOTIF_ID, createNotification(title, content));
        }
    }

    // --- UDP Discovery & Zero-Save Hotspot Handover ---
    private void startUdpBeaconListener() {
        threadPool.execute(() -> {
            try {
                udpSocket = new DatagramSocket(UDP_PORT);
                byte[] buffer = new byte[2048];
                while (isRunning && !udpSocket.isClosed()) {
                    DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
                    udpSocket.receive(packet);
                    String msg = new String(packet.getData(), 0, packet.getLength(), StandardCharsets.UTF_8).trim();
                    if (msg.startsWith("AIRBEAM_DISCOVER")) {
                        String model = Build.MANUFACTURER + " " + Build.MODEL;
                        String replyMsg = "AIRBEAM_ACK|" + model + "|" + NIO_PORT;
                        byte[] replyBytes = replyMsg.getBytes(StandardCharsets.UTF_8);
                        DatagramPacket reply = new DatagramPacket(replyBytes, replyBytes.length, packet.getAddress(), packet.getPort());
                        udpSocket.send(reply);
                    } else if (msg.startsWith("AIRBEAM_HOTSPOT_HANDOVER|")) {
                        String[] parts = msg.split("\\|");
                        if (parts.length >= 4) {
                            String ssid = parts[1].trim();
                            String passphrase = parts[2].trim();
                            String hostIp = parts[3].trim();
                            String band = parts.length >= 5 ? parts[4].trim() : "5GHz";
                            String senderIp = packet.getAddress().getHostAddress();
                            if (!"LAPTOP_HOTSPOT".equalsIgnoreCase(connectionMode)) {
                                Log.d(TAG, "Ignoring PC hotspot handover because current tablet mode is: " + connectionMode);
                                return;
                            }
                            if (!isConnectingHotspot.compareAndSet(false, true)) {
                                Log.d(TAG, "Ignoring duplicate Hotspot handover packet while connection is in progress");
                                return;
                            }
                            Log.d(TAG, "Received Hotspot handover request: " + ssid + " (Band: " + band + ") -> " + hostIp + " from sender: " + senderIp);
                            connectToUnsavedWindowsHotspot(ssid, passphrase, hostIp, band, senderIp);
                        }
                    }
                }
            } catch (Exception e) {
                Log.e(TAG, "UDP Beacon stopped", e);
            }
        });
    }

    private void startPeriodicAnnouncement() {
        threadPool.execute(() -> {
            try {
                Thread.sleep(1000);
            } catch (InterruptedException ignored) {}

            while (isRunning) {
                try {
                    String ip = getLocalIpAddress(this);
                    if (ip != null && !ip.equals("127.0.0.1") && !ip.isEmpty()) {
                        String model = Build.MANUFACTURER + " " + Build.MODEL;
                        String msg = "AIRBEAM_ACK|" + model + "|" + NIO_PORT;
                        byte[] data = msg.getBytes(StandardCharsets.UTF_8);

                        try (DatagramSocket s = new DatagramSocket()) {
                            s.setBroadcast(true);
                            // 1. General broadcast
                            try {
                                s.send(new DatagramPacket(data, data.length, InetAddress.getByName("255.255.255.255"), UDP_PORT));
                            } catch (Exception ignored) {}

                            // 2. Local subnet broadcast
                            int lastDot = ip.lastIndexOf('.');
                            if (lastDot > 0) {
                                String subnetBcast = ip.substring(0, lastDot) + ".255";
                                try {
                                    s.send(new DatagramPacket(data, data.length, InetAddress.getByName(subnetBcast), UDP_PORT));
                                } catch (Exception ignored) {}
                            }

                            // 3. Hotspot gateway if connected to hotspot
                            if (ip.startsWith("192.168.137.")) {
                                try {
                                    s.send(new DatagramPacket(data, data.length, InetAddress.getByName("192.168.137.1"), UDP_PORT));
                                } catch (Exception ignored) {}
                            }
                        }
                    }
                } catch (Exception ignored) {}

                try {
                    Thread.sleep(2000);
                } catch (InterruptedException e) {
                    break;
                }
            }
        });
    }

    private void connectToUnsavedWindowsHotspot(String ssid, String passphrase, String hotspotHostIp, String band, String senderIp) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            threadPool.execute(() -> {
                try {
                    WifiManager wifiManager = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
                    ScanResult matchingScanResult = null;

                    // Trigger wifiManager.startScan() (up to 3 times for 5GHz, 2 times for 2.4GHz)
                    int maxAttempts = "5GHz".equalsIgnoreCase(band) ? 3 : 2;
                    for (int scanAttempt = 0; scanAttempt < maxAttempts; scanAttempt++) {
                        if (wifiManager != null) {
                            try {
                                wifiManager.startScan();
                            } catch (Exception e) {
                                Log.w(TAG, "WifiManager startScan exception: " + e.getMessage());
                            }
                        }
                        Thread.sleep(2500);

                        if (wifiManager != null) {
                            try {
                                List<ScanResult> results = wifiManager.getScanResults();
                                if (results != null) {
                                    for (ScanResult sr : results) {
                                        if (sr != null && sr.SSID != null && sr.SSID.trim().equals(ssid)) {
                                            matchingScanResult = sr;
                                            break;
                                        }
                                    }
                                }
                            } catch (SecurityException se) {
                                Log.w(TAG, "Location permission missing for getScanResults: " + se.getMessage());
                            }
                        }

                        if (matchingScanResult != null) {
                            break;
                        }
                    }

                    // Build specifier (with BSSID if found in scan, or just SSID to let hardware scan)
                    WifiNetworkSpecifier.Builder specifierBuilder = new WifiNetworkSpecifier.Builder()
                            .setSsid(ssid);

                    if (matchingScanResult != null) {
                        Log.d(TAG, "Found matching SSID: " + ssid + " with BSSID: " + matchingScanResult.BSSID + " (Freq: " + matchingScanResult.frequency + " MHz)");
                        specifierBuilder.setBssid(MacAddress.fromString(matchingScanResult.BSSID));
                        if (matchingScanResult.capabilities != null && matchingScanResult.capabilities.contains("SAE") && !matchingScanResult.capabilities.contains("PSK")) {
                            specifierBuilder.setWpa3Passphrase(passphrase);
                        } else {
                            specifierBuilder.setWpa2Passphrase(passphrase);
                        }
                    } else {
                        Log.d(TAG, "Pre-scan throttled or SSID not in cache yet. Using hardware scan for: " + ssid + " (" + band + ")");
                        specifierBuilder.setWpa2Passphrase(passphrase);
                    }

                    WifiNetworkSpecifier specifier = specifierBuilder.build();

                    // Register network suggestion as parallel auto-connect fallback
                    try {
                        if (wifiManager != null) {
                            WifiNetworkSuggestion suggestion = new WifiNetworkSuggestion.Builder()
                                    .setSsid(ssid)
                                    .setWpa2Passphrase(passphrase)
                                    .build();
                            wifiManager.addNetworkSuggestions(Collections.singletonList(suggestion));
                        }
                    } catch (Exception ignored) {}

                    NetworkRequest request = new NetworkRequest.Builder()
                            .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
                            .removeCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                            .setNetworkSpecifier(specifier)
                            .build();

                    ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
                    if (cm != null) {
                        if (activeNetworkCallback != null) {
                            try { cm.unregisterNetworkCallback(activeNetworkCallback); } catch (Exception ignored) {}
                        }
                        activeNetworkCallback = new ConnectivityManager.NetworkCallback() {
                            @Override
                            public void onAvailable(@NonNull Network network) {
                                super.onAvailable(network);
                                isConnectingHotspot.set(false);
                                cm.bindProcessToNetwork(network);
                                updateNotification("AirBeam Direct Hotspot", "Connected to " + ssid + " (Max Speed 50-95+ MB/s)");
                                sendHotspotReadyBeacon(network, hotspotHostIp, ssid);
                            }

                            @Override
                            public void onUnavailable() {
                                super.onUnavailable();
                                Log.w(TAG, "Hotspot connection unavailable on specifier request.");
                                isConnectingHotspot.set(false);
                                if ("5GHz".equalsIgnoreCase(band)) {
                                    updateNotification("AirBeam Hotspot", "5 GHz hotspot timed out; falling back to 2.4 GHz...");
                                    sendNeed24GhzBeacon(senderIp);
                                }
                            }

                            @Override
                            public void onLost(@NonNull Network network) {
                                super.onLost(network);
                                isConnectingHotspot.set(false);
                                cm.bindProcessToNetwork(null);
                                updateNotification("AirBeam Active", "Fell back to standard Wi-Fi");
                            }
                        };
                        cm.requestNetwork(request, activeNetworkCallback);
                    }
                } catch (Exception e) {
                    isConnectingHotspot.set(false);
                    Log.e(TAG, "Failed in connectToUnsavedWindowsHotspot", e);
                }
            });
        }
    }

    private void sendNeed24GhzBeacon(String senderIp) {
        threadPool.execute(() -> {
            try (DatagramSocket socket = new DatagramSocket()) {
                socket.setBroadcast(true);
                String model = Build.MANUFACTURER + " " + Build.MODEL;
                String msg = "AIRBEAM_NEED_24GHZ|" + model;
                byte[] data = msg.getBytes(StandardCharsets.UTF_8);

                // Send unicast to Windows PC sender address
                if (senderIp != null && !senderIp.isEmpty()) {
                    try {
                        InetAddress dest = InetAddress.getByName(senderIp);
                        for (int i = 0; i < 3; i++) {
                            DatagramPacket packet = new DatagramPacket(data, data.length, dest, UDP_PORT);
                            socket.send(packet);
                            Thread.sleep(100);
                        }
                    } catch (Exception ignored) {}
                }

                // Also send broadcast so sender receives even if routing table is strange
                try {
                    InetAddress bcast = InetAddress.getByName("255.255.255.255");
                    DatagramPacket bcastPacket = new DatagramPacket(data, data.length, bcast, UDP_PORT);
                    socket.send(bcastPacket);
                } catch (Exception ignored) {}

                Log.d(TAG, "Sent AIRBEAM_NEED_24GHZ to " + senderIp + " and broadcast");
            } catch (Exception e) {
                Log.e(TAG, "Failed sending AIRBEAM_NEED_24GHZ", e);
            }
        });
    }

    private void sendHotspotReadyBeacon(Network network, String hotspotHostIp, String ssid) {
        threadPool.execute(() -> {
            // 1. Wait until tablet actually gets a 192.168.137.x IP (DHCP resolution)
            String localIp = "";
            for (int wait = 0; wait < 20; wait++) {
                localIp = getLocalIpAddress(this);
                if (localIp != null && localIp.startsWith("192.168.137.")) {
                    break;
                }
                try {
                    Thread.sleep(300);
                } catch (InterruptedException ignored) {}
            }

            Log.d(TAG, "Hotspot assigned local IP: " + localIp);
            updateNotification("AirBeam Direct Hotspot", "Connected to " + ssid + " — IP: " + localIp + ":7777");

            // 2. Proactively ping Windows host via TCP port 8888 to force Windows ARP cache registration
            try {
                Socket arpSocket = new Socket();
                if (network != null) {
                    try { network.bindSocket(arpSocket); } catch (Exception ignored) {}
                }
                arpSocket.connect(new InetSocketAddress(hotspotHostIp, 8888), 1000);
                arpSocket.close();
                Log.d(TAG, "Pinged Windows host ARP on port 8888 successfully");
            } catch (Exception e) {
                Log.w(TAG, "ARP TCP probe note: " + e.getMessage());
            }

            // 3. Send UDP Hotspot Ready beacons
            String model = Build.MANUFACTURER + " " + Build.MODEL;
            String msg = "AIRBEAM_HOTSPOT_READY|" + model;
            byte[] data = msg.getBytes(StandardCharsets.UTF_8);

            for (int i = 0; i < 15; i++) {
                try (DatagramSocket beaconSocket = new DatagramSocket()) {
                    if (network != null) {
                        try {
                            network.bindSocket(beaconSocket);
                        } catch (Exception ignored) {}
                    }
                    beaconSocket.setBroadcast(true);

                    // Unicast to PC host
                    InetAddress dest = InetAddress.getByName(hotspotHostIp);
                    beaconSocket.send(new DatagramPacket(data, data.length, dest, UDP_PORT));

                    // Subnet broadcast
                    try {
                        InetAddress bcast = InetAddress.getByName("192.168.137.255");
                        beaconSocket.send(new DatagramPacket(data, data.length, bcast, UDP_PORT));
                    } catch (Exception ignored) {}
                } catch (Exception e) {
                    Log.w(TAG, "Hotspot ready beacon attempt failed: " + e.getMessage());
                }
                try {
                    Thread.sleep(500);
                } catch (InterruptedException ignored) {
                    break;
                }
            }
        });
    }

    // --- High-Speed Java NIO Multi-Stream Server (TCP Port 7777) ---
    private void startNioServer() {
        threadPool.execute(() -> {
            try {
                nioServerChannel = ServerSocketChannel.open();
                nioServerChannel.setOption(StandardSocketOptions.SO_REUSEADDR, true);
                nioServerChannel.setOption(StandardSocketOptions.SO_RCVBUF, 16 * 1024 * 1024);
                nioServerChannel.bind(new InetSocketAddress(NIO_PORT));
                Log.d(TAG, "NIO Multi-Stream Server started on port " + NIO_PORT);

                while (isRunning && nioServerChannel.isOpen()) {
                    SocketChannel socketChannel = nioServerChannel.accept();
                    socketChannel.configureBlocking(true);
                    socketChannel.setOption(StandardSocketOptions.TCP_NODELAY, true);
                    socketChannel.setOption(StandardSocketOptions.SO_RCVBUF, 16 * 1024 * 1024);
                    socketChannel.setOption(StandardSocketOptions.SO_SNDBUF, 2 * 1024 * 1024);
                    threadPool.execute(() -> handleNioClient(socketChannel));
                }
            } catch (Exception e) {
                if (isRunning) {
                    Log.e(TAG, "NIO Server error", e);
                }
            }
        });
    }

    private void handleNioClient(SocketChannel channel) {
        try {
            ByteBuffer magicBuf = ByteBuffer.allocate(4);
            readFully(channel, magicBuf);
            magicBuf.flip();
            byte[] magicBytes = new byte[4];
            magicBuf.get(magicBytes);
            String magic = new String(magicBytes, StandardCharsets.US_ASCII);

            if ("ABM_".equals(magic)) {
                // Control stream: read remaining 4 bytes "CTRL"
                ByteBuffer ctrlBuf = ByteBuffer.allocate(4);
                readFully(channel, ctrlBuf);
                handleNioControlStream(channel);
            } else if ("ABM2".equals(magic)) {
                // Multi-stream worker connection: persistent stripe receiving loop
                handleNioStripeWorker(channel);
            } else {
                Log.w(TAG, "Unknown NIO magic: " + magic);
                channel.close();
            }
        } catch (Exception e) {
            Log.e(TAG, "NIO client error", e);
        } finally {
            try { channel.close(); } catch (Exception ignored) {}
        }
    }

    private void handleNioControlStream(SocketChannel channel) throws Exception {
        while (isRunning && channel.isOpen()) {
            ByteBuffer lenBuf = ByteBuffer.allocate(4);
            if (!readFullyOrEof(channel, lenBuf)) break;
            lenBuf.flip();
            int firstInt = lenBuf.getInt();

            // If client prefixed with "ABM_", consume "CTRL" and read real length
            if (firstInt == 0x41424D5F) { // ASCII "ABM_"
                ByteBuffer ctrlPart = ByteBuffer.allocate(4);
                readFully(channel, ctrlPart);
                lenBuf.clear();
                if (!readFullyOrEof(channel, lenBuf)) break;
                lenBuf.flip();
                firstInt = lenBuf.getInt();
            }

            int jsonLen = firstInt;
            if (jsonLen <= 0 || jsonLen > 1024 * 1024) break;

            ByteBuffer jsonBuf = ByteBuffer.allocate(jsonLen);
            readFully(channel, jsonBuf);
            jsonBuf.flip();
            String jsonStr = new String(jsonBuf.array(), 0, jsonLen, StandardCharsets.UTF_8);

            JSONObject json = new JSONObject(jsonStr);
            String action = json.optString("action", "MANIFEST");

            if ("MANIFEST".equalsIgnoreCase(action)) {
                long transferId = json.getLong("transfer_id");
                String filename = json.getString("filename");
                long filesize = json.getLong("filesize");

                filename = filename.replaceAll("[\\\\/:*?\"<>|]", "_");
                File downloadsDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
                if (!downloadsDir.exists()) downloadsDir.mkdirs();
                File targetFile = getUniqueFile(downloadsDir, filename);
                File partFile = new File(downloadsDir, targetFile.getName() + ".airbeam.part");

                RandomAccessFile raf = new RandomAccessFile(partFile, "rw");
                raf.setLength(filesize); // Pre-allocate full file length on flash storage!
                FileChannel fc = raf.getChannel();

                TransferItem item = new TransferItem(String.valueOf(transferId), targetFile.getName(), filesize);
                ActiveTransferSession session = new ActiveTransferSession(transferId, partFile, targetFile, raf, fc, filesize, item);
                activeSessions.put(transferId, session);

                acquireWakeAndWifiLocks();

                if (transferListener != null) {
                    transferListener.onTransferStart(item);
                }
                updateNotification("Receiving: " + targetFile.getName(), "50-95+ MB/s Multi-Stream Transfer");

                ByteBuffer resp = ByteBuffer.wrap("MANIFEST_OK\n".getBytes(StandardCharsets.US_ASCII));
                writeFully(channel, resp);
            } else if ("FINALIZE".equalsIgnoreCase(action)) {
                long transferId = json.getLong("transfer_id");
                ActiveTransferSession session = activeSessions.remove(transferId);
                if (session != null) {
                    try {
                        session.fileChannel.force(true);
                        session.fileChannel.close();
                        session.raf.close();
                    } catch (Exception ignored) {}

                    // Atomic rename from .airbeam.part to targetFile
                    if (session.partFile.exists()) {
                        if (session.targetFile.exists()) {
                            session.targetFile.delete();
                        }
                        boolean renamed = session.partFile.renameTo(session.targetFile);
                        if (!renamed) {
                            try (InputStream in = new java.io.FileInputStream(session.partFile);
                                 OutputStream out = new FileOutputStream(session.targetFile)) {
                                byte[] copyBuf = new byte[1024 * 1024];
                                int r;
                                while ((r = in.read(copyBuf)) != -1) {
                                    out.write(copyBuf, 0, r);
                                }
                            } catch (Exception e) {
                                Log.e(TAG, "Fallback copy failed", e);
                            }
                            session.partFile.delete();
                        }
                    }

                    session.transferItem.setStatus(TransferItem.Status.COMPLETED);
                    session.transferItem.setTransferredBytes(session.totalBytes);
                    session.transferItem.setSavedPath(session.targetFile.getAbsolutePath());

                    MediaScannerConnection.scanFile(getApplicationContext(), new String[]{session.targetFile.getAbsolutePath()}, null, null);

                    if (transferListener != null) {
                        transferListener.onTransferComplete(session.transferItem);
                    }
                    updateNotification("AirBeam V2 Complete", session.targetFile.getName() + " saved to Downloads");

                    String respStr = "FINALIZE_OK|" + session.targetFile.getAbsolutePath() + "\n";
                    ByteBuffer resp = ByteBuffer.wrap(respStr.getBytes(StandardCharsets.US_ASCII));
                    writeFully(channel, resp);
                }
                releaseWakeAndWifiLocks();
                break;
            } else if ("CANCEL".equalsIgnoreCase(action)) {
                long transferId = json.getLong("transfer_id");
                ActiveTransferSession session = activeSessions.remove(transferId);
                if (session != null) {
                    try {
                        session.fileChannel.close();
                        session.raf.close();
                    } catch (Exception ignored) {}
                    if (session.partFile != null && session.partFile.exists()) {
                        boolean del = session.partFile.delete();
                        Log.d(TAG, "Transfer " + transferId + " cancelled. Part file deleted: " + del);
                    }
                    session.transferItem.setStatus(TransferItem.Status.FAILED);
                    if (transferListener != null) {
                        transferListener.onTransferFailed(session.transferItem, "Transfer cancelled by sender");
                    }
                    updateNotification("AirBeam V2", "Transfer cancelled");
                    String respStr = "CANCEL_OK\n";
                    ByteBuffer resp = ByteBuffer.wrap(respStr.getBytes(StandardCharsets.US_ASCII));
                    writeFully(channel, resp);
                }
                releaseWakeAndWifiLocks();
                break;
            } else if ("CLIPBOARD".equalsIgnoreCase(action) || "CLIPBOARD".equalsIgnoreCase(json.optString("type"))) {
                String text = json.optString("text", "");
                handleIncomingClipboard(text);
                ByteBuffer resp = ByteBuffer.wrap("CLIPBOARD_OK\n".getBytes(StandardCharsets.US_ASCII));
                writeFully(channel, resp);
            }
        }
    }

    private void handleIncomingClipboard(String text) {
        if (text == null || text.isEmpty()) return;
        new Handler(Looper.getMainLooper()).post(() -> {
            try {
                ClipboardManager clipboard = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
                if (clipboard != null) {
                    ClipData clip = ClipData.newPlainText("AirBeam", text);
                    clipboard.setPrimaryClip(clip);
                }
                String preview = text.length() > 60 ? text.substring(0, 60) + "..." : text;
                Toast.makeText(getApplicationContext(), "📋 Copied from PC: " + preview, Toast.LENGTH_LONG).show();

                Intent intent = new Intent("com.airbeam.CLIPBOARD_RECEIVED");
                intent.setPackage(getPackageName());
                intent.putExtra("text", text);
                sendBroadcast(intent);
            } catch (Exception e) {
                Log.e(TAG, "Error handling clipboard", e);
            }
        });
    }

    private void handleNioStripeWorker(SocketChannel channel) throws Exception {
        // Reusable 4 MB off-heap direct buffer per worker (tuned as per prompt DIRECT_BUFFER_SIZE = 4 * 1024 * 1024)
        ByteBuffer directPayloadBuf = ByteBuffer.allocateDirect(4 * 1024 * 1024);
        ByteBuffer headerBuf = ByteBuffer.allocate(32); // remaining 32 bytes after magic b"ABM2"
        ByteBuffer ackBuf = ByteBuffer.wrap("COK!".getBytes(StandardCharsets.US_ASCII));

        while (isRunning && channel.isOpen()) {
            // Read 32 bytes header: transferId(Q), chunkIndex(I), totalChunks(I), chunkOffset(Q), chunkLength(Q)
            headerBuf.clear();
            if (!readFullyOrEof(channel, headerBuf)) break;
            headerBuf.flip();

            long transferId = headerBuf.getLong();
            int chunkIndex = headerBuf.getInt();
            int totalChunks = headerBuf.getInt();
            long chunkOffset = headerBuf.getLong();
            long chunkLength = headerBuf.getLong();

            ActiveTransferSession session = activeSessions.get(transferId);
            if (session == null) {
                Log.e(TAG, "Session not found for transferId: " + transferId);
                break;
            }

            long writePos = chunkOffset;
            long remaining = chunkLength;

            while (remaining > 0) {
                int toRead = (int) Math.min(directPayloadBuf.capacity(), remaining);
                directPayloadBuf.clear();
                directPayloadBuf.limit(toRead);

                readFully(channel, directPayloadBuf);
                directPayloadBuf.flip();

                // Thread-safe positional write directly to flash storage at chunk offset!
                while (directPayloadBuf.hasRemaining()) {
                    int written = session.fileChannel.write(directPayloadBuf, writePos);
                    writePos += written;
                }

                remaining -= toRead;
                long totalDone = session.transferredBytes.addAndGet(toRead);

                long now = System.currentTimeMillis();
                if (now - session.lastProgressUpdate >= 200) {
                    long dt = now - session.lastProgressUpdate;
                    long bytesDelta = totalDone - session.lastBytesDone;
                    double speedMBps = dt > 0 ? ((double) bytesDelta / (1024.0 * 1024.0)) / (dt / 1000.0) : 0.0;
                    session.speedMBps = speedMBps;
                    session.lastBytesDone = totalDone;
                    session.lastProgressUpdate = now;
                    session.transferItem.setTransferredBytes(totalDone);
                    session.transferItem.setSpeedMBps(speedMBps);

                    if (transferListener != null) {
                        transferListener.onTransferProgress(session.transferItem);
                    }

                    Intent progIntent = new Intent("com.airbeam.TRANSFER_PROGRESS");
                    progIntent.setPackage(getPackageName());
                    progIntent.putExtra("transfer_id", transferId);
                    progIntent.putExtra("filename", session.targetFile.getName());
                    progIntent.putExtra("transferred", totalDone);
                    progIntent.putExtra("total", session.totalBytes);
                    progIntent.putExtra("speed_mbps", speedMBps);
                    sendBroadcast(progIntent);
                }
            }

            // Acknowledge stripe completion with 4-byte b"COK!"
            ackBuf.rewind();
            writeFully(channel, ackBuf);
        }
    }

    private static void readFully(SocketChannel channel, ByteBuffer buf) throws IOException {
        while (buf.hasRemaining()) {
            int r = channel.read(buf);
            if (r == -1) throw new IOException("Unexpected EOF from channel");
        }
    }

    private static boolean readFullyOrEof(SocketChannel channel, ByteBuffer buf) throws IOException {
        while (buf.hasRemaining()) {
            int r = channel.read(buf);
            if (r == -1) {
                if (buf.position() == 0) return false;
                throw new IOException("Unexpected EOF during packet");
            }
        }
        return true;
    }

    private static void writeFully(SocketChannel channel, ByteBuffer buf) throws IOException {
        while (buf.hasRemaining()) {
            channel.write(buf);
        }
    }

    // --- Backwards-Compatible HTTP Server (Port 8080) ---
    private void startHttpServer() {
        if (isRunning) return;
        isRunning = true;
        threadPool.execute(() -> {
            try {
                serverSocket = new ServerSocket(PORT);
                serverSocket.setReceiveBufferSize(4 * 1024 * 1024);
                serverSocket.setReuseAddress(true);
                Log.d(TAG, "HTTP Server started on port " + PORT);
                while (isRunning && !serverSocket.isClosed()) {
                    Socket clientSocket = serverSocket.accept();
                    clientSocket.setTcpNoDelay(true);
                    clientSocket.setReceiveBufferSize(4 * 1024 * 1024);
                    clientSocket.setSendBufferSize(1024 * 1024);
                    threadPool.execute(() -> handleHttpClient(clientSocket));
                }
            } catch (IOException e) {
                if (isRunning) {
                    Log.e(TAG, "Server socket error", e);
                }
            }
        });
    }

    private void handleHttpClient(Socket socket) {
        try (InputStream in = socket.getInputStream();
             OutputStream out = socket.getOutputStream()) {

            BufferedInputStream bis = new BufferedInputStream(in, 1048576);
            String firstLine = readLine(bis);
            if (firstLine == null || firstLine.isEmpty()) return;

            String[] parts = firstLine.split(" ");
            if (parts.length < 2) return;
            String method = parts[0].toUpperCase();
            String uri = parts[1];

            Map<String, String> headers = new HashMap<>();
            String headerLine;
            while ((headerLine = readLine(bis)) != null && !headerLine.isEmpty()) {
                int colon = headerLine.indexOf(':');
                if (colon > 0) {
                    headers.put(headerLine.substring(0, colon).trim().toLowerCase(),
                                headerLine.substring(colon + 1).trim());
                }
            }

            if ("OPTIONS".equalsIgnoreCase(method)) {
                sendCorsOk(out);
                return;
            }

            if ("GET".equalsIgnoreCase(method)) {
                if (uri.startsWith("/info") || uri.startsWith("/ping")) {
                    String deviceName = Build.MANUFACTURER + " " + Build.MODEL;
                    String json = "{\"name\":\"" + deviceName + "\",\"port\":" + PORT + ",\"nio_port\":" + NIO_PORT + ",\"status\":\"ready\"}";
                    byte[] body = json.getBytes(StandardCharsets.UTF_8);
                    sendResponse(out, 200, "OK", "application/json", body);
                } else {
                    String html = "<html><body style='font-family:sans-serif;padding:20px;text-align:center;background:#0f172a;color:#fff;'>"
                            + "<h2>AirBeam V2 Receiver</h2>"
                            + "<p>Device: " + Build.MANUFACTURER + " " + Build.MODEL + "</p>"
                            + "<p style='color:#10b981;'>Ready for 50-95+ MB/s transfers!</p>"
                            + "</body></html>";
                    byte[] body = html.getBytes(StandardCharsets.UTF_8);
                    sendResponse(out, 200, "OK", "text/html", body);
                }
                return;
            }

            if ("POST".equalsIgnoreCase(method) && uri.startsWith("/upload")) {
                handleHttpUpload(uri, headers, bis, out);
                return;
            }

            sendResponse(out, 404, "Not Found", "text/plain", "Not Found".getBytes(StandardCharsets.UTF_8));
        } catch (Exception e) {
            Log.e(TAG, "Error handling client", e);
        } finally {
            try { socket.close(); } catch (IOException ignored) {}
        }
    }

    private void handleHttpUpload(String uri, Map<String, String> headers, InputStream in, OutputStream out) throws IOException {
        String fileName = "received_file_" + System.currentTimeMillis();
        long contentLength = -1;

        if (headers.containsKey("content-length")) {
            try {
                contentLength = Long.parseLong(headers.get("content-length"));
            } catch (Exception ignored) {}
        }

        if (headers.containsKey("x-file-name")) {
            try {
                fileName = URLDecoder.decode(headers.get("x-file-name"), "UTF-8");
            } catch (Exception ignored) {
                fileName = headers.get("x-file-name");
            }
        }

        fileName = fileName.replaceAll("[\\\\/:*?\"<>|]", "_");
        File downloadsDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
        if (!downloadsDir.exists()) downloadsDir.mkdirs();

        File targetFile = getUniqueFile(downloadsDir, fileName);
        String transferId = UUID.randomUUID().toString();
        TransferItem item = new TransferItem(transferId, targetFile.getName(), contentLength);

        if (transferListener != null) {
            transferListener.onTransferStart(item);
        }

        try (FileOutputStream fos = new FileOutputStream(targetFile);
             BufferedOutputStream bos = new BufferedOutputStream(fos, 1048576)) {

            byte[] buffer = new byte[1048576];
            long bytesReadTotal = 0;
            int read;
            long lastProgressUpdate = 0;

            if (contentLength > 0) {
                while (bytesReadTotal < contentLength) {
                    int toRead = (int) Math.min(buffer.length, contentLength - bytesReadTotal);
                    read = in.read(buffer, 0, toRead);
                    if (read == -1) break;
                    bos.write(buffer, 0, read);
                    bytesReadTotal += read;

                    long now = System.currentTimeMillis();
                    if (now - lastProgressUpdate > 500) {
                        item.setTransferredBytes(bytesReadTotal);
                        if (transferListener != null) transferListener.onTransferProgress(item);
                        lastProgressUpdate = now;
                    }
                }
            } else {
                while ((read = in.read(buffer)) != -1) {
                    bos.write(buffer, 0, read);
                    bytesReadTotal += read;
                }
            }

            bos.flush();
            item.setTransferredBytes(bytesReadTotal);
            item.setTotalBytes(bytesReadTotal);
            item.setStatus(TransferItem.Status.COMPLETED);
            item.setSavedPath(targetFile.getAbsolutePath());

            MediaScannerConnection.scanFile(this, new String[]{targetFile.getAbsolutePath()}, null, null);

            if (transferListener != null) {
                transferListener.onTransferComplete(item);
            }
            sendResponse(out, 200, "OK", "text/plain", ("OK: " + targetFile.getName()).getBytes(StandardCharsets.UTF_8));
        } catch (Exception e) {
            item.setStatus(TransferItem.Status.FAILED);
            if (transferListener != null) {
                transferListener.onTransferFailed(item, e.getMessage());
            }
            sendResponse(out, 500, "Internal Server Error", "text/plain", e.getMessage().getBytes(StandardCharsets.UTF_8));
        }
    }

    private File getUniqueFile(File dir, String filename) {
        File file = new File(dir, filename);
        if (!file.exists()) return file;

        String name = filename;
        String ext = "";
        int dot = filename.lastIndexOf('.');
        if (dot > 0) {
            name = filename.substring(0, dot);
            ext = filename.substring(dot);
        }

        int count = 1;
        while (file.exists()) {
            file = new File(dir, name + " (" + count + ")" + ext);
            count++;
        }
        return file;
    }

    private String readLine(InputStream in) throws IOException {
        StringBuilder sb = new StringBuilder();
        int c;
        while ((c = in.read()) != -1) {
            if (c == '\r') {
                int next = in.read();
                if (next == '\n' || next == -1) break;
                sb.append((char) c).append((char) next);
            } else if (c == '\n') {
                break;
            } else {
                sb.append((char) c);
            }
        }
        return sb.toString();
    }

    private void sendCorsOk(OutputStream out) throws IOException {
        String resp = "HTTP/1.1 204 No Content\r\n"
                + "Access-Control-Allow-Origin: *\r\n"
                + "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
                + "Access-Control-Allow-Headers: *\r\n"
                + "Content-Length: 0\r\n"
                + "Connection: close\r\n\r\n";
        out.write(resp.getBytes(StandardCharsets.UTF_8));
        out.flush();
    }

    private void sendResponse(OutputStream out, int statusCode, String statusText, String contentType, byte[] body) throws IOException {
        String headers = "HTTP/1.1 " + statusCode + " " + statusText + "\r\n"
                + "Content-Type: " + contentType + "\r\n"
                + "Content-Length: " + body.length + "\r\n"
                + "Access-Control-Allow-Origin: *\r\n"
                + "Connection: close\r\n\r\n";
        out.write(headers.getBytes(StandardCharsets.UTF_8));
        out.write(body);
        out.flush();
    }

    public static String getLocalIpAddress(Context context) {
        try {
            List<NetworkInterface> interfaces = Collections.list(NetworkInterface.getNetworkInterfaces());
            // 1. Prioritize direct hotspot subnets (192.168.43.x tablet hotspot or 192.168.137.x Windows hotspot)
            for (NetworkInterface intf : interfaces) {
                if (intf.isLoopback() || !intf.isUp()) continue;
                List<InetAddress> addrs = Collections.list(intf.getInetAddresses());
                for (InetAddress addr : addrs) {
                    if (!addr.isLoopbackAddress() && addr.getAddress().length == 4) {
                        String host = addr.getHostAddress();
                        if (host != null && (host.startsWith("192.168.43.") || host.startsWith("192.168.137."))) {
                            return host;
                        }
                    }
                }
            }
            // 2. Standard Wi-Fi
            WifiManager wm = (WifiManager) context.getApplicationContext().getSystemService(Context.WIFI_SERVICE);
            if (wm != null && wm.isWifiEnabled()) {
                int ipInt = wm.getConnectionInfo().getIpAddress();
                if (ipInt != 0) {
                    return Formatter.formatIpAddress(ipInt);
                }
            }
            // 3. Any active IPv4 interface
            for (NetworkInterface intf : interfaces) {
                if (intf.isLoopback() || !intf.isUp()) continue;
                List<InetAddress> addrs = Collections.list(intf.getInetAddresses());
                for (InetAddress addr : addrs) {
                    if (!addr.isLoopbackAddress() && addr.getAddress().length == 4) {
                        String host = addr.getHostAddress();
                        if (host != null && !host.startsWith("127.")) {
                            return host;
                        }
                    }
                }
            }
        } catch (Exception ignored) {}
        return "10.150.131.50";
    }

    public static boolean isHotspotActive(Context context) {
        try {
            WifiManager wm = (WifiManager) context.getApplicationContext().getSystemService(Context.WIFI_SERVICE);
            if (wm != null) {
                try {
                    java.lang.reflect.Method method = wm.getClass().getDeclaredMethod("isWifiApEnabled");
                    method.setAccessible(true);
                    Object res = method.invoke(wm);
                    if (res instanceof Boolean && (Boolean) res) {
                        return true;
                    }
                } catch (Exception ignored) {}
            }
            List<NetworkInterface> interfaces = Collections.list(NetworkInterface.getNetworkInterfaces());
            for (NetworkInterface intf : interfaces) {
                if (intf.isLoopback() || !intf.isUp()) continue;
                String name = intf.getName().toLowerCase();
                List<InetAddress> addrs = Collections.list(intf.getInetAddresses());
                for (InetAddress addr : addrs) {
                    if (!addr.isLoopbackAddress() && addr.getAddress().length == 4) {
                        String host = addr.getHostAddress();
                        if (host != null && (host.startsWith("192.168.43.") || ((name.contains("ap") || name.contains("swlan") || name.contains("wlan1") || name.contains("hotspot")) && (host.startsWith("10.") || host.startsWith("192.168."))))) {
                            return true;
                        }
                    }
                }
            }
        } catch (Exception ignored) {}
        return false;
    }

    public static String getHotspotIpAddress(Context context) {
        try {
            List<NetworkInterface> interfaces = Collections.list(NetworkInterface.getNetworkInterfaces());
            for (NetworkInterface intf : interfaces) {
                if (intf.isLoopback() || !intf.isUp()) continue;
                String name = intf.getName().toLowerCase();
                List<InetAddress> addrs = Collections.list(intf.getInetAddresses());
                for (InetAddress addr : addrs) {
                    if (!addr.isLoopbackAddress() && addr.getAddress().length == 4) {
                        String host = addr.getHostAddress();
                        if (host != null) {
                            if (host.startsWith("192.168.43.")) return host;
                            if ((name.contains("ap") || name.contains("swlan") || name.contains("wlan1")) && (host.startsWith("10.") || host.startsWith("192.168."))) {
                                return host;
                            }
                        }
                    }
                }
            }
        } catch (Exception ignored) {}
        return getLocalIpAddress(context);
    }

    @Override
    public void onDestroy() {
        isRunning = false;
        isConnectingHotspot.set(false);
        try {
            if (serverSocket != null) serverSocket.close();
            if (nioServerChannel != null) nioServerChannel.close();
            if (udpSocket != null) udpSocket.close();
            if (activeNetworkCallback != null) {
                ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
                if (cm != null) cm.unregisterNetworkCallback(activeNetworkCallback);
            }
            if (threadPool != null) threadPool.shutdownNow();
        } catch (Exception ignored) {}

        for (ActiveTransferSession session : activeSessions.values()) {
            try {
                if (session.fileChannel != null) session.fileChannel.close();
                if (session.raf != null) session.raf.close();
            } catch (Exception ignored) {}
            if (session.partFile != null && session.partFile.exists()) {
                session.partFile.delete();
            }
        }
        activeSessions.clear();

        synchronized (lockSync) {
            try {
                if (wakeLock != null && wakeLock.isHeld()) wakeLock.release();
            } catch (Exception ignored) {}
            try {
                if (wifiLock != null && wifiLock.isHeld()) wifiLock.release();
            } catch (Exception ignored) {}
        }

        super.onDestroy();
    }
}
