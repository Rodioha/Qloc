# main.py
import os
import traceback

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image as KvImage
from kivy.uix.scrollview import ScrollView
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.utils import platform
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle, RoundedRectangle

from model_tflite import get_class
from database import get_nearby_places, find_main_place_by_partial_name
from plants_database import get_plant_info, find_plant_by_partial_name
from theme import THEMES

# --- Android-специфичные модули ---
if platform == 'android':
    from android.permissions import request_permissions, Permission
    from android_media import request_storage_permission, take_photo, pick_photo
else:
    from android_media import request_storage_permission, take_photo, pick_photo

# На десктопе — окно в пропорциях телефона (9:16)
if platform != 'android':
    Window.size = (400, 711)
    Window.top = 60
    Window.left = 60


BTN_H = dp(48)
TAB_H = dp(44)
RESULT_H = dp(56)


class ThemedBackground(BoxLayout):

    def __init__(self, theme, **kwargs):
        super().__init__(**kwargs)
        self.theme = theme
        with self.canvas.before:
            Color(*theme['bg'])
            self._rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size


class RecognitionTab(ThemedBackground):
    def __init__(self, mode='places', **kwargs):
        self.mode = mode
        self.theme = THEMES[mode]
        super().__init__(
            theme=self.theme,
            orientation='vertical',
            padding=dp(10),
            spacing=dp(10),
            **kwargs
        )
        self.current_result = None

        preview_box = BoxLayout(padding=dp(4))
        with preview_box.canvas.before:
            Color(*self.theme['panel'])
            self._preview_rect = RoundedRectangle(
                pos=preview_box.pos,
                size=preview_box.size,
                radius=[dp(12)],
            )
        preview_box.bind(
            pos=lambda *a: setattr(self._preview_rect, 'pos', preview_box.pos),
            size=lambda *a: setattr(self._preview_rect, 'size', preview_box.size),
        )
        self.image_widget = KvImage(allow_stretch=True, keep_ratio=True)
        preview_box.add_widget(self.image_widget)

        btn_row = BoxLayout(size_hint_y=None, height=BTN_H, spacing=dp(8))
        btn_cam = self._make_button("Камера")
        btn_gal = self._make_button("Галерея")
        btn_cam.bind(on_press=self.on_take_photo)
        btn_gal.bind(on_press=self.on_pick_photo)
        btn_row.add_widget(btn_cam)
        btn_row.add_widget(btn_gal)
        self.add_widget(btn_row)

        self.result_label = Label(
            text="Загрузите фото или сделайте снимок",
            size_hint_y=None,
            height=RESULT_H,
            halign="center",
            valign="middle",
            color=self.theme['text'],
            font_size=dp(15),
        )
        self.result_label.bind(size=self._update_label_size)
        self.add_widget(self.result_label)

        btn_text = "Места поблизости" if mode == 'places' else "Где растёт"
        self.btn_action = self._make_button(btn_text)
        self.btn_action.bind(on_press=self.show_info)
        self.btn_action.disabled = True
        self.add_widget(self.btn_action)
-
        self.scroll = ScrollView(size_hint_y=0.35)
        self.scroll_content = BoxLayout(
            orientation="vertical", size_hint_y=None, spacing=dp(10)
        )
        self.scroll_content.bind(
            minimum_height=self.scroll_content.setter("height")
        )
        self.scroll.add_widget(self.scroll_content)
        self.add_widget(self.scroll)

    def _make_button(self, text):
        btn = Button(
            text=text,
            size_hint_y=None,
            height=BTN_H,
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=self.theme['text'],
            font_size=dp(15),
        )
        with btn.canvas.before:
            btn._bg_color = Color(*self.theme['accent'])
            btn._bg_rect = RoundedRectangle(
                pos=btn.pos, size=btn.size, radius=[dp(16)]
            )

        def _update_rect(inst, *args):
            inst._bg_rect.pos = inst.pos
            inst._bg_rect.size = inst.size

        def _update_color(inst, value):
            if inst.disabled:
                inst._bg_color.rgba = (0.3, 0.3, 0.3, 1)
            elif value == 'down':
                inst._bg_color.rgba = self.theme['accent_dn']
            else:
                inst._bg_color.rgba = self.theme['accent']

        btn.bind(pos=_update_rect, size=_update_rect, state=_update_color,
                 disabled=_update_color)
        return btn

    def _update_label_size(self, instance, value):
        instance.text_size = (value[0] - dp(20), None)

    def on_take_photo(self, *args):
        try:
            take_photo(self.process_image)
        except Exception as e:
            self.result_label.text = f"Ошибка камеры: {e}"

    def on_pick_photo(self, *args):
        try:
            pick_photo(self.process_image)
        except Exception as e:
            self.result_label.text = f"Ошибка галереи: {e}"

    def process_image(self, path):
        if not path or not os.path.exists(path):
            self.result_label.text = "Файл не найден"
            return
        self.image_widget.source = ""
        self.image_widget.source = path
        self.image_widget.reload()
        self.result_label.text = "Анализирую..."
        Clock.schedule_once(lambda dt: self._run_prediction(path), 0.1)

    def _run_prediction(self, path):
        try:
            label, confidence = get_class(path, mode=self.mode)
            if label is None:
                self.current_result = None
                self.result_label.text = "Не могу распознать (уверенность ниже 50%)"
                self.btn_action.disabled = True
                return
            self.current_result = label
            self.result_label.text = f"{label} ({confidence:.0%})"
            self.btn_action.disabled = False
        except Exception as e:
            traceback.print_exc()
            self.result_label.text = f"Ошибка: {e}"
            self.btn_action.disabled = True

    def show_info(self, *args):
        self.scroll_content.clear_widgets()
        if not self.current_result:
            return
        if self.mode == 'places':
            self._show_places_info()
        else:
            self._show_plant_info()

    def _show_places_info(self):
        place = self.current_result
        full = find_main_place_by_partial_name(place)
        if full:
            place = full
        for p in get_nearby_places(place):
            self._add_card(p['name'], p['description'])

    def _show_plant_info(self):
        name = self.current_result
        full = find_plant_by_partial_name(name)
        if full:
            name = full
        info = get_plant_info(name)
        self._add_card(
            info['name'],
            f"{info['description']}\n\n"
            f"Где растёт: {info['habitat']}\n\n"
            f"Уход: {info['care']}"
        )

    def _add_card(self, title_text, desc_text):
        card = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(8),
            spacing=dp(4),
        )
        with card.canvas.before:
            Color(*self.theme['panel'])
            card._rect = RoundedRectangle(
                pos=card.pos, size=card.size, radius=[dp(12)]
            )
        card.bind(
            pos=lambda *a: setattr(card._rect, 'pos', card.pos),
            size=lambda *a: setattr(card._rect, 'size', card.size),
            minimum_height=card.setter('height'),
        )

        title = Label(
            text=f"[b]{title_text}[/b]",
            markup=True,
            size_hint_y=None,
            height=dp(28),
            color=self.theme['text'],
            font_size=dp(15),
        )
        desc = Label(
            text=desc_text,
            size_hint_y=None,
            color=self.theme['text_dim'],
            font_size=dp(13),
            text_size=(Window.width - dp(40), None),
        )
        desc.bind(
            width=lambda inst, w: setattr(inst, 'text_size', (w - dp(20), None))
        )
        desc.bind(texture_size=lambda inst, ts: setattr(inst, 'height', ts[1]))

        card.add_widget(title)
        card.add_widget(desc)
        self.scroll_content.add_widget(card)

class HelpTab(ThemedBackground):
    """Вкладка со справкой и инструкцией по приложению."""

    def __init__(self, **kwargs):
        self.theme = THEMES.get('help', THEMES['places'])
        super().__init__(
            theme=self.theme,
            orientation='vertical',
            padding=dp(12),
            spacing=dp(10),
            **kwargs
        )

        title = Label(
            text="Инструкция по использованию",
            size_hint_y=None,
            height=dp(36),
            font_size=dp(18),
            bold=True,
            color=self.theme['text'],
            halign="center",
            valign="middle",
        )
        title.bind(size=lambda inst, val: setattr(inst, 'text_size', val))
        self.add_widget(title)

        scroll = ScrollView(do_scroll_x=False)
        content = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(10),
            padding=(0, dp(4)),
        )
        content.bind(minimum_height=content.setter("height"))

        sections = [
            (
                "1. Выбор режима",
                "Переключайтесь между вкладками «Места» и «Растения» в верхней части экрана "
                "в зависимости от того, что вы хотите распознать."
            ),
            (
                "2. Загрузка фотографии",
                "Нажмите «Камера», чтобы сделать новый снимок, или «Галерея», "
                "чтобы выбрать готовое фото с устройства."
            ),
            (
                "3. Распознавание",
                "Нейросеть автоматически проанализирует изображение и покажет название объекта "
                "с процентом уверенности. Для точного результата объект должен находиться в центре кадра "
                "при хорошем освещении."
            ),
            (
                "4. Подробная информация",
                "Если уверенность выше 50%, станет активна кнопка «Места поблизости» или «Где растёт». "
                "Нажмите её, чтобы открыть карточки с описанием, средой обитания или советами по уходу."
            ),
            (
                "Если фото не открываются",
                "Проверьте в настройках Android, выданы ли приложению разрешения на доступ к камере и файлам."
            ),
        ]

        for sec_title, sec_body in sections:
            content.add_widget(self._make_help_card(sec_title, sec_body))

        scroll.add_widget(content)
        self.add_widget(scroll)

    def _make_help_card(self, title_text, body_text):
        card = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(12),
            spacing=dp(6),
        )
        with card.canvas.before:
            Color(*self.theme['panel'])
            rect = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(12)])

        card.bind(
            pos=lambda inst, *a: setattr(rect, 'pos', inst.pos),
            size=lambda inst, *a: setattr(rect, 'size', inst.size),
        )

        lbl_title = Label(
            text=title_text,
            font_size=dp(15),
            bold=True,
            color=self.theme['text'],
            size_hint_y=None,
            halign="left",
            valign="top",
        )
        lbl_body = Label(
            text=body_text,
            font_size=dp(14),
            color=self.theme['text'],
            size_hint_y=None,
            halign="left",
            valign="top",
        )

        for lbl in (lbl_title, lbl_body):
            lbl.bind(
                width=lambda inst, val: setattr(inst, 'text_size', (val, None)),
                texture_size=lambda inst, val: setattr(inst, 'height', val[1]),
            )

        card.add_widget(lbl_title)
        card.add_widget(lbl_body)
        card.bind(minimum_height=card.setter("height"))
        return card

class QukLocApp(App):
    def build(self):
        self.title = "QukLoc"

        if platform == 'android':
            request_permissions([
                Permission.CAMERA,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
            ])
        else:
            Window.bind(on_drop_file=self._on_drop_file)

        root = TabbedPanel(do_default_tab=False)
        root.tab_width = Window.width / 3
        root.background_color = THEMES['places']['bg']
        root.default_tab_height = TAB_H

        tab_places = TabbedPanelItem(text='Места')
        tab_places.background_color = THEMES['places']['tab_active']
        tab_places.color = THEMES['places']['text']
        tab_places.add_widget(RecognitionTab(mode='places'))
        root.add_widget(tab_places)

        tab_plants = TabbedPanelItem(text='Растения')
        tab_plants.background_color = THEMES['plants']['tab_active']
        tab_plants.color = THEMES['plants']['text']
        tab_plants.add_widget(RecognitionTab(mode='plants'))
        root.add_widget(tab_plants)

        tab_help = TabbedPanelItem(text='Справка')
        tab_help.background_color = THEMES.get('help', THEMES['places'])['tab_active']
        tab_help.color = THEMES.get('help', THEMES['places'])['text']
        tab_help.add_widget(HelpTab())
        root.add_widget(tab_help)

        return root

    def _on_drop_file(self, window, file_path, *args):
        path = file_path.decode('utf-8') if isinstance(file_path, bytes) else file_path
        if not path.lower().endswith(('.jpg', '.jpeg', '.png')):
            return
        try:
            current_tab = self.root.current_tab
            for child in current_tab.children:
                if hasattr(child, 'process_image'):
                    child.process_image(path)
                    break
        except Exception as e:
            print(f"drop error: {e}")

if __name__ == "__main__":
    QukLocApp().run()
