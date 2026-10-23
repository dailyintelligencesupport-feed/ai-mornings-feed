#!/usr/bin/env python3
"""Sync the "AI Mornings with Aman" mirror feed.

Fetches the source feed from muse.ai and writes feed.xml with the
channel metadata Apple Podcasts and Spotify require but the source
feed does not emit:
  - <itunes:author>            (Apple's "Artist" field)
  - <itunes:owner> name+email  (directory ownership verification)
  - <itunes:category>          (required by Apple)
  - the owner-approved show description (source ignores updates)
  - the atom self-link rewritten to this mirror's public URL

Run by .github/workflows/sync-feed.yml on GitHub's runners; can also
be run locally:  python3 inject.py
The public URL is read from the FEED_PUBLIC_URL environment variable
(the workflow sets it automatically from the repo name). If it is
unset, the source self-link is left as-is.
"""
import os
import re
import sys
import urllib.request

SOURCE_URL = ("https://muse.ai/podcasts/feed/792746890580046/"
              "c6dcc620-f4b7-4a9c-9ed1-7bd3124daff8")
AUTHOR_NAME = "Aman Gupta"
OWNER_EMAIL = "dailyintelligence.support@gmail.com"
DESCRIPTION = """AI Mornings with Aman \u2014 the 20-minute weekday briefing for people who build with AI.

Every weekday morning: the day's biggest AI stories, then one big idea explained properly \u2014 from first principles, with the numbers that matter: what it costs, how fast it runs, and how you know it actually works.

No hype, no hot takes. News up front, deep dive after \u2014 the stuff that matters if you ship AI products, framed the way a practitioner wants it: cost, latency, evals, and the decision you can act on.

New episodes every weekday morning."""


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;"))


def inject(xml, public_url=""):
    """Return the feed with channel metadata injected. Only the
    channel header (everything before the first <item>) is touched;
    episodes, enclosures and GUIDs pass through byte-identical."""
    head, sep, rest = xml.partition("<item>")
    if not sep:
        raise ValueError("no <item> found - not a podcast feed?")

    # Approved show description (channel-level <description> is the
    # first one in the document).
    head = re.sub(r"<description>.*?</description>",
                  "<description>" + esc(DESCRIPTION) + "</description>",
                  head, count=1, flags=re.S)

    # Point the atom self-link at this mirror.
    if public_url:
        head = re.sub(r'(<atom:link href=")[^"]*(" rel="self")',
                      lambda m: m.group(1) + public_url + m.group(2),
                      head, count=1)

    block = []
    if "<itunes:author>" not in head:
        block.append(f"  <itunes:author>{esc(AUTHOR_NAME)}"
                     "</itunes:author>")
    if "<itunes:owner>" not in head:
        block.append("  <itunes:owner>\n"
                     f"    <itunes:name>{esc(AUTHOR_NAME)}</itunes:name>\n"
                     f"    <itunes:email>{esc(OWNER_EMAIL)}</itunes:email>\n"
                     "  </itunes:owner>")
    if "<itunes:category" not in head:
        block.append('  <itunes:category text="Technology">\n'
                     '    <itunes:category text="Tech News"/>\n'
                     "  </itunes:category>")
    if "<itunes:summary>" not in head:
        block.append("  <itunes:summary>" + esc(DESCRIPTION)
                     + "</itunes:summary>")
    if "<itunes:type>" not in head:
        block.append("  <itunes:type>episodic</itunes:type>")

    if block:
        text = "\n".join(block) + "\n"
        anchor = "  <itunes:explicit>"
        if anchor in head:
            head = head.replace(anchor, text + anchor, 1)
        else:
            head = head + text
    return head + sep + rest


def main():
    req = urllib.request.Request(SOURCE_URL,
                                 headers={"User-Agent": "ai-mornings-feed-sync"})
    with urllib.request.urlopen(req, timeout=60) as r:
        xml = r.read().decode("utf-8")
    out = inject(xml, os.environ.get("FEED_PUBLIC_URL", "").strip())
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "feed.xml")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"wrote {out_path}: {out.count('<item>')} episodes, "
          f"author={'<itunes:author>' in out}, "
          f"owner={'<itunes:owner>' in out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
