package com.airsend.receiver;

public class TransferItem {
    public enum Status {
        TRANSFERRING,
        COMPLETED,
        FAILED
    }

    private final String id;
    private final String fileName;
    private long totalBytes;
    private long transferredBytes;
    private Status status;
    private String savedPath;
    private double speedMBps = 0.0;

    public TransferItem(String id, String fileName, long totalBytes) {
        this.id = id;
        this.fileName = fileName;
        this.totalBytes = totalBytes;
        this.transferredBytes = 0;
        this.status = Status.TRANSFERRING;
    }

    public String getId() { return id; }
    public String getFileName() { return fileName; }
    public long getTotalBytes() { return totalBytes; }
    public void setTotalBytes(long bytes) { this.totalBytes = bytes; }
    public long getTransferredBytes() { return transferredBytes; }
    public void setTransferredBytes(long transferredBytes) { this.transferredBytes = transferredBytes; }
    public Status getStatus() { return status; }
    public void setStatus(Status status) { this.status = status; }
    public String getSavedPath() { return savedPath; }
    public void setSavedPath(String savedPath) { this.savedPath = savedPath; }
    public double getSpeedMBps() { return speedMBps; }
    public void setSpeedMBps(double speedMBps) { this.speedMBps = speedMBps; }

    public int getProgressPercent() {
        if (totalBytes <= 0) return 0;
        return (int) Math.min(100, (transferredBytes * 100) / totalBytes);
    }
}
