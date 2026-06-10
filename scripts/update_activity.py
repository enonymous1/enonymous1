"""
Fetches the latest public GitHub activity for a user and updates
the README.md between <!--START_SECTION:activity--> markers.
"""

import os
import re
import sys
import json
import urllib.request
from datetime import datetime, timezone

USERNAME = os.environ.get("GH_USERNAME", "enonymous1")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README_PATH = os.environ.get("TARGET_FILE", "README.md")
MAX_LINES = int(os.environ.get("MAX_LINES", "5"))

EVENT_ICONS = {
    "PushEvent": "📦",
    "CreateEvent": "🌱",
    "ForkEvent": "🍴",
    "WatchEvent": "⭐",
    "IssuesEvent": "🐛",
    "IssueCommentEvent": "💬",
    "PullRequestEvent": "🔀",
    "ReleaseEvent": "🚀",
    "DeleteEvent": "🗑️",
    "PublicEvent": "📢",
}

# Events to skip entirely (noisy or uninteresting)
SKIP_EVENTS = {"WatchEvent", "DeleteEvent", "MemberEvent"}

# Skip events on the profile repo itself to avoid infinite loops
SKIP_REPO = f"{USERNAME}/{USERNAME}"


def fetch_events():
    url = f"https://api.github.com/users/{USERNAME}/events/public?per_page=50"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "github-activity-updater",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def format_event(event):
    etype = event.get("type", "")
    repo = event.get("repo", {}).get("name", "unknown/unknown")
    repo_url = f"https://github.com/{repo}"
    icon = EVENT_ICONS.get(etype, "🔧")
    created_at = event.get("created_at", "")

    try:
        dt = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        date_str = dt.strftime("%b %d, %Y")
    except ValueError:
        date_str = created_at[:10]

    payload = event.get("payload", {})

    if etype == "PushEvent":
        commits = payload.get("commits", [])
        count = len(commits)
        noun = "commit" if count == 1 else "commits"
        branch = payload.get("ref", "refs/heads/main").replace("refs/heads/", "")
        return f"{icon} Pushed {count} {noun} to [`{repo}`]({repo_url}) on `{branch}` — {date_str}"

    if etype == "CreateEvent":
        ref_type = payload.get("ref_type", "repository")
        ref = payload.get("ref", "")
        if ref_type == "repository":
            return f"{icon} Created repository [`{repo}`]({repo_url}) — {date_str}"
        return f"{icon} Created {ref_type} `{ref}` in [`{repo}`]({repo_url}) — {date_str}"

    if etype == "ForkEvent":
        forkee = payload.get("forkee", {}).get("full_name", repo)
        return f"{icon} Forked [`{forkee}`](https://github.com/{forkee}) — {date_str}"

    if etype == "IssuesEvent":
        action = payload.get("action", "opened")
        issue = payload.get("issue", {})
        title = issue.get("title", "an issue")
        url = issue.get("html_url", repo_url)
        return f"{icon} {action.capitalize()} issue [{title}]({url}) in [`{repo}`]({repo_url}) — {date_str}"

    if etype == "IssueCommentEvent":
        issue = payload.get("issue", {})
        title = issue.get("title", "an issue")
        url = payload.get("comment", {}).get("html_url", repo_url)
        return f"{icon} Commented on [{title}]({url}) in [`{repo}`]({repo_url}) — {date_str}"

    if etype == "PullRequestEvent":
        action = payload.get("action", "opened")
        pr = payload.get("pull_request", {})
        title = pr.get("title", "a pull request")
        url = pr.get("html_url", repo_url)
        return f"{icon} {action.capitalize()} PR [{title}]({url}) in [`{repo}`]({repo_url}) — {date_str}"

    if etype == "ReleaseEvent":
        release = payload.get("release", {})
        tag = release.get("tag_name", "")
        url = release.get("html_url", repo_url)
        return f"{icon} Released [`{tag}`]({url}) in [`{repo}`]({repo_url}) — {date_str}"

    return None


def build_activity_lines(events):
    lines = []
    seen_repos_for_push = {}  # collapse multiple pushes to the same repo/branch

    for event in events:
        etype = event.get("type", "")
        repo = event.get("repo", {}).get("name", "")

        if etype in SKIP_EVENTS:
            continue
        if repo == SKIP_REPO:
            continue

        # Collapse consecutive pushes to the same repo+branch into one entry
        if etype == "PushEvent":
            payload = event.get("payload", {})
            branch = payload.get("ref", "").replace("refs/heads/", "")
            key = f"{repo}:{branch}"
            if key in seen_repos_for_push:
                # Accumulate commit count on the existing entry instead
                seen_repos_for_push[key]["payload"]["commits"] = (
                    seen_repos_for_push[key]["payload"].get("commits", [])
                    + payload.get("commits", [])
                )
                continue
            seen_repos_for_push[key] = event

        line = format_event(event)
        if line:
            lines.append(line)

        if len(lines) >= MAX_LINES:
            break

    return lines


def update_readme(lines):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    start_marker = "<!--START_SECTION:activity-->"
    end_marker = "<!--END_SECTION:activity-->"

    if start_marker not in content or end_marker not in content:
        print("ERROR: Activity markers not found in README.", file=sys.stderr)
        sys.exit(1)

    new_section = start_marker + "\n"
    if lines:
        new_section += "\n".join(f"- {line}" for line in lines) + "\n"
    new_section += end_marker

    updated = re.sub(
        re.escape(start_marker) + r".*?" + re.escape(end_marker),
        new_section,
        content,
        flags=re.DOTALL,
    )

    if updated == content:
        print("No changes to README.")
        return False

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"Updated README with {len(lines)} activity line(s).")
    return True


def main():
    print(f"Fetching activity for {USERNAME}...")
    events = fetch_events()
    print(f"Fetched {len(events)} events.")

    lines = build_activity_lines(events)

    if not lines:
        print("No displayable activity found.")
        sys.exit(0)

    changed = update_readme(lines)
    sys.exit(0 if changed else 0)


if __name__ == "__main__":
    main()
