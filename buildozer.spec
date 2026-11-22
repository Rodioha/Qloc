[app]
title = QukLoc
package.name = qukloc
package.domain = org.qukloc
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,tflite,txt,h5,xml
source.include_patterns = images/*,images/plants/*,models/*
version = 0.1

requirements = hostpython3==3.11.9,python3==3.11.9,kivy,numpy,plyer,pillow,pyjnius

orientation = portrait
fullscreen = 0

android.api = 34
android.minapi = 26
android.ndk_api = 26
android.ndk = 26b
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.accept_sdk_license = True
p4a.branch = develop

# Зависимости TensorFlow Lite (LiteRT) и AndroidX
android.gradle_dependencies = androidx.core:core:1.13.1, com.google.ai.edge.litert:litert:1.4.1, com.google.ai.edge.litert:litert-support:1.4.1, com.google.ai.edge.litert:litert-gpu:1.4.1, com.google.ai.edge.litert:litert-gpu-api:1.4.1

# Разрешения для камеры и галереи (Android 8–14+)
android.permissions = CAMERA, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, READ_MEDIA_IMAGES

# Регистрация FileProvider для камеры (Android 7+)
# Требует наличия файла android_res/xml/file_paths.xml
android.add_providers = androidx.core.content.FileProvider:org.qukloc.qukloc.fileprovider:@xml/file_paths
android.add_resources = android_res

[buildozer]
log_level = 2
pip_index_url = https://pypi.org
