"""Tests for the Open-source contributions table: text from other repos must stay inert.

    python3 -I -m unittest discover -s scripts -p 'test_*.py'
"""
import copy
import json
import re
import unittest

import upstream

HOSTILE = [
    "<img src=x onerror=1>",
    "[click](https://evil.example)",
    "![p](https://t.example/p.png)",
    "**bold** | pipe",
    "<a href=\"https://evil.example\">x</a> www.evil.example https://evil.example/a_b",
    "# heading\nsecond `code` line @someone ~~gone~~",
    "`<img src=x onerror=1>` and `[c](https://evil.example)` and `a|b` and ` stray",
    "x" * 500,
]


def outside_code(text):
    """GitHub shows code spans literally, so only the text outside them can be live."""
    text = re.sub(r"(?<!\\)`[^`]+`", "", text)
    return text.replace("<span>@</span>", "@").replace("<span>$</span>", "$")


def fake(title):
    cfg = {"projects": {}, "pull_requests": [], "issues": {}, "hide": [],
           "curated_until": "2000-01-01", "max_bullets": 5}
    data = {"user": "me",
            "repos": {"o/r": {"stars": "1.5K", "about": title},
                      "o/q": {"stars": "0", "about": ""}},
            "pull_requests": [
                {"key": "o/r#1", "url": "https://github.com/o/r/pull/1", "title": title,
                 "created": "2026-01-01", "state": "MERGED", "draft": False,
                 "merged": "2026-01-02", "fixes": []},
                {"key": "o/q#2", "url": "https://github.com/o/q/pull/2) ![x](https://t.example/p.png",
                 "title": "open", "created": "2026-01-03", "state": "OPEN", "draft": False,
                 "merged": "", "fixes": []}],
            "issues": [{"key": "o/r#3", "url": "https://github.com/o/r/issues/3", "title": title,
                        "created": "2026-01-01", "state": "CLOSED", "reason": "COMPLETED"}]}
    return cfg, data


class Safe(unittest.TestCase):
    def test_nothing_live_survives(self):
        for text in HOSTILE:
            out = upstream.safe(text)
            self.assertNotIn("\n", out)
            self.assertLessEqual(len(out), upstream.MAX_TEXT * 2, text)
            self.assertIsNone(re.search(r"(?<!\\)\|", out), out)  # no pipe breaks the table, even in code
            live = outside_code(out)
            self.assertNotIn("<", live, text)
            self.assertIsNone(re.search(r"(?<!\\)[\[\]`*]", live), live)
            self.assertIsNone(re.search(r"(?<!\\)\]\(", live), live)
            self.assertNotIn("://", live)

    def test_code_spans_stay_code(self):
        self.assertEqual(upstream.safe("Fix `Index` and `a|b`"), "Fix `Index` and `a\\|b`")
        self.assertEqual(upstream.safe("`<b>x</b>` [y](z)"), "`<b>x</b>` \\[y\\]\\(z\\)")
        self.assertEqual(upstream.safe("one ` stray"), "one \\` stray")
        # an escaped pipe in the source stays one cell: GitHub reads `\\|` in a table as `\|`
        self.assertEqual(upstream.safe("`a\\|b`"), "`a\\\\|b`")

    def test_invisible_and_math_characters(self):
        self.assertEqual(upstream.safe("a‎b‏c؜d​e‮f"), "abcdef")
        self.assertEqual(upstream.safe("costs $x^2$ @me"), "costs <span>$</span>x^2<span>$</span> <span>@</span>me")

    def test_cap(self):
        out = upstream.safe("x" * 500)
        self.assertEqual(out, "x" * 119 + "…")
        self.assertEqual(upstream.safe("short"), "short")

    def test_plain_titles_look_the_same(self):
        self.assertEqual(upstream.safe("Fix the parser, 100% faster"), "Fix the parser, 100% faster")

    def test_trusted_text_keeps_markdown(self):
        self.assertEqual(upstream.cell("subclass `from_dict` | x"), "subclass `from_dict` \\| x")


class Render(unittest.TestCase):
    def test_hostile_values_are_inert_everywhere(self):
        for text in HOSTILE:
            out = upstream.render(*fake(text))
            body = out.split("\n")
            table = [l for l in body if l.startswith("|")]
            self.assertEqual(len(table), 3)  # header, separator, one project row
            for line in table:  # the row must still have exactly 3 cells
                self.assertEqual(len(re.split(r"(?<!\\)\|", line.strip())) - 2, 3, line)
            live = outside_code(out)
            # the only raw tag is the 16px avatar the renderer itself writes
            self.assertEqual(re.findall(r"<[a-z]+", live.replace("<br>", "").replace("<sub>", "")), ["<img"])
            self.assertNotIn("](https://evil", live)  # no live link or image to a stranger's host
            self.assertNotIn("](https://t.example", live)
            self.assertNotIn("(https://evil", live)
            self.assertNotIn("https://t.example", live)
            self.assertNotIn("<a ", live)
            for line in body:
                self.assertLess(len(line), 1500)

    def test_bad_url_and_key_are_dropped(self):
        cfg, data = fake("ok")
        data["pull_requests"].append({"key": "bad key#1", "url": "x", "title": "t", "created": "2026-01-04",
                                      "state": "OPEN", "draft": False, "merged": "", "fixes": []})
        out = upstream.render(cfg, copy.deepcopy(data))
        self.assertNotIn("t.example", out)
        self.assertNotIn("bad key", out)
        self.assertIn("(https://github.com/o/q)", out)

    def test_real_data_still_renders(self):
        out = upstream.render()
        self.assertIn("subclass `from_dict` returned the base class", out)
        self.assertTrue(out.startswith("| Project |"))
        json.loads(upstream.DATA.read_text())


if __name__ == "__main__":
    unittest.main()
