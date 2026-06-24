
import os
import re
import sys
import time
import base64
import zipfile
import traceback
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import WebDriverException, StaleElementReferenceException
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

APP_TITLE = "Program do pobierania FV KSeF - Emerlog"
KSEF_URL = "https://ap.ksef.mf.gov.pl/web/invoice-list"
DEFAULT_BATCH_SIZE = 10
MAX_SCAN_PAGES = 300
ROW_WAIT_SECONDS = 15
MAX_RETRY_PASSES = 2
LOGO_BASE64 = "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"


def safe_remove(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def is_dir_writable(path):
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, ".write_test.tmp")
        with open(probe, "w", encoding="utf-8") as handle:
            handle.write("ok")
        safe_remove(probe)
        return True
    except Exception:
        return False


def resolve_base_dir():
    if getattr(sys, "frozen", False):
        candidate = os.path.dirname(sys.executable)
    else:
        candidate = os.path.dirname(os.path.abspath(__file__))

    if is_dir_writable(candidate):
        return candidate

    fallback = os.path.join(str(Path.home()), "Documents", "Ksef-Pobieranie")
    os.makedirs(fallback, exist_ok=True)
    return fallback


def open_in_file_manager(path):
    try:
        os.startfile(path)
        return
    except Exception:
        pass

    try:
        subprocess.Popen(["explorer", path])
    except Exception:
        raise RuntimeError(f"Nie udało się otworzyć folderu: {path}")


def write_crash_log(base_dir, exc):
    try:
        os.makedirs(base_dir, exist_ok=True)
        path = os.path.join(base_dir, "crash_log.txt")
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("=" * 70 + "\n")
            handle.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
            handle.write(str(exc) + "\n\n")
            handle.write(traceback.format_exc())
            handle.write("\n")
        return path
    except Exception:
        return None


class KsefApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1200x840")
        self.root.minsize(1120, 760)
        self.root.configure(bg="#ffffff")

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

        self.base_dir = resolve_base_dir()
        self.base_download_dir = os.path.join(self.base_dir, "pobrane_fv")
        os.makedirs(self.base_download_dir, exist_ok=True)

        self.step_var = tk.StringVar(value="Status: gotowe")
        self.result_count_var = tk.StringVar(value="")
        self.found_var = tk.StringVar(value="0")
        self.downloaded_var = tk.StringVar(value="0")

        self.setup_style()
        self.build_ui()
        self.animate_progress()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # =========================
    # UI
    # =========================
    def setup_style(self):
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=11,
            background="#d10f14",
            foreground="#ffffff",
            borderwidth=0,
        )
        self.style.configure(
            "Secondary.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=11,
            background="#000000",
            foreground="#ffffff",
            borderwidth=0,
        )
        self.style.configure(
            "Danger.TButton",
            font=("Segoe UI", 11, "bold"),
            padding=12,
            background="#d10f14",
            foreground="#ffffff",
            borderwidth=0,
        )

        self.style.map("Primary.TButton", background=[("active", "#b30000")], foreground=[("active", "#ffffff")])
        self.style.map("Secondary.TButton", background=[("active", "#2a2a2a")], foreground=[("active", "#ffffff")])
        self.style.map("Danger.TButton", background=[("active", "#b30000")], foreground=[("active", "#ffffff")])

        self.style.configure(
            "Modern.Horizontal.TProgressbar",
            troughcolor="#d9d9d9",
            background="#d10f14",
            bordercolor="#d9d9d9",
            lightcolor="#d10f14",
            darkcolor="#d10f14",
        )

    def build_ui(self):
        main = tk.Frame(self.root, bg="#ffffff", padx=18, pady=18)
        main.pack(fill="both", expand=True)

        header = tk.Frame(main, bg="#000000", bd=0)
        header.pack(fill="x", pady=(0, 14))

        header_inner = tk.Frame(header, bg="#000000", padx=24, pady=20)
        header_inner.pack(fill="x")

        left_header = tk.Frame(header_inner, bg="#000000")
        left_header.pack(side="left", fill="both", expand=True)

        self.load_logo(left_header)

        tk.Label(
            left_header,
            text=APP_TITLE,
            font=("Segoe UI", 24, "bold"),
            bg="#000000",
            fg="#ffffff",
        ).pack(anchor="w", pady=(12, 0))

        stats_row = tk.Frame(main, bg="#ffffff")
        stats_row.pack(fill="x", pady=(0, 12))

        self.make_stat_card(stats_row, "Znalezione FV", self.found_var, "#d10f14").pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        self.make_stat_card(stats_row, "Pobrane FV", self.downloaded_var, "#000000").pack(
            side="left", fill="x", expand=True, padx=(8, 0)
        )

        body = tk.Frame(main, bg="#ffffff")
        body.pack(fill="both", expand=True)

        left = self.card(body, width=430, padx=18, pady=18)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.pack_propagate(False)

        center = self.card(body, padx=18, pady=18)
        center.pack(side="left", fill="both", expand=True)

        tk.Label(left, text="Sterowanie", font=("Segoe UI", 17, "bold"), bg="white", fg="#000000").pack(anchor="w", pady=(0, 14))

        buttons_grid = tk.Frame(left, bg="white")
        buttons_grid.pack(fill="x", pady=(0, 14))
        buttons_grid.grid_columnconfigure(0, weight=1)
        buttons_grid.grid_columnconfigure(1, weight=1)

        ttk.Button(
            buttons_grid,
            text="Start / Otwórz KSeF",
            style="Primary.TButton",
            command=self.start_browser,
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        ttk.Button(
            buttons_grid,
            text="Otwórz folder",
            style="Secondary.TButton",
            command=self.open_download_folder,
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        separator1 = tk.Frame(left, bg="#d10f14", height=2)
        separator1.pack(fill="x", pady=10)

        tk.Label(left, text="Pobieranie", font=("Segoe UI", 15, "bold"), bg="white", fg="#000000").pack(anchor="w", pady=(4, 12))
        ttk.Button(left, text="Pobierz FV", style="Danger.TButton", command=self.download_invoices).pack(fill="x")

        separator2 = tk.Frame(left, bg="#000000", height=1)
        separator2.pack(fill="x", pady=16)

        tk.Label(left, text="Postęp", font=("Segoe UI", 13, "bold"), bg="white", fg="#000000").pack(anchor="w", pady=(0, 8))

        self.progress = ttk.Progressbar(
            left,
            mode="determinate",
            maximum=100,
            style="Modern.Horizontal.TProgressbar",
        )
        self.progress.pack(fill="x")

        status_card = tk.Frame(
            left,
            bg="#fafafa",
            bd=1,
            relief="solid",
            padx=12,
            pady=10,
            highlightbackground="#d10f14",
            highlightthickness=1,
        )
        status_card.pack(fill="x", pady=(12, 0))

        tk.Label(
            status_card,
            textvariable=self.step_var,
            font=("Segoe UI", 10, "bold"),
            bg="#fafafa",
            fg="#000000",
            wraplength=360,
            justify="left",
        ).pack(anchor="w")

        tk.Label(
            left,
            textvariable=self.result_count_var,
            font=("Segoe UI", 10, "bold"),
            bg="white",
            fg="#d10f14",
            wraplength=370,
            justify="left",
        ).pack(anchor="w", pady=(12, 0))

        top_center = tk.Frame(center, bg="white")
        top_center.pack(fill="x", pady=(0, 12))
        tk.Label(top_center, text="Log operacji", font=("Segoe UI", 17, "bold"), bg="white", fg="#000000").pack(side="left")

        log_frame = tk.Frame(center, bg="#000000", bd=0)
        log_frame.pack(fill="both", expand=True)

        self.status_box = tk.Text(
            log_frame,
            height=26,
            font=("Consolas", 10),
            bg="#000000",
            fg="#ffffff",
            insertbackground="white",
            bd=0,
            relief="flat",
            wrap="word",
            padx=14,
            pady=14,
        )
        self.status_box.pack(fill="both", expand=True)
        self.status_box.configure(state="normal")
        self.status_box.insert("end", "[INFO] Aplikacja uruchomiona.\n")
        self.status_box.insert("end", "[INFO] Silnik: Selenium + Microsoft Edge.\n")
        self.status_box.insert("end", f"[INFO] Folder programu: {self.base_dir}\n")
        self.status_box.insert("end", f"[INFO] Folder pobierania: {self.base_download_dir}\n")
        self.status_box.configure(state="disabled")

        footer = tk.Frame(main, bg="#ffffff")
        footer.pack(fill="x", pady=(12, 0))

        tk.Label(
            footer,
            text="Made by Paweł Ruchlicki",
            font=("Segoe UI", 10, "bold"),
            bg="#ffffff",
            fg="#000000",
        ).pack(anchor="e")

    def load_logo(self, parent):
        try:
            self.logo_image = tk.PhotoImage(data=LOGO_BASE64)
            if self.logo_image.width() > 560:
                factor = max(1, self.logo_image.width() // 560)
                self.logo_image = self.logo_image.subsample(factor, factor)
            tk.Label(parent, image=self.logo_image, bg="#000000").pack(anchor="w")
            return
        except Exception:
            pass

        possible_names = [
            os.path.join(self.base_dir, "logo.png"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png"),
            os.path.join(self.base_dir, "emerloglogo.png"),
            os.path.join(self.base_dir, "emerlog_logo.png"),
        ]

        for path in possible_names:
            if os.path.exists(path):
                try:
                    self.logo_image = tk.PhotoImage(file=path)
                    if self.logo_image.width() > 560:
                        factor = max(1, self.logo_image.width() // 560)
                        self.logo_image = self.logo_image.subsample(factor, factor)
                    tk.Label(parent, image=self.logo_image, bg="#000000").pack(anchor="w")
                    return
                except Exception:
                    pass

    def card(self, parent, width=None, padx=16, pady=16):
        frame = tk.Frame(
            parent,
            bg="white",
            bd=1,
            relief="solid",
            padx=padx,
            pady=pady,
            highlightbackground="#d10f14",
            highlightthickness=1,
        )
        if width:
            frame.configure(width=width)
        return frame

    def make_stat_card(self, parent, label, value_var, accent):
        card = tk.Frame(
            parent,
            bg="white",
            bd=1,
            relief="solid",
            padx=14,
            pady=12,
            highlightbackground=accent,
            highlightthickness=1,
        )
        strip = tk.Frame(card, bg=accent, height=4)
        strip.pack(fill="x", pady=(0, 10))
        tk.Label(card, text=label, font=("Segoe UI", 10, "bold"), bg="white", fg="#000000").pack(anchor="w")
        tk.Label(card, textvariable=value_var, font=("Segoe UI", 20, "bold"), bg="white", fg=accent).pack(anchor="w", pady=(4, 0))
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
        return re.sub(r"\s+", " ", text or "").strip()

    def extract_item_key(self, text):
        text = self.normalize_text(text)
        patterns = [
            r"(\d{10,}-\d{8}-[A-Z0-9]+-\d+)",
            r"([A-Z0-9/\-]{6,}/\d{4})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).lower()
        return text.lower()

    def open_download_folder(self):
        try:
            os.makedirs(self.base_download_dir, exist_ok=True)
            open_in_file_manager(self.base_download_dir)
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się otworzyć folderu.\n\n{e}")

    def wait_for_rows(self, timeout=ROW_WAIT_SECONDS):
        selectors = [
            (By.CSS_SELECTOR, "tbody tr"),
            (By.CSS_SELECTOR, "table tbody tr"),
            (By.CSS_SELECTOR, "[role='row']"),
        ]
        end_time = time.time() + timeout
        while time.time() < end_time:
            for by, value in selectors:
                try:
                    found = self.driver.find_elements(by, value)
                    if found:
                        return True
                except Exception:
                    pass
            time.sleep(0.3)
        return False

    # =========================
    # Selenium
    # =========================
    def create_driver(self):
        options = EdgeOptions()
        options.use_chromium = True
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-features=msEdgeSidebarV2")
        options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": self.base_download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "plugins.always_open_pdf_externally": True,
            },
        )

        driver = webdriver.Edge(options=options)
        driver.implicitly_wait(2)
        driver.set_page_load_timeout(90)
        self.wait = WebDriverWait(driver, 20)
        return driver

    def ensure_browser_fullscreen(self):
        if self.driver is None:
            return

        try:
            self.driver.maximize_window()
            time.sleep(0.4)
        except Exception:
            pass

        try:
            width, height = self.driver.execute_script(
                "return [window.screen.availWidth || 1920, window.screen.availHeight || 1080];"
            )
            self.driver.set_window_position(0, 0)
            self.driver.set_window_size(int(width), int(height))
            time.sleep(0.4)
        except Exception:
            pass

        try:
            self.driver.execute_script(
                "window.moveTo(0,0); window.resizeTo(window.screen.availWidth, window.screen.availHeight);"
            )
        except Exception:
            pass

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
                    WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable((by, value)))
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
                {"behavior": "allow", "downloadPath": path},
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
                candidates = row.find_elements(By.CSS_SELECTOR, "input[type='checkbox'], [role='checkbox']")
                if candidates:
                    checkbox = candidates[0]
                if checkbox is None:
                    continue

                rows_data.append(
                    {
                        "row": row,
                        "text": text,
                        "row_id": self.extract_item_key(text),
                        "checkbox": checkbox,
                        "index": i,
                    }
                )
            except Exception:
                pass

        return rows_data

    def get_page_signature(self):
        rows = self.get_current_page_rows()
        if not rows:
            return "EMPTY"
        return "|".join(item["row_id"] for item in rows)

    def go_to_next_page(self):
        candidates = [
            (By.CSS_SELECTOR, "button[aria-label*='Następna']"),
            (By.CSS_SELECTOR, "button[title*='Następna']"),
            (By.CSS_SELECTOR, "[role='button'][aria-label*='Następna']"),
            (By.XPATH, "//*[contains(text(),'Następna')]"),
            (By.XPATH, "//*[contains(text(),'Next')]"),
        ]
        before = self.get_page_signature()
        if not self.safe_click_candidates(candidates, timeout=2, wait_after=1.2):
            return False

        self.wait_for_rows(timeout=8)
        for _ in range(12):
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
            if not self.safe_click_candidates(prev_candidates, timeout=1, wait_after=0.8):
                break
            self.wait_for_rows(timeout=6)
            after = self.get_page_signature()
            if after == before:
                break

    def click_checkbox(self, checkbox):
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", checkbox)
        except Exception:
            pass

        methods = [
            lambda: checkbox.click(),
            lambda: ActionChains(self.driver).move_to_element(checkbox).click(checkbox).perform(),
            lambda: self.driver.execute_script(
                """
                arguments[0].click();
                if (arguments[0].type === 'checkbox') {
                    arguments[0].checked = true;
                    arguments[0].dispatchEvent(new Event('input', {bubbles:true}));
                    arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
                }
                if (arguments[0].getAttribute('role') === 'checkbox') {
                    arguments[0].setAttribute('aria-checked', 'true');
                    arguments[0].dispatchEvent(new Event('click', {bubbles:true}));
                }
                """,
                checkbox,
            ),
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

    def uncheck_checkbox(self, checkbox):
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", checkbox)
        except Exception:
            pass

        methods = [
            lambda: checkbox.click(),
            lambda: ActionChains(self.driver).move_to_element(checkbox).click(checkbox).perform(),
            lambda: self.driver.execute_script(
                """
                try { arguments[0].click(); } catch (e) {}
                if (arguments[0].type === 'checkbox') {
                    arguments[0].checked = false;
                    arguments[0].dispatchEvent(new Event('input', {bubbles:true}));
                    arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
                }
                if (arguments[0].getAttribute('role') === 'checkbox') {
                    arguments[0].setAttribute('aria-checked', 'false');
                }
                """,
                checkbox,
            ),
        ]

        for method in methods:
            try:
                method()
                time.sleep(0.1)
                aria = checkbox.get_attribute("aria-checked")
                checked = checkbox.get_attribute("checked")
                selected = False
                try:
                    selected = checkbox.is_selected()
                except Exception:
                    selected = False
                if not selected and aria != "true" and checked is None:
                    return True
            except Exception:
                pass

        return False

    def clear_all_visible_checkboxes(self):
        cleared = 0
        for item in self.get_current_page_rows():
            checkbox = item["checkbox"]
            try:
                aria = checkbox.get_attribute("aria-checked")
                checked = checkbox.get_attribute("checked")
                is_selected = False
                try:
                    is_selected = checkbox.is_selected()
                except Exception:
                    is_selected = False

                if is_selected or aria == "true" or checked is not None:
                    if self.uncheck_checkbox(checkbox):
                        cleared += 1
            except (StaleElementReferenceException, Exception):
                continue

        if cleared:
            self.log(f"[INFO] Wyczyszczono zaznaczenie: {cleared}")

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

    # =========================
    # Manifest i weryfikacja
    # =========================
    def scan_manifest(self):
        all_rows = []
        unique_ids = set()
        seen_page_signatures = set()

        self.go_to_first_page()
        self.wait_for_rows(timeout=10)
        time.sleep(0.8)

        pages_scanned = 0
        while pages_scanned < MAX_SCAN_PAGES:
            rows_data = self.get_current_page_rows()
            signature = self.get_page_signature()

            if not rows_data or signature == "EMPTY":
                break
            if signature in seen_page_signatures:
                break

            seen_page_signatures.add(signature)
            pages_scanned += 1

            for item in rows_data:
                if item["row_id"] not in unique_ids:
                    unique_ids.add(item["row_id"])
                    all_rows.append({"row_id": item["row_id"], "text": item["text"]})

            self.found_var.set(str(len(unique_ids)))
            self.update_progress(pages_scanned, max(1, pages_scanned + 1), "Skanowanie listy FV")
            self.log(f"[INFO] Skan strony {pages_scanned}: {len(rows_data)} wierszy, unikalnych FV: {len(unique_ids)}")

            if not self.go_to_next_page():
                break

        self.go_to_first_page()
        self.wait_for_rows(timeout=10)
        time.sleep(0.8)

        return all_rows

    def save_missing_report(self, session_dir, missing_rows):
        path = os.path.join(session_dir, "brakujace_fv.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("Brakujące FV po weryfikacji:\n\n")
            for item in missing_rows:
                handle.write(f"{item['row_id']} | {item['text']}\n")
        return path

    def create_session_folder(self):
        session_name = f"{datetime.now().strftime('%Y-%m-%d__%H-%M-%S')}__WSZYSTKIE_FV"
        session_dir = os.path.join(self.base_download_dir, session_name)
        os.makedirs(session_dir, exist_ok=True)
        return session_dir

    def write_session_info(self, session_dir, found_count, downloaded_count, retry_count=0, missing_count=0):
        info_path = os.path.join(session_dir, "info.txt")
        content = (
            f"Data pobrania: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Tryb: pobierz wszystko\n"
            f"Znalezione FV: {found_count}\n"
            f"Pobrane FV: {downloaded_count}\n"
            f"Próby naprawcze: {retry_count}\n"
            f"Brakujące po weryfikacji: {missing_count}\n"
        )
        with open(info_path, "w", encoding="utf-8") as handle:
            handle.write(content)

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

    def maybe_extract_archive(self, save_path, session_dir):
        extracted = False
        if zipfile.is_zipfile(save_path):
            with zipfile.ZipFile(save_path, "r") as archive:
                archive.extractall(session_dir)
            safe_remove(save_path)
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
                ],
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
    # Pobieranie i weryfikacja
    # =========================
    def process_pages_for_ids(self, target_ids, target_map, session_dir, already_processed=None):
        processed = set(already_processed or set())
        batch_number = 1

        self.go_to_first_page()
        self.wait_for_rows(timeout=10)
        time.sleep(0.8)

        seen_page_signatures = set()
        while len(seen_page_signatures) < MAX_SCAN_PAGES:
            rows_data = self.get_current_page_rows()
            signature = self.get_page_signature()

            if not rows_data or signature == "EMPTY":
                break
            if signature in seen_page_signatures:
                break

            seen_page_signatures.add(signature)

            while True:
                rows_data = self.get_current_page_rows()
                remaining_rows = [
                    item for item in rows_data
                    if item["row_id"] in target_ids and item["row_id"] not in processed
                ]

                if not remaining_rows:
                    break

                target_on_this_page = min(DEFAULT_BATCH_SIZE, len(remaining_rows))
                self.clear_all_visible_checkboxes()
                time.sleep(0.2)

                selected_rows = []
                for item in remaining_rows[:target_on_this_page]:
                    if self.click_checkbox(item["checkbox"]):
                        selected_rows.append(item)
                        self.log(f"[INFO] Zaznaczono: {item['text'][:140]}")
                    else:
                        self.log(f"[BŁĄD] Nie udało się zaznaczyć: {item['text'][:140]}")

                checked_now = self.count_checked_on_page()
                self.log(f"[INFO] Faktycznie zaznaczonych na stronie: {checked_now}")

                if not selected_rows or checked_now < len(selected_rows):
                    raise RuntimeError("Nie udało się poprawnie zaznaczyć części FV.")

                self.set_step(f"Pobieranie partii {batch_number}")
                self.log(f"[INFO] Pobieram partię {batch_number}. Zaznaczone: {len(selected_rows)}")

                downloaded_path = self.try_download_selected(session_dir)
                if downloaded_path is None:
                    raise RuntimeError("Nie udało się pobrać zaznaczonej partii.")

                self.log(f"[OK] Zapisano: {os.path.basename(downloaded_path)}")

                if self.maybe_extract_archive(downloaded_path, session_dir):
                    self.log("[OK] Archiwum ZIP zostało wypakowane.")
                else:
                    self.log("[INFO] Pobrany plik nie był ZIP-em.")

                for item in selected_rows:
                    processed.add(item["row_id"])

                self.downloaded_var.set(str(len(processed)))
                self.update_progress(len(processed), max(1, len(target_ids)), "Pobieranie faktur")
                self.log(f"[OK] Łącznie pobrano: {len(processed)}/{len(target_ids)}")
                batch_number += 1
                time.sleep(1.0)

            if len(processed) >= len(target_ids):
                break

            if not self.go_to_next_page():
                break

        missing = [target_map[item_id] for item_id in target_ids if item_id not in processed]
        return processed, missing

    def start_browser(self):
        try:
            if self.driver is not None:
                messagebox.showinfo("Informacja", "Przeglądarka jest już otwarta.")
                return

            self.start_loading("Uruchamianie przeglądarki", mode="pulse")
            self.log("[INFO] Uruchamianie Edge...")

            self.driver = self.create_driver()
            self.driver.get(KSEF_URL)
            self.ensure_browser_fullscreen()

            self.stop_loading("Czekam na logowanie")
            self.log("[OK] KSeF otwarty w Edge.")
            self.log("[INFO] Okno przeglądarki zostało maksymalnie powiększone.")
            self.log("[INFO] Zaloguj się ręcznie i przejdź do listy faktur.")
            messagebox.showinfo(
                "Logowanie",
                "KSeF został otwarty w Edge.\n\nZaloguj się ręcznie i przejdź do listy faktur.\nFiltry ustawiasz bezpośrednio w KSeF."
            )

        except WebDriverException as e:
            self.stop_loading("Błąd")
            self.log(f"[BŁĄD] Nie udało się otworzyć Edge: {e}")
            log_path = write_crash_log(self.base_dir, e)
            extra = f"\n\nLog błędu: {log_path}" if log_path else ""
            messagebox.showerror(
                "Błąd Edge",
                "Nie udało się uruchomić Microsoft Edge.\n\n"
                "Sprawdź, czy Microsoft Edge jest zainstalowany i zaktualizowany.\n"
                "Jeżeli to świeży komputer, uruchom najpierw build_exe.bat na komputerze roboczym albo zainstaluj zależności z requirements.txt."
                + extra
            )
            self.driver = None
            self.wait = None
        except Exception as e:
            self.stop_loading("Błąd")
            self.log(f"[BŁĄD] Nie udało się otworzyć przeglądarki: {e}")
            log_path = write_crash_log(self.base_dir, e)
            extra = f"\n\nLog błędu: {log_path}" if log_path else ""
            messagebox.showerror("Błąd", f"Nie udało się otworzyć przeglądarki.\n\n{e}{extra}")
            self.driver = None
            self.wait = None

    def download_invoices(self):
        try:
            if self.driver is None:
                messagebox.showwarning("Uwaga", "Najpierw kliknij Start.")
                return

            self.start_loading("Skanowanie listy FV", mode="pulse")
            self.log("[INFO] Rozpoczynam automatyczne skanowanie listy FV...")

            manifest_rows = self.scan_manifest()
            if not manifest_rows:
                self.stop_loading("Brak FV")
                messagebox.showwarning("Brak FV", "Nie znaleziono żadnych FV na aktualnej liście KSeF.")
                return

            target_ids = [item["row_id"] for item in manifest_rows]
            target_map = {item["row_id"]: item for item in manifest_rows}
            self.found_var.set(str(len(target_ids)))
            self.result_count_var.set(f"Na liście: {len(target_ids)} FV")
            self.log(f"[OK] Zeskanowano wszystkie strony. Znalezione FV: {len(target_ids)}")

            session_dir = self.create_session_folder()
            self.log(f"[INFO] Folder sesji: {session_dir}")

            processed_ids, missing_rows = self.process_pages_for_ids(set(target_ids), target_map, session_dir)

            retry_count = 0
            while missing_rows and retry_count < MAX_RETRY_PASSES:
                retry_count += 1
                self.log(f"[INFO] Weryfikacja wykryła brakujące FV: {len(missing_rows)}. Próba naprawcza {retry_count}/{MAX_RETRY_PASSES}.")
                missing_ids = set(item["row_id"] for item in missing_rows)
                processed_ids, missing_rows = self.process_pages_for_ids(missing_ids, target_map, session_dir, processed_ids)

            missing_count = len(missing_rows)
            self.write_session_info(session_dir, len(target_ids), len(processed_ids), retry_count, missing_count)

            if missing_rows:
                missing_report = self.save_missing_report(session_dir, missing_rows)
                self.stop_loading("Weryfikacja zakończona z brakami")
                self.result_count_var.set(
                    f"Pobrane: {len(processed_ids)} z {len(target_ids)} FV | Brakuje: {missing_count}"
                )
                self.log(f"[BŁĄD] Po weryfikacji nadal brakuje {missing_count} FV.")
                self.log(f"[INFO] Lista braków: {missing_report}")
                messagebox.showwarning(
                    "Niepełne pobranie",
                    f"Pobrano {len(processed_ids)} z {len(target_ids)} FV.\n\nBrakujące pozycje: {missing_count}\nLista braków została zapisana do pliku:\n{missing_report}"
                )
            else:
                self.stop_loading("Gotowe")
                self.result_count_var.set(
                    f"Pobrane: {len(processed_ids)} z {len(target_ids)} FV"
                )
                self.log(f"[OK] Koniec. Znalezione: {len(target_ids)}, pobrane: {len(processed_ids)}. Weryfikacja kompletności OK.")
                messagebox.showinfo(
                    "Sukces",
                    f"Pobieranie zakończone.\n\nZnalezione FV: {len(target_ids)}\nPobrane FV: {len(processed_ids)}\nWeryfikacja: OK\nFolder:\n{session_dir}"
                )

        except Exception as e:
            self.stop_loading("Błąd")
            self.log(f"[BŁĄD] Nie udało się wykonać pobierania: {e}")
            log_path = write_crash_log(self.base_dir, e)
            extra = f"\n\nLog błędu: {log_path}" if log_path else ""
            messagebox.showerror("Błąd", f"Nie udało się wykonać pobierania.\n\n{e}{extra}")

    def on_close(self):
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
        self.root.destroy()


if __name__ == "__main__":
    base_dir = resolve_base_dir()
    try:
        root = tk.Tk()
        app = KsefApp(root)
        root.mainloop()
    except Exception as e:
        log_path = write_crash_log(base_dir, e)
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Błąd startu programu",
                f"Program nie uruchomił się poprawnie.\n\n{e}\n\nLog błędu: {log_path}"
            )
            root.destroy()
        except Exception:
            pass
        raise
