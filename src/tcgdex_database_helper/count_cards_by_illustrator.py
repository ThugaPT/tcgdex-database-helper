import os
import re
import csv
import unicodedata

from collections import Counter

from pathlib import Path

# ---------- CONFIG (initialized from main) ----------
DATABASE_ROOT_EN: Path | None = None
DATABASE_ROOT_JA: Path | None = None
OUTPUT_CSV: Path | None = None
# -----------------------------------------------


ILLUSTRATOR_REGEX = re.compile(
    r"illustrator\s*:\s*['\"](.+?)['\"]",
    re.IGNORECASE
)

def configure_count_cards_by_illustrator(
    database_root_en: Path,
    database_root_ja: Path,
    illustrator_csv: Path,
):
    global DATABASE_ROOT_EN, DATABASE_ROOT_JA, OUTPUT_CSV
    DATABASE_ROOT_EN = database_root_en
    DATABASE_ROOT_JA = database_root_ja
    OUTPUT_CSV = illustrator_csv

def normalize_illustrator(name: str) -> str:
    # Normalize unicode (important for JP / full-width chars)
    name = unicodedata.normalize("NFKC", name)

    # Strip leading/trailing whitespace
    name = name.strip()

    # Collapse multiple spaces into one
    name = re.sub(r"\s+", " ", name)

    return name

def iter_ts_files(root: str):
    """Yield full paths to all .ts files under root."""
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.endswith(".ts"):
                yield os.path.join(dirpath, name)


def extract_illustrator(file_path: str) -> str | None:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"⚠️ Could not read {file_path}: {e}")
        return None

    match = ILLUSTRATOR_REGEX.search(content)
    if not match:
        return None

    return normalize_illustrator(match.group(1))


def run_count_cards_by_illustrator():
    counter = Counter()
    counter_ja = Counter()
    total_files = 0
    total_files_ja = 0
    with_illustrator = 0
    with_illustrator_ja = 0

    ##LOAD GLOBALS
    assert DATABASE_ROOT_EN is not None, "Module not configured"
    assert OUTPUT_CSV is not None, "Module not configured"
    
    for file_path_en in iter_ts_files(DATABASE_ROOT_EN):
        total_files += 1
        illustrator = extract_illustrator(file_path_en)
        if illustrator:
            if illustrator == '313':
                illustrator = '0313'
            counter[illustrator] += 1
            with_illustrator += 1

    for file_path_ja in iter_ts_files(DATABASE_ROOT_JA):
        total_files += 1
        illustrator = extract_illustrator(file_path_ja)
        if illustrator:
            if illustrator == '313':
                illustrator = '0313'
            counter[illustrator] += 1
            with_illustrator += 1

    # Write CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Illustrator", "Card Count"])

        for illustrator, count in counter.most_common():
            writer.writerow([illustrator, count])
  

    #for illustrator_en in counter_en:
    #    exists_both = False;
    #    for illustrator_ja in counter_ja:
    #        if illustrator_en == illustrator_ja:
    #            exists_both = True
    #    if exists_both==False:
    #        print(f"Illustrator EN does not exist in JA: {illustrator_en}")
    #for illustrator_ja in counter_ja:
    #    exists_both = False;
    #    for illustrator_en in counter_en:
    #        if illustrator_en == illustrator_ja:
    #            exists_both = True
    #    if exists_both==False:
    #        print(f"Illustrator JA does not exist in EN: {illustrator_ja}")

    print("✅ Done")
    print(f"📁 Total card files scanned: {total_files}")
    print(f"🎨 Cards with illustrator: {with_illustrator}")
    print(f"📊 Unique illustrators: {len(counter)}")
    #print(f"📁 Total card files scanned JA: {total_files_ja}")
    #print(f"🎨 Cards with illustrator JA: {with_illustrator_ja}")
    #print(f"📊 Unique illustrators JA: {len(counter_ja)}")
    print(f"💾 Output written to: {OUTPUT_CSV}")


if __name__ == "__main__":
    run_count_cards_by_illustrator()

