package com.hookmt.xrm;

import android.annotation.SuppressLint;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.webkit.WebViewAssetLoader;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

public class MainActivity extends AppCompatActivity {
    private static final int FILE_REQUEST = 1001;
    private static final int SAVE_REQUEST = 1002;
    private byte[] pendingFile;
    private String pendingHost, pendingPath;
    private static final String ORIGIN = "https://appassets.androidplatform.net";
    private static final String KEY_ALIAS = "xrm-router-password";
    private WebView webView;
    private ValueCallback<Uri[]> upload;
    private final ExecutorService executor = Executors.newFixedThreadPool(2);

    @SuppressLint("SetJavaScriptEnabled")
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(R.layout.activity_main);
        webView = findViewById(R.id.webview);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        WebViewAssetLoader assets = new WebViewAssetLoader.Builder()
                .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this)).build();
        webView.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest req) {
                return assets.shouldInterceptRequest(req.getUrl());
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                return !req.getUrl().toString().startsWith(ORIGIN + "/assets/");
            }
        });
        webView.addJavascriptInterface(new RouterBridge(), "AndroidRouter");
        webView.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onJsAlert(WebView view, String url, String message, android.webkit.JsResult result) {
                new AlertDialog.Builder(MainActivity.this).setTitle("Xiaomi Router Manager").setMessage(message)
                        .setPositiveButton(android.R.string.ok, (dialog, which) -> result.confirm())
                        .setOnCancelListener(dialog -> result.cancel()).show();
                return true;
            }
            @Override public boolean onJsConfirm(WebView view, String url, String message, android.webkit.JsResult result) {
                new AlertDialog.Builder(MainActivity.this).setTitle("Xiaomi Router Manager").setMessage(message)
                        .setPositiveButton(android.R.string.ok, (dialog, which) -> result.confirm())
                        .setNegativeButton(android.R.string.cancel, (dialog, which) -> result.cancel())
                        .setOnCancelListener(dialog -> result.cancel()).show();
                return true;
            }
            @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (upload != null) upload.onReceiveValue(null);
                upload = callback;
                try { startActivityForResult(params.createIntent(), FILE_REQUEST); return true; }
                catch (Exception e) { upload = null; return false; }
            }
        });
        webView.loadUrl(ORIGIN + "/assets/index.html");
    }

    private SecretKey key() throws Exception {
        KeyStore ks = KeyStore.getInstance("AndroidKeyStore");
        ks.load(null);
        if (!ks.containsAlias(KEY_ALIAS)) {
            KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
            generator.init(new KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                    .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build());
            generator.generateKey();
        }
        return (SecretKey) ks.getKey(KEY_ALIAS, null);
    }

    private class RouterBridge {
        @JavascriptInterface public boolean isPreview() { return BuildConfig.PREVIEW_READ_ONLY; }
        @JavascriptInterface public void request(int id, String host, String path, String method, String body) {
            executor.execute(() -> {
                String response;
                try {
                    if (!host.matches("[A-Za-z0-9.-]{1,253}") || !path.startsWith("/cgi-bin/luci/") || path.contains("..") ||
                            !(method.equals("GET") || method.equals("POST"))) throw new IllegalArgumentException("Nieprawidłowy adres");
                    if (BuildConfig.PREVIEW_READ_ONLY && !previewAllows(path, method)) {
                        callback(id, false, "W wersji testowej zmiana ustawień jest zablokowana");
                        return;
                    }
                    HttpURLConnection conn = (HttpURLConnection) new URL("http", host, path).openConnection();
                    conn.setConnectTimeout(6000);
                    conn.setReadTimeout(10000);
                    conn.setInstanceFollowRedirects(false);
                    conn.setRequestMethod(method);
                    if (method.equals("POST")) {
                        conn.setDoOutput(true);
                        conn.setRequestProperty("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8");
                        try (OutputStream out = conn.getOutputStream()) { out.write(body.getBytes(StandardCharsets.UTF_8)); }
                    }
                    int status = conn.getResponseCode();
                    if (status < 200 || status >= 300) throw new Exception("HTTP " + status);
                    ByteArrayOutputStream bytes = new ByteArrayOutputStream();
                    try (InputStream in = conn.getInputStream()) {
                        byte[] buf = new byte[8192]; int n;
                        while ((n = in.read(buf)) != -1) {
                            if (bytes.size() + n > 2_000_000) throw new Exception("Odpowiedź jest zbyt duża");
                            bytes.write(buf, 0, n);
                        }
                    } finally { conn.disconnect(); }
                    response = new String(bytes.toByteArray(), StandardCharsets.UTF_8);
                    callback(id, true, response);
                } catch (Exception e) { callback(id, false, "Brak odpowiedzi routera lub błąd połączenia"); }
            });
        }
        private boolean previewAllows(String path, String method) {
            if (path.equals("/cgi-bin/luci/web") && method.equals("GET")) return true;
            String endpoint = path.replaceFirst("^/cgi-bin/luci/(;stok=[a-zA-Z0-9_-]+/)?api/", "");
            if (method.equals("POST")) return endpoint.equals("xqsystem/login");
            if (!method.equals("GET")) return false;
            String base = endpoint.split("\\?", 2)[0];
            String[] allowed = {"xqsystem/init_info", "misystem/status", "misystem/devicelist", "xqnetwork/wan_info",
                "xqnetwork/macbind_info", "xqnetwork/wifi_detail_all", "misystem/get_ps_map", "xqnetwork/lan_info",
                "xqnetwork/get_aimesh_config", "xqnetwork/get_twt", "xqnetwork/get_wifi_txbf", "xqnetwork/get_miotrelay_switch",
                "xqnetwork/get_wifi_silence", "xqnetwork/lan_dhcp", "misystem/get_ps_service", "xqsystem/dmz",
                "xqsystem/portforward", "xqsystem/upnp", "misystem/qos_info", "misystem/topo_graph"};
            for (String item : allowed) if (item.equals(base)) return true;
            return false;
        }
        private void callback(int id, boolean ok, String value) {
            String js = "window.xrmNativeResult(" + id + "," + ok + "," + JSONObject.quote(value) + ")";
            runOnUiThread(() -> { if (webView != null) webView.evaluateJavascript(js, null); });
        }
        @JavascriptInterface public boolean savePassword(String host, String password) {
            try {
                Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
                cipher.init(Cipher.ENCRYPT_MODE, key());
                cipher.updateAAD(host.getBytes(StandardCharsets.UTF_8));
                String iv = Base64.encodeToString(cipher.getIV(), Base64.NO_WRAP);
                String data = Base64.encodeToString(cipher.doFinal(password.getBytes(StandardCharsets.UTF_8)), Base64.NO_WRAP);
                return getSharedPreferences("xrm_secret", MODE_PRIVATE).edit().putString("host", host).putString("iv", iv).putString("data", data).commit();
            } catch (Exception e) { return false; }
        }
        @JavascriptInterface public String readPassword(String host) {
            try {
                android.content.SharedPreferences p = getSharedPreferences("xrm_secret", MODE_PRIVATE);
                if (!host.equals(p.getString("host", ""))) return "";
                Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
                cipher.init(Cipher.DECRYPT_MODE, key(), new GCMParameterSpec(128, Base64.decode(p.getString("iv", ""), Base64.NO_WRAP)));
                cipher.updateAAD(host.getBytes(StandardCharsets.UTF_8));
                return new String(cipher.doFinal(Base64.decode(p.getString("data", ""), Base64.NO_WRAP)), StandardCharsets.UTF_8);
            } catch (Exception e) { return ""; }
        }
        @JavascriptInterface public void saveTextFile(String name, String mime, String text) {
            if (text == null || text.length() > 4_000_000) return;
            runOnUiThread(() -> { pendingHost=null; pendingPath=null; pendingFile=text.getBytes(StandardCharsets.UTF_8); requestSave(name, mime); });
        }
        @JavascriptInterface public void saveRouterFile(String host, String path, String name) {
            if (!host.matches("[A-Za-z0-9.-]{1,253}") || !path.matches("/cgi-bin/luci/;stok=[A-Za-z0-9_-]+/api/misystem/c_download/[A-Za-z0-9._-]+")) return;
            runOnUiThread(() -> { pendingFile=null; pendingHost=host; pendingPath=path; requestSave(name, "application/gzip"); });
        }
        @JavascriptInterface public void forgetPassword() { getSharedPreferences("xrm_secret", MODE_PRIVATE).edit().clear().apply(); }
    }
    private void requestSave(String name, String mime) {
        try {
            Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType(mime);
            intent.putExtra(Intent.EXTRA_TITLE, name.replaceAll("[^A-Za-z0-9._-]", "_"));
            startActivityForResult(intent, SAVE_REQUEST);
        } catch (Exception e) { pendingFile=null; pendingHost=null; pendingPath=null; reportSave(false); }
    }
    private void reportSave(boolean success) {
        runOnUiThread(() -> { if (webView != null) webView.evaluateJavascript("window.xrmSaveComplete && window.xrmSaveComplete(" + success + ")", null); });
    }
    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == FILE_REQUEST && upload != null) {
            upload.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(resultCode, data)); upload = null;
        } else if (requestCode == SAVE_REQUEST) {
            byte[] bytes=pendingFile; String host=pendingHost, path=pendingPath;
            pendingFile=null; pendingHost=null; pendingPath=null;
            if (resultCode != RESULT_OK || data == null || data.getData() == null) return;
            Uri destination=data.getData();
            executor.execute(() -> {
                try (OutputStream out=getContentResolver().openOutputStream(destination)) {
                    if (out == null) throw new Exception();
                    if (bytes != null) out.write(bytes);
                    else {
                        HttpURLConnection conn=(HttpURLConnection)new URL("http",host,path).openConnection();
                        conn.setConnectTimeout(6000); conn.setReadTimeout(20000); conn.setInstanceFollowRedirects(false);
                        if (conn.getResponseCode()!=200) throw new Exception();
                        try (InputStream in=conn.getInputStream()) {
                            byte[] buf=new byte[8192]; int n,total=0;
                            while((n=in.read(buf))!=-1) { total+=n; if(total>20_000_000) throw new Exception(); out.write(buf,0,n); }
                        } finally { conn.disconnect(); }
                    }
                    reportSave(true);
                } catch(Exception e) { reportSave(false); }
            });
        }
    }
    @Override protected void onDestroy() {
        executor.shutdownNow();
        if (webView != null) { webView.removeJavascriptInterface("AndroidRouter"); webView.destroy(); webView = null; }
        super.onDestroy();
    }
}
