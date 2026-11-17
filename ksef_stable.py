"""Stabilniejsze pobieranie faktur z Aplikacji Podatnika KSeF.

Warstwa GUI i uruchamianie Edge pozostaja w oryginalnym KsefApp.
Ta wersja kontroluje paginacje, pliki, ponowienia oraz bledy.
"""

import os
import re
import shutil
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

from selenium.webdriver.common.by import By

from ksef_app_selenium_edge_fix import (
    KsefApp,
    MAX_SCAN_PAGES,
    open_in_file_manager,
    write_crash_log,
)

MAX_BATCH = 10
MAX_BATCH_ATTEMPTS = 2
MAX_RETRY_PASSES = 2
PAGE_TIMEOUT = 9
DOWNLOAD_TIMEOUT = 120
NO_FILE_SIGNAL_TIMEOUT = 45
MAX_PDF_SIZE = 100 * 1024 * 1024
KSEF_ID_RE = re.compile(r"\b\d{10}-\d{8}-[A-Z0-9]+-[A-Z0-9]+\b", re.I)
PARTIAL_EXTENSIONS = (".crdownload", ".tmp", ".part")


def unique_destination(folder, filename):
    """Nie nadpisuj plikow o tej samej nazwie."""
    filename = Path(filename.replace("\\", "/")).name
    if not filename or filename in (".", ".."):
        raise ValueError("Niepoprawna nazwa pliku PDF")
    stem, suffix = os.path.splitext(filename)
    target = os.path.join(folder, filename)
    counter = 2
    while os.path.exists(target):
        target = os.path.join(folder, f"{stem}__{counter}{suffix}")
        counter += 1
    return target


def pdf_magic_ok(path):
    try:
        with open(path, "rb") as handle:
            return b"%PDF-" in handle.read(1024)
    except OSError:
        return False


class KsefStable(KsefApp):
    def __init__(self, root):
        self._busy = False
        self._pumping = False
        self._session_log_path = None
        self._first_signature = None
        self._batch_counter = 0
        super().__init__(root)
        self.root.title("KSeF - pobieranie faktur | EMERLOG")
        self.log("[INFO] Wersja z kontrola pobranych plikow jest gotowa.")

    def log(self, text):
        super().log(text)
        if self._session_log_path:
            try:
                with open(self._session_log_path, "a", encoding="utf-8") as handle:
                    handle.write(datetime.now().strftime("%H:%M:%S") + " " + str(text) + "\n")
            except OSError:
                pass

    def _sleep(self, seconds):
        """Odswiezaj Tkinter podczas przerw; blokada _busy zapobiega podwojnemu startowi."""
        end = time.monotonic() + max(0, seconds)
        while time.monotonic() < end:
            if not self._pumping:
                self._pumping = True
                try:
                    self.root.update()
                except Exception:
                    pass
                finally:
                    self._pumping = False
            time.sleep(min(0.08, max(0.01, end - time.monotonic())))

    def extract_item_key(self, text):
        text = self.normalize_text(text)
        match = KSEF_ID_RE.search(text)
        if match:
            return match.group(0).lower()
        return super().extract_item_key(text)

    def create_driver(self):
        driver = super().create_driver()
        driver.implicitly_wait(0.2)
        driver.set_page_load_timeout(60)
        return driver

    def start_browser(self):
        if self._busy:
            messagebox.showinfo("Pobieranie", "Pobieranie jest w toku.")
            return
        if self.driver is not None:
            try:
                _ = self.driver.current_window_handle
            except Exception:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None
        return super().start_browser()

    @staticmethod
    def _nav_selectors(direction):
        if direction == "next":
            return [
                (By.CSS_SELECTOR, "button[aria-label*='Następna']"),
                (By.CSS_SELECTOR, "button[title*='Następna']"),
                (By.CSS_SELECTOR, "button[aria-label*='Next']"),
                (By.CSS_SELECTOR, "button[title*='Next']"),
                (By.XPATH, "//button[contains(normalize-space(.),'Następna') or contains(normalize-space(.),'Next')]"),
            ]
        if direction == "prev":
            return [
                (By.CSS_SELECTOR, "button[aria-label*='Poprzednia']"),
                (By.CSS_SELECTOR, "button[title*='Poprzednia']"),
                (By.CSS_SELECTOR, "button[aria-label*='Previous']"),
                (By.CSS_SELECTOR, "button[title*='Previous']"),
                (By.XPATH, "//button[contains(normalize-space(.),'Poprzednia') or contains(normalize-space(.),'Previous')]"),
            ]
        return [
            (By.CSS_SELECTOR, "button[aria-label*='Pierwsza']"),
            (By.CSS_SELECTOR, "button[title*='Pierwsza']"),
            (By.CSS_SELECTOR, "button[aria-label*='First']"),
            (By.XPATH, "//button[contains(normalize-space(.),'Pierwsza') or contains(normalize-space(.),'First')]"),
        ]

    def _enabled_nav(self, direction):
        """Brak przycisku lub przycisk nieaktywny oznacza koniec listy."""
        for by, value in self._nav_selectors(direction):
            try:
                elements = self.driver.find_elements(by, value)
            except Exception:
                continue
            for element in elements:
                try:
                    if not element.is_displayed():
                        continue
                    if not element.is_enabled():
                        continue
                    if element.get_attribute("disabled") is not None:
                        continue
                    if element.get_attribute("aria-disabled") == "true":
                        continue
                    return element
                except Exception:
                    continue
        return None

    def _click_and_wait_for_page(self, button, old_signature):
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", button)
        except Exception:
            pass
        try:
            button.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", button)

        end = time.monotonic() + PAGE_TIMEOUT
        while time.monotonic() < end:
            sig = self.get_page_signature()
            if sig != "EMPTY" and sig != old_signature:
                return True
            self._sleep(0.15)
        return False

    def go_to_next_page(self):
        before = self.get_page_signature()
        button = self._enabled_nav("next")
        if button is None:
            return False
        for attempt in range(2):
            if self._click_and_wait_for_page(button, before):
                return True
            self.log(f"[UWAGA] Strona nie zmienila sie. Proba {attempt + 1}/2.")
            button = self._enabled_nav("next")
            if button is None:
                break
        raise RuntimeError("KSeF nie przelaczyl na nastepna strone. Przerwano, aby nie pominac faktur.")

    def go_to_first_page(self, max_steps=None):
        limit = MAX_SCAN_PAGES + 5
        current = self.get_page_signature()
        if current == "EMPTY":
            raise RuntimeError("Lista faktur nie jest zaladowana.")
        if self._first_signature and current == self._first_signature:
            return True

        first = self._enabled_nav("first")
        if first is not None:
            if self._click_and_wait_for_page(first, current):
                current = self.get_page_signature()
                if self._first_signature and current != self._first_signature:
                    raise RuntimeError("Przycisk pierwszej strony przeniosl w inne miejsce.")
                return True

        for _ in range(limit):
            button = self._enabled_nav("prev")
            if button is None:
                if self._first_signature and current != self._first_signature:
                    raise RuntimeError("Nie udalo sie wrocic do pierwszej strony listy FV.")
                return True
            if not self._click_and_wait_for_page(button, current):
                raise RuntimeError("KSeF nie cofnal strony. Pobieranie nie zostanie uruchomione od zlej strony.")
            current = self.get_page_signature()
            if self._first_signature and current == self._first_signature:
                return True
        raise RuntimeError(f"Nie osiagnieto pierwszej strony po {limit} przejsciach.")

    def scan_manifest(self):
        self._first_signature = None
        self.go_to_first_page()
        all_rows, seen_ids, seen_pages = [], set(), set()
        page_count = 0

        while page_count < MAX_SCAN_PAGES:
            rows = self.get_current_page_rows()
            signature = self.get_page_signature()
            if not rows or signature == "EMPTY":
                raise RuntimeError("KSeF nie zaladowal listy FV podczas skanowania.")
            if signature in seen_pages:
                raise RuntimeError("Podczas skanowania wykryto powtorzenie strony.")
            if page_count == 0:
                self._first_signature = signature
            seen_pages.add(signature)
            page_count += 1

            for row in rows:
                key = row["row_id"]
                if key not in seen_ids:
                    seen_ids.add(key)
                    all_rows.append({"row_id": key, "text": row["text"]})

            self.found_var.set(str(len(seen_ids)))
            self.log(f"[INFO] Skanowanie: strona {page_count}, faktur {len(seen_ids)}.")
            self.update_progress(page_count, page_count + 1, "Skanowanie listy")
            if not self.go_to_next_page():
                break
        else:
            if self._enabled_nav("next") is not None:
                raise RuntimeError(f"Lista przekracza limit {MAX_SCAN_PAGES} stron; skanowanie przerwane.")

        self.go_to_first_page()
        if self.get_page_signature() != self._first_signature:
            raise RuntimeError("Po skanowaniu nie udalo sie wrocic na strone 1.")
        self.log("[OK] Skan zakonczony. Jestesmy na pierwszej stronie.")
        return all_rows

    def wait_for_new_download(self, folder, before_files, timeout=DOWNLOAD_TIMEOUT):
        start = time.monotonic()
        unchanged_size = {}
        had_signal = False
        last_notice = 0
        while time.monotonic() - start < timeout:
            try:
                names = os.listdir(folder)
            except OSError:
                names = []
            partials = [name for name in names if name.lower().endswith(PARTIAL_EXTENSIONS)]
            if partials:
                had_signal = True
            candidates = []
            for name in names:
                if name in before_files or not name.lower().endswith((".pdf", ".zip")):
                    continue
                path = os.path.join(folder, name)
                if os.path.isfile(path):
                    candidates.append(path)
            if candidates:
                had_signal = True
                path = max(candidates, key=os.path.getmtime)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    size = 0
                if size > 0 and not partials:
                    prev, count = unchanged_size.get(path, (-1, 0))
                    count = count + 1 if prev == size else 0
                    unchanged_size[path] = (size, count)
                    if count >= 2:
                        return path

            elapsed = int(time.monotonic() - start)
            if elapsed - last_notice >= 15:
                last_notice = elapsed
                self.set_step(f"Czekam na plik z KSeF ({elapsed} s)")
            if elapsed >= NO_FILE_SIGNAL_TIMEOUT and not had_signal:
                self.log(f"[UWAGA] Brak pliku przez {elapsed} s. Ponowie pobieranie.")
                return None
            self._sleep(0.25)
        self.log(f"[UWAGA] Przekroczony czas pobierania ({timeout} s).")
        return None

    def _click_visible(self, candidates, timeout=3):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            for by, value in candidates:
                try:
                    elements = self.driver.find_elements(by, value)
                except Exception:
                    elements = []
                for el in elements:
                    try:
                        if not el.is_displayed() or not el.is_enabled():
                            continue
                        if el.get_attribute("aria-disabled") == "true":
                            continue
                        try:
                            el.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", el)
                        return True
                    except Exception:
                        continue
            self._sleep(0.12)
        return False

    def set_download_directory(self, path):
        path = os.path.abspath(path)
        os.makedirs(path, exist_ok=True)
        for command in ("Page.setDownloadBehavior", "Browser.setDownloadBehavior"):
            try:
                self.driver.execute_cdp_cmd(command, {"behavior": "allow", "downloadPath": path})
                return
            except Exception:
                pass
        raise RuntimeError("Nie udalo sie ustawic folderu pobierania w Edge.")

    def try_download_selected(self, session_dir):
        self.set_download_directory(session_dir)
        before = set(os.listdir(session_dir))
        open_menu = [
            (By.XPATH, "//button[contains(normalize-space(.),'Pobierz')]"),
            (By.XPATH, "//*[@role='button' and contains(normalize-space(.),'Pobierz')]"),
            (By.XPATH, "//button[contains(normalize-space(.),'Eksportuj')]"),
        ]
        if not self._click_visible(open_menu, timeout=3):
            self.log("[UWAGA] Nie znaleziono przycisku Pobierz.")
            return None
        pdf_option = [
            (By.XPATH, "//*[@role='menuitem' and contains(normalize-space(.),'PDF')]"),
            (By.XPATH, "//button[normalize-space(.)='PDF']"),
            (By.XPATH, "//*[normalize-space(.)='PDF']"),
        ]
        zip_option = [
            (By.XPATH, "//*[@role='menuitem' and contains(normalize-space(.),'ZIP')]"),
            (By.XPATH, "//*[normalize-space(.)='ZIP']"),
        ]
        if not self._click_visible(pdf_option, timeout=3):
            if not self._click_visible(zip_option, timeout=2):
                # Niektore wersje KSeF uruchamiaja pobieranie bez osobnego menu.
                return self.wait_for_new_download(session_dir, before, timeout=10)
        return self.wait_for_new_download(session_dir, before)

    @staticmethod
    def _selected(checkbox):
        try:
            return checkbox.is_selected() or checkbox.get_attribute("aria-checked") == "true"
        except Exception:
            return False

    def _selected_ids(self):
        return {
            row["row_id"] for row in self.get_current_page_rows()
            if self._selected(row["checkbox"])
        }

    def _verify_and_store(self, file_path, session_dir, expected_ids):
        """Zaliczenie paczki tylko po weryfikacji wszystkich PDF."""
        expected_ids = set(expected_ids)
        if not file_path or not os.path.isfile(file_path):
            return False
        try:
            with tempfile.TemporaryDirectory(prefix=".ksef_stage_", dir=session_dir) as stage:
                staged = []
                if zipfile.is_zipfile(file_path):
                    with zipfile.ZipFile(file_path) as archive:
                        entries = [
                            info for info in archive.infolist()
                            if not info.is_dir() and info.filename.lower().endswith(".pdf")
                        ]
                        if len(entries) != len(expected_ids):
                            self.log(f"[UWAGA] Paczka: {len(entries)} PDF zamiast {len(expected_ids)}. Ponawiam.")
                            return False
                        if any(info.file_size > MAX_PDF_SIZE for info in entries):
                            self.log("[UWAGA] Jeden z plikow PDF przekracza dozwolony rozmiar.")
                            return False
                        for idx, info in enumerate(entries):
                            target = os.path.join(stage, f"{idx:03d}.pdf")
                            with archive.open(info) as src, open(target, "wb") as dst:
                                shutil.copyfileobj(src, dst, length=1024 * 1024)
                            staged.append((info.filename, target))
                elif file_path.lower().endswith(".pdf") and len(expected_ids) == 1:
                    target = os.path.join(stage, "000.pdf")
                    shutil.copy2(file_path, target)
                    staged.append((os.path.basename(file_path), target))
                else:
                    self.log("[UWAGA] KSeF zwrocil niewlasciwy format pliku.")
                    return False

                if len(staged) != len(expected_ids) or not all(pdf_magic_ok(path) for _, path in staged):
                    self.log("[UWAGA] Pobrane dane nie zawieraja kompletnego PDF.")
                    return False

                file_ids = []
                for filename, _ in staged:
                    match = KSEF_ID_RE.search(filename)
                    file_ids.append(match.group(0).lower() if match else None)
                recognized = [i for i in file_ids if i is not None]
                if recognized and (len(recognized) != len(expected_ids) or set(recognized) != expected_ids):
                    self.log("[UWAGA] Numery KSeF w plikach nie zgadzaja sie z zaznaczonymi FV.")
                    return False
                if not recognized:
                    self.log("[INFO] Nazwy PDF nie zawieraja numerow KSeF - sprawdzono format i liczbe plikow.")

                for filename, src in staged:
                    dest = unique_destination(session_dir, filename)
                    shutil.move(src, dest)
            try:
                os.remove(file_path)
            except OSError:
                pass
            return True
        except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError, ValueError) as exc:
            self.log(f"[UWAGA] Nie udalo sie sprawdzic paczki: {exc}")
            return False

    def _download_batch(self, batch_ids, session_dir):
        batch_ids = list(batch_ids)
        self._batch_counter += 1
        batch_no = self._batch_counter
        expected = set(batch_ids)

        for attempt in range(1, MAX_BATCH_ATTEMPTS + 1):
            self.set_step(f"Paczka {batch_no}: {len(batch_ids)} FV ({attempt}/{MAX_BATCH_ATTEMPTS})")
            self.clear_all_visible_checkboxes()
            rows = {row["row_id"]: row for row in self.get_current_page_rows()}
            for key in batch_ids:
                item = rows.get(key)
                if item is None or not self.click_checkbox(item["checkbox"]):
                    self.log(f"[UWAGA] Nie udalo sie zaznaczyc FV: {key}")

            actual = self._selected_ids()
            if actual != expected:
                self.log(f"[UWAGA] Wybrane FV nie zgadzaja sie z paczka: {len(actual)}/{len(expected)}.")
            else:
                self.log(f"[INFO] Pobieram paczke {batch_no}: {len(expected)} FV.")
                path = self.try_download_selected(session_dir)
                if path and self._verify_and_store(path, session_dir, batch_ids):
                    self.clear_all_visible_checkboxes()
                    self.log(f"[OK] Paczka {batch_no}: pobrano {len(expected)} FV.")
                    return expected
                self.log(f"[UWAGA] Paczka {batch_no} nie powiodla sie.")

            self.clear_all_visible_checkboxes()
            if attempt < MAX_BATCH_ATTEMPTS:
                self._sleep(2)

        if len(batch_ids) > 1:
            middle = (len(batch_ids) + 1) // 2
            self.log(f"[INFO] Dziele paczke {batch_no} na mniejsze.")
            left = self._download_batch(batch_ids[:middle], session_dir)
            right = self._download_batch(batch_ids[middle:], session_dir)
            return left | right

        self.log(f"[BŁĄD] Nie pobrano FV: {batch_ids[0]}")
        return set()

    def process_pages_for_ids(self, target_ids, target_map, session_dir, already_processed=None):
        target_ids = set(target_ids)
        processed = set(already_processed or ())
        self.go_to_first_page()
        seen_pages = set()

        while len(seen_pages) < MAX_SCAN_PAGES:
            rows = self.get_current_page_rows()
            signature = self.get_page_signature()
            if not rows or signature == "EMPTY":
                raise RuntimeError("Podczas pobierania lista KSeF nie zaladowala sie.")
            if signature in seen_pages:
                raise RuntimeError("KSeF pokazal ponownie te sama strone podczas pobierania.")
            seen_pages.add(signature)

            page_ids = [row["row_id"] for row in rows if row["row_id"] in target_ids and row["row_id"] not in processed]
            self.log(f"[INFO] Pobieranie: strona {len(seen_pages)}, do pobrania {len(page_ids)} FV.")
            for offset in range(0, len(page_ids), MAX_BATCH):
                batch_ids = page_ids[offset:offset + MAX_BATCH]
                completed = self._download_batch(batch_ids, session_dir)
                processed.update(completed)
                self.downloaded_var.set(str(len(processed)))
                self.update_progress(len(processed), max(1, len(target_map)), "Pobieranie faktur")

            if target_ids.issubset(processed):
                break
            if not self.go_to_next_page():
                break
        else:
            if self._enabled_nav("next") is not None:
                raise RuntimeError(f"Przekroczono limit {MAX_SCAN_PAGES} stron podczas pobierania.")

        missing = [target_map[key] for key in target_map if key in target_ids and key not in processed]
        return processed, missing

    def download_invoices(self):
        if self._busy:
            messagebox.showinfo("Pobieranie", "Pobieranie juz trwa.")
            return
        if self.driver is None:
            messagebox.showwarning("Uwaga", "Najpierw otworz KSeF w Edge.")
            return

        self._busy = True
        session_dir = None
        manifest = []
        processed = set()
        retry_count = 0

        try:
            session_dir = self.create_session_folder()
            self._session_log_path = os.path.join(session_dir, "run_log.txt")
            self.log("[INFO] Rozpoczynam skanowanie listy FV.")
            self.start_loading("Skanowanie listy FV", mode="pulse")

            manifest = self.scan_manifest()
            if not manifest:
                raise RuntimeError("Lista KSeF nie zawiera faktur.")
            target_map = {row["row_id"]: row for row in manifest}
            target_ids = set(target_map)
            self.result_count_var.set(f"Na liscie: {len(target_ids)} FV")
            self.log(f"[OK] Znaleziono {len(target_ids)} FV. Start od strony 1.")

            processed, missing = self.process_pages_for_ids(target_ids, target_map, session_dir)
            while missing and retry_count < MAX_RETRY_PASSES:
                retry_count += 1
                missing_ids = {row["row_id"] for row in missing}
                self.log(f"[INFO] Ponawiam {len(missing_ids)} brakujacych FV ({retry_count}/{MAX_RETRY_PASSES}).")
                processed, missing = self.process_pages_for_ids(missing_ids, target_map, session_dir, processed)

            pdf_count = sum(1 for filename in os.listdir(session_dir) if filename.lower().endswith(".pdf"))
            self.write_session_info(session_dir, len(target_ids), len(processed), retry_count, len(missing))
            self.log(f"[INFO] Plikow PDF na dysku: {pdf_count}, potwierdzonych FV: {len(processed)}.")
            if pdf_count < len(processed):
                raise RuntimeError("Liczba zapisanych PDF jest mniejsza niz liczba potwierdzonych FV.")
            if missing:
                report = self.save_missing_report(session_dir, missing)
                self.stop_loading("Pobieranie zakonczone z brakami")
                self.result_count_var.set(f"Pobrano: {len(processed)}/{len(target_ids)}, brakuje {len(missing)}")
                self.log(f"[UWAGA] Brakuje {len(missing)} FV. Raport: {report}")
                messagebox.showwarning("Niepelne pobieranie", f"Pobrano {len(processed)}/{len(target_ids)} FV.\nLista brakow:\n{report}")
            else:
                self.stop_loading("Gotowe")
                self.result_count_var.set(f"Pobrano: {len(processed)}/{len(target_ids)} FV")
                self.log(f"[OK] Pobrano komplet: {len(processed)}/{len(target_ids)} FV.")
                messagebox.showinfo("Gotowe", f"Pobrano {len(processed)} FV.\nFolder:\n{session_dir}")
        except Exception as exc:
            self.stop_loading("Blad")
            self.log(f"[BŁĄD] {exc}")
            if session_dir:
                try:
                    if manifest:
                        target_map = {row["row_id"]: row for row in manifest}
                        missing = [row for key, row in target_map.items() if key not in processed]
                        self.save_missing_report(session_dir, missing)
                        self.write_session_info(session_dir, len(target_map), len(processed), retry_count, len(missing))
                except Exception:
                    pass
            log_path = write_crash_log(self.base_dir, exc)
            messagebox.showerror("Blad pobierania", f"{exc}\n\nLog: {self._session_log_path or log_path}")
        finally:
            self._session_log_path = None
            self._busy = False

    def on_close(self):
        if self._busy:
            messagebox.showinfo("Pobieranie", "Pobieranie trwa. Zamknij program po zakonczeniu.")
            return
        return super().on_close()


def main():
    import tkinter as tk
    root = tk.Tk()
    KsefStable(root)
    root.mainloop()


if __name__ == "__main__":
    main()
