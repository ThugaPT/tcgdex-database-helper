import os
import re
import csv
import asyncio
import time
import unicodedata
import tkinter as tk
from tkinter import ttk, messagebox
from io import BytesIO
from threading import Thread

import requests
from PIL import Image, ImageTk
from tcgdexsdk import TCGdex
from tcgdex_database_helper.config import get_language


from pathlib import Path

# ---------- CONFIG ----------
LANGUAGE: str | None = None
DATABASE_ROOT: Path | None = None
ILLUSTRATOR_CSV: Path | None = None
MAX_RETRIES: int | None = None
AUTOCOMPLETE_MIN_CHARS: int | None = None

# ----------------------------

#Config_Loading#
def configure_tcgDex_database_helper_GUI(
    database_root_en: Path,
    database_root_ja: Path,
    illustrator_csv: Path,
    max_retries: int,
    autocomplete_min_chars: int,
):
    global DATABASE_ROOT, LANGUAGE, ILLUSTRATOR_CSV, MAX_RETRIES, AUTOCOMPLETE_MIN_CHARS
    if get_language() == "en":
            DATABASE_ROOT = database_root_en
    if get_language() == "ja":
            DATABASE_ROOT = database_root_ja
    LANGUAGE = get_language()
    ILLUSTRATOR_CSV = illustrator_csv
    MAX_RETRIES = max_retries
    AUTOCOMPLETE_MIN_CHARS = autocomplete_min_chars
    print("USING DATABASE ROOT:", DATABASE_ROOT)
    print("USING LANGUAGE:", LANGUAGE)
#------------------#

# ---------- NORMALIZATION ----------
def normalize_illustrator(name: str) -> str:
    name = unicodedata.normalize("NFKC", name)
    name = name.strip()
    name = re.sub(r"\s+", " ", name)
    return name
# -------------------------------

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
    def __init__(self, api):
        super().__init__()

        self.title("TCGDex Illustrator Editor")
        self.geometry("480x260")

        # Store the API instance
        self.api = api

        self.series_var = tk.StringVar()
        self.set_var = tk.StringVar()

        self.series_map = {}
        self.set_map = {}

        self.missing_cards = []
        self.current_index = 0

        self.create_widgets()
        # Note: don't call load_series here directly
        # We'll call it from top-level async function with await
    # ---------- ASYNC LOAD DATA ----------
    async def load_series_async(self):
        series = await self.api.serie.list()
        for s in series:
            self.series_map[s.name] = s.id
        self.series_cb["values"] = sorted(self.series_map.keys())

    async def load_sets_async(self, series_name):
        series_id = self.series_map[series_name]
        sets = await self.api.serie.get(series_id)
        self.set_map = {s.name: s.id for s in sets.sets}
        self.set_cb["values"] = sorted(self.set_map.keys())

    async def fetch_card_async(self, card_id):
        return await self.api.card.get(card_id)
    
    # ---------- LOAD CSV ----------
    def load_possible_illustrators(self):
        if not os.path.exists(ILLUSTRATOR_CSV):
            messagebox.showwarning(
                "Warning",
                f"{ILLUSTRATOR_CSV} not found.\nAutocomplete disabled."
            )
            return

        with open(ILLUSTRATOR_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("Illustrator")
                if name:
                    self.possible_illustrators.add(normalize_illustrator(name))

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
        series_name = self.series_var.get()
        series_id = self.series_map[series_name]
        # run async function in separate thread
        def worker():
            import asyncio
            series_obj = asyncio.run(self.api.serie.get(series_id))
            sets_dict = {s.name: s.id for s in series_obj.sets}
            self.after(0, self._update_set_combobox, sets_dict)

        Thread(target=worker, daemon=True).start()

#    async def _load_sets_for_gui(self):
#        try:
#            series_name = self.series_var.get()
#            series_id = self.series_map[series_name]
#            series_obj = await self.api.serie.get(series_id)
#            sets_dict = {s.name: s.id for s in series_obj.sets}
#            return sets_dict
#        except Exception as e:
#            print("Error loading sets:", e)

    def _update_set_combobox(self, sets_dict):
        self.set_map = sets_dict
        self.set_cb["values"] = sorted(self.set_map.keys())
        # Force the combobox to refresh
        self.set_cb["state"] = "readonly"
        

    def on_set_selected(self, _):
        self.scan_btn["state"] = "normal"

    # ---------- SCAN ----------
    def start_scan(self):
        series = self.series_var.get()
        set_name = self.set_var.get()
        path = os.path.join(DATABASE_ROOT, series, set_name)

        self.missing_cards.clear()
        self.current_index = 0

        for file in sorted(
            os.listdir(path),
            key=lambda x: int(x.split(".")[0]) if x.split(".")[0].isdigit() else float("inf")
        ):
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

        # ---------- IMAGE ----------
        img_url = card.get_image_url(quality="high", extension="png")

        r = requests.get(img_url, timeout=30)
        image = Image.open(BytesIO(r.content)).resize((600, 840))
        photo = ImageTk.PhotoImage(image)

        img_label = ttk.Label(editor, image=photo)
        img_label.image = photo
        img_label.pack(pady=10)

        # ---------- INPUT ----------
        ttk.Label(editor, text="Illustrator").pack(pady=(10, 5))

        input_frame = ttk.Frame(editor)
        input_frame.pack(fill="x", padx=20)

        illustrator_var = tk.StringVar()
        entry = ttk.Entry(input_frame, textvariable=illustrator_var)
        entry.pack(side="left", fill="x", expand=True)
        entry.focus_set()

        skip_btn = ttk.Button(
            input_frame,
            text="Skip",
            command=lambda: self.skip_card(editor)
        )
        skip_btn.pack(side="left", padx=(10, 10))

        save_btn = ttk.Button(
            input_frame,
            text="Save",
            state="disabled",
            command=lambda: self.validate_and_save(editor, path, illustrator_var.get())
        )
        save_btn.pack(side="right")

        # ---------- AUTOCOMPLETE ----------
        listbox = tk.Listbox(editor, height=6)
        listbox.place_forget()

        def update_autocomplete(*_):
            text = illustrator_var.get()
            listbox.delete(0, tk.END)

            if len(text) < AUTOCOMPLETE_MIN_CHARS:
                listbox.place_forget()
                return

            text_norm = normalize_illustrator(text).lower()

            starts = []
            contains = []

            for name in self.possible_illustrators:
                n = name.lower()
                if n.startswith(text_norm):
                    starts.append(name)
                elif text_norm in n:
                    contains.append(name)

            matches = sorted(starts) + sorted(contains)

            if not matches:
                listbox.place_forget()
                return

            for name in matches:
                listbox.insert(tk.END, name)

            x = entry.winfo_rootx() - editor.winfo_rootx()
            y = entry.winfo_rooty() - editor.winfo_rooty() + entry.winfo_height()
            listbox.place(x=x, y=y, width=entry.winfo_width())

        def accept_selection(index=0):
            if listbox.size() == 0:
                return
            illustrator_var.set(listbox.get(index))
            listbox.place_forget()
            entry.focus_set()
            entry.icursor(tk.END)

        illustrator_var.trace_add("write", update_autocomplete)

        entry.bind("<Down>", lambda e: listbox.focus_set() if listbox.winfo_ismapped() else None)
        entry.bind("<Tab>", lambda e: (accept_selection(0), "break")[1] if listbox.winfo_ismapped() else None)

        listbox.bind("<Return>", lambda e: accept_selection(listbox.curselection()[0]))
        listbox.bind("<Double-Button-1>", lambda e: accept_selection(listbox.curselection()[0]))

        entry.bind(
            "<Return>",
            lambda e: self.validate_and_save(editor, path, illustrator_var.get())
            if illustrator_var.get().strip() else None
        )

        illustrator_var.trace_add(
            "write",
            lambda *_: save_btn.config(
                state="normal" if illustrator_var.get().strip() else "disabled"
            )
        )

    # ---------- ACTIONS ----------
    def skip_card(self, editor):
        editor.destroy()
        self.current_index += 1
        self.open_card_editor()

    def validate_and_save(self, editor, path, illustrator):
        illustrator_norm = normalize_illustrator(illustrator)

        if self.possible_illustrators and illustrator_norm not in self.possible_illustrators:
            self.show_unknown_illustrator_warning(editor, path, illustrator)
            return

        self.save_illustrator(editor, path, illustrator)

    def show_unknown_illustrator_warning(self, editor, path, illustrator):
        warning = tk.Toplevel(editor)
        warning.title("Unknown illustrator")
        warning.transient(editor)
        warning.grab_set()

        ttk.Label(
            warning,
            text=f"Illustrator “{illustrator}” was not found.\nSave anyway?",
            justify="center"
        ).pack(padx=20, pady=20)

        btns = ttk.Frame(warning)
        btns.pack(pady=10)

        ttk.Button(btns, text="Cancel", command=warning.destroy).pack(side="left", padx=10)
        ttk.Button(
            btns,
            text="Confirm",
            command=lambda: (warning.destroy(), self.save_illustrator(editor, path, illustrator))
        ).pack(side="right", padx=10)

    def save_illustrator(self, editor, path, illustrator):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        indent = re.search(r"\n(\s*)rarity\s*:", content).group(1)
        insert = f"\n{indent}illustrator: \"{illustrator}\","

        content = re.sub(
            r"\n\s*\n(\s*rarity\s*:)",
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
        return not re.search(r"illustrator\s*:", content)

    @staticmethod
    def extract_card_id(content, set_id, filename):
        match = re.search(r"id\s*:\s*['\"](.+?)['\"]", content)
        return match.group(1) if match else f"{set_id}-{filename.replace('.ts','')}"


# ---------- RUN ----------
async def run_tcgDex_database_helper_GUI_async():
    api = TCGdex(LANGUAGE)  # Initialize API once
    app = CardInspectorApp(api)
    
    # Load series before showing GUI
    await app.load_series_async()
    
    # Now run Tkinter mainloop
    app.mainloop()
    
if __name__ == "__main__":
    CardInspectorApp().mainloop()
