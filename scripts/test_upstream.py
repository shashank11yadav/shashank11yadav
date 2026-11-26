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
           "curated_until": "2000-01-01", "max_bullets": 5, "since": "2025-01-01"}
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
        data["pull_requests"][1].update(state="MERGED", merged="2026-01-04")  # its URL is hostile
        data["pull_requests"].append({"key": "bad key#1", "url": "x", "title": "t", "created": "2026-01-04",
                                      "state": "OPEN", "draft": False, "merged": "", "fixes": []})
        out = upstream.render(cfg, copy.deepcopy(data))
        self.assertNotIn("t.example", out)
        self.assertNotIn("bad key", out)
        self.assertIn("(https://github.com/o/q)", out)

    def test_real_data_still_renders(self):
        out = upstream.render()
        self.assertIn("subclass `from_dict` returned the base class", out)
        self.assertIn("\n| Project |", out)
        json.loads(upstream.DATA.read_text())


def pr(key, state="MERGED", merged="2026-01-02", created="2026-01-01", draft=False):
    return {"key": key, "url": f"https://github.com/{key.replace('#', '/pull/')}", "title": f"Fix {key}",
            "created": created, "state": state, "draft": draft, "merged": merged, "fixes": []}


def layout(prs, **cfg_extra):
    cfg = {"projects": {"o/*": {"name": "Org"}}, "pull_requests": [], "issues": {}, "hide": [],
           "curated_until": "2000-01-01", "max_bullets": 5, "since": "2025-01-01", **cfg_extra}
    data = {"user": "me", "repos": {}, "pull_requests": prs, "issues": []}
    return upstream.render(cfg, data)


class Layout(unittest.TestCase):
    """Summary line, deepest projects first with tier dividers, open PRs as one count."""

    def test_summary_line_counts_and_links_everything(self):
        out = layout([pr("o/a#1", merged="2025-08-09"), pr("o/b#2"), pr("x/y#3"),
                      pr("x/y#4", state="OPEN", merged="")])
        first = out.split("\n")[0]
        self.assertTrue(first.startswith("**3 merged PRs in 2 projects since Aug 2025**, 2 of them in Org. "), first)
        self.assertIn("https://github.com/search?type=pullrequests&q=is%3Apr+is%3Amerged+author%3Ame"
                      "+-user%3Ame+created%3A%3E%3D2025-01-01", first)

    def test_summary_singular_and_no_top_project_for_one(self):
        first = layout([pr("x/y#1", merged="2026-11-19")]).split("\n")[0]
        self.assertTrue(first.startswith("**1 merged PR in 1 project since Nov 2026**. [See them all"), first)

    def test_bad_merge_date_drops_since(self):
        first = layout([pr("x/y#1", merged="soon")]).split("\n")[0]
        self.assertTrue(first.startswith("**1 merged PR in 1 project**."), first)

    def test_no_merged_prs_means_no_summary(self):
        out = layout([pr("x/y#1", state="OPEN", merged="")])
        self.assertTrue(out.startswith("| Project |"), out)

    def test_deepest_projects_first_with_dividers(self):
        out = layout([pr("x/y#1"), pr("o/a#2"), pr("o/b#3"), pr("o/a#4"), pr("p/q#5"), pr("p/q#6")])
        table = [l for l in out.split("\n") if l.startswith("| ") and "Project" not in l and not l.startswith("| :")]
        self.assertIn("Sustained work", table[0])
        self.assertIn("**[Org]", table[1])          # 3 merged
        self.assertIn("Targeted fixes", table[2])
        self.assertIn("**[q]", table[3])            # 2 merged
        self.assertIn("**[y]", table[4])            # 1 merged
        for line in table:
            self.assertEqual(len(re.split(r"(?<!\\)\|", line.strip())) - 2, 3, line)

    def test_ties_keep_config_order_and_one_tier_has_no_divider(self):
        out = layout([pr("x/y#1"), pr("o/a#2")])
        self.assertNotIn("Sustained work", out)
        self.assertNotIn("Targeted fixes", out)
        self.assertLess(out.index("**[Org]"), out.index("**[y]"))

    def test_count_links_work_signed_out_and_match_filters(self):
        out = layout([pr("x/y#1")])
        self.assertNotIn("github.com/pulls", out)
        self.assertIn("(https://github.com/search?type=pullrequests&q=is%3Apr+is%3Amerged+author%3Ame"
                      "+repo%3Ax%2Fy+created%3A%3E%3D2025-01-01)", out)

    def test_open_prs_are_one_linked_count(self):
        out = layout([pr("x/y#1"), pr("x/y#2", state="OPEN", merged=""), pr("o/a#3", state="OPEN", merged=""),
                      pr("o/b#4", state="OPEN", merged=""), pr("o/c#5", state="OPEN", merged="", draft=True)])
        review = [l for l in out.split("\n") if l.startswith("**In review:**")]
        self.assertEqual(len(review), 1)
        self.assertTrue(review[0].startswith("**In review:** [3 open PRs in 2 projects](https://github.com/search?"),
                        review[0])
        self.assertIn("draft%3Afalse", review[0])
        self.assertNotIn("/pull/", review[0])


if __name__ == "__main__":
    unittest.main()
