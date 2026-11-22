import os
import traceback
from kivy.utils import platform
from kivy.logger import Logger

# =========================================================
#                     ANDROID
# =========================================================
if platform == 'android':
    from jnius import autoclass, cast
    from android import activity
    from android.permissions import request_permissions, check_permission, Permission
    from android.storage import app_storage_path

    Intent = autoclass('android.content.Intent')
    MediaStore = autoclass('android.provider.MediaStore')
    File = autoclass('java.io.File')
    FileOutputStream = autoclass('java.io.FileOutputStream')
    FileProvider = autoclass('androidx.core.content.FileProvider')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')

    FILE_PROVIDER_AUTHORITY = 'org.qukloc.qukloc.fileprovider'

    def request_storage_permission():
        perms = [
            Permission.CAMERA,
            Permission.READ_EXTERNAL_STORAGE,
            Permission.WRITE_EXTERNAL_STORAGE,
        ]
        if hasattr(Permission, 'READ_MEDIA_IMAGES'):
            perms.append(Permission.READ_MEDIA_IMAGES)
        request_permissions(perms)

    def take_photo(callback, error_callback=None):
        def _do_take_photo():
            try:
                ctx = PythonActivity.mActivity
                # Используем внутренний кэш — он всегда доступен и не требует прав на SD-карту
                cache_dir = ctx.getCacheDir()
                if not cache_dir.exists():
                    cache_dir.mkdirs()

                output_file = File(cache_dir, "qukloc_capture.jpg")
                if output_file.exists():
                    output_file.delete()

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
                    activity.unbind(on_activity_result=on_activity_result)
                    if result_code == -1 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        callback(output_path)
                    else:
                        if error_callback:
                            error_callback(f"Снимок не сохранён (код: {result_code})")
                        else:
                            callback(None)

                activity.bind(on_activity_result=on_activity_result)
                ctx.startActivityForResult(intent, 0x123)

            except Exception as e:
                Logger.error(f"android_media: take_photo error: {e}\n{traceback.format_exc()}")
                if error_callback:
                    error_callback(f"Ошибка камеры: {e}")
                else:
                    callback(None)

        if not check_permission(Permission.CAMERA):
            def on_perm_result(permissions, grants):
                if all(grants):
                    _do_take_photo()
                elif error_callback:
                    error_callback("Нет системного разрешения на камеру")
            request_permissions([Permission.CAMERA], on_perm_result)
        else:
            _do_take_photo()

    def pick_photo(callback, error_callback=None):
        try:
            ctx = PythonActivity.mActivity
            intent = Intent(Intent.ACTION_GET_CONTENT)
            intent.setType("image/*")
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

            def on_activity_result(request_code, result_code, data):
                if request_code != 0x124:
                    return
                activity.unbind(on_activity_result=on_activity_result)

                if result_code != -1 or data is None:
                    callback(None)
                    return

                try:
                    uri = data.getData()
                    if uri is None:
                        if error_callback:
                            error_callback("Галерея не вернула URI файла")
                        return

                    dest = os.path.join(app_storage_path(), "selected.jpg")
                    resolver = ctx.getContentResolver()
                    input_stream = resolver.openInputStream(uri)
                    if input_stream is None:
                        if error_callback:
                            error_callback("Не удалось открыть поток файла из галереи")
                        return

                    # Нативное копирование через Java-потоки (надёжнее shutil на Android)
                    out_stream = FileOutputStream(dest)
                    buf = bytearray(8192)
                    while True:
                        bytes_read = input_stream.read(buf)
                        if bytes_read == -1:
                            break
                        out_stream.write(buf, 0, bytes_read)

                    out_stream.flush()
                    out_stream.close()
                    input_stream.close()

                    callback(dest)
                except Exception as e:
                    Logger.error(f"android_media: gallery copy error: {e}\n{traceback.format_exc()}")
                    if error_callback:
                        error_callback(f"Ошибка чтения файла: {e}")
                    else:
                        callback(None)

            activity.bind(on_activity_result=on_activity_result)
            ctx.startActivityForResult(intent, 0x124)

        except Exception as e:
            Logger.error(f"android_media: pick_photo error: {e}\n{traceback.format_exc()}")
            if error_callback:
                error_callback(f"Ошибка запуска галереи: {e}")
            else:
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

    def request_storage_permission():
        pass

    def take_photo(callback, error_callback=None):
        _show_message(
            "Камера недоступна",
            "Камера работает только на Android.\n"
            "Используйте «Галерея» для выбора файла."
        )
        callback(None)

    def pick_photo(callback, error_callback=None):
        _open_file_chooser(callback)

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
