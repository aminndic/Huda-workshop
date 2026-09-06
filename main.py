# -*- coding: utf-8 -*-
import threading
import time
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.widget import Widget

from android.runnable import run_on_ui_thread
from jnius import autoclass

import app as flask_app

BASE_DIR = Path(__file__).resolve().parent
flask_app.DB_NAME = str(BASE_DIR / "database.db")


class WebViewWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(lambda dt: self.start_server(), 0.2)

    def start_server(self):
        threading.Thread(target=self._server, daemon=True).start()
        Clock.schedule_once(lambda dt: self.open_webview(), 1.0)

    def _server(self):
        flask_app.app.run(
            host="127.0.0.1",
            port=5000,
            debug=False,
            threaded=True,
            use_reloader=False,
        )

    @run_on_ui_thread
    def open_webview(self):
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        WebView = autoclass("android.webkit.WebView")
        WebViewClient = autoclass("android.webkit.WebViewClient")
        activity = PythonActivity.mActivity

        webview = WebView(activity)
        webview.setWebViewClient(WebViewClient())
        settings = webview.getSettings()
        settings.setJavaScriptEnabled(True)
        settings.setDomStorageEnabled(True)
        settings.setAllowFileAccess(True)
        settings.setAllowContentAccess(True)
        webview.loadUrl("http://127.0.0.1:5000")
        activity.setContentView(webview)


class HudaWorkshopApp(App):
    def build(self):
        return WebViewWidget()


if __name__ == "__main__":
    HudaWorkshopApp().run()
