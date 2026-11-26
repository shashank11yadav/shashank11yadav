"""Keep the Open-source contributions table current.

    python scripts/upstream.py <user>     fetch PRs and issues opened on other people's public
                                          repos into scripts/upstream.data.json
    python scripts/build_readme.py        renders the table at {{upstream}} with render()

Fetching uses $GITHUB_TOKEN when set (the profile workflow), otherwise the local `gh` login.
What each PR says, project names and what to hide live in scripts/upstream.json.

The section is: a summary line (merged PRs, projects, first merge month, a link to all of them),
the table with the projects that have the most merged PRs first (split into "Sustained work" and
"Targeted fixes" at `sustained_min` when both kinds exist), and open PRs as one linked count.
Every count links to github.com/search, which works for visitors who are not signed in, with the
same filters the count uses (so it matches unless something is in `hide`).

Two kinds of text reach the table. Text from scripts/upstream.json is hand-written and trusted:
it only gets cell() (so a `|` can't break the table; backticks and links still work). Everything
that comes from other people through scripts/upstream.data.json (repo descriptions, PR and issue
titles, repo names, URLs, star counts) goes through safe(), which makes it inert: HTML and Markdown
are escaped (a matched pair of backticks stays code, which GitHub shows literally), whitespace is
collapsed and the length is capped. The workflow commits the result to
master unattended, so a hostile maintainer must not be able to inject tags, links or images.
"""
import unicodedata
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "scripts/upstream.json"
DATA = ROOT / "scripts/upstream.data.json"

QUERY = """query($q: String!, $after: String) {
  search(query: $q, type: ISSUE, first: 100, after: $after) {
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on PullRequest { number title url state isDraft createdAt mergedAt
        repository { nameWithOwner isPrivate stargazerCount description }
        closingIssuesReferences(first: 10) { nodes { number repository { nameWithOwner } } } }
      ... on Issue { number title url state stateReason createdAt
        repository { nameWithOwner isPrivate stargazerCount description } }
    }
  }
}"""


# ---------------------------------------------------------------- fetch

def graphql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
            "Authorization": f"bearer {token}", "Content-Type": "application/json"})
        out = json.load(urllib.request.urlopen(req, timeout=30))
    else:
        out = json.loads(subprocess.run(["gh", "api", "graphql", "--input", "-"], input=body,
                                        capture_output=True, check=True).stdout)
    if out.get("errors"):
        sys.exit("GitHub said: %s" % out["errors"][0].get("message"))
    return out["data"]


def search(q):
    nodes, after = [], None
    for _ in range(5):
        page = graphql(QUERY, {"q": q, "after": after})["search"]
        nodes += [n for n in page["nodes"] if n]
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]
    return nodes


def stars(n):
    if n >= 10000:
        return f"{round(n / 1000)}K"
    if n >= 1000:
        return f"{n / 1000:.1f}K"
    return str(n)


def fetch(user):
    since = json.loads(CONFIG.read_text())["since"]
    repos, prs, issues = {}, [], []
    for kind in ("pr", "issue"):
        for n in search(f"author:{user} is:{kind} -user:{user} created:>={since}"):
            repo = n["repository"]
            if repo["isPrivate"]:
                continue  # never put a private repo's work on a public profile
            name = repo["nameWithOwner"]
            # stars are stored as shown, so a few new stars don't change the file
            repos[name] = {"stars": stars(repo["stargazerCount"]), "about": repo["description"] or ""}
            item = {"key": f"{name}#{n['number']}", "url": n["url"], "title": n["title"],
                    "created": n["createdAt"][:10]}
            if kind == "pr":
                item.update(state=n["state"], draft=n["isDraft"], merged=(n["mergedAt"] or "")[:10],
                            fixes=sorted(f"{i['repository']['nameWithOwner']}#{i['number']}"
                                         for i in n["closingIssuesReferences"]["nodes"]))
                prs.append(item)
            else:
                item.update(state=n["state"], reason=n["stateReason"])
                issues.append(item)
    data = {"user": user, "repos": dict(sorted(repos.items())),
            "pull_requests": sorted(prs, key=lambda p: p["key"]),
            "issues": sorted(issues, key=lambda i: i["key"])}
    DATA.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(prs)} pull requests, {len(issues)} issues on {len(repos)} repos")


# ---------------------------------------------------------------- render

def repo_of(key):
    return key.split("#")[0]


def number(key):
    return key.split("#")[1]


def matches(repo, pattern):
    return pattern == repo or (pattern.endswith("/*") and repo.split("/")[0] == pattern[:-2])


def project_of(repo, projects):
    for pattern in projects:
        if matches(repo, pattern):
            return pattern
    return repo


def hidden(key, hide):
    return any(key == h or matches(repo_of(key), h) for h in hide)


def clean_title(title):
    title = re.sub(r"^\s*(\[[^\]]*\]\s*)+", "", title)
    title = re.sub(r"^[a-z]+(\([^)]*\))?!?:\s*", "", title)
    title = title.strip().rstrip(".")
    return title[:1].upper() + title[1:]


def cell(text):
    """Trusted text (scripts/upstream.json): keep its Markdown, just don't break the table."""
    return text.replace("|", "\\|").replace("\n", " ")


MAX_TEXT = 120
_MD = re.compile(r"([\\`*_\[\]()!#|~+{}])")
_WWW = re.compile(r"(?i)\b(www)\.")


def safe(text, limit=MAX_TEXT):
    """Untrusted text (from other people): inert in a GitHub Markdown table cell.

    Control and invisible format characters (bidi marks, zero-width) are dropped, whitespace is
    collapsed, the text is cut at `limit` characters (ending with an ellipsis), then & < > and
    quotes become HTML entities and every Markdown control character is backslash-escaped, so it
    shows up as plain text. `@` and `$` get an empty span around them instead, because GitHub
    turns them into mentions and math even after a backslash.
    Bare URLs and www. names are broken up so GitHub does not autolink them.
    A matched pair of backticks stays a code span: GitHub shows code spans literally (no links,
    images or HTML), so only `|` needs escaping inside one.
    """
    text = "".join(c for c in str(text) if c in "\t\n\r" or unicodedata.category(c) not in ("Cc", "Cf"))
    text = " ".join(text.split())
    if len(text) > limit:
        text = text[:limit - 1].rstrip() + "\u2026"
    return "".join(_code(part) if _CODE.fullmatch(part) else _plain(part) for part in _CODE.split(text))


_CODE = re.compile(r"(`[^`]+`)")


def _code(part):
    return part.replace("|", "\\|")


def _plain(text):
    text = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))
    text = _MD.sub(r"\\\1", text)
    # a backslash doesn't stop GitHub's @mentions or $math$, an empty span around the sign does
    text = text.replace("@", "<span>@</span>").replace("$", "<span>$</span>")
    text = text.replace("://", ":\\/\\/")
    return _WWW.sub(r"\1\\.", text)


_KEY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#[0-9]+$")
_STARS = re.compile(r"^[0-9]+(\.[0-9])?K?$")


def safe_url(url, fallback):
    """A github.com link without anything that could end the Markdown link early."""
    ok = isinstance(url, str) and re.fullmatch(r"https://github\.com/[A-Za-z0-9_./#?=&%+:-]+", url)
    return url if ok else fallback


def refs(pr_keys, issue_keys, urls):
    def link(key):
        return f"[#{number(key)}]({urls[key]})" if key in urls else f"#{number(key)}"
    prs = ", ".join(link(k) for k in pr_keys)
    if not issue_keys:
        return f"(PR {prs})"
    issues = ", ".join(link(k) for k in issue_keys)
    return f"({'issues' if len(issue_keys) > 1 else 'issue'} {issues} → {'PRs' if len(pr_keys) > 1 else 'PR'} {prs})"


MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def month(date):
    """'2025-08-09' -> 'Aug 2025', without depending on the machine's locale; '' if not a date."""
    found = re.match(r"^(\d{4})-(0[1-9]|1[0-2])-", str(date))
    return f"{MONTHS[int(found.group(2)) - 1]} {found.group(1)}" if found else ""


def plural(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def search_url(query):
    """A GitHub search link for pull requests. github.com/search works for visitors who aren't
    signed in; github.com/pulls sends them to the login page instead."""
    return "https://github.com/search?type=pullrequests&q=" + urllib.parse.quote_plus(query)


def divider(title, note):
    return f"| **{title}**<br><sub>{note}</sub> | | |"


def render(cfg=None, data=None):
    cfg = cfg or json.loads(CONFIG.read_text())
    data = data or json.loads(DATA.read_text())
    projects, hide = cfg["projects"], cfg.get("hide", [])
    user, since = data["user"], cfg["since"]
    deep_min = cfg.get("sustained_min", 3)
    # drop anything whose key is not a plain owner/repo#number, and pin every link to github.com
    data["pull_requests"] = [p for p in data["pull_requests"] if _KEY.match(p["key"])]
    data["issues"] = [i for i in data["issues"] if _KEY.match(i["key"])]
    for item in data["pull_requests"] + data["issues"]:
        item["url"] = safe_url(item.get("url"), "https://github.com/" + repo_of(item["key"]))
    urls = {i["key"]: i["url"] for i in data["pull_requests"] + data["issues"]}
    prs = [p for p in data["pull_requests"] if not hidden(p["key"], hide)]
    issues = [i for i in data["issues"] if not hidden(i["key"], hide)]
    extra_fixes = {k: v.get("fixes", []) for k, v in cfg.get("issues", {}).items()}
    fixes = {p["key"]: sorted(set(p["fixes"]) | set(extra_fixes.get(p["key"], []))) for p in prs}

    def name(project):
        configured = projects.get(project, {}).get("name")
        return cell(configured) if configured else safe(project.split("/")[-1])

    # group merged PRs by project; most merged PRs first, ties in the order of upstream.json
    merged = {}
    for p in prs:
        if p["state"] == "MERGED":
            merged.setdefault(project_of(repo_of(p["key"]), projects), []).append(p)
    rank = {k: i for i, k in enumerate(projects)}
    order = sorted(merged, key=lambda k: (-len(merged[k]), rank.get(k, len(rank)), k))

    rows = []
    for project in order:
        info, items = projects.get(project, {}), merged[project]
        keys = {p["key"] for p in items}
        bullets, covered = [], set()
        for entry in cfg.get("pull_requests", []):
            mine = [k for k in entry["prs"] if k in keys]
            if mine:
                covered.update(entry["prs"])
                linked = sorted({i for k in mine for i in fixes.get(k, [])})
                bullets.append(f"• {cell(entry['text'])} {refs(mine, linked, urls)}")
        new = sorted((p for p in items if p["key"] not in covered and p["merged"] > cfg["curated_until"]),
                     key=lambda p: p["merged"], reverse=True)
        for p in new[:max(0, cfg["max_bullets"] - len(bullets))]:
            bullets.append(f"• {safe(clean_title(p['title']))} {refs([p['key']], fixes[p['key']], urls)}")
        if not bullets:
            continue
        repos = sorted({repo_of(k) for k in keys})
        owner = repos[0].split("/")[0]
        url = info.get("url") or f"https://github.com/{repos[0]}"
        if info.get("about"):
            about = cell(info["about"].rstrip("."))
        else:
            about = safe(data["repos"].get(repos[0], {}).get("about", "").rstrip("."))
        star = data["repos"].get(repos[0], {}).get("stars", "0") if len(repos) == 1 else ""
        if star and star[-1] == "K" and _STARS.match(star):
            about = f"{about} · {star}★" if about else f"{star}★"
        scope = f"repo:{repos[0]}" if len(repos) == 1 else f"user:{owner}"
        search = search_url(f"is:pr is:merged author:{user} {scope} created:>={since}")
        rows.append((len(items), f'| <img src="https://github.com/{owner}.png" width="16" height="16"> **[{name(project)}]({url})**'
                     f"{'<br><sub>' + about + '</sub>' if about else ''} | [**{len(items)}**]({search}) | "
                     + "<br>".join(bullets) + " |"))

    out = []
    if merged:
        total = sum(len(items) for items in merged.values())
        first = month(min((p["merged"] for items in merged.values() for p in items if p["merged"]), default=""))
        top = order[0]
        summary = f"**{plural(total, 'merged PR')} in {plural(len(merged), 'project')}{' since ' + first if first else ''}**"
        if len(merged) > 1 and len(merged[top]) > 1:
            summary += f", {len(merged[top])} of them in {name(top)}"
        everything = search_url(f"is:pr is:merged author:{user} -user:{user} created:>={since}")
        out += [f"{summary}. [See them all on GitHub]({everything})", ""]

    # projects with several merged PRs first, under their own divider, when both kinds exist
    deep = [line for n, line in rows if n >= deep_min]
    quick = [line for n, line in rows if n < deep_min]
    if deep and quick:
        few = "1 merged PR each" if deep_min == 2 else f"fewer than {deep_min} merged PRs each"
        body = ([divider("Sustained work", f"{deep_min} or more merged PRs each")] + deep
                + [divider("Targeted fixes", few)] + quick)
    else:
        body = deep + quick
    out += ["| Project | Merged | What I fixed or built |", "| :--- | :---: | :--- |"] + body

    # open PRs as one linked count: a long list of unmerged work reads as volume, not depth
    review = [p for p in prs if p["state"] == "OPEN" and not p["draft"]]
    if review:
        waiting = len({project_of(repo_of(p["key"]), projects) for p in review})
        open_search = search_url(f"is:pr is:open draft:false author:{user} -user:{user} created:>={since}")
        out += ["", f"**In review:** [{plural(len(review), 'open PR')} in {plural(waiting, 'project')}]({open_search})"]

    # reports the maintainers fixed themselves: closed as completed, not by one of my PRs
    mine = {i for keys in fixes.values() for i in keys}
    fixed = [i for i in issues if i["state"] == "CLOSED" and i["reason"] == "COMPLETED" and i["key"] not in mine]
    if fixed:
        out += ["", "**Reported, fixed by the maintainers:** " + " · ".join(
            f"[{name(project_of(repo_of(i['key']), projects))} #{number(i['key'])}]({i['url']}): "
            + (cell(cfg["issues"][i["key"]]["text"]) if "text" in cfg.get("issues", {}).get(i["key"], {})
               else safe(clean_title(i["title"])))
            for i in sorted(fixed, key=lambda i: i["created"]))]
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    fetch(sys.argv[1])
