package com.airsend.receiver;

import android.content.Context;
import android.net.Uri;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.Locale;

public class StagedFile {
    public final int index;
    public final String name;
    public final long size;
    public final Uri uri;
    public final File file;
    public final String mimeType;

    public StagedFile(int index, String name, long size, Uri uri, String mimeType) {
        this.index = index;
        this.name = name;
        this.size = size;
        this.uri = uri;
        this.file = null;
        this.mimeType = mimeType != null ? mimeType : "application/octet-stream";
    }

    public StagedFile(int index, File file) {
        this.index = index;
        this.name = file.getName();
        this.size = file.length();
        this.uri = null;
        this.file = file;
        this.mimeType = guessMimeType(file.getName());
    }

    public InputStream openInputStream(Context context) throws IOException {
        if (uri != null) {
            InputStream is = context.getContentResolver().openInputStream(uri);
            if (is == null) throw new IOException("Could not open content URI: " + uri);
            return is;
        } else if (file != null) {
            return new FileInputStream(file);
        }
        throw new IOException("No valid file or URI for staged file " + name);
    }

    public String getFormattedSize() {
        if (size <= 0) return "0 B";
        if (size < 1024) return size + " B";
        if (size < 1024 * 1024) return String.format(Locale.US, "%.1f KB", size / 1024.0);
        if (size < 1024 * 1024 * 1024) return String.format(Locale.US, "%.1f MB", size / (1024.0 * 1024.0));
        return String.format(Locale.US, "%.2f GB", size / (1024.0 * 1024.0 * 1024.0));
    }

    public JSONObject toJson() {
        JSONObject obj = new JSONObject();
        try {
            obj.put("index", index);
            obj.put("name", name);
            obj.put("size", size);
            obj.put("formatted_size", getFormattedSize());
            obj.put("mime", mimeType);
            obj.put("thumb_url", "");
        } catch (JSONException ignored) {}
        return obj;
    }

    public static String guessMimeType(String filename) {
        if (filename == null) return "application/octet-stream";
        String lower = filename.toLowerCase(Locale.ROOT);
        if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) return "image/jpeg";
        if (lower.endsWith(".png")) return "image/png";
        if (lower.endsWith(".gif")) return "image/gif";
        if (lower.endsWith(".webp")) return "image/webp";
        if (lower.endsWith(".heic")) return "image/heic";
        if (lower.endsWith(".mp4")) return "video/mp4";
        if (lower.endsWith(".mov")) return "video/quicktime";
        if (lower.endsWith(".mkv")) return "video/x-matroska";
        if (lower.endsWith(".mp3")) return "audio/mpeg";
        if (lower.endsWith(".m4a")) return "audio/mp4";
        if (lower.endsWith(".wav")) return "audio/wav";
        if (lower.endsWith(".pdf")) return "application/pdf";
        if (lower.endsWith(".zip")) return "application/zip";
        if (lower.endsWith(".apk")) return "application/vnd.android.package-archive";
        return "application/octet-stream";
    }
}
