"""
Скачивание фотографий растений с Wikimedia Commons.

Использование:
    python download_plant_images.py

Результат: папка images/plants/ с файлами вида moroshka.jpg, chernika.jpg и т.д.
"""

import os
import time
import requests

# ---------- Настройки ----------
OUTPUT_DIR = os.path.join("images", "plants")
API_URL = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "QukLocBot/1.0 (educational project; contact: your@email.com)"
# ВАЖНО: замените email на свой — Wikimedia требует идентифицирующий User-Agent[citation:13]
MIN_SIZE = 10_000        # минимум 10 КБ (отсекаем иконки и битые файлы)
MAX_SIZE = 5_000_000     # максимум 5 МБ (чтобы APK не раздулся)
ALLOWED_MIME = {"image/jpeg", "image/png"}
REQUEST_DELAY = 0.5      # пауза между запросами, сек (вежливость к API)


# ---------- Соответствие: имя файла -> латинское название ----------
# Ключ — то, как файл будет называться в images/plants/
# Значение — латинское название для поиска на Wikimedia Commons
PLANTS = {
    # Ягодные
    "moroshka": "Rubus chamaemorus",
    "knyazhenika": "Rubus arcticus",
    "chernika": "Vaccinium myrtillus",
    "golubika": "Vaccinium uliginosum",
    "brusnika": "Vaccinium vitis-idaea",
    "vodyanika": "Empetrum nigrum",
    "kostyanika": "Rubus saxatilis",
    "malina": "Rubus idaeus",
    "zemlyanika": "Fragaria vesca",
    "zhimolost": "Lonicera caerulea",

    # Лекарственные и декоративные
    "rodiola": "Rhodiola rosea",
    "bagulnik": "Rhododendron tomentosum",
    "veresk": "Calluna vulgaris",
    "ivanchay": "Chamaenerion angustifolium",
    "klever": "Trifolium pratense",
    "kupalnitsa": "Trollius europaeus",
    "pion": "Paeonia anomala",
    "ven_chesh": "Cypripedium calceolus",
    "kalipso": "Calypso bulbosa",

    # Папоротники, хвощи, плауны
    "kochedyzhnik": "Athyrium filix-femina",
    "shchitovnik": "Dryopteris filix-mas",
    "hvoshch": "Equisetum sylvaticum",
    "hvoshch_polevoy": "Equisetum arvense",
    "plaun": "Lycopodium annotinum",
    "baranets": "Huperzia selago",

    # Деревья и кустарники
    "bereza_karl": "Betula nana",
    "iva_pol": "Salix polaris",
    "mozhzhevelnik": "Juniperus communis",
    "ryabina": "Sorbus aucuparia",
    "cheryomuha": "Prunus padus",
    "olha": "Alnus incana",

    # Тундровые и альпийские
    "driada": "Dryas octopetala",
    "kamnelomka": "Saxifraga oppositifolia",
    "diapensiya": "Diapensia lapponica",
    "kassiopeia": "Cassiope tetragona",
    "fillodots": "Phyllodoce caerulea",
    "timyan": "Thymus serpyllum",

    # Водные и прибрежные
    "vahta": "Menyanthes trifoliata",
    "sabelnik": "Comarum palustre",
    "belokopytnik": "Petasites frigidus",
    "pushitsa": "Eriophorum vaginatum",

    # Луговые и сорные
    "oduvanchik": "Taraxacum",
    "mat_i_macheha": "Tussilago farfara",
    "podorozhnik": "Plantago maritima",
    "tysyachelistnik": "Achillea millefolium",
    "pizhma": "Tanacetum vulgare",
    "zolotarnik": "Solidago virgaurea",
    "labaznik": "Filipendula ulmaria",
    "gravilat": "Geum rivale",
    "geran": "Geranium sylvaticum",
    "kolokolchik": "Campanula rotundifolia",
    "nivyanik": "Leucanthemum vulgare",
    "gvozdika": "Dianthus superbus",
    "nezabudka": "Myosotis scorpioides",
    "fialka": "Viola tricolor",
    "veronika": "Veronica longifolia",
    "shlemnik": "Scutellaria galericulata",
    "chernogolovka": "Prunella vulgaris",
    "myata": "Mentha arvensis",
    "zveroboy": "Hypericum maculatum",
    "lnyanka": "Linaria vulgaris",
    "maryannik": "Melampyrum pratense",
    "mytnik": "Pedicularis sceptrum-carolinum",
    "krovohlebka": "Sanguisorba officinalis",
    "sinyuha": "Polemonium caeruleum",
    "kislitsa": "Oxalis acetosella",
    "maynik": "Maianthemum bifolium",
    "sedmichnik": "Lysimachia europaea",
    "odnotsvetka": "Moneses uniflora",
    "grushanka": "Pyrola rotundifolia",
    "ortiliya": "Orthilia secunda",
    "linneya": "Linnaea borealis",

    # Ядовитые
    "voroniy_glaz": "Paris quadrifolia",
    "voronets": "Actaea erythrocarpa",
    "chemeritsa": "Veratrum lobelianum",
    "borets": "Aconitum septentrionale",
    "volcheyagodnik": "Daphne mezereum",
    "borshchevik": "Heracleum sibiricum",

    # Злаки
    "myatlik": "Poa pratensis",
    "ovsyanitsa": "Festuca ovina",
    "timofeevka": "Phleum pratense",
    "ezha": "Dactylis glomerata",
    "lisohvost": "Alopecurus pratensis",
    "veynik": "Calamagrostis",
    "polevitsa": "Agrostis capillaris",

    # Осоки
    "osoka_vodyanaya": "Carex aquatilis",
    "osoka_zheltaya": "Carex flava",
    "osoka_puzyrchataya": "Carex vesicaria",
    "osoka_nosataya": "Carex rostrata",

    # Орхидеи
    "palchatokorennik": "Dactylorhiza maculata",
    "lyubka": "Platanthera bifolia",
    "dremlik": "Epipactis atrorubens",
    "gudayera": "Goodyera repens",
    "taynik": "Neottia ovata",
    "kokushnik": "Gymnadenia conopsea",

    # Зонтичные
    "tmin": "Carum carvi",
    "dyagil": "Angelica archangelica",
    "dudnik": "Angelica sylvestris",
    "kupyr": "Anthriscus sylvestris",
    "bedrenets": "Pimpinella saxifraga",
    "sinyuha_severnaya": "Polemonium boreale",

    # Лишайники и мхи
    "yagel": "Cladonia rangiferina",
    "tsetrariya": "Cetraria islandica",
    "kladoniya": "Cladonia",
    "parmeliya": "Parmelia",
    "usneya": "Usnea",
    "ksantoriya": "Xanthoria parietina",
    "sfagnum": "Sphagnum",
    "kukushkin_len": "Polytrichum commune",
}


def search_image(latin_name):
    """Ищет одно изображение на Wikimedia Commons по латинскому названию."""
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"filetype:bitmap {latin_name}",
        "gsrnamespace": 6,          # только файлы
        "gsrlimit": 5,              # берём первые 5, выберем подходящий
        "prop": "imageinfo",
        "iiprop": "url|mime|size",
    }
    headers = {"User-Agent": USER_AGENT}

    try:
        r = requests.get(API_URL, params=params, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  [ошибка запроса] {e}")
        return None

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return None

    # Проходим по результатам и берём первый подходящий по размеру и типу
    for page in pages.values():
        info_list = page.get("imageinfo", [])
        if not info_list:
            continue
        info = info_list[0]
        mime = info.get("mime", "")
        size = info.get("size", 0)
        if mime in ALLOWED_MIME and MIN_SIZE <= size <= MAX_SIZE:
            return info.get("url")

    return None


def download_file(url, dest_path):
    """Скачивает файл по URL и сохраняет по указанному пути."""
    headers = {"User-Agent": USER_AGENT}
    try:
        r = requests.get(url, headers=headers, stream=True, timeout=30)
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"  [ошибка скачивания] {e}")
        return False


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    total = len(PLANTS)
    downloaded = 0
    skipped = 0
    failed = []

    for i, (filename, latin_name) in enumerate(PLANTS.items(), 1):
        dest = os.path.join(OUTPUT_DIR, f"{filename}.jpg")

        if os.path.exists(dest) and os.path.getsize(dest) > MIN_SIZE:
            print(f"[{i}/{total}] {filename}.jpg — уже есть, пропуск")
            skipped += 1
            continue

        print(f"[{i}/{total}] {filename}.jpg — ищу: {latin_name}")
        url = search_image(latin_name)

        if not url:
            print(f"  ✗ не найдено")
            failed.append(filename)
            time.sleep(REQUEST_DELAY)
            continue

        if download_file(url, dest):
            size_kb = os.path.getsize(dest) // 1024
            print(f"  ✓ скачано ({size_kb} КБ)")
            downloaded += 1
        else:
            print(f"  ✗ ошибка скачивания")
            failed.append(filename)

        time.sleep(REQUEST_DELAY)

    print("\n" + "=" * 50)
    print(f"Скачано: {downloaded}")
    print(f"Пропущено (уже были): {skipped}")
    print(f"Не удалось: {len(failed)}")
    if failed:
        print("Не найдены:")
        for name in failed:
            print(f"  - {name}")


if __name__ == "__main__":
    main()