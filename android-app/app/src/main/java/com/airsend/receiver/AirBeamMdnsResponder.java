package com.airsend.receiver;

import android.content.Context;
import android.net.nsd.NsdManager;
import android.net.nsd.NsdServiceInfo;
import android.net.wifi.WifiManager;
import android.util.Log;

import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.net.DatagramPacket;
import java.net.InetAddress;
import java.net.MulticastSocket;
import java.net.NetworkInterface;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.Enumeration;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class AirBeamMdnsResponder {
    private static final String TAG = "AirBeamMDNS";
    private static final String MDNS_GROUP = "224.0.0.251";
    private static final int MDNS_PORT = 5353;
    private static final String TARGET_HOST = "airbeam.local";

    private final Context context;
    private final int httpPort;
    private volatile boolean isRunning = false;
    private MulticastSocket multicastSocket;
    private WifiManager.MulticastLock multicastLock;
    private NsdManager nsdManager;
    private NsdManager.RegistrationListener registrationListener;
    private ExecutorService executor;

    public AirBeamMdnsResponder(Context context, int httpPort) {
        this.context = context.getApplicationContext();
        this.httpPort = httpPort;
    }

    public synchronized void start() {
        if (isRunning) return;
        isRunning = true;
        executor = Executors.newCachedThreadPool();

        acquireMulticastLock();
        registerNsdService();
        startMdnsSocketListener();
        startPeriodicAnnouncements();
        Log.i(TAG, "AirBeam mDNS Responder started for " + TARGET_HOST + " on port " + httpPort);
    }

    private void acquireMulticastLock() {
        try {
            WifiManager wm = (WifiManager) context.getSystemService(Context.WIFI_SERVICE);
            if (wm != null) {
                multicastLock = wm.createMulticastLock("airbeam_mdns_lock");
                multicastLock.setReferenceCounted(true);
                multicastLock.acquire();
                Log.d(TAG, "WifiManager MulticastLock acquired");
            }
        } catch (Exception e) {
            Log.w(TAG, "Could not acquire MulticastLock: " + e.getMessage());
        }
    }

    private void registerNsdService() {
        try {
            nsdManager = (NsdManager) context.getSystemService(Context.NSD_SERVICE);
            if (nsdManager != null) {
                NsdServiceInfo serviceInfo = new NsdServiceInfo();
                serviceInfo.setServiceName("AirBeam");
                serviceInfo.setServiceType("_http._tcp.");
                serviceInfo.setPort(httpPort);

                registrationListener = new NsdManager.RegistrationListener() {
                    @Override
                    public void onServiceRegistered(NsdServiceInfo NsdServiceInfo) {
                        Log.d(TAG, "NSD Service registered: " + NsdServiceInfo.getServiceName());
                    }

                    @Override
                    public void onRegistrationFailed(NsdServiceInfo serviceInfo, int errorCode) {
                        Log.w(TAG, "NSD Registration failed: " + errorCode);
                    }

                    @Override
                    public void onServiceUnregistered(NsdServiceInfo arg0) {
                        Log.d(TAG, "NSD Service unregistered");
                    }

                    @Override
                    public void onUnregistrationFailed(NsdServiceInfo serviceInfo, int errorCode) {
                        Log.w(TAG, "NSD Unregistration failed: " + errorCode);
                    }
                };

                nsdManager.registerService(serviceInfo, NsdManager.PROTOCOL_DNS_SD, registrationListener);
            }
        } catch (Exception e) {
            Log.w(TAG, "NsdManager registration failed: " + e.getMessage());
        }
    }

    private void startMdnsSocketListener() {
        executor.execute(() -> {
            try {
                multicastSocket = new MulticastSocket(MDNS_PORT);
                multicastSocket.setReuseAddress(true);
                multicastSocket.setTimeToLive(255);

                InetAddress group = InetAddress.getByName(MDNS_GROUP);
                joinGroupOnAllInterfaces(multicastSocket, group);

                byte[] buffer = new byte[2048];
                Log.d(TAG, "Listening for mDNS queries on UDP 5353");

                while (isRunning && !multicastSocket.isClosed()) {
                    DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
                    multicastSocket.receive(packet);

                    String currentIp = FileServerService.getLocalIpAddress(context);
                    if (currentIp == null || currentIp.isEmpty() || currentIp.equals("127.0.0.1")) {
                        continue;
                    }

                    if (isAirbeamLocalQuery(packet.getData(), packet.getLength())) {
                        Log.d(TAG, "Received query for airbeam.local from " + packet.getAddress().getHostAddress());
                        sendMdnsAnswer(multicastSocket, packet.getAddress(), packet.getPort(), currentIp, packet.getData(), packet.getLength());
                    }
                }
            } catch (Exception e) {
                if (isRunning) {
                    Log.w(TAG, "mDNS socket error: " + e.getMessage());
                }
            }
        });
    }

    private void joinGroupOnAllInterfaces(MulticastSocket socket, InetAddress group) {
        try {
            Enumeration<NetworkInterface> interfaces = NetworkInterface.getNetworkInterfaces();
            if (interfaces == null) return;
            for (NetworkInterface intf : Collections.list(interfaces)) {
                if (!intf.isUp() || intf.isLoopback()) continue;
                try {
                    socket.joinGroup(new java.net.InetSocketAddress(group, MDNS_PORT), intf);
                } catch (Exception ignored) {}
            }
        } catch (Exception e) {
            Log.w(TAG, "Error joining multicast group on all interfaces: " + e.getMessage());
        }
    }

    private boolean isAirbeamLocalQuery(byte[] data, int length) {
        if (length < 12) return false;
        String s = new String(data, 0, length, StandardCharsets.ISO_8859_1).toLowerCase();
        // If specifically for airbeam-pc, let PC respond
        if (s.contains("airbeam-pc")) return false;
        return s.contains("airbeam") && s.contains("local");
    }

    private void sendMdnsAnswer(MulticastSocket socket, InetAddress senderAddr, int senderPort, String currentIp, byte[] queryData, int queryLen) {
        try {
            String qStr = queryData != null ? new String(queryData, 0, queryLen, StandardCharsets.ISO_8859_1).toLowerCase() : "";
            String host = "airbeam";
            if (qStr.contains("airbeam-android")) host = "airbeam-android";
            else if (qStr.contains("airbeam-tablet")) host = "airbeam-tablet";

            byte[] responseBytes = buildMdnsAnswerPacket(currentIp, host);
            if (responseBytes == null) return;

            // 1. Unicast reply to the querying client
            if (senderAddr != null && senderPort > 0) {
                DatagramPacket unicastPacket = new DatagramPacket(responseBytes, responseBytes.length, senderAddr, senderPort);
                socket.send(unicastPacket);
            }

            // 2. Multicast reply to the mDNS group 224.0.0.251:5353
            InetAddress group = InetAddress.getByName(MDNS_GROUP);
            DatagramPacket multicastPacket = new DatagramPacket(responseBytes, responseBytes.length, group, MDNS_PORT);
            socket.send(multicastPacket);
        } catch (Exception e) {
            Log.w(TAG, "Failed sending mDNS response: " + e.getMessage());
        }
    }

    private byte[] buildMdnsAnswerPacket(String ipAddress) {
        return buildMdnsAnswerPacket(ipAddress, "airbeam");
    }

    private byte[] buildMdnsAnswerPacket(String ipAddress, String hostname) {
        try {
            byte[] ipBytes = InetAddress.getByName(ipAddress).getAddress();
            if (ipBytes.length != 4) return null;

            ByteArrayOutputStream baos = new ByteArrayOutputStream(64);
            DataOutputStream dos = new DataOutputStream(baos);

            // Transaction ID: 0x0000
            dos.writeShort(0);
            // Flags: 0x8400 (Response, Authoritative Answer, No Error)
            dos.writeShort(0x8400);
            // Questions: 0
            dos.writeShort(0);
            // Answers: 1
            dos.writeShort(1);
            // Authorities: 0
            dos.writeShort(0);
            // Additional: 0
            dos.writeShort(0);

            // Name: \x<len><hostname>\x05local\x00
            byte[] hostBytes = hostname.getBytes(StandardCharsets.US_ASCII);
            dos.writeByte(hostBytes.length);
            dos.write(hostBytes);
            dos.writeByte(5);
            dos.writeBytes("local");
            dos.writeByte(0);

            // Type: 1 (A Record)
            dos.writeShort(1);
            // Class: 0x8001 (IN class, flush cache bit)
            dos.writeShort(0x8001);
            // TTL: 120 seconds
            dos.writeInt(120);
            // RDLENGTH: 4 bytes
            dos.writeShort(4);
            // RDATA: IPv4 Address
            dos.write(ipBytes);

            dos.flush();
            return baos.toByteArray();
        } catch (Exception e) {
            Log.e(TAG, "Error building mDNS answer packet", e);
            return null;
        }
    }

    private void startPeriodicAnnouncements() {
        executor.execute(() -> {
            while (isRunning) {
                try {
                    Thread.sleep(15000);
                    if (!isRunning || multicastSocket == null || multicastSocket.isClosed()) break;

                    String currentIp = FileServerService.getLocalIpAddress(context);
                    if (currentIp != null && !currentIp.isEmpty() && !currentIp.equals("127.0.0.1")) {
                        byte[] responseBytes = buildMdnsAnswerPacket(currentIp);
                        if (responseBytes != null) {
                            InetAddress group = InetAddress.getByName(MDNS_GROUP);
                            DatagramPacket packet = new DatagramPacket(responseBytes, responseBytes.length, group, MDNS_PORT);
                            multicastSocket.send(packet);
                        }
                    }
                } catch (InterruptedException e) {
                    break;
                } catch (Exception ignored) {}
            }
        });
    }

    public synchronized void stop() {
        isRunning = false;

        if (nsdManager != null && registrationListener != null) {
            try {
                nsdManager.unregisterService(registrationListener);
            } catch (Exception ignored) {}
            registrationListener = null;
        }

        if (multicastSocket != null) {
            try {
                multicastSocket.close();
            } catch (Exception ignored) {}
            multicastSocket = null;
        }

        if (multicastLock != null && multicastLock.isHeld()) {
            try {
                multicastLock.release();
            } catch (Exception ignored) {}
            multicastLock = null;
        }

        if (executor != null) {
            executor.shutdownNow();
            executor = null;
        }

        Log.i(TAG, "AirBeam mDNS Responder stopped");
    }
}
