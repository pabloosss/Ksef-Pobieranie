
import os
import re
import sys
import time
import sqlite3
import zipfile
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class KsefApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Program do pobierania FV KSeF - Emerlog")
        self.root.geometry("1240x860")
        self.root.minsize(1160, 780)
        self.root.configure(bg="#edf2f7")

        self.driver = None
        self.wait = None

        self.animating = False
        self.progress_mode = "idle"
        self.progress_value = 0
        self.progress_max = 100
        self.progress_direction = 1
        self.base_step_text = "Gotowe"

        self.status_box = None
        self.progress = None
        self.logo_image = None

        if getattr(sys, "frozen", False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))

        self.base_download_dir = os.path.join(self.base_dir, "pobrane_fv")
        os.makedirs(self.base_download_dir, exist_ok=True)

        self.registry_path = os.path.join(self.base_dir, "rejestr_pobran.sqlite")
        self.init_db()

        self.count_var = tk.StringVar(value="10")
        self.step_var = tk.StringVar(value="Status: gotowe")
        self.result_count_var = tk.StringVar(value="Wynik: nie sprawdzono")
        self.found_var = tk.StringVar(value="0")
        self.downloaded_var = tk.StringVar(value="0")
        self.skipped_var = tk.StringVar(value="0")
        self.skip_duplicates_var = tk.BooleanVar(value=True)

        self.last_total_count = 0
        self.last_new_count = 0

        self.setup_style()
        self.build_ui()
        self.animate_progress()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # =========================
    # DB
    # =========================
    def init_db(self):
        try:
            conn = sqlite3.connect(self.registry_path)
            cur = conn.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS download_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    folder_name TEXT NOT NULL,
                    downloaded_at TEXT NOT NULL,
                    requested_count INTEGER,
                    downloaded_count INTEGER,
                    skipped_count INTEGER
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS downloaded_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_key TEXT NOT NULL UNIQUE,
                    row_text TEXT,
                    downloaded_at TEXT NOT NULL,
                    session_folder TEXT
                )
            """)

            conn.commit()
            conn.close()
        except sqlite3.DatabaseError:
            bad_path = self.registry_path + ".bak"
            try:
                if os.path.exists(bad_path):
                    os.remove(bad_path)
            except Exception:
                pass
            try:
                if os.path.exists(self.registry_path):
                    os.rename(self.registry_path, bad_path)
            except Exception:
                pass

            conn = sqlite3.connect(self.registry_path)
            cur = conn.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS download_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    folder_name TEXT NOT NULL,
                    downloaded_at TEXT NOT NULL,
                    requested_count INTEGER,
                    downloaded_count INTEGER,
                    skipped_count INTEGER
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS downloaded_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_key TEXT NOT NULL UNIQUE,
                    row_text TEXT,
                    downloaded_at TEXT NOT NULL,
                    session_folder TEXT
                )
            """)

            conn.commit()
            conn.close()

    def add_session(self, folder_name, requested_count, downloaded_count, skipped_count):
        conn = sqlite3.connect(self.registry_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO download_sessions (folder_name, downloaded_at, requested_count, downloaded_count, skipped_count)
            VALUES (?, ?, ?, ?, ?)
        """, (
            folder_name,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            requested_count,
            downloaded_count,
            skipped_count
        ))
        conn.commit()
        conn.close()

    def add_downloaded_item(self, item_key, row_text, session_folder):
        conn = sqlite3.connect(self.registry_path)
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO downloaded_items (item_key, row_text, downloaded_at, session_folder)
                VALUES (?, ?, ?, ?)
            """, (
                item_key,
                row_text,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                session_folder
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        conn.close()

    def is_duplicate(self, item_key):
        conn = sqlite3.connect(self.registry_path)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM downloaded_items WHERE item_key = ? LIMIT 1", (item_key,))
        result = cur.fetchone()
        conn.close()
        return result is not None

    # =========================
    # UI
    # =========================
    def setup_style(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=11)
        self.style.configure("Secondary.TButton", font=("Segoe UI", 10, "bold"), padding=11)
        self.style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"), padding=11)

        self.style.map("Primary.TButton", background=[("active", "#d9e8ff")])
        self.style.map("Secondary.TButton", background=[("active", "#eef3f8")])
        self.style.map("Danger.TButton", background=[("active", "#ffd9df")])

        self.style.configure(
            "Modern.Horizontal.TProgressbar",
            troughcolor="#d9e2ec",
            background="#d90429",
            bordercolor="#d9e2ec",
            lightcolor="#d90429",
            darkcolor="#d90429"
        )

    def build_ui(self):
        main = tk.Frame(self.root, bg="#edf2f7", padx=18, pady=18)
        main.pack(fill="both", expand=True)

        header = tk.Frame(main, bg="#0f172a", bd=0)
        header.pack(fill="x", pady=(0, 14))

        header_inner = tk.Frame(header, bg="#0f172a", padx=24, pady=20)
        header_inner.pack(fill="x")

        left_header = tk.Frame(header_inner, bg="#0f172a")
        left_header.pack(side="left", fill="both", expand=True)

        self.load_logo(left_header)

        tk.Label(
            left_header,
            text="Program do pobierania FV KSeF - Emerlog",
            font=("Segoe UI", 24, "bold"),
            bg="#0f172a",
            fg="#ffffff"
        ).pack(anchor="w", pady=(12, 0))

        stats_row = tk.Frame(main, bg="#edf2f7")
        stats_row.pack(fill="x", pady=(0, 12))

        self.make_stat_card(stats_row, "Wszystkich FV", self.found_var, "#0f4c81").pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.make_stat_card(stats_row, "Pobrane", self.downloaded_var, "#166534").pack(side="left", fill="x", expand=True, padx=8)
        self.make_stat_card(stats_row, "Pominięte / duplikaty", self.skipped_var, "#b45309").pack(side="left", fill="x", expand=True, padx=(8, 0))

        body = tk.Frame(main, bg="#edf2f7")
        body.pack(fill="both", expand=True)

        left = self.card(body, width=430, padx=18, pady=18)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.pack_propagate(False)

        center = self.card(body, padx=18, pady=18)
        center.pack(side="left", fill="both", expand=True)

        tk.Label(left, text="Sterowanie", font=("Segoe UI", 17, "bold"), bg="white", fg="#0f172a").pack(anchor="w", pady=(0, 14))

        buttons_grid = tk.Frame(left, bg="white")
        buttons_grid.pack(fill="x", pady=(0, 14))
        buttons_grid.grid_columnconfigure(0, weight=1)
        buttons_grid.grid_columnconfigure(1, weight=1)

        ttk.Button(buttons_grid, text="Start / Otwórz KSeF", style="Primary.TButton", command=self.start_browser).grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10)
        )
        ttk.Button(buttons_grid, text="Sprawdź ilość FV", style="Secondary.TButton", command=self.check_invoice_count).grid(
            row=1, column=0, sticky="ew", padx=(0, 6), pady=(0, 10)
        )
        ttk.Button(buttons_grid, text="Otwórz folder", style="Secondary.TButton", command=self.open_download_folder).grid(
            row=1, column=1, sticky="ew", padx=(6, 0), pady=(0, 10)
        )

        separator1 = tk.Frame(left, bg="#e2e8f0", height=1)
        separator1.pack(fill="x", pady=10)

        tk.Label(left, text="Pobieranie", font=("Segoe UI", 15, "bold"), bg="white", fg="#0f172a").pack(anchor="w", pady=(4, 12))

        tk.Label(left, text="Ilość FV do pobrania", font=("Segoe UI", 10), bg="white", fg="#334155").pack(anchor="w")
        self.count_entry = tk.Entry(
            left,
            textvariable=self.count_var,
            font=("Segoe UI", 15, "bold"),
            bd=1,
            relief="solid",
            justify="center"
        )
        self.count_entry.pack(fill="x", pady=(6, 12), ipady=6)

        checkbox_wrap = tk.Frame(left, bg="#f8fafc", bd=1, relief="solid", padx=10, pady=10)
        checkbox_wrap.pack(fill="x", pady=(0, 12))
        ttk.Checkbutton(
            checkbox_wrap,
            text="Pomijaj już pobrane FV",
            variable=self.skip_duplicates_var
        ).pack(anchor="w")

        ttk.Button(left, text="Pobierz", style="Danger.TButton", command=self.download_invoices).pack(fill="x")

        separator2 = tk.Frame(left, bg="#e2e8f0", height=1)
        separator2.pack(fill="x", pady=16)

        tk.Label(left, text="Postęp", font=("Segoe UI", 13, "bold"), bg="white", fg="#0f172a").pack(anchor="w", pady=(0, 8))

        self.progress = ttk.Progressbar(
            left,
            mode="determinate",
            maximum=100,
            style="Modern.Horizontal.TProgressbar"
        )
        self.progress.pack(fill="x")

        status_card = tk.Frame(left, bg="#f8fafc", bd=1, relief="solid", padx=12, pady=10)
        status_card.pack(fill="x", pady=(12, 0))

        tk.Label(
            status_card,
            textvariable=self.step_var,
            font=("Segoe UI", 10, "bold"),
            bg="#f8fafc",
            fg="#334155",
            wraplength=360,
            justify="left"
        ).pack(anchor="w")

        tk.Label(
            left,
            textvariable=self.result_count_var,
            font=("Segoe UI", 10, "bold"),
            bg="white",
            fg="#0f4c81",
            wraplength=370,
            justify="left"
        ).pack(anchor="w", pady=(12, 0))

        top_center = tk.Frame(center, bg="white")
        top_center.pack(fill="x", pady=(0, 12))
        tk.Label(top_center, text="Log operacji", font=("Segoe UI", 17, "bold"), bg="white", fg="#0f172a").pack(side="left")

        log_frame = tk.Frame(center, bg="#0b1220", bd=0)
        log_frame.pack(fill="both", expand=True)

        self.status_box = tk.Text(
            log_frame,
            height=26,
            font=("Consolas", 10),
            bg="#0b1220",
            fg="#d7e3f4",
            insertbackground="white",
            bd=0,
            relief="flat",
            wrap="word",
            padx=14,
            pady=14
        )
        self.status_box.pack(fill="both", expand=True)
        self.status_box.configure(state="normal")
        self.status_box.insert("end", "[INFO] Aplikacja uruchomiona.\n")
        self.status_box.insert("end", "[INFO] Silnik: Selenium + Microsoft Edge.\n")
        self.status_box.insert("end", f"[INFO] Folder programu: {self.base_dir}\n")
        self.status_box.configure(state="disabled")

        footer = tk.Frame(main, bg="#edf2f7")
        footer.pack(fill="x", pady=(12, 0))

        tk.Label(
            footer,
            text="Made by Paweł Ruchlicki",
            font=("Segoe UI", 10, "bold"),
            bg="#edf2f7",
            fg="#475569"
        ).pack(anchor="e")

    def load_logo(self, parent):
        possible_names = [
            os.path.join(self.base_dir, "emerloglogo.png"),
            os.path.join(self.base_dir, "emerlog_logo.png"),
            os.path.join(self.base_dir, "logo.png"),
            "/mnt/data/emerloglogo.png",
        ]

        for path in possible_names:
            if os.path.exists(path):
                try:
                    self.logo_image = tk.PhotoImage(file=path)
                    width = self.logo_image.width()
                    if width > 560:
                        self.logo_image = self.logo_image.subsample(2, 2)
                    tk.Label(parent, image=self.logo_image, bg="#0f172a").pack(anchor="w")
                    return
                except Exception:
                    pass

    def card(self, parent, width=None, padx=16, pady=16):
        frame = tk.Frame(parent, bg="white", bd=1, relief="solid", padx=padx, pady=pady)
        if width:
            frame.configure(width=width)
        return frame

    def make_stat_card(self, parent, label, value_var, accent):
        card = tk.Frame(parent, bg="white", bd=1, relief="solid", padx=14, pady=12)
        strip = tk.Frame(card, bg=accent, height=4)
        strip.pack(fill="x", pady=(0, 10))
        tk.Label(card, text=label, font=("Segoe UI", 10, "bold"), bg="white", fg="#475569").pack(anchor="w")
        tk.Label(card, textvariable=value_var, font=("Segoe UI", 20, "bold"), bg="white", fg="#0f172a").pack(anchor="w", pady=(4, 0))
        return card

    # =========================
    # Helpers
    # =========================
    def log(self, text):
        self.status_box.configure(state="normal")
        self.status_box.insert("end", f"{text}\n")
        self.status_box.see("end")
        self.status_box.configure(state="disabled")
        self.root.update_idletasks()

    def set_step(self, text):
        self.base_step_text = text
        self.step_var.set(f"Status: {text}")
        self.root.update_idletasks()

    def start_loading(self, text="Przetwarzanie", mode="pulse", progress_value=None, progress_max=None):
        self.animating = True
        self.progress_mode = mode
        self.base_step_text = text

        if progress_max is not None:
            self.progress_max = max(1, progress_max)
            self.progress.configure(maximum=self.progress_max)

        if progress_value is not None:
            self.progress_value = max(0, progress_value)
            self.progress["value"] = self.progress_value

        self.step_var.set(f"Status: {text}")
        self.root.update_idletasks()

    def update_progress(self, current, total, text):
        total = max(1, total)
        self.animating = True
        self.progress_mode = "determinate"
        self.progress_max = total
        self.progress_value = min(current, total)
        self.progress.configure(maximum=total)
        self.progress["value"] = self.progress_value
        percent = int((self.progress_value / total) * 100)
        self.base_step_text = text
        self.step_var.set(f"Status: {text} ({current}/{total}, {percent}%)")
        self.root.update_idletasks()

    def stop_loading(self, text=None):
        self.animating = False
        self.progress_mode = "idle"
        self.progress_value = 0
        self.progress["value"] = 0
        if text:
            self.base_step_text = text
        self.step_var.set(f"Status: {self.base_step_text}")

    def animate_progress(self):
        if self.animating:
            if self.progress_mode == "pulse":
                step = 4
                self.progress_value += step * self.progress_direction
                if self.progress_value >= 100:
                    self.progress_value = 100
                    self.progress_direction = -1
                elif self.progress_value <= 0:
                    self.progress_value = 0
                    self.progress_direction = 1
                self.progress.configure(maximum=100)
                self.progress["value"] = self.progress_value
            elif self.progress_mode == "determinate":
                self.progress.configure(maximum=max(1, self.progress_max))
                self.progress["value"] = self.progress_value

        self.root.after(40, self.animate_progress)

    def normalize_text(self, text):
        return re.sub(r"\s+", " ", text).strip()

    def extract_item_key(self, text):
        text = self.normalize_text(text)

        patterns = [
            r"(\d{10,}-\d{8}-[A-Z0-9]+-\d+)",
            r"([A-Z0-9/\-]{6,}/\d{4})",
        ]

        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return m.group(1).lower()

        return text.lower()

    def open_download_folder(self):
        try:
            os.makedirs(self.base_download_dir, exist_ok=True)
            os.startfile(self.base_download_dir)
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się otworzyć folderu.\n\n{e}")

    # =========================
    # Selenium
    # =========================
    def create_driver(self):
        options = EdgeOptions()
        options.use_chromium = True
        options.add_argument("--start-maximized")
        options.add_experimental_option("prefs", {
            "download.default_directory": self.base_download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
        })
        # Selenium Manager should resolve msedgedriver automatically
        driver = webdriver.Edge(options=options)
        driver.set_page_load_timeout(90)
        self.wait = WebDriverWait(driver, 20)
        return driver

    def safe_find(self, by, value, timeout=4):
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except Exception:
            return None

    def safe_find_all(self, by, value):
        try:
            return self.driver.find_elements(by, value)
        except Exception:
            return []

    def safe_click_candidates(self, candidates, timeout=3, wait_after=0.8):
        for by, value in candidates:
            try:
                el = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, value))
                )
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                try:
                    WebDriverWait(self.driver, timeout).until(
                        EC.element_to_be_clickable((by, value))
                    )
                    el.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", el)
                time.sleep(wait_after)
                self.log(f"[OK] Kliknięto: {value}")
                return True
            except Exception:
                pass
        return False

    def set_download_directory(self, path):
        try:
            self.driver.execute_cdp_cmd(
                "Page.setDownloadBehavior",
                {"behavior": "allow", "downloadPath": path}
            )
        except Exception:
            pass

    def get_current_page_rows(self):
        selectors = [
            (By.CSS_SELECTOR, "tbody tr"),
            (By.CSS_SELECTOR, "table tbody tr"),
            (By.CSS_SELECTOR, "[role='row']"),
        ]

        rows = []
        for by, value in selectors:
            rows = self.safe_find_all(by, value)
            if rows:
                break

        rows_data = []
        for i, row in enumerate(rows):
            try:
                text = self.normalize_text(row.text)
                if not text:
                    continue

                checkbox = None
                cands = row.find_elements(By.CSS_SELECTOR, "input[type='checkbox'], [role='checkbox']")
                if cands:
                    checkbox = cands[0]
                if checkbox is None:
                    continue

                rows_data.append({
                    "row": row,
                    "text": text,
                    "row_id": self.extract_item_key(text),
                    "checkbox": checkbox,
                    "index": i
                })
            except Exception:
                pass

        return rows_data

    def get_page_signature(self):
        rows = self.get_current_page_rows()
        if not rows:
            return "EMPTY"
        return "|".join(item["row_id"] for item in rows[:5])

    def go_to_next_page(self):
        candidates = [
            (By.CSS_SELECTOR, "button[aria-label*='Następna']"),
            (By.CSS_SELECTOR, "button[title*='Następna']"),
            (By.CSS_SELECTOR, "[role='button'][aria-label*='Następna']"),
            (By.XPATH, "//*[contains(text(),'Następna')]"),
            (By.XPATH, "//*[contains(text(),'Next')]"),
        ]
        before = self.get_page_signature()
        if not self.safe_click_candidates(candidates, timeout=2, wait_after=1.5):
            return False

        for _ in range(10):
            time.sleep(0.4)
            after = self.get_page_signature()
            if after != before and after != "EMPTY":
                self.log("[OK] Przejście na następną stronę")
                return True
        return False

    def go_to_first_page(self, max_steps=50):
        prev_candidates = [
            (By.CSS_SELECTOR, "button[aria-label*='Poprzednia']"),
            (By.CSS_SELECTOR, "button[title*='Poprzednia']"),
            (By.CSS_SELECTOR, "[role='button'][aria-label*='Poprzednia']"),
            (By.XPATH, "//*[contains(text(),'Poprzednia')]"),
            (By.XPATH, "//*[contains(text(),'Previous')]"),
        ]

        for _ in range(max_steps):
            before = self.get_page_signature()
            if not self.safe_click_candidates(prev_candidates, timeout=1, wait_after=1.0):
                break
            after = self.get_page_signature()
            if after == before:
                break

    def scan_all_pages(self):
        all_rows = []
        seen_page_signatures = set()

        self.go_to_first_page()
        time.sleep(1.0)
        pages_scanned = 0

        while True:
            rows_data = self.get_current_page_rows()
            signature = self.get_page_signature()

            if signature in seen_page_signatures:
                break
            seen_page_signatures.add(signature)

            all_rows.extend(rows_data)
            pages_scanned += 1
            self.update_progress(pages_scanned, max(1, pages_scanned + 1), "Skanowanie stron")
            self.log(f"[INFO] Odczytano stronę: {len(rows_data)} wierszy")

            if not self.go_to_next_page():
                break

        self.go_to_first_page()
        time.sleep(1.0)
        return all_rows

    def click_checkbox(self, checkbox):
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", checkbox)
        except Exception:
            pass

        methods = [
            lambda: checkbox.click(),
            lambda: ActionChains(self.driver).move_to_element(checkbox).click(checkbox).perform(),
            lambda: self.driver.execute_script("""
                arguments[0].click();
                if (arguments[0].type === 'checkbox') {
                    arguments[0].checked = true;
                    arguments[0].dispatchEvent(new Event('input', {bubbles:true}));
                    arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
                }
            """, checkbox),
        ]

        for method in methods:
            try:
                method()
                time.sleep(0.15)
                if checkbox.is_selected():
                    return True
                aria = checkbox.get_attribute("aria-checked")
                checked = checkbox.get_attribute("checked")
                if aria == "true" or checked is not None:
                    return True
            except Exception:
                pass

        return False

    def count_checked_on_page(self):
        total = 0
        selectors = [
            (By.CSS_SELECTOR, "input[type='checkbox']:checked"),
            (By.CSS_SELECTOR, "[role='checkbox'][aria-checked='true']"),
        ]
        for by, value in selectors:
            try:
                total += len(self.driver.find_elements(by, value))
            except Exception:
                pass
        return total

    def create_session_folder(self, count_to_download):
        session_name = f"{datetime.now().strftime('%Y-%m-%d__%H-%M')}__{count_to_download}_FV"
        session_dir = os.path.join(self.base_download_dir, session_name)
        os.makedirs(session_dir, exist_ok=True)
        return session_name, session_dir

    def write_session_info(self, session_dir, requested_count, downloaded_count, skipped_count):
        info_path = os.path.join(session_dir, "info.txt")
        content = (
            f"Data pobrania: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Żądana liczba FV: {requested_count}\n"
            f"Pobrano: {downloaded_count}\n"
            f"Pominięto: {skipped_count}\n"
        )
        with open(info_path, "w", encoding="utf-8") as f:
            f.write(content)

    def wait_for_new_download(self, folder, before_files, timeout=40):
        start = time.time()
        while time.time() - start < timeout:
            current = set(os.listdir(folder))
            new_files = [f for f in current - before_files if not f.endswith((".crdownload", ".tmp", ".part"))]
            temp_files = [f for f in current if f.endswith((".crdownload", ".tmp", ".part"))]
            if new_files and not temp_files:
                newest = max((os.path.join(folder, f) for f in new_files), key=os.path.getmtime)
                return newest
            time.sleep(0.5)
        return None

    def save_download_keep_name(self, downloaded_path):
        return os.path.basename(downloaded_path), downloaded_path

    def maybe_extract_archive(self, save_path, session_dir):
        extracted = False
        if zipfile.is_zipfile(save_path):
            with zipfile.ZipFile(save_path, "r") as zf:
                zf.extractall(session_dir)
            try:
                os.remove(save_path)
            except Exception:
                pass
            extracted = True
        return extracted

    def try_download_selected(self, session_dir):
        self.set_download_directory(session_dir)
        before_files = set(os.listdir(session_dir))

        variants = [
            {
                "open": [
                    (By.XPATH, "//*[contains(text(),'Pobierz')]"),
                    (By.XPATH, "//*[contains(text(),'Eksportuj')]"),
                ],
                "prefer": [
                    (By.XPATH, "//*[contains(text(),'ZIP')]"),
                    (By.XPATH, "//*[contains(text(),'zip')]"),
                ],
                "fallback": [
                    (By.XPATH, "//*[contains(text(),'PDF')]"),
                ]
            }
        ]

        for variant in variants:
            try:
                if not self.safe_click_candidates(variant["open"], timeout=3, wait_after=1.0):
                    continue

                picked = False
                if self.safe_click_candidates(variant["prefer"], timeout=2, wait_after=1.0):
                    self.log("[INFO] Wybrano ZIP")
                    picked = True
                elif self.safe_click_candidates(variant["fallback"], timeout=2, wait_after=1.0):
                    self.log("[INFO] Wybrano PDF")
                    picked = True

                if not picked:
                    continue

                new_file = self.wait_for_new_download(session_dir, before_files, timeout=45)
                if new_file:
                    return new_file
            except Exception:
                pass

        return None

    # =========================
    # Main actions
    # =========================
    def start_browser(self):
        try:
            if self.driver is not None:
                messagebox.showinfo("Informacja", "Przeglądarka jest już otwarta.")
                return

            self.start_loading("Uruchamianie przeglądarki", mode="pulse")
            self.log("[INFO] Uruchamianie Edge...")

            self.driver = self.create_driver()
            self.driver.get("https://ap.ksef.mf.gov.pl/web/invoice-list")

            self.stop_loading("Czekam na logowanie")
            self.log("[OK] KSeF otwarty w Edge.")
            self.log("[INFO] Zaloguj się ręcznie i przejdź do listy faktur.")
            messagebox.showinfo(
                "Logowanie",
                "KSeF został otwarty w Edge.\n\nZaloguj się ręcznie i przejdź do listy faktur.\nFiltry ustawiasz bezpośrednio w KSeF."
            )

        except WebDriverException as e:
            self.stop_loading("Błąd")
            self.log(f"[BŁĄD] Nie udało się otworzyć Edge: {e}")
            messagebox.showerror(
                "Błąd Edge",
                "Nie udało się uruchomić Microsoft Edge.\n\n"
                "Sprawdź, czy Edge jest zainstalowany.\n\n"
                f"Szczegóły:\n{e}"
            )
            self.driver = None
            self.wait = None
        except Exception as e:
            self.stop_loading("Błąd")
            self.log(f"[BŁĄD] Nie udało się otworzyć przeglądarki: {e}")
            messagebox.showerror("Błąd", f"Nie udało się otworzyć przeglądarki.\n\n{e}")
            self.driver = None
            self.wait = None

    def check_invoice_count(self):
        try:
            if self.driver is None:
                messagebox.showwarning("Uwaga", "Najpierw kliknij Start.")
                return

            self.start_loading("Skanowanie stron", mode="pulse")
            self.log("[INFO] Skanuję wszystkie strony z FV...")

            all_rows = self.scan_all_pages()
            total_count = len(all_rows)

            skipped_count = 0
            new_count = total_count

            if self.skip_duplicates_var.get():
                filtered = []
                total_items = len(all_rows) if all_rows else 1
                for idx, item in enumerate(all_rows, start=1):
                    self.update_progress(idx, total_items, "Sprawdzanie duplikatów")
                    if self.is_duplicate(item["row_id"]):
                        skipped_count += 1
                    else:
                        filtered.append(item)
                new_count = len(filtered)

            self.last_total_count = total_count
            self.last_new_count = new_count

            self.found_var.set(str(total_count))
            self.downloaded_var.set("0")
            self.skipped_var.set(str(skipped_count))
            self.result_count_var.set(
                f"Wynik: wszystkich FV = {total_count}, nowych = {new_count}, duplikatów = {skipped_count}"
            )

            self.stop_loading("Sprawdzanie zakończone")
            self.log(f"[OK] Wszystkich FV: {total_count}")
            self.log(f"[OK] Nowych FV: {new_count}")
            self.log(f"[OK] Duplikatów: {skipped_count}")

            messagebox.showinfo(
                "Wynik",
                f"Wszystkich FV: {total_count}\nNowych FV: {new_count}\nDuplikatów: {skipped_count}"
            )

        except Exception as e:
            self.stop_loading("Błąd liczenia")
            self.log(f"[BŁĄD] Nie udało się sprawdzić ilości FV: {e}")
            messagebox.showerror("Błąd", f"Nie udało się sprawdzić ilości FV.\n\n{e}")

    def download_invoices(self):
        try:
            if self.driver is None:
                messagebox.showwarning("Uwaga", "Najpierw kliknij Start.")
                return

            count_text = self.count_var.get().strip()
            if not count_text.isdigit():
                messagebox.showwarning("Uwaga", "Wpisz poprawną liczbę FV do pobrania.")
                return

            wanted = int(count_text)
            if wanted <= 0:
                messagebox.showwarning("Uwaga", "Liczba FV musi być większa od 0.")
                return

            if self.last_total_count == 0 and self.last_new_count == 0:
                messagebox.showwarning("Uwaga", "Najpierw kliknij 'Sprawdź ilość FV'.")
                return

            limit = self.last_new_count if self.skip_duplicates_var.get() else self.last_total_count
            if wanted > limit:
                messagebox.showwarning(
                    "Za dużo FV",
                    f"Chcesz pobrać {wanted} FV, a dostępnych po sprawdzeniu jest tylko {limit}."
                )
                return

            self.start_loading("Przygotowanie pobierania", mode="pulse")
            self.log(f"[INFO] Rozpoczynam pobieranie. Cel: {wanted} FV")

            session_name, session_dir = self.create_session_folder(wanted)
            self.log(f"[INFO] Folder sesji: {session_dir}")

            total_downloaded = 0
            total_skipped = 0
            batch_number = 1
            batch_size = 10

            self.go_to_first_page()
            time.sleep(1.0)

            seen_page_signatures = set()

            while total_downloaded < wanted:
                rows_data = self.get_current_page_rows()
                signature = self.get_page_signature()

                if signature in seen_page_signatures:
                    break
                seen_page_signatures.add(signature)

                selected_rows = []
                target_on_this_page = min(batch_size, wanted - total_downloaded)

                self.update_progress(total_downloaded, wanted, "Zaznaczanie faktur")

                for item in rows_data:
                    if len(selected_rows) >= target_on_this_page:
                        break

                    if self.skip_duplicates_var.get() and self.is_duplicate(item["row_id"]):
                        total_skipped += 1
                        self.skipped_var.set(str(total_skipped))
                        continue

                    if self.click_checkbox(item["checkbox"]):
                        selected_rows.append(item)
                        self.log(f"[INFO] Zaznaczono: {item['text'][:140]}")
                    else:
                        self.log(f"[BŁĄD] Nie udało się zaznaczyć: {item['text'][:140]}")

                checked_now = self.count_checked_on_page()
                self.log(f"[INFO] Faktycznie zaznaczonych na stronie: {checked_now}")

                if selected_rows and checked_now >= len(selected_rows):
                    self.set_step(f"Pobieranie partii {batch_number}")
                    self.log(f"[INFO] Pobieram partię {batch_number}. Zaznaczone: {len(selected_rows)}")

                    downloaded_path = self.try_download_selected(session_dir)
                    if downloaded_path is None:
                        self.stop_loading("Błąd pobierania")
                        self.log("[BŁĄD] Nie udało się pobrać zaznaczonej partii.")
                        messagebox.showerror("Błąd", "Nie udało się pobrać zaznaczonej partii.")
                        return

                    original_name, save_path = self.save_download_keep_name(downloaded_path)
                    self.log(f"[OK] Zapisano: {original_name}")

                    if self.maybe_extract_archive(save_path, session_dir):
                        self.log("[OK] Archiwum ZIP zostało wypakowane.")
                    else:
                        self.log("[INFO] Pobrany plik nie był ZIP-em.")

                    for item in selected_rows:
                        self.add_downloaded_item(item["row_id"], item["text"], session_name)

                    total_downloaded += len(selected_rows)
                    self.downloaded_var.set(str(total_downloaded))
                    self.skipped_var.set(str(total_skipped))
                    self.update_progress(total_downloaded, wanted, "Pobieranie faktur")
                    self.log(f"[OK] Łącznie pobrano: {total_downloaded}/{wanted}")
                    batch_number += 1
                    time.sleep(1.2)
                else:
                    self.log("[INFO] Na tej stronie nie udało się zaznaczyć żadnej nowej partii.")

                if total_downloaded >= wanted:
                    break

                if not self.go_to_next_page():
                    break

            self.write_session_info(session_dir, wanted, total_downloaded, total_skipped)
            self.add_session(session_name, wanted, total_downloaded, total_skipped)

            self.stop_loading("Gotowe")
            self.log(f"[OK] Koniec. Pobrano: {total_downloaded}, pominięto: {total_skipped}")

            if total_downloaded < wanted:
                messagebox.showwarning(
                    "Niepełne pobranie",
                    f"Pobrano {total_downloaded} z {wanted} FV.\nFolder:\n{session_dir}"
                )
            else:
                messagebox.showinfo(
                    "Sukces",
                    f"Pobieranie zakończone.\n\nPobrano: {total_downloaded} FV\nFolder:\n{session_dir}"
                )

        except Exception as e:
            self.stop_loading("Błąd")
            self.log(f"[BŁĄD] Nie udało się wykonać pobierania: {e}")
            messagebox.showerror("Błąd", f"Nie udało się wykonać pobierania.\n\n{e}")

    def on_close(self):
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = KsefApp(root)
    root.mainloop()
