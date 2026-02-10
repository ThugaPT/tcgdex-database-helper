import os
import re
import csv
import asyncio
import ssl
import unicodedata
import tkinter as tk
from tkinter import ttk, messagebox
from io import BytesIO
from threading import Thread

import requests
from PIL import Image, ImageTk
from tcgdexsdk import TCGdex
from tcgdex_database_helper.config import get_language, get_no_ssl_verify, get_is_local_endpoint

#limitless fallback
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

from pathlib import Path

# ---------- CONFIG ----------
LANGUAGE: str | None = None
DATABASE_ROOT: Path | None = None
ILLUSTRATOR_CSV: Path | None = None
FALLBACK_IMAGE_PATH: Path | None = None
MAX_RETRIES: int | None = None
AUTOCOMPLETE_MIN_CHARS: int | None = None
NO_SSL_VERIFICATION: bool = None
IS_LOCAL_ENDPOINT: bool | None = None
LOCAL_ENDPOINT: str | None = None
MODE: str = None
IMAGE_LOCAL_ENABLED: bool = False
# ----------------------------

#Config_Loading#
def configure_tcgDex_database_helper_GUI(
    database_root_en: Path,
    database_root_ja: Path,
    illustrator_csv: Path,
    fallback_image: Path,
    max_retries: int,
    autocomplete_min_chars: int,
    local_endpoint: str,
    allowLocalImage: bool,
    mode: str 
):
    global DATABASE_ROOT, LANGUAGE, ILLUSTRATOR_CSV, FALLBACK_IMAGE_PATH, MAX_RETRIES, AUTOCOMPLETE_MIN_CHARS, NO_SSL_VERIFICATION, IS_LOCAL_ENDPOINT, LOCAL_ENDPOINT, IMAGE_LOCAL_ENABLED, MODE
    if get_language() == "en":
            DATABASE_ROOT = database_root_en
    if get_language() == "ja":
            DATABASE_ROOT = database_root_ja
    LANGUAGE = get_language()
    ILLUSTRATOR_CSV = illustrator_csv
    FALLBACK_IMAGE_PATH = fallback_image
    MAX_RETRIES = max_retries
    AUTOCOMPLETE_MIN_CHARS = autocomplete_min_chars
    NO_SSL_VERIFICATION = get_no_ssl_verify()
    IS_LOCAL_ENDPOINT = get_is_local_endpoint()
    LOCAL_ENDPOINT = local_endpoint
    IMAGE_LOCAL_ENABLED =  allowLocalImage
    MODE = mode

#------------------#

# ---------- NORMALIZATION ----------
def normalize_illustrator(name: str) -> str:
    name = unicodedata.normalize("NFKC", name)
    name = name.strip()
    name = re.sub(r"\s+", " ", name)
    return name
# -------------------------------

# ---------- GUI APP ----------
class CardInspectorApp(tk.Tk):
    _MISSING_FIELD_CHECKS = {
        "Illustrators": lambda c: CardInspectorApp.missing_field_illustrator(c),
        "RetreatCost": lambda c: CardInspectorApp.missing_field_retreat_cost(c),
        "HP": lambda c: CardInspectorApp.missing_field_hp(c),
    }
    def __init__(self, api):
        super().__init__()
        mainWindowTitle = "No value"
        if MODE == "Illustrators":
            mainWindowTitle = "TCGDex Illustrator Editor"
        if MODE == "RetreatCost":
            mainWindowTitle = "TCGDex Retreat Cost Editor"
        if MODE == "HP":
            mainWindowTitle = "TCGDex HP Editor"
        
        self.title(mainWindowTitle)
        self.geometry("480x260")

        # Store the API instance
        self.api = api

        self.series_var = tk.StringVar()
        self.set_var = tk.StringVar()

        self.series_map = {}
        self.set_map = {}
        self.series_obj = None

        self.missing_cards = []
        self.current_index = 0
        self.card: TCGdex.card.Card | None = None

        self.possible_illustrators = set()
        if MODE == "Illustrators":
            self.load_possible_illustrators()

        if NO_SSL_VERIFICATION:
            print("Disabling SSL verification for requests")
            ssl._create_default_https_context = ssl._create_unverified_context

        self.create_widgets()

    # ---------- ASYNC LOAD DATA ----------
    async def load_series_async(self):
        series = await self.api.serie.list()
        for s in series:
            self.series_map[s.name] = s.id
        self.series_cb["values"] = sorted(self.series_map.keys())

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

        #MODE VARIABLES
        scanButtonLabel = None
        match MODE:
            case "Illustrators":
                scanButtonLabel= "Start illustrator review"
            case "RetreatCost":
                scanButtonLabel= "Start retrat cost review"
            case "HP":
                scanButtonLabel= "Start HP review"
            case _:
                print("Unknown mode")
                return

        self.scan_btn = ttk.Button(
            self,
            text=scanButtonLabel,
            state="disabled",
            command=self.start_scan
        )
        self.scan_btn.pack(pady=25)

    # ---------- DATA ----------
    def on_series_selected(self, _):
        self.set_cb.set("")
        self.scan_btn["state"] = "disabled"
        self.set_cb["state"] = "readonly"
        series_name = self.series_var.get()
        series_id = self.series_map[series_name]
        # run async function in separate thread
        
        # Create, launch and wait on a thread to fetch series data
        def worker():
            import asyncio
            self.series_obj = asyncio.run(self.api.serie.get(series_id))
        series_selected_thread = Thread(target=worker, daemon=True)
        series_selected_thread.start()
        series_selected_thread.join()

        #Fill sets combobox
        sets_dict = {s.name: s.id for s in self.series_obj.sets}
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
        set_id = self.set_map[set_name]
        series_id = self.series_map[series]
        if LANGUAGE == "ja":
            path = os.path.join(DATABASE_ROOT, series_id, set_id)
        if LANGUAGE == "en":
            path = os.path.join(DATABASE_ROOT, series, set_name)
       
        self.missing_cards.clear()
        self.current_index = 0
        ##Add a check to see if path exists
        if not os.path.exists(path):
            messagebox.showerror("Error", f"Path does not exist: {path}\nThe cards from the selected set ({set_id}/{set_name}) from the selected series({series_id}/{series}) may not have been added yet.")
            return
        for file in sorted(
            os.listdir(path),
            key=lambda x: int(x.split(".")[0]) if x.split(".")[0].isdigit() else float("inf")
        ):
            if not file.endswith(".ts"):
                continue

            full = os.path.join(path, file)
            with open(full, "r", encoding="utf-8") as f:
                content = f.read()
                if self.missing_field(content, MODE):
                    card_id = self.extract_card_id(
                        content=content,
                        set_id=self.set_map[self.set_var.get()],
                        filename=file
                    )
                    print("CARD: ", content)
                    self.missing_cards.append((full, card_id))
            
        if MODE == "Illustrators":
            noMissingText = "No cards missing illustrator 🎉"
        if MODE == "RetreatCost":
            noMissingText = "No cards missing Retreat Cost 🎉"
        if MODE == "HP":
            noMissingText = "No cards missing HP 🎉"
        if not self.missing_cards:
            messagebox.showinfo("Done", noMissingText)
            return
        self.open_card_editor(mode= MODE)

    # ---------- CARD EDITOR ----------
    def open_card_editor(self, mode):
        completeMessageText = None
        if mode == "Illustrators":
            completeMessageText = "All missing illustrators processed 🎉"
        if mode == "RetreatCost":
            completeMessageText = "All missing retrat costs processed 🎉"
        if mode == "HP":
            completeMessageText = "All missing HP processed 🎉"
        if self.current_index >= len(self.missing_cards):
            messagebox.showinfo("Done", completeMessageText)
            return

        path, card_id = self.missing_cards[self.current_index]
        print("fetching card:" , card_id) #DEBUG ONLY
        # Create, launch and wait on a thread to fetch card data
        def worker():
            import asyncio
            try:
                self.card = asyncio.run(self.fetch_card_async(card_id))
            except:
                self.card = None

        get_card_thread = Thread(target=worker, daemon=True)
        get_card_thread.start()
        get_card_thread.join() 
        if self.card is None:
            self.current_index += 1
            return self.open_card_editor(mode = mode)

        editor = tk.Toplevel(self)
        editor.title(self.card.name)
        editor.geometry("760x1000")

        # ---------- IMAGE ----------
        print("LOCAL_IMAGES_ENABLED? ", IMAGE_LOCAL_ENABLED)
        image = None
        r = None
        #Main source of images is TCGDex
        img_url = self.card.get_image_url(quality="high", extension="png")
        try:
            if NO_SSL_VERIFICATION:
                r = requests.get(img_url, timeout=30, verify=False)
            else:
                r = requests.get(img_url, timeout=30)
        except Exception as e:
            print(f"⚠️ Could not load image for card {self.card.name} from {img_url} with error: {e}")
        
        if r is not None and r.content is not None and r.status_code == 200:
            image = Image.open(BytesIO(r.content)).resize((600, 840))
        elif image is None:
            #------JUST A PLACEHOLDER FOR IMAGES LOCALLY----
            if IMAGE_LOCAL_ENABLED:
                img_path = self.card.get_image_local(quality="high", extension="jpg")
                print("IMAGE URL: ", img_path)
                if  img_path and img_path.startswith("/"):
                    print("IMAGE URL AFTER REPLACE: ", img_path)
                    local_path = os.path.normpath(img_path)
                    try:
                        image = Image.open(local_path).resize((600, 840))
                    except Exception as e:
                        print(f"Could not open image at path {img_path} from local repository for card ID: {self.card.id} with error: [{e}]")
            if image is None:
                if not FALLBACK_IMAGE_PATH.exists():
                    raise FileNotFoundError(
                        f"Fallback image not found: {FALLBACK_IMAGE_PATH}"
                    )
                else:
                    messagebox.showerror(
                        "Image Load Error",
                        f"Could not load image for card {self.card.name} ."
                    )
                    image = Image.open(FALLBACK_IMAGE_PATH).resize((600, 840))
        #DISPLAY IMAGE IN TKINTER
        photo = ImageTk.PhotoImage(image) 
        img_label = ttk.Label(editor, image=photo)
        img_label.image = photo
        img_label.pack(pady=10)

        # ---------- INPUT ----------
        #TODO: Put this all inside an if with the mode and replicate for Retreat Cost and for CardEditor
        editorLabel = "Not defined"
        if mode == "Illustrators":
            editorLabel = "Illustrator"
        if mode == "RetreatCost":
            editorLabel = "Retreat Cost"
        if mode == "HP":
            editorLabel = "HP"
        ttk.Label(editor, text=editorLabel).pack(pady=(10, 5))
        input_frame = ttk.Frame(editor)
        input_frame.pack(fill="x", padx=20)

        field_var = tk.StringVar()
        entry = ttk.Entry(input_frame, textvariable=field_var)
        entry.pack(side="left", fill="x", expand=True)
        entry.focus_set()
        skip_btn = ttk.Button(
                input_frame,
                text="Skip",
                command=lambda: self.skip_card(editor, mode)
            )
        skip_btn.pack(side="left", padx=(10, 10))

        save_btn = ttk.Button(
            input_frame,
            text="Save",
            state="disabled",
            command=lambda: self.validate_and_save(editor, path, field_var.get())
        )
        save_btn.pack(side="right")
        entry.bind("<Control-Return>",
                lambda e: self.skip_card(editor, mode)
            )

        if mode == "Illustrators":
            # ----------ILLUSTRATOR AUTOCOMPLETE ----------
            listbox = tk.Listbox(editor, height=6)
            listbox.place_forget()

            def update_autocomplete(*_):
                text = field_var.get()
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
                field_var.set(listbox.get(index))
                listbox.place_forget()
                entry.focus_set()
                entry.icursor(tk.END)

            field_var.trace_add("write", update_autocomplete)

            entry.bind("<Down>", lambda e: listbox.focus_set() if listbox.winfo_ismapped() else None)
            entry.bind("<Tab>", lambda e: (accept_selection(0), "break")[1] if listbox.winfo_ismapped() else None)

            listbox.bind("<Return>", lambda e: accept_selection(listbox.curselection()[0]))
            listbox.bind("<Double-Button-1>", lambda e: accept_selection(listbox.curselection()[0]))

            entry.bind(
                "<Return>",
                lambda e: self.validate_and_save(editor, path, field_var.get())
                if field_var.get().strip() else None
            )
            field_var.trace_add(
                "write",
                lambda *_: save_btn.config(
                    state="normal" if field_var.get().strip() else "disabled"
                )
            )
        elif mode == "RetreatCost":
            print("Not yet ready for productive environment")
            entry.bind(
                "<Return>",
                lambda e: self.validate_and_save(editor, path, field_var.get())
                if field_var.get().strip() else None
            )
            def update_save_button(*_):
                value = field_var.get().strip()
                if value.isdigit():
                    save_btn.state(["!disabled"])
                else:
                    save_btn.state(["disabled"])
            field_var.trace_add("write", update_save_button)

        elif mode == "HP":
            print("Not yet ready for productive environment")
            entry.bind(
                "<Return>",
                lambda e: self.validate_and_save(editor, path, field_var.get())
                if field_var.get().strip() else None
            )
            def update_save_button(*_):
                value = field_var.get().strip()
                if value.isdigit():
                    save_btn.state(["!disabled"])
                else:
                    save_btn.state(["disabled"])
            field_var.trace_add("write", update_save_button)

        elif True:
            print("Not implemented")
            return
    # ---------- ACTIONS ----------
    def skip_card(self, editor, mode):
        editor.destroy()
        self.current_index += 1
        self.open_card_editor(mode = mode)

    def validate_and_save(self, editor, path, fieldValue):
        print(f"INSIDE VALIDATE AND SAVE WITH path: {path} and fieldValue: {fieldValue} ")
        if MODE == "Illustrators":
            illustrator_norm = normalize_illustrator(fieldValue)

            if self.possible_illustrators and illustrator_norm not in self.possible_illustrators:
                self.show_unknown_illustrator_warning(editor, path, fieldValue)
                return

            self.save_illustrator(editor, path, fieldValue)

        if MODE == "RetreatCost":
            self.save_retreat_cost(editor, path, fieldValue)
        
        if MODE == "HP":
            self.save_hp(editor, path, fieldValue)

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

    def save_retreat_cost(self, editor, path, fieldValue):
        retreatCostMode = "RetreatCost"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            #print("ORIGINAL FILE: ", content)

        # 1️⃣ Locate thirdParty and indentation
        chosen_regex = "thirdParty"
        field_match = re.search(r"\n(\s*)thirdParty\s*:", content)
        if not field_match:
            #messagebox.showerror("Error", "Could not locate thirdParty field")
            print("Error, Could not locate thirdParty field, trying attacks")
            field_match = re.search(r"\n(\s*)attacks\s*:", content)
            chosen_regex = "attacks"
            if not field_match:
                messagebox.showerror("Error", "Could not locate attacks field")
                print("Error, Could not locate attacks field")
                return
#attacks: [
        #print(field_match)
        indent = field_match.group(1)
        RC_line = f'{indent}retreat: {fieldValue},'

        # 2️⃣ If illustrator already exists → overwrite it
        if re.search(r"\n\s*retreat\s*:\s*['\"].*?['\"],?", content):
            content = re.sub(
                r"\n(\s*)retreat\s*:\s*,?",
                f"\n{RC_line}",
                content,
                count=1
            )
        # 3️⃣ Otherwise → insert illustrator before rarity
        else:
            key = "attacks" if chosen_regex == "attacks" else "thirdParty"
            content = re.sub(
                rf"\n(\s*)({key}\s*:)",
                r"\n\1" + RC_line + r"\n\1\2",
                content,
                count=1
            )


        # 4️⃣ Write file back
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        #print("CONTENT TO REPLACE: ", content)
        editor.destroy()
        self.current_index += 1
        self.open_card_editor(mode = retreatCostMode)

    def save_hp(self, editor, path, fieldValue):
        HPMode = "HP"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            #print("ORIGINAL FILE: ", content)

        # 1️⃣ Locate thirdParty and indentation
        chosen_regex = "types"
        field_match = re.search(r"\n(\s*)types\s*:", content)
        if not field_match:
            #messagebox.showerror("Error", "Could not locate thirdParty field")
            print("Error, Could not locate types field, trying evolveFrom")
            field_match = re.search(r"\n(\s*)evolveFrom\s*:", content)
            if path == "/Users/sfreire/Downloads/Workspace_local_API/cards-database/data/Trainer kits/HS trainer Kit (Raichu)/19.ts":
                print(content)
            chosen_regex = "evolveFrom"
            if not field_match: #stage
                print("Error, Could not locate types evolveFrom, trying stage")
                field_match = re.search(r"\n(\s*)stage\s*:", content)
                chosen_regex = "stage"
                if not field_match:
                    messagebox.showerror("Error", "Could not locate stage field")
                    print("Error, Could not locate stage field")
                    return
#attacks: [
        #print(field_match)
        indent = field_match.group(1)
        HP_line = f'{indent}hp: {fieldValue},'

        # 2️⃣ If illustrator already exists → overwrite it
        if re.search(r"\n\s*hp\s*:\s*['\"].*?['\"],?", content):
            content = re.sub(
                r"\n(\s*)hp\s*:\s*,?",
                f"\n{HP_line}",
                content,
                count=1
            )
        # 3️⃣ Otherwise → insert illustrator before rarity
        else:
            key = {
                "types": "types",
                "evolveFrom": "evolveFrom",
            }.get(chosen_regex, "stage")            
            content = re.sub(
                rf"\n(\s*)({key}\s*:)",
                r"\1" + HP_line + r"\n\1\2",
                content,
                count=1
            )


        # 4️⃣ Write file back
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        #print("CONTENT TO REPLACE: ", content)
        editor.destroy()
        self.current_index += 1
        self.open_card_editor(mode = HPMode)

    def save_illustrator(self, editor, path, fieldValue):
        illustratorMode = "Illustrators"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1️⃣ Locate rarity and indentation
        rarity_match = re.search(r"\n(\s*)rarity\s*:", content)
        if not rarity_match:
            messagebox.showerror("Error", "Could not locate rarity field")
            return

        indent = rarity_match.group(1)
        escaped_illustrator = fieldValue.replace("\\", "\\\\").replace('"', '\\"')
        illustrator_line = f'\n{indent}illustrator: "{escaped_illustrator}",'

        # 2️⃣ If illustrator already exists → overwrite it
        if re.search(r"\n\s*illustrator\s*:\s*['\"].*?['\"],?", content):
            content = re.sub(
                r"\n(\s*)illustrator\s*:\s*['\"].*?['\"],?",
                f"\n{illustrator_line}",
                content,
                count=1
            )
        # 3️⃣ Otherwise → insert illustrator before rarity
        else:
            content = re.sub(
                r"\n(\s*rarity\s*:)",
                f"\n{illustrator_line}\n\\1",
                content,
                count=1
            )

        # 4️⃣ Write file back
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        editor.destroy()
        self.current_index += 1
        self.open_card_editor(mode = illustratorMode)

    # ---------- UTIL ----------
    @staticmethod
    def missing_field_illustrator(content)->bool:
        return not re.search(r"illustrator\s*:", content) or re.search(r"illustrator\s*:\s*['\"]\s*['\"]", content)
    @staticmethod
    def missing_field_retreat_cost(content)->bool:
        retreat_present = bool(re.search(r"\bretreat\s*:", content))

        # --- Check category line existence ---
        category_match = re.search(
            r"\bcategory\s*:\s*['\"]([^'\"]+)['\"]",
            content
        )

        if not category_match:
            # Hard fail: this should never happen in normal card files
            raise RuntimeError("❌ No category field found in file")

        category_value = category_match.group(1)
        is_pokemon = category_value == "Pokemon"

        # --- Debug output ---
        print(f"retreat present: {retreat_present}")
        print(f"is pokemon: {is_pokemon}")

        # --- Final decision ---
        return (not retreat_present) and is_pokemon
    
    @staticmethod
    def missing_field_hp(content)->bool:
        hp_present = bool(re.search(r"\bhp\s*:", content))

        # --- Check category line existence ---
        category_match = re.search(
            r"\bcategory\s*:\s*['\"]([^'\"]+)['\"]",
            content
        )

        if not category_match:
            # Hard fail: this should never happen in normal card files
            raise RuntimeError("❌ No category field found in file")

        category_value = category_match.group(1)
        is_pokemon = category_value == "Pokemon"

        # --- Debug output ---
        #print(f"HP present: {retreat_present}")
        #print(f"is pokemon: {is_pokemon}")

        # --- Final decision ---
        return (not hp_present) and is_pokemon
    
    @staticmethod
    def missing_field(content, mode) -> bool:
        try:
            return CardInspectorApp._MISSING_FIELD_CHECKS[mode](content)
        except KeyError:
            raise ValueError(f"Unknown MODE: {mode}")

    @staticmethod
    def extract_card_id(content, set_id, filename):
        match = re.search(r"id\s*:\s*['\"](.+?)['\"]", content)
        return match.group(1) if match else f"{set_id}-{filename.replace('.ts','')}"


# ---------- RUN ----------
async def run_tcgDex_database_helper_GUI_async():
# Initialize API once
    print("MODE IS : ", MODE)
    api = TCGdex(LANGUAGE)
    if IS_LOCAL_ENDPOINT:
        api = api.setEndpoint(LOCAL_ENDPOINT) ## Use local TCGdex instance
    app = CardInspectorApp(api)
    
    # Load series before showing GUI
    await app.load_series_async()
    
    # Now run Tkinter mainloop
    app.mainloop()
    
if __name__ == "__main__":
    CardInspectorApp().mainloop()
