# android_media.py
"""
Камера и галерея.
- Android: FileProvider + ACTION_GET_CONTENT (нативные).
- Desktop: FileChooserPopup от Kivy (загрузка из файловой системы).
"""

from kivy.utils import platform
from kivy.logger import Logger


# =========================================================
#                     ANDROID
# =========================================================
if platform == 'android':
    import shutil
    from jnius import autoclass, cast
    from android import activity
    from android.permissions import request_permissions, Permission
    from android.storage import app_storage_path

    Intent = autoclass('android.content.Intent')
    MediaStore = autoclass('android.provider.MediaStore')
    Uri = autoclass('android.net.Uri')
    File = autoclass('java.io.File')
    FileProvider = autoclass('androidx.core.content.FileProvider')
    Environment = autoclass('android.os.Environment')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Parcelable = autoclass('android.os.Parcelable')

    FILE_PROVIDER_AUTHORITY = 'org.qukloc.qukloc.fileprovider'

    def request_storage_permission():
        perms = [
            Permission.READ_EXTERNAL_STORAGE,
            Permission.WRITE_EXTERNAL_STORAGE,
        ]
        if hasattr(Permission, 'READ_MEDIA_IMAGES'):
            perms.append(Permission.READ_MEDIA_IMAGES)
        request_permissions(perms)

    def take_photo(callback):
        try:
            ctx = PythonActivity.mActivity
            cache_dir = ctx.getExternalCacheDir() or ctx.getCacheDir()
            output_file = File(cache_dir, "qukloc_capture.jpg")
            output_path = output_file.getAbsolutePath()

            uri = FileProvider.getUriForFile(
                ctx, FILE_PROVIDER_AUTHORITY, output_file
            )

            intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
            intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

            parcelable_uri = cast('android.os.Parcelable', uri)
            intent.putExtra(MediaStore.EXTRA_OUTPUT, parcelable_uri)

            def on_activity_result(request_code, result_code, data):
                if request_code != 0x123:
                    return
                if result_code == -1:
                    callback(output_path)
                else:
                    callback(None)

            activity.bind(on_activity_result=on_activity_result)
            ctx.startActivityForResult(intent, 0x123)

        except Exception as e:
            Logger.error(f"android_media: take_photo error: {e}")
            callback(None)

    def pick_photo(callback):
        try:
            intent = Intent(Intent.ACTION_GET_CONTENT)
            intent.setType("image/*")
            intent.addCategory(Intent.CATEGORY_OPENABLE)

            def on_activity_result(request_code, result_code, data):
                if request_code != 0x124:
                    return
                if result_code != -1 or data is None:
                    callback(None)
                    return
                try:
                    uri = data.getData()
                    dest = app_storage_path() + "/selected.jpg"
                    resolver = PythonActivity.mActivity.getContentResolver()
                    input_stream = resolver.openInputStream(uri)
                    with open(dest, 'wb') as f:
                        shutil.copyfileobj(input_stream, f)
                    input_stream.close()
                    callback(dest)
                except Exception as e:
                    Logger.error(f"android_media: gallery copy error: {e}")
                    callback(None)

            activity.bind(on_activity_result=on_activity_result)
            PythonActivity.mActivity.startActivityForResult(intent, 0x124)

        except Exception as e:
            Logger.error(f"android_media: pick_photo error: {e}")
            callback(None)


# =========================================================
#                     DESKTOP (WSL / Linux / Win / Mac)
# =========================================================
else:
    from kivy.uix.filechooser import FileChooserListView
    from kivy.uix.popup import Popup
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.label import Label
    from kivy.metrics import dp
    import os

    def request_storage_permission():
        pass

    def take_photo(callback):
        """На десктопе камеры нет — показываем сообщение."""
        _show_message(
            "Камера недоступна",
            "Камера работает только на Android.\n"
            "Используйте «Галерея» для выбора файла."
        )
        callback(None)

    def pick_photo(callback):
        """Открывает файловый диалог Kivy для выбора изображения."""
        _open_file_chooser(callback)

    # ------------------ вспомогательные ------------------
    def _show_message(title, text):
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content.add_widget(Label(text=text, halign='center'))
        btn = Button(text="OK", size_hint_y=None, height=dp(48))
        content.add_widget(btn)
        popup = Popup(
            title=title,
            content=content,
            size_hint=(0.8, 0.4),
            auto_dismiss=False,
        )
        btn.bind(on_release=popup.dismiss)
        popup.open()

    def _open_file_chooser(callback):
        start_dir = os.path.expanduser("~")

        chooser = FileChooserListView(
            path=start_dir,
            filters=['*.jpg', '*.jpeg', '*.png'],
        )

        layout = BoxLayout(orientation='vertical', spacing=dp(5), padding=dp(5))
        layout.add_widget(chooser)

        btn_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(5))
        btn_ok = Button(text="Открыть")
        btn_cancel = Button(text="Отмена")
        btn_row.add_widget(btn_ok)
        btn_row.add_widget(btn_cancel)
        layout.add_widget(btn_row)

        popup = Popup(
            title="Выберите изображение",
            content=layout,
            size_hint=(0.9, 0.9),
            auto_dismiss=False,
        )

        def on_ok(_):
            if chooser.selection:
                popup.dismiss()
                callback(chooser.selection[0])

        def on_cancel(_):
            popup.dismiss()
            callback(None)

        btn_ok.bind(on_release=on_ok)
        btn_cancel.bind(on_release=on_cancel)
        chooser.bind(
            on_submit=lambda inst, selection, touch: (
                popup.dismiss(),
                callback(selection[0]) if selection else None,
            )
        )
        popup.open()