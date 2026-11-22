# convert.py
"""
Конвертирует Keras .h5 → TensorFlow Lite .tflite для обеих моделей QukLoc:
  - keras_model.h5  → models/model.tflite   (места, 32 класса)
  - plants_model.h5 → models/plants.tflite  (растения, 108 классов)

Запуск (в отдельном venv с TensorFlow):
    python3.11 -m venv venv_convert
    source venv_convert/bin/activate
    pip install tensorflow h5py
    python convert.py
"""

import os
import tensorflow as tf
import h5py

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# (вход .h5, выход .tflite)
JOBS = [
    ("keras_model.h5",  "model.tflite"),    # места
    ("plants_model.h5", "plants.tflite"),   # растения
]


def fix_h5(h5_path):
    """
    Удаляет "groups": 1 из model_config.
    Нужно для совместимости со старыми .h5 в новых Keras/TF.
    """
    with h5py.File(h5_path, mode="r+") as f:
        cfg = f.attrs.get("model_config")
        if cfg is None:
            print(f"  [{os.path.basename(h5_path)}] model_config не найден — пропускаю хак")
            return
        if isinstance(cfg, bytes):
            cfg = cfg.decode("utf-8")

        changed = False
        if '"groups": 1,' in cfg:
            cfg = cfg.replace('"groups": 1,', "")
            changed = True
        elif '"groups": 1' in cfg:
            cfg = cfg.replace('"groups": 1', "")
            changed = True

        if changed:
            f.attrs.modify("model_config", cfg)
            f.flush()
            print(f"  [{os.path.basename(h5_path)}] хак 'groups' применён")
        else:
            print(f"  [{os.path.basename(h5_path)}] хак не потребовался")


def convert_one(h5_name, tflite_name):
    h5_path = os.path.join(BASE_DIR, h5_name)
    tflite_path = os.path.join(MODELS_DIR, tflite_name)

    print(f"\n=== {h5_name} → models/{tflite_name} ===")

    if not os.path.exists(h5_path):
        print(f"  ✗ {h5_name} не найден, пропускаю")
        return False

    try:
        fix_h5(h5_path)
        model = tf.keras.models.load_model(h5_path, compile=False)
    except Exception as e:
        print(f"  ✗ Не удалось загрузить {h5_name}: {e}")
        return False

    try:
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        tflite_model = converter.convert()
    except Exception as e:
        print(f"  ✗ Ошибка конвертации: {e}")
        return False

    with open(tflite_path, "wb") as f:
        f.write(tflite_model)

    size_mb = len(tflite_model) / 1024 / 1024
    print(f"  ✓ Готово: {tflite_path}  ({size_mb:.2f} МБ)")
    return True


def main():
    results = {}
    for h5_name, tflite_name in JOBS:
        results[h5_name] = convert_one(h5_name, tflite_name)

    print("\n" + "=" * 50)
    print("Итог:")
    for h5_name, ok in results.items():
        status = "✓ OK" if ok else "✗ пропущено / ошибка"
        print(f"  {h5_name}: {status}")


if __name__ == "__main__":
    main()