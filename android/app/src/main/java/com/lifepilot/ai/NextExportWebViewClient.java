package com.lifepilot.ai;

import android.net.Uri;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import com.getcapacitor.Bridge;
import com.getcapacitor.BridgeWebViewClient;
import java.io.IOException;
import java.io.InputStream;
import java.util.Collections;

/** Serve Next.js's per-route HTML on reload instead of Capacitor's SPA index fallback. */
public class NextExportWebViewClient extends BridgeWebViewClient {
    private final Bridge bridge;

    public NextExportWebViewClient(Bridge bridge) {
        super(bridge);
        this.bridge = bridge;
    }

    @Override
    public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
        Uri url = request.getUrl();
        Uri local = Uri.parse(bridge.getLocalUrl());
        String route = url.getPath();
        if (request.isForMainFrame() && "GET".equals(request.getMethod())
                && local.getScheme().equals(url.getScheme())
                && local.getAuthority().equals(url.getAuthority())
                && route != null && route.matches("/(?:[a-zA-Z0-9_-]+/)*[a-zA-Z0-9_-]*")) {
            String asset = "public" + (route.endsWith("/") ? route : route + "/") + "index.html";
            try {
                return html(asset, 200, "OK");
            } catch (IOException missingPage) {
                try {
                    return html("public/404.html", 404, "Not Found");
                } catch (IOException missingExport) {
                    // Let Capacitor report a missing/broken export through its normal handler.
                }
            }
        }
        // Keep Capacitor's handling of JS, CSS, Next.js RSC .txt files, plugins and API calls.
        return super.shouldInterceptRequest(view, request);
    }

    private WebResourceResponse html(String asset, int status, String reason) throws IOException {
        InputStream stream = bridge.getContext().getAssets().open(asset);
        return new WebResourceResponse(
            "text/html", "UTF-8", status, reason, Collections.emptyMap(),
            bridge.getLocalServer().getJavaScriptInjectedStream(stream)
        );
    }
}
