package com.subping.app;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.content.res.ColorStateList;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Bundle;
import android.os.Message;
import android.view.Gravity;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;

public class MainActivity extends Activity {

    private static final String HOME = "https://gan4ik13.github.io/subtrack/";

    private WebView webView;
    private View loadingView;
    private View errorView;
    private boolean loadedOnce = false;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        Window win = getWindow();
        win.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
        win.setStatusBarColor(0xFF0B0C10);
        win.setNavigationBarColor(0xFF0B0C10);

        WebView.setWebContentsDebuggingEnabled(true);

        webView = new WebView(this);
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setSupportMultipleWindows(true);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if (isInternal(uri)) {
                    return false;
                }
                openExternal(uri);
                return true;
            }

            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {
                if (!loadedOnce) showLoading();
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                loadedOnce = true;
                hideLoading();
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame() && !loadedOnce) showError();
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onCreateWindow(WebView view, boolean isDialog, boolean isUserGesture, Message resultMsg) {
                WebView child = new WebView(MainActivity.this);
                child.getSettings().setJavaScriptEnabled(true);
                child.getSettings().setDomStorageEnabled(true);
                child.setWebViewClient(new WebViewClient() {
                    @Override
                    public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
                        if (isInternal(r.getUrl())) {
                            return false;
                        }
                        openExternal(r.getUrl());
                        return true;
                    }
                });
                WebView.WebViewTransport transport = (WebView.WebViewTransport) resultMsg.obj;
                transport.setWebView(child);
                resultMsg.sendToTarget();
                return true;
            }
        });

        FrameLayout root = new FrameLayout(this);
        root.addView(webView, matchParent());

        loadingView = buildLoading();
        errorView = buildError();
        root.addView(loadingView, matchParent());
        root.addView(errorView, matchParent());

        setContentView(root);

        webView.loadUrl(HOME);
    }

    private boolean isInternal(Uri uri) {
        String host = uri.getHost();
        return host != null && (host.equals("gan4ik13.github.io") || host.endsWith(".github.io"));
    }

    private void openExternal(Uri uri) {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, uri));
        } catch (Exception ignored) {
        }
    }

    private FrameLayout.LayoutParams matchParent() {
        return new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT);
    }

    private LinearLayout.LayoutParams wrapContent() {
        return new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
    }

    private View buildLoading() {
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.VERTICAL);
        l.setGravity(Gravity.CENTER);
        l.setBackgroundColor(0xFF0B0C10);
        ProgressBar pb = new ProgressBar(this, null, android.R.attr.progressBarStyleLarge);
        pb.setIndeterminateTintList(ColorStateList.valueOf(0xFF818CF8));
        l.addView(pb, wrapContent());
        TextView t = new TextView(this);
        t.setText("Загрузка SubPing…");
        t.setTextColor(0xFF9497A8);
        t.setTextSize(14);
        l.addView(t);
        return l;
    }

    private View buildError() {
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.VERTICAL);
        l.setGravity(Gravity.CENTER);
        l.setBackgroundColor(0xFF0B0C10);
        l.setPadding(48, 48, 48, 48);
        TextView title = new TextView(this);
        title.setText("Нет подключения к интернету");
        title.setTextColor(0xFFF1F2F6);
        title.setTextSize(18);
        l.addView(title, wrapContent());
        TextView sub = new TextView(this);
        sub.setText("Проверьте соединение и попробуйте ещё раз");
        sub.setTextColor(0xFF9497A8);
        sub.setTextSize(14);
        l.addView(sub, wrapContent());
        Button btn = new Button(this);
        btn.setText("Повторить");
        btn.setOnClickListener(v -> {
            loadedOnce = false;
            errorView.setVisibility(View.GONE);
            loadingView.setVisibility(View.VISIBLE);
            webView.reload();
        });
        l.addView(btn, wrapContent());
        return l;
    }

    private void showLoading() {
        loadingView.setVisibility(View.VISIBLE);
    }

    private void hideLoading() {
        loadingView.setVisibility(View.GONE);
    }

    private void showError() {
        loadingView.setVisibility(View.GONE);
        errorView.setVisibility(View.VISIBLE);
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        if (webView != null) webView.destroy();
        super.onDestroy();
    }
}
