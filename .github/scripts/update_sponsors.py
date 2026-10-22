"""Rewrite the sponsors block in README.md from GitHub Sponsors data.

Lists active, public, monthly sponsors at $10 a month or more, which is what the
sponsorship tiers promise. Private sponsorships are never returned. Works with the
workflow's GITHUB_TOKEN, passed to the GitHub CLI as GH_TOKEN.
"""

import json
from pathlib import Path
import subprocess


LOGIN = "cravingmaker"
MINIMUM_MONTHLY_DOLLARS = 10
README = Path("README.md")
START = "<!-- sponsors:start -->"
END = "<!-- sponsors:end -->"
QUERY = """
query($login: String!) {
  user(login: $login) {
    sponsorshipsAsMaintainer(first: 100, activeOnly: true, includePrivate: false) {
      nodes {
        tier { monthlyPriceInDollars isOneTime }
        sponsorEntity {
          ... on User { login name url }
          ... on Organization { login name url }
        }
      }
    }
  }
}
"""


def fetch_sponsorships():
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={QUERY}", "-F", f"login={LOGIN}"],
        check=True, stdout=subprocess.PIPE, text=True,
    )
    data = json.loads(result.stdout)
    if data.get("errors"):
        raise SystemExit(f"GitHub API error: {data['errors']}")
    return data["data"]["user"]["sponsorshipsAsMaintainer"]["nodes"]


def listed_sponsors(sponsorships):
    sponsors = []
    for sponsorship in sponsorships:
        entity = sponsorship.get("sponsorEntity")
        if not entity:
            continue
        tier = sponsorship.get("tier")
        if tier and tier.get("isOneTime"):
            continue
        # If the API hides the tier, list the sponsor rather than risk leaving out
        # someone the tiers promise to list.
        if tier and tier.get("monthlyPriceInDollars", 0) < MINIMUM_MONTHLY_DOLLARS:
            continue
        sponsors.append(entity)
    return sorted(sponsors, key=lambda entity: entity["login"].lower())


def render(sponsors):
    if not sponsors:
        return "_No sponsors yet. Be the first!_"
    return "\n".join(f"- [{entity.get('name') or entity['login']}]({entity['url']})" for entity in sponsors)


def main():
    text = README.read_text(encoding="utf-8")
    before, start, rest = text.partition(START)
    middle, end, after = rest.partition(END)
    if not start or not end:
        raise SystemExit(f"README.md must contain {START} and {END}")
    block = render(listed_sponsors(fetch_sponsorships()))
    updated = f"{before}{START}\n{block}\n{END}{after}"
    if updated != text:
        README.write_text(updated, encoding="utf-8")
        print("Sponsors section updated.")
    else:
        print("Sponsors section is current.")


if __name__ == "__main__":
    main()
