import os
import time
import glob
import traceback
from kivy.utils import platform
from kivy.logger import Logger
from kivy.clock import Clock

if platform == 'android':
    from jnius import autoclass, cast
    from android import activity
    from android.permissions import request_permissions, check_permission, Permission
    from android.storage import app_storage_path

    Intent = autoclass('android.content.Intent')
    ContentValues = autoclass('android.content.ContentValues')
    MediaStore = autoclass('android.provider.MediaStore')
    MediaColumns = autoclass('android.provider.MediaStore$MediaColumns')
    ImagesMedia = autoclass('android.provider.MediaStore$Images$Media')
    FileOutputStream = autoclass('java.io.FileOutputStream')
    BitmapCompressFormat = autoclass('android.graphics.Bitmap$CompressFormat')
    BuildVersion = autoclass('android.os.Build$VERSION')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')

    REQ_CAMERA = 1001
    REQ_GALLERY = 1002

    def _run_on_ui(func, *args):
        if func:
            Clock.schedule_once(lambda dt: func(*args), 0)

    def _clean_old_temp_files():
        try:
            pattern = os.path.join(app_storage_path(), "qukloc_img_*.jpg")
            for f in glob.glob(pattern):
                try:
                    os.remove(f)
                except OSError:
                    pass
        except Exception:
            pass

    def _new_temp_path():
        _clean_old_temp_files()
        return os.path.join(app_storage_path(), f"qukloc_img_{int(time.time() * 1000)}.jpg")

    def _copy_uri_to_local(ctx, uri):
        dest = _new_temp_path()
        resolver = ctx.getContentResolver()
        input_stream = resolver.openInputStream(uri)
        if input_stream is None:
            raise IOError("InputStream вернул None")

        out_stream = FileOutputStream(dest)
        buf = bytearray(8192)
        total_bytes = 0
        try:
            while True:
                bytes_read = input_stream.read(buf)
                if bytes_read == -1:
                    break
                out_stream.write(buf, 0, bytes_read)
                total_bytes += bytes_read
            out_stream.flush()
        finally:
            out_stream.close()
            input_stream.close()

        if total_bytes == 0 or not os.path.exists(dest):
            raise IOError("Файл пуст (0 байт)")

        return dest

    def request_storage_permission():
        perms = [Permission.CAMERA]
        if hasattr(Permission, 'READ_MEDIA_IMAGES'):
            perms.append(Permission.READ_MEDIA_IMAGES)
        else:
            perms.extend([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
            ])
        request_permissions(perms)

    def take_photo(callback, error_callback=None):
        def _launch_camera():
            photo_uri = None
            try:
                ctx = PythonActivity.mActivity
                resolver = ctx.getContentResolver()

                values = ContentValues()
                values.put(MediaColumns.DISPLAY_NAME, f"qukloc_{int(time.time())}.jpg")
                values.put(MediaColumns.MIME_TYPE, "image/jpeg")
                if BuildVersion.SDK_INT >= 29:
                    values.put(MediaColumns.RELATIVE_PATH, "Pictures/QukLoc")

                photo_uri = resolver.insert(ImagesMedia.EXTERNAL_CONTENT_URI, values)

                intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
                if photo_uri is not None:
                    intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
                    intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    parcelable_uri = cast('android.os.Parcelable', photo_uri)
                    intent.putExtra(MediaStore.EXTRA_OUTPUT, parcelable_uri)

                def on_activity_result(request_code, result_code, data):
                    if request_code != REQ_CAMERA:
                        return
                    activity.unbind(on_activity_result=on_activity_result)

                    if result_code != -1:
                        if photo_uri is not None:
                            try:
                                resolver.delete(photo_uri, None, None)
                            except Exception:
                                pass
                        _run_on_ui(error_callback, f"Съёмка отменена (код {result_code})")
                        return

                    if photo_uri is not None:
                        try:
                            local_path = _copy_uri_to_local(ctx, photo_uri)
                            try:
                                resolver.delete(photo_uri, None, None)
                            except Exception:
                                pass
                            _run_on_ui(callback, local_path)
                            return
                        except Exception as e:
                            Logger.warning(f"android_media: URI read failed, trying extras: {e}")

                    try:
                        if data is not None and data.getExtras() is not None:
                            bmp = data.getExtras().get("data")
                            if bmp is not None:
                                dest = _new_temp_path()
                                out = FileOutputStream(dest)
                                bmp.compress(BitmapCompressFormat.JPEG, 95, out)
                                out.flush()
                                out.close()
                                _run_on_ui(callback, dest)
                                return
                    except Exception as e:
                        Logger.error(f"android_media: extras bitmap error: {e}")

                    _run_on_ui(error_callback, "Камера не вернула изображение")

                activity.bind(on_activity_result=on_activity_result)
                ctx.startActivityForResult(intent, REQ_CAMERA)

            except Exception as e:
                Logger.error(f"android_media: take_photo error: {e}\n{traceback.format_exc()}")
                _run_on_ui(error_callback, f"Ошибка камеры: {e}")

        if not check_permission(Permission.CAMERA):
            def on_perm_result(permissions, grants):
                if all(grants):
                    _launch_camera()
                else:
                    _run_on_ui(error_callback, "Разрешите доступ к камере в настройках")
            request_permissions([Permission.CAMERA], on_perm_result)
        else:
            _launch_camera()

    def pick_photo(callback, error_callback=None):
        try:
            ctx = PythonActivity.mActivity
            intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent.setType("image/*")
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

            def on_activity_result(request_code, result_code, data):
                if request_code != REQ_GALLERY:
                    return
                activity.unbind(on_activity_result=on_activity_result)

                if result_code != -1 or data is None:
                    _run_on_ui(error_callback, "Выбор файла отменён")
                    return

                try:
                    uri = data.getData()
                    if uri is None:
                        _run_on_ui(error_callback, "Галерея не вернула URI")
                        return

                    local_path = _copy_uri_to_local(ctx, uri)
                    _run_on_ui(callback, local_path)
                except Exception as e:
                    Logger.error(f"android_media: gallery copy error: {e}\n{traceback.format_exc()}")
                    _run_on_ui(error_callback, f"Ошибка чтения: {e}")

            activity.bind(on_activity_result=on_activity_result)
            ctx.startActivityForResult(intent, REQ_GALLERY)

        except Exception as e:
            Logger.error(f"android_media: pick_photo error: {e}\n{traceback.format_exc()}")
            _run_on_ui(error_callback, f"Ошибка галереи: {e}")

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
        if error_callback:
            error_callback("Камера работает только на Android")

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
