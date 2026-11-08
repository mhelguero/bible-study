# Bible Study Commentary: handoff notes

Live version: https://claude.ai/artifact/NpDDWjSQQPZeSp3vyTEHXk

## What it is
A static web page (index.html + data/*.json). Search a passage like "John 3:16-36"; it shows the
text (KJV or WEB, words of Jesus in red) and three expandable commentary rows:
- Enduring Word (David Guzik): link to the chapter on enduringword.com
- BibleRef: chapter overview link + one link per verse on bibleref.com
- Matthew Henry (complete, public domain): shown inline, trimmed to the searched verses
  using Henry's own markers ("v. 16", "ver. 16-18"), with a button to show the whole section.

## Files
- index.html — the whole app (built from build/template.html with build/index.json inlined)
- data/{book}.json — KJV + WEB text (from CrossWire SWORD modules)
- data/mhc-{book}.json — Matthew Henry Complete, each paragraph tagged [startVerse, endVerse, text]
  (from github.com/samueldotj/bible-commentaries, en/henry, which comes from CrossWire MHC 2.2)
- build/ — the scripts that produced the data (paths inside point at the old cloud workspace)

## Run locally
    cd bible-study && python3 -m http.server 8000   # then open http://localhost:8000

## Next step that was in progress
Host on GitHub Pages and try embedding Enduring Word and BibleRef in iframes:
- Enduring Word sends no X-Frame-Options / CSP frame-ancestors header, so an iframe will
  probably work (still check for in-page frame-busting or a Cloudflare challenge).
- BibleRef's headers could not be checked; test it with `curl -sI` and an iframe.
Keep each row's link as a fallback if the embed comes up blank.
