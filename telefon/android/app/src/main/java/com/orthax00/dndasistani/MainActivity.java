package com.orthax00.dndasistani;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
  private static final String SITE = "https://dnd-asistan.vercel.app";

  @Override
  public void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    girisBaglantisi(getIntent());
  }

  @Override
  protected void onNewIntent(Intent intent) {
    super.onNewIntent(intent);
    girisBaglantisi(intent);
  }

  /** dndasistani://giris?code=...&next=/k/1 → https://site/auth/callback?code=...&next=/k/1 (girişi başlatan WebView çerezleriyle). */
  private void girisBaglantisi(Intent intent) {
    Uri uri = intent == null ? null : intent.getData();
    if (uri == null || !"dndasistani".equals(uri.getScheme()) || !"giris".equals(uri.getHost())) return;
    String sorgu = uri.getEncodedQuery();
    final String adres = SITE + "/auth/callback" + (sorgu == null ? "" : "?" + sorgu);
    getBridge().getWebView().post(() -> getBridge().getWebView().loadUrl(adres));
  }
}
