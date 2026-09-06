[app]

title = Huda Workshop
package.name = hudaworkshop
package.domain = org.aminndic

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,json,txt,db,css,js

source.exclude_dirs = tests,bin,venv,.venv,.github,.git

version = 1.0

requirements = python3==3.12.10,hostpython3==3.12.10,kivy==2.3.0,flask==3.0.3,pyjnius

orientation = portrait
fullscreen = 0

android.permissions = INTERNET

android.api = 33
android.minapi = 21
android.ndk = 25b

android.archs = arm64-v8a

android.allow_backup = True

[buildozer]

log_level = 2
warn_on_root = 1
