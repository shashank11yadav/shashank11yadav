"""Keep the Open-source contributions table current.

    python scripts/upstream.py <user>     fetch PRs and issues opened on other people's public
                                          repos into scripts/upstream.data.json
    python scripts/build_readme.py        renders the table at {{upstream}} with render()

Fetching uses $GITHUB_TOKEN when set (the profile workflow), otherwise the local `gh` login.
What each PR says, project names and what to hide live in scripts/upstream.json.
"""
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
    return text.replace("|", "\\|").replace("\n", " ")


def refs(pr_keys, issue_keys, urls):
    def link(key):
        return f"[#{number(key)}]({urls[key]})" if key in urls else f"#{number(key)}"
    prs = ", ".join(link(k) for k in pr_keys)
    if not issue_keys:
        return f"(PR {prs})"
    issues = ", ".join(link(k) for k in issue_keys)
    return f"({'issues' if len(issue_keys) > 1 else 'issue'} {issues} → {'PRs' if len(pr_keys) > 1 else 'PR'} {prs})"


def render():
    cfg = json.loads(CONFIG.read_text())
    data = json.loads(DATA.read_text())
    projects, hide = cfg["projects"], cfg.get("hide", [])
    urls = {i["key"]: i["url"] for i in data["pull_requests"] + data["issues"]}
    prs = [p for p in data["pull_requests"] if not hidden(p["key"], hide)]
    issues = [i for i in data["issues"] if not hidden(i["key"], hide)]
    extra_fixes = {k: v.get("fixes", []) for k, v in cfg.get("issues", {}).items()}
    fixes = {p["key"]: sorted(set(p["fixes"]) | set(extra_fixes.get(p["key"], []))) for p in prs}

    def name(project):
        return projects.get(project, {}).get("name") or project.split("/")[-1]

    # group merged PRs by project; configured projects first, the rest by number of PRs
    merged = {}
    for p in prs:
        if p["state"] == "MERGED":
            merged.setdefault(project_of(repo_of(p["key"]), projects), []).append(p)
    order = [k for k in projects if k in merged]
    order += sorted((k for k in merged if k not in projects), key=lambda k: -len(merged[k]))

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
            bullets.append(f"• {cell(clean_title(p['title']))} {refs([p['key']], fixes[p['key']], urls)}")
        if not bullets:
            continue
        repos = sorted({repo_of(k) for k in keys})
        owner = repos[0].split("/")[0]
        url = info.get("url") or f"https://github.com/{repos[0]}"
        about = (info.get("about") or data["repos"].get(repos[0], {}).get("about", "")).rstrip(".")
        star = data["repos"].get(repos[0], {}).get("stars", "0") if len(repos) == 1 else ""
        if star and star[-1] == "K":
            about = f"{about} · {star}★" if about else f"{star}★"
        scope = f"repo:{repos[0]}" if len(repos) == 1 else f"user:{owner}"
        search = "https://github.com/pulls?q=" + urllib.parse.quote_plus(
            f"is:pr is:merged author:{data['user']} {scope}")
        rows.append(f'| <img src="https://github.com/{owner}.png" width="16" height="16"> **[{name(project)}]({url})**'
                    f"{'<br><sub>' + cell(about) + '</sub>' if about else ''} | [**{len(items)}**]({search}) | "
                    + "<br>".join(bullets) + " |")

    out = ["| Project | Merged | What I fixed or built |", "| :--- | :---: | :--- |"] + rows

    review = [p for p in prs if p["state"] == "OPEN" and not p["draft"]]
    if review:
        out += ["", "**In review:** " + " · ".join(
            f"[{name(project_of(repo_of(p['key']), projects))} #{number(p['key'])}]({p['url']})"
            for p in sorted(review, key=lambda p: p["created"]))]

    # reports the maintainers fixed themselves: closed as completed, not by one of my PRs
    mine = {i for keys in fixes.values() for i in keys}
    fixed = [i for i in issues if i["state"] == "CLOSED" and i["reason"] == "COMPLETED" and i["key"] not in mine]
    if fixed:
        out += ["", "**Reported, fixed by the maintainers:** " + " · ".join(
            f"[{name(project_of(repo_of(i['key']), projects))} #{number(i['key'])}]({i['url']}): "
            + cfg.get("issues", {}).get(i["key"], {}).get("text", clean_title(i["title"]))
            for i in sorted(fixed, key=lambda i: i["created"]))]
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    fetch(sys.argv[1])
