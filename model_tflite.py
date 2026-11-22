# model_tflite.py
import os
import numpy as np
from PIL import Image, ImageOps
from tflite_model import TensorFlowModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- Модель и метки для МЕСТ ----------
PLACES_MODEL  = os.path.join(BASE_DIR, "models", "model.tflite")
PLACES_LABELS = os.path.join(BASE_DIR, "labels_places.txt")

# ---------- Модель и метки для РАСТЕНИЙ ----------
PLANTS_MODEL  = os.path.join(BASE_DIR, "models", "plants.tflite")
PLANTS_LABELS = os.path.join(BASE_DIR, "labels_plants.txt")

IMG_SIZE = (224, 224)
CONFIDENCE_THRESHOLD = 0.50   # ниже — «не могу распознать»

_cache = {}


def _paths_for(mode):
    if mode == "plants":
        return PLANTS_MODEL, PLANTS_LABELS
    return PLACES_MODEL, PLACES_LABELS


def _load(mode):
    """Загружает и кэширует (model, labels) для указанного режима."""
    if mode in _cache:
        return _cache[mode]

    model_path, labels_path = _paths_for(mode)

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"[{mode}] Модель не найдена: {model_path}")
    if not os.path.exists(labels_path):
        raise FileNotFoundError(f"[{mode}] Файл меток не найден: {labels_path}")

    print(f"[model_tflite] Загружаю модель ({mode}): {model_path}")
    model = TensorFlowModel(model_path, num_threads=2, use_gpu=False)
    model.load()

    try:
        in_det = model.interpreter.get_input_details()[0]
        out_det = model.interpreter.get_output_details()[0]
        print(f"[model_tflite] INPUT : dtype={in_det['dtype']} shape={in_det['shape']}")
        print(f"[model_tflite] OUTPUT: dtype={out_det['dtype']} shape={out_det['shape']}")
    except Exception as e:
        print(f"[model_tflite] не удалось прочитать детали тензоров: {e}")

    with open(labels_path, "r", encoding="utf-8") as f:
        labels = [ln.rstrip("\n") for ln in f if ln.strip()]
    print(f"[model_tflite] Меток загружено: {len(labels)}")

    _cache[mode] = (model, labels)
    return model, labels


def _prepare_input(image_path, expected_dtype):
    """Готовит numpy-массив под вход модели с учётом dtype."""
    image = Image.open(image_path).convert("RGB")
    image = ImageOps.fit(image, IMG_SIZE, Image.Resampling.LANCZOS)
    arr = np.asarray(image).astype(np.float32)

    # Нормализация как при обучении Keras: (x / 127.5) - 1  ->  [-1, 1]
    arr = (arr / 127.5) - 1.0

    if expected_dtype == np.uint8:
        arr = ((arr + 1.0) * 127.5).astype(np.uint8)
    elif expected_dtype == np.int8:
        arr = (arr * 127.0).astype(np.int8)

    return np.expand_dims(arr, axis=0)


def get_class(image_path, mode="places"):
    """
    Возвращает (label, confidence) или (None, confidence).
    mode: "places" | "plants"
    """
    model, labels = _load(mode)

    try:
        expected_dtype = model.interpreter.get_input_details()[0]["dtype"]
    except Exception:
        expected_dtype = np.float32

    data = _prepare_input(image_path, expected_dtype)
    prediction = np.asarray(model.pred(data)).reshape(-1)

    # Отладочный вывод топ-3
    top_idx = np.argsort(prediction)[-3:][::-1]
    print(f"[model_tflite] top-3 ({mode}):")
    for i in top_idx:
        name = labels[i] if i < len(labels) else f"<idx {i}>"
        print(f"    {prediction[i]:.3f}  {name.strip()}")

    index = int(np.argmax(prediction))
    confidence = float(prediction[index])

    if index >= len(labels):
        print(f"[model_tflite] индекс {index} вне labels")
        return None, confidence

    if confidence < CONFIDENCE_THRESHOLD:
        print(f"[model_tflite] отказ: уверенность {confidence:.2f} < {CONFIDENCE_THRESHOLD:.2f}")
        return None, confidence

    label = labels[index]
    # Убираем ведущий номер: "0 Название" -> "Название"
    parts = label.split(" ", 1)
    if len(parts) == 2 and parts[0].isdigit():
        label = parts[1]
    return label.strip(), confidence