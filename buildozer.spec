[app]
# رفع API إلى 33 و MinAPI إلى 24 لتفادي مشاكل الأذونات والـ Headers
android.api = 33
android.minapi = 24
android.ndk_api = 24

# تحديد إصدار NDK 25b الصريح الذي يعالج مشاكل التجميع مع Kivy
android.ndk = 25b

# المتطلبات الأساسية
requirements = python3,kivy==2.3.0,flask==3.0.3,pyjnius
