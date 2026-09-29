"""Regression coverage for GitHub issues #11, #14, #15, #16 and #17."""
import ast
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IssueRegressionTests(unittest.TestCase):
    def test_account_save_does_not_require_os_fchmod(self):
        account = load("account_no_fchmod", CORE / "account.py")
        real_os = account.os

        class OSProxy:
            path = real_os.path
            fdopen = staticmethod(real_os.fdopen)
            fsync = staticmethod(real_os.fsync)
            replace = staticmethod(real_os.replace)
            close = staticmethod(real_os.close)

        account.os = OSProxy()
        with tempfile.TemporaryDirectory() as directory:
            store = account.Store(directory)
            store.save({"token": "test-only"})
            self.assertEqual(store.load()["token"], "test-only")

    def test_account_save_retries_transient_replace_error(self):
        account = load("account_replace_retry", CORE / "account.py")
        real_replace = account.os.replace
        attempts = []

        def flaky_replace(source, target):
            attempts.append(1)
            if len(attempts) == 1:
                raise PermissionError("sharing violation")
            return real_replace(source, target)

        with tempfile.TemporaryDirectory() as directory:
            store = account.Store(directory)
            with patch.object(account.os, "replace", side_effect=flaky_replace),                  patch.object(account.time, "sleep"):
                store.save({"token": "test-only"})
            self.assertEqual(len(attempts), 2)
            self.assertEqual(store.load()["token"], "test-only")

    def test_home_catalogs_fall_back_when_threads_cannot_start(self):
        catalogs = load("home_catalogs_thread_fallback", ROOT / "lib/home_catalogs.py")
        addons = [{
            "transportUrl": "https://example.org/manifest.json",
            "manifest": {"catalogs": [
                {"id": "one", "name": "One", "type": "movie"},
                {"id": "two", "name": "Two", "type": "series"},
            ]}
        }]

        class BrokenPool:
            def __init__(self, *args, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def map(self, *args, **kwargs):
                raise RuntimeError("can't start new thread")

        with patch.object(catalogs, "ThreadPoolExecutor", BrokenPool):
            rows = catalogs.load_rows(
                addons,
                lambda url: {"metas": [{"id": url, "name": "Title"}]},
                lambda url, resource, kind, identity: identity,
            )
        self.assertEqual([row["catalog_id"] for row in rows], ["one", "two"])
        self.assertFalse(any(row["failed"] for row in rows))

    def test_episode_cards_show_code_title_and_metadata_pills(self):
        tree = ET.parse(ROOT / "resources/skins/Main/1080i/script-stremio-info.xml")
        episodes = tree.find('.//control[@id="501"]')
        self.assertIsNotNone(episodes)
        xml = ET.tostring(episodes, encoding="unicode")
        for prop in ("episode_heading", "episode_runtime", "episode_imdb", "episode_date"):
            self.assertIn("ListItem.Property({})".format(prop), xml)
        self.assertIn("ratings/imdb.png", xml)
        self.assertIn('colordiffuse="99171920"', xml)

        source = (ROOT / "lib/nimbus.py").read_text(encoding="utf-8")
        for prop in ("episode_heading", "episode_runtime", "episode_imdb", "episode_date"):
            self.assertIn("setProperty('{}'".format(prop), source)

    def test_episode_card_metadata_formatters(self):
        # Load only the helper functions so the test stays Kodi-independent.
        source = (ROOT / "lib/nimbus.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        names = {"episode_runtime", "episode_rating", "episode_date"}
        functions = [node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name in names]
        scope = {
            "re": __import__("re"),
            "_MONTHS": ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
        }
        exec(compile(ast.Module(body=functions, type_ignores=[]), "<episode-formatters>", "exec"), scope)
        self.assertEqual(scope["episode_runtime"]("65 min"), "1h 5m")
        self.assertEqual(scope["episode_runtime"]("PT58M"), "58m")
        self.assertEqual(scope["episode_rating"]({"imdbRating": "8.2"}), "8.2")
        self.assertEqual(scope["episode_date"]({"released": "2019-12-20T00:00:00.000Z"}), "20 Dec 2019")

    def test_runtime_seconds_formats(self):
        metadata_bridge = load("metadata_bridge", CORE / "metadata_bridge.py")
        fn = metadata_bridge.runtime_seconds
        self.assertEqual(fn("65 min"), 3900)
        self.assertEqual(fn("PT58M"), 3480)
        self.assertEqual(fn("PT1H30M"), 5400)
        self.assertEqual(fn("PT1H30M15S"), 5415)
        self.assertEqual(fn("1h 30m"), 5400)
        self.assertEqual(fn("2 hours 15 mins"), 8100)
        self.assertEqual(fn("45m"), 2700)
        self.assertEqual(fn(5400), 5400)
        self.assertEqual(fn(90), 5400)
        self.assertEqual(fn("90"), 5400)
        self.assertEqual(fn(""), 0)
        self.assertEqual(fn(None), 0)

    def test_sources_collect_thread_fallback(self):
        sources = load("sources_thread_fallback", CORE / "sources.py")
        providers = [{
            "transportUrl": "https://example.org/manifest.json",
            "manifest": {
                "name": "Test",
                "types": ["movie"],
                "resources": ["stream"],
            }
        }]

        class BrokenPool:
            def __init__(self, *args, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def map(self, *args, **kwargs):
                raise RuntimeError("can't start new thread")

        with patch.object(sources, "ThreadPoolExecutor", BrokenPool):
            rows, skipped, failed = sources.collect(
                providers, "movie", "tt123",
                fetcher=lambda url: {"streams": [{"url": "https://example.org/play.mkv"}]}
            )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["url"], "https://example.org/play.mkv")

    def test_subtitles_collect_thread_fallback(self):
        subtitles = load("subtitles_thread_fallback", CORE / "subtitles.py")
        providers = [{
            "transportUrl": "https://example.org/manifest.json",
            "manifest": {
                "types": ["movie"],
                "resources": ["subtitles"],
            }
        }]

        class BrokenPool:
            def __init__(self, *args, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def map(self, *args, **kwargs):
                raise RuntimeError("can't start new thread")

        with patch.object(subtitles, "ThreadPoolExecutor", BrokenPool):
            results = subtitles.collect_subtitles(
                providers, "movie", "tt123", ["eng"], "eng",
                fetcher=lambda url: {"subtitles": [{"url": "https://example.org/sub.srt", "lang": "eng"}]}
            )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["lang"], "eng")

    def test_metadata_bridge_thread_fallback(self):
        meta_bridge = load("meta_bridge_fallback", CORE / "metadata_bridge.py")
        providers = [{
            "transportUrl": "https://example.org/manifest.json",
            "manifest": {
                "types": ["movie"],
                "resources": ["meta"],
            }
        }]

        class BrokenPool:
            def __init__(self, *args, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def map(self, *args, **kwargs):
                raise RuntimeError("can't start new thread")

        with patch.object(meta_bridge, "ThreadPoolExecutor", BrokenPool):
            merged = meta_bridge.merged_meta(
                "movie", "tt123", providers,
                fetcher=lambda url: {"meta": {"id": "tt123", "name": "Fallback Title"}}
            )
        self.assertEqual(merged["name"], "Fallback Title")

    def test_button_label_safe_without_underscore_id(self):
        cont = load("continue_playback", CORE / "continue_playback.py")
        self.assertEqual(cont.button_label({"id": "tt123", "type": "series", "state": {"video_id": "tt123:1:2"}}), "Play Season 1: Episode 2")
        self.assertEqual(cont.button_label({"type": "movie"}), "Play")

    def test_account_store_utf8_roundtrip(self):
        account = load("account_utf8", CORE / "account.py")
        with tempfile.TemporaryDirectory() as directory:
            store = account.Store(directory)
            special_data = {"token": "test-token", "title": "Amélie — ñoño — 映画 — 🎬"}
            store.save(special_data)
            self.assertEqual(store.load(), special_data)

    def test_disk_cache_indexes_and_wal(self):
        from lib.disk_cache import DiskCache
        with tempfile.TemporaryDirectory() as directory:
            cache = DiskCache(directory)
            with cache.connect() as db:
                indexes = [r[1] for r in db.execute("PRAGMA index_list('responses')").fetchall()]
                self.assertIn("idx_responses_expires", indexes)
                self.assertIn("idx_responses_used", indexes)


if __name__ == "__main__":
    unittest.main()
