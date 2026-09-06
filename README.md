# ورشة الهدى - Offline Android APK

المشروع مبني من كود Flask المرفق ويشغل النظام داخل تطبيق Android عبر localhost.

## الملفات
- app.py: كود Flask الأصلي
- main.py: مشغل Android/Kivy وWebView
- buildozer.spec: إعداد بناء APK
- requirements.txt: المتطلبات
- .github/workflows/build.yml: بناء APK على GitHub Actions

## مهم
الواجهة الأصلية في app.py تحتوي على روابط Bootstrap/Bootstrap Icons من CDN.
هذه الروابط تحتاج إلى إزالة/استبدال بملفات محلية حتى تكون الواجهة 100% Offline.
قاعدة البيانات SQLite محلية.

## البناء
1. ارفع الملفات إلى مستودع GitHub.
2. افتح Actions.
3. شغّل Build Huda Workshop Offline APK.
4. نزّل artifact باسم huda-workshop-offline-apk.
# Huda-workshop
تطبيق ورشة الهدى اوف لاين 
