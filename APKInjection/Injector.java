package com.inject;

import android.content.Context;
import android.widget.Toast;
import android.util.Log;
import android.os.Environment;
import android.content.Intent;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;

public class Injector {
    private static final String version = "1.0.0";
    public static void init(Context context) {
        Toast.makeText(context, "Injector loaded! Version: " + version, Toast.LENGTH_SHORT).show();
        if (!checkPermissions(context)) {return;}
        copyFile(new File("/data/data/com.gramgames.mergedragons/files/md_db.db"), new File(Environment.getExternalStorageDirectory(), "MergeDragons/md_db_" + System.currentTimeMillis() + ".db"));
        if(new File(Environment.getExternalStorageDirectory(), "MergeDragons/md_db_import.db").exists()) {
            copyFile(new File(Environment.getExternalStorageDirectory(), "MergeDragons/md_db_import.db"), new File("/data/data/com.gramgames.mergedragons/files/md_db.db"));
            deleteFile(new File(Environment.getExternalStorageDirectory(), "MergeDragons/md_db_import.db"));
            Toast.makeText(context, "File to import found! Restarting app...", Toast.LENGTH_LONG).show();
            restartApp(context);
        }
    }
    private static void log(String message, String severity) {
        Log.d("[Injector] " + severity, message);
    }
    private static boolean checkPermissions(Context context) {
        if (!Environment.getExternalStorageDirectory().exists()) {
            Toast.makeText(context, "External storage not found! Injector cannot work!", Toast.LENGTH_LONG).show();
            return false;
        }
        if (!Environment.getExternalStorageDirectory().canWrite()) {
            Toast.makeText(context, "External storage not writable! Injector cannot work!", Toast.LENGTH_LONG).show();
            return false;
        }
        if (!Environment.getExternalStorageDirectory().canRead()) {
            Toast.makeText(context, "External storage not readable! Injector cannot work!", Toast.LENGTH_LONG).show();
            return false;
        }
        if (!new File("/data/data/com.gramgames.mergedragons/files/md_db.db").exists()) {
            Toast.makeText(context, "File to export not found! Maybe you don't have any savegame?", Toast.LENGTH_LONG).show();
            return false;
        }
        return true;
    }
    private static boolean copyFile(File source, File dest) {
        if (!dest.getParentFile().exists()) {
            dest.getParentFile().mkdirs();
        }
        if (!source.exists()) {
            log("Source file does not exist: " + source.getAbsolutePath(), "WARNING");
            return false;
        }
        
        log("Copying file: " + source.getName(), "INFO");
        try (InputStream in = new FileInputStream(source);
             OutputStream out = new FileOutputStream(dest)) {

            byte[] buffer = new byte[8192];
            int length;

            while ((length = in.read(buffer)) > 0) {
                out.write(buffer, 0, length);
            }
            out.flush();
            log("File copied successfully: " + dest.getAbsolutePath(), "INFO");
            return true;
        } catch (Exception e) {
            log("Error copying file: " + e.getMessage(), "ERROR");
            return false;
        }
    }
    private static void deleteFile(File source) {
        if (source.exists()) {
            source.delete();
            log("File deleted: " + source.getAbsolutePath(), "INFO");
        }
    }
    private static void restartApp(Context context) {
        try {
            Intent intent = context.getPackageManager()
                    .getLaunchIntentForPackage(context.getPackageName());

            if (intent == null) return;

            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | 
                            Intent.FLAG_ACTIVITY_CLEAR_TASK);

            context.startActivity(intent);

            android.os.Process.killProcess(android.os.Process.myPid());

        } catch (Exception e) {
            log("Error restarting app: " + e.getMessage(), "ERROR");
        }
    }
}
