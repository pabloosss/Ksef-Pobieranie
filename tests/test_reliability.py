import os
import tempfile
import unittest
import zipfile

from ksef_stable import KsefStable, pdf_magic_ok, unique_destination


PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
ID_A = "1234567890-20261117-AABBCC-DD"
ID_B = "1234567890-20261117-112233-AA"


def app_stub():
    app = KsefStable.__new__(KsefStable)
    app._first_signature = None
    app._completed_ids = set()
    app._batch_counter = 0
    app.log = lambda message: None
    app.set_step = lambda message: None
    app._sleep = lambda sec: None
    return app


class DownloadIntegrityTests(unittest.TestCase):
    def test_pdf_magic(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "one.pdf")
            with open(path, "wb") as out:
                out.write(PDF)
            self.assertTrue(pdf_magic_ok(path))
            with open(path, "wb") as out:
                out.write(b"not a PDF")
            self.assertFalse(pdf_magic_ok(path))

    def test_unique_destination_preserves_old_pdf(self):
        with tempfile.TemporaryDirectory() as folder:
            old = os.path.join(folder, "invoice.pdf")
            with open(old, "wb") as out:
                out.write(PDF)
            next_file = unique_destination(folder, "../invoice.pdf")
            self.assertEqual(os.path.basename(next_file), "invoice__2.pdf")
            self.assertTrue(os.path.isfile(old))

    def test_zip_count_must_match_selected_invoices(self):
        app = app_stub()
        with tempfile.TemporaryDirectory() as folder:
            archive = os.path.join(folder, "download.zip")
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr(f"{ID_A}.pdf", PDF)
            self.assertFalse(app._verify_and_store(archive, folder, [ID_A, ID_B]))
            self.assertFalse(os.path.exists(os.path.join(folder, f"{ID_A}.pdf")))

    def test_reject_wrong_ksef_id_even_if_count_matches(self):
        app = app_stub()
        with tempfile.TemporaryDirectory() as folder:
            archive = os.path.join(folder, "download.zip")
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr(f"{ID_A}.pdf", PDF)
            self.assertFalse(app._verify_and_store(archive, folder, [ID_B]))

    def test_successful_zip_extracts_exactly_two_pdfs(self):
        app = app_stub()
        with tempfile.TemporaryDirectory() as folder:
            archive = os.path.join(folder, "download.zip")
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr(f"nested/{ID_A}.pdf", PDF)
                zf.writestr(f"nested/{ID_B}.pdf", PDF)
            self.assertTrue(app._verify_and_store(archive, folder, [ID_A.lower(), ID_B.lower()]))
            self.assertFalse(os.path.exists(archive))
            self.assertEqual(len([name for name in os.listdir(folder) if name.endswith(".pdf")]), 2)

    def test_reject_non_pdf_zip_payload(self):
        app = app_stub()
        with tempfile.TemporaryDirectory() as folder:
            archive = os.path.join(folder, "download.zip")
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr(f"{ID_A}.pdf", b"this is not a pdf")
            self.assertFalse(app._verify_and_store(archive, folder, [ID_A]))


class PageNavigationTests(unittest.TestCase):
    def test_go_to_first_page_after_sixty_one_pages(self):
        app = app_stub()
        state = {"page": 61}
        app._first_signature = "page1"
        app.get_page_signature = lambda: f"page{state['page']}"
        app._enabled_nav = lambda d: None if d == "first" or (d == "prev" and state["page"] == 1) else "previous"
        def navigate(button, old):
            state["page"] -= 1
            return True
        app._click_and_wait_for_page = navigate
        self.assertTrue(app.go_to_first_page())
        self.assertEqual(state["page"], 1)

    def test_scan_sixty_one_pages_returns_to_first(self):
        app = app_stub()
        state = {"page": 1}
        app.found_var = type("Var", (), {"set": lambda self, x: None})()
        app.update_progress = lambda *args: None
        app.go_to_first_page = lambda: state.update(page=1)
        app.get_page_signature = lambda: f"page{state['page']}"
        app.get_current_page_rows = lambda: [{"row_id": f"invoice-{state['page']}", "text": f"invoice-{state['page']}"}]
        def next_page():
            if state["page"] == 61:
                return False
            state["page"] += 1
            return True
        app.go_to_next_page = next_page
        result = app.scan_manifest()
        self.assertEqual(len(result), 61)
        self.assertEqual(state["page"], 1)
        self.assertEqual(app._first_signature, "page1")

    def test_failed_page_change_is_error_not_end_of_list(self):
        app = app_stub()
        app.get_page_signature = lambda: "page34"
        app._enabled_nav = lambda d: "next"
        app._click_and_wait_for_page = lambda button, old: False
        with self.assertRaises(RuntimeError):
            app.go_to_next_page()

    def test_retry_pass_does_not_skip_when_previous_total_is_large(self):
        app = app_stub()
        app.go_to_first_page = lambda: True
        app.get_current_page_rows = lambda: [{"row_id": "new", "text": "new"}]
        app.get_page_signature = lambda: "page1"
        called = []
        def batch(ids, session):
            called.extend(ids)
            return set(ids)
        app._download_batch = batch
        app._save_checkpoint = lambda folder: None
        app.go_to_next_page = lambda: False
        app.downloaded_var = type("Var", (), {"set": lambda self, x: None})()
        app.update_progress = lambda *args: None
        processed, missing = app.process_pages_for_ids({"new"}, {"new": {"row_id": "new"}}, ".", already_processed={"old1", "old2"})
        self.assertEqual(called, ["new"])
        self.assertEqual(processed, {"old1", "old2", "new"})
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
