[app]
title = QukLoc
package.name = qukloc
package.domain = org.qukloc
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,tflite,txt,h5,xml
source.include_patterns = images/*,images/plants/*,models/*,file_paths.xml
version = 0.1

requirements = hostpython3==3.11.9,python3==3.11.9,kivy,numpy,plyer,pillow,pyjnius

orientation = portrait
fullscreen = 0

android.api = 33
android.minapi = 26
android.ndk_api = 26
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.accept_sdk_license = True
# Зависимости TensorFlow Lite (LiteRT)

android.gradle_dependencies = androidx.core:core:1.13.1, com.google.ai.edge.litert:litert:1.4.1, com.google.ai.edge.litert:litert-support:1.4.1, com.google.ai.edge.litert:litert-gpu:1.4.1, com.google.ai.edge.litert:litert-gpu-api:1.4.1
# Разрешения: для Android 12 и ниже — READ/WRITE_EXTERNAL_STORAGE,
# для Android 13+ — READ_MEDIA_IMAGES
android.permissions = CAMERA, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, READ_MEDIA_IMAGES

# FileProvider для передачи Uri в камеру (Android 7+)
#android.add_providers = androidx.core.content.FileProvider:org.qukloc.qukloc.fileprovider:file_paths.xml
p4a.extra_args = --fileprovider-paths=file_paths.xml
#p4a.source_dir = /home/NinaR/Qukloc/.buildozer/android/platform/python-for-android

[buildozer]
log_level = 2
pip_index_url = https://pypi.org/simple
