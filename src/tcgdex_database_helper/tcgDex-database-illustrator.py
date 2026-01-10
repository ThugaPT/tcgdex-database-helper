import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import os
import re
import asyncio
import time
import tkinter as tk
from tkinter import ttk, messagebox
from io import BytesIO

import requests

from PIL import Image, ImageTk

from tcgdexsdk import TCGdex


# ---------- CONFIG ----------
LANGUAGE = "en"
DATABASE_ROOT = "cards-database/data"
MAX_RETRIES = 3
# ----------------------------


# ---------- ASYNC SDK ----------
async def fetch_series():
    return await TCGdex(LANGUAGE).serie.list()


async def fetch_sets(series_id):
    series = await TCGdex(LANGUAGE).serie.get(series_id)
    return series.sets


async def fetch_card(card_id):
    return await TCGdex(LANGUAGE).card.get(card_id)
# ----------------------------


class CardInspectorApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("TCGDex Illustrator Editor")
        self.geometry("480x260")

        self.series_var = tk.StringVar()
        self.set_var = tk.StringVar()

        self.series_map = {}
        self.set_map = {}

        self.missing_cards = []
        self.current_index = 0

        self.create_widgets()
        self.load_series()

    # ---------- UI ----------
    def create_widgets(self):
        ttk.Label(self, text="Series").pack(pady=(20, 5))
        self.series_cb = ttk.Combobox(self, textvariable=self.series_var, state="readonly")
        self.series_cb.pack(fill="x", padx=20)
        self.series_cb.bind("<<ComboboxSelected>>", self.on_series_selected)

        ttk.Label(self, text="Set").pack(pady=(15, 5))
        self.set_cb = ttk.Combobox(self, textvariable=self.set_var, state="disabled")
        self.set_cb.pack(fill="x", padx=20)
        self.set_cb.bind("<<ComboboxSelected>>", self.on_set_selected)

        self.scan_btn = ttk.Button(
            self,
            text="Start illustrator review",
            state="disabled",
            command=self.start_scan
        )
        self.scan_btn.pack(pady=25)

    # ---------- DATA ----------
    def load_series(self):
        series = asyncio.run(fetch_series())
        for s in series:
            self.series_map[s.name] = s.id
        self.series_cb["values"] = sorted(self.series_map.keys())

    def on_series_selected(self, _):
        self.set_cb.set("")
        self.scan_btn["state"] = "disabled"
        self.set_cb["state"] = "readonly"

        series_id = self.series_map[self.series_var.get()]
        sets = asyncio.run(fetch_sets(series_id))

        self.set_map = {s.name: s.id for s in sets}
        self.set_cb["values"] = sorted(self.set_map.keys())

    def on_set_selected(self, _):
        self.scan_btn["state"] = "normal"

    # ---------- SCAN ----------
    def start_scan(self):
        series = self.series_var.get()
        set_name = self.set_var.get()
        path = os.path.join(DATABASE_ROOT, series, set_name)

        self.missing_cards.clear()
        self.current_index = 0

        for file in sorted(os.listdir(path), key=lambda x: int(x.split(".")[0])):
            if not file.endswith(".ts"):
                continue

            full = os.path.join(path, file)
            with open(full, "r", encoding="utf-8") as f:
                content = f.read()

            if self.missing_illustrator(content):
                card_id = self.extract_card_id(
                    content=content,
                    set_id=self.set_map[self.set_var.get()],
                    filename=file
                )
                self.missing_cards.append((full, card_id))


        if not self.missing_cards:
            messagebox.showinfo("Done", "No cards missing illustrator 🎉")
            return

        self.open_card_editor()

    # ---------- CARD EDITOR ----------
    def open_card_editor(self):
        if self.current_index >= len(self.missing_cards):
            messagebox.showinfo("Done", "All missing illustrators processed 🎉")
            return

        path, card_id = self.missing_cards[self.current_index]
        card = asyncio.run(fetch_card(card_id))

        editor = tk.Toplevel(self)
        editor.title(card.name)
        editor.geometry("760x1000")

        # Image
        img_url = card.get_image_url(quality="high", extension="png").replace("https", "http")
        print(f"Image to fetch: {img_url}", flush=True)        
        
        r = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                r = requests.get(img_url, timeout=30, verify=False)
                if r.status_code != 200:
                    raise Exception(f"HTTP {r.status_code}")
                break  # ✅ success → exit retry loop
            except Exception as e:
                if attempt == MAX_RETRIES:
                    raise
                print(f"    🔁 Retry {attempt}/{MAX_RETRIES} ({e})")
                time.sleep(1)

        print("Got the image!", flush=True)

        image = Image.open(BytesIO(r.content)).resize((600, 840))
        photo = ImageTk.PhotoImage(image)

        img_label = ttk.Label(editor, image=photo)
        img_label.image = photo  # 🔒 keep reference
        img_label.pack(pady=10)
        
        # Entry
        ttk.Label(editor, text="Illustrator").pack()
        illustrator_var = tk.StringVar()
        entry = ttk.Entry(editor, textvariable=illustrator_var)
        entry.pack(fill="x", padx=20)

        # Save button
        save_btn = ttk.Button(
            editor,
            text="Save illustrator",
            state="disabled",
            command=lambda: self.save_illustrator(
                editor, path, illustrator_var.get()
            )
        )
        save_btn.pack(pady=20)

        illustrator_var.trace_add(
            "write",
            lambda *_: save_btn.config(
                state="normal" if illustrator_var.get().strip() else "disabled"
            )
        )

    # ---------- FILE UPDATE ----------
    def save_illustrator(self, editor, path, illustrator):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Detect indentation from rarity line
        indent_match = re.search(r"\n(\s*)rarity\s*:", content)
        if not indent_match:
            messagebox.showerror("Error", "Could not locate rarity field")
            return

        indent = indent_match.group(1)
        insert = f"\n{indent}illustrator: \"{illustrator}\","

        # Prefer removing existing blank lines before rarity
        content, count = re.subn(
            r"\n\s*\n(\s*rarity\s*:\s*['\"].+?['\"],?)",
            insert + r"\n\1",
            content,
            count=1
        )

        # Fallback if no blank line existed
        if count == 0:
            content = re.sub(
                r"\n(\s*rarity\s*:\s*['\"].+?['\"],?)",
                insert + r"\n\1",
                content,
                count=1
            )

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        editor.destroy()
        self.current_index += 1
        self.open_card_editor()


    # ---------- UTIL ----------
    @staticmethod
    def missing_illustrator(content):
        return not re.search(r"illustrator\s*:\s*['\"].+?['\"]", content)

    @staticmethod
    def extract_card_id(content: str, set_id: str, filename: str) -> str:
        """
        Try to extract card id from file content.
        Fallback to set_id + filename convention.
        """

        # 1️⃣ Try explicit id field
        match = re.search(r"id\s*:\s*['\"](.+?)['\"]", content)
        if match:
            return match.group(1)

        # 2️⃣ Fallback: derive from filename
        number = filename.replace(".ts", "")
        return f"{set_id}-{number}"

# ---------- RUN ----------
if __name__ == "__main__":
    CardInspectorApp().mainloop()
