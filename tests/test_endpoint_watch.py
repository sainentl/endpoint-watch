import contextlib
import io
import json
import socket
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from endpoint_watch.__main__ import check_url, main


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/slow":
            time.sleep(0.15)
        if self.path in {"/redirect", "/loop"}:
            self.send_response(302)
            self.send_header("Location", "/ok" if self.path == "/redirect" else "/loop")
        else:
            self.send_response({"/ok": 204, "/slow": 204, "/fail": 503}.get(self.path, 404))
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format, *args):
        pass


class EndpointWatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_success_and_redirect(self):
        for path in ("/ok", "/redirect"):
            with self.subTest(path=path):
                result = check_url(self.base + path)
                self.assertTrue(result.ok)
                self.assertEqual(result.status_code, 204)
                self.assertEqual(result.final_url, self.base + "/ok")
                self.assertIsNone(result.error)
                self.assertGreaterEqual(result.elapsed_ms, 0)

    def test_http_errors_are_results(self):
        for path, status in (("/fail", 503), ("/missing", 404)):
            with self.subTest(path=path):
                result = check_url(self.base + path)
                self.assertFalse(result.ok)
                self.assertEqual(result.status_code, status)
                self.assertIn(str(status), result.error)

    def test_redirect_loop_is_unhealthy(self):
        result = check_url(self.base + "/loop")
        self.assertFalse(result.ok)
        self.assertEqual(result.status_code, 302)
        self.assertIsNotNone(result.error)

    def test_connection_refused(self):
        with socket.socket() as unused:
            unused.bind(("127.0.0.1", 0))
            result = check_url(f"http://127.0.0.1:{unused.getsockname()[1]}", timeout=0.5)
        self.assertFalse(result.ok)
        self.assertIsNone(result.status_code)
        self.assertIsNotNone(result.error)

    def test_timeout(self):
        result = check_url(self.base + "/slow", timeout=0.02)
        self.assertFalse(result.ok)
        self.assertIsNone(result.status_code)
        self.assertIsNotNone(result.error)

    def test_json_report_and_failure_exit_code(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main([self.base + "/ok", self.base + "/fail", "--json"])
        report = json.loads(output.getvalue())
        self.assertEqual(code, 1)
        self.assertEqual(report["summary"], {"total": 2, "healthy": 1, "unhealthy": 1})
        self.assertEqual([item["ok"] for item in report["results"]], [True, False])
        self.assertEqual(report["results"][0]["url"], self.base + "/ok")

    def test_text_report_and_success_exit_code(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main([self.base + "/ok"])
        self.assertEqual(code, 0)
        self.assertIn("OK " + self.base + "/ok", output.getvalue())
        self.assertIn("1/1 healthy", output.getvalue())

    def test_invalid_urls_are_rejected_before_network_access(self):
        invalid = [
            "file:///etc/hosts", "ftp://example.com", "http://", "https://a:99999/",
            "https://a:0/", "http://exa mple.com", "http://a/\npath",
            "https://user:password@example.com/", "http://[broken", "https://例子.测试/",
        ]
        for value in invalid:
            with self.subTest(value=value), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main([self.base + "/ok", value])
                self.assertEqual(raised.exception.code, 2)

    def test_invalid_timeouts(self):
        for value in ("0", "-1", "nan", "inf", "abc", "86401", "1e100"):
            with self.subTest(value=value), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main([self.base + "/ok", "--timeout=" + value])
                self.assertEqual(raised.exception.code, 2)

    def test_missing_url(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            main([])
        self.assertEqual(raised.exception.code, 2)

    def test_version(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(output.getvalue().strip(), "endpoint-watch 0.1.0")


if __name__ == "__main__":
    unittest.main()
