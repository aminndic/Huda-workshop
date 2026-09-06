[app]
title = ورشة الهدى
package.name = hudaworkshop
package.domain = org.hudaworkshop

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,json,txt,ttf,db,css,js

version = 1.0

requirements = python3,kivy==2.3.0,flask==3.0.3,pyjnius

orientation = portrait
fullscreen = 0

android.api = 35
android.minapi = 23
android.archs = arm64-v8a
android.ndk = 26b
android.accept_sdk_license = True

android.permissions = INTERNET

[buildozer]
log_level = 2
warn_on_root = 1

[python-for-android]
python_version = 3.12
