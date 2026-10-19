package com.airsend.receiver;

import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.core.content.FileProvider;
import androidx.recyclerview.widget.RecyclerView;

import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class TransferAdapter extends RecyclerView.Adapter<TransferAdapter.ViewHolder> {

    private final List<TransferItem> items = new ArrayList<>();
    private final Context context;

    public TransferAdapter(Context context) {
        this.context = context;
    }

    public void addOrUpdate(TransferItem item) {
        int index = -1;
        for (int i = 0; i < items.size(); i++) {
            if (items.get(i).getId().equals(item.getId())) {
                index = i;
                break;
            }
        }
        if (index >= 0) {
            items.set(index, item);
            notifyItemChanged(index);
        } else {
            items.add(0, item);
            notifyItemInserted(0);
        }
    }

    public int getItemCountActual() {
        return items.size();
    }

    @NonNull
    @Override
    public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_transfer, parent, false);
        return new ViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
        TransferItem item = items.get(position);
        holder.tvFileName.setText(item.getFileName());

        String sizeText = formatSize(item.getTransferredBytes());
        if (item.getTotalBytes() > 0) {
            sizeText += " / " + formatSize(item.getTotalBytes());
        }
        holder.tvTransferSize.setText(sizeText);

        holder.pbTransfer.setProgress(item.getProgressPercent());

        if (item.getStatus() == TransferItem.Status.COMPLETED) {
            holder.tvStatusBadge.setText("Completed");
            holder.tvStatusBadge.setTextColor(0xFF10B981);
            holder.tvTransferSpeed.setText("Saved to Downloads");

            if (item.getSavedPath() != null) {
                holder.layoutItemActions.setVisibility(View.VISIBLE);
                holder.btnOpenItem.setOnClickListener(v -> openFile(item.getSavedPath()));
                holder.btnShareItem.setOnClickListener(v -> shareFile(item.getSavedPath()));
            } else {
                holder.layoutItemActions.setVisibility(View.GONE);
            }
        } else if (item.getStatus() == TransferItem.Status.FAILED) {
            holder.tvStatusBadge.setText("Failed");
            holder.tvStatusBadge.setTextColor(0xFFEF4444);
            holder.tvTransferSpeed.setText("Error");
            holder.layoutItemActions.setVisibility(View.GONE);
        } else {
            holder.tvStatusBadge.setText("Receiving...");
            holder.tvStatusBadge.setTextColor(0xFF3B82F6);
            holder.tvTransferSpeed.setText(item.getProgressPercent() + "%");
            holder.layoutItemActions.setVisibility(View.GONE);
        }

        holder.itemView.setOnClickListener(v -> {
            if (item.getStatus() == TransferItem.Status.COMPLETED && item.getSavedPath() != null) {
                openFile(item.getSavedPath());
            }
        });
    }

    private void openFile(String path) {
        try {
            File file = new File(path);
            if (!file.exists()) {
                Toast.makeText(context, "File not found", Toast.LENGTH_SHORT).show();
                return;
            }
            Uri uri = FileProvider.getUriForFile(context, context.getPackageName() + ".fileprovider", file);
            Intent intent = new Intent(Intent.ACTION_VIEW);
            intent.setDataAndType(uri, getMimeType(path));
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
            context.startActivity(intent);
        } catch (Exception e) {
            Toast.makeText(context, "Cannot open file: " + e.getMessage(), Toast.LENGTH_SHORT).show();
        }
    }

    private void shareFile(String path) {
        try {
            File file = new File(path);
            if (!file.exists()) {
                Toast.makeText(context, "File not found", Toast.LENGTH_SHORT).show();
                return;
            }
            Uri uri = FileProvider.getUriForFile(context, context.getPackageName() + ".fileprovider", file);
            Intent intent = new Intent(Intent.ACTION_SEND);
            intent.setType(getMimeType(path));
            intent.putExtra(Intent.EXTRA_STREAM, uri);
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
            context.startActivity(Intent.createChooser(intent, "Share " + file.getName()));
        } catch (Exception e) {
            Toast.makeText(context, "Cannot share file: " + e.getMessage(), Toast.LENGTH_SHORT).show();
        }
    }

    private String getMimeType(String path) {
        String ext = android.webkit.MimeTypeMap.getFileExtensionFromUrl(path);
        if (ext != null) {
            String type = android.webkit.MimeTypeMap.getSingleton().getMimeTypeFromExtension(ext.toLowerCase(Locale.ROOT));
            if (type != null) return type;
        }
        return "*/*";
    }

    private String formatSize(long bytes) {
        if (bytes < 1024) return bytes + " B";
        int exp = (int) (Math.log(bytes) / Math.log(1024));
        char pre = "KMGTPE".charAt(exp - 1);
        return String.format(Locale.US, "%.1f %cB", bytes / Math.pow(1024, exp), pre);
    }

    @Override
    public int getItemCount() {
        return items.size();
    }

    static class ViewHolder extends RecyclerView.ViewHolder {
        TextView tvFileName, tvStatusBadge, tvTransferSize, tvTransferSpeed;
        ProgressBar pbTransfer;
        LinearLayout layoutItemActions;
        Button btnOpenItem, btnShareItem;

        public ViewHolder(@NonNull View itemView) {
            super(itemView);
            tvFileName = itemView.findViewById(R.id.tvFileName);
            tvStatusBadge = itemView.findViewById(R.id.tvStatusBadge);
            tvTransferSize = itemView.findViewById(R.id.tvTransferSize);
            tvTransferSpeed = itemView.findViewById(R.id.tvTransferSpeed);
            pbTransfer = itemView.findViewById(R.id.pbTransfer);
            layoutItemActions = itemView.findViewById(R.id.layoutItemActions);
            btnOpenItem = itemView.findViewById(R.id.btnOpenItem);
            btnShareItem = itemView.findViewById(R.id.btnShareItem);
        }
    }
}
