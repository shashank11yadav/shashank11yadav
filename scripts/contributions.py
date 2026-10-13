"""Fetch the last year of GitHub contributions and print them as JSON.

Usage: GITHUB_TOKEN=... python scripts/contributions.py <user> > contributions.json

Uses the GraphQL contribution calendar (public contributions, plus private ones only if the
user has turned on "Include private contributions on my profile").
"""
import json
import os
import sys
import urllib.request

QUERY = """query($login: String!) { user(login: $login) { contributionsCollection {
  contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
} } }"""

user = sys.argv[1]
req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
    headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json"},
)
cal = json.load(urllib.request.urlopen(req, timeout=30))["data"]["user"]["contributionsCollection"]["contributionCalendar"]
weeks = [[(d["date"], d["contributionCount"]) for d in w["contributionDays"]] for w in cal["weeks"]]
json.dump({"total": cal["totalContributions"], "weeks": weeks}, sys.stdout)
print()
