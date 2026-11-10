# Bible Study Commentary: handoff notes

Live version: https://claude.ai/artifact/NpDDWjSQQPZeSp3vyTEHXk

## What it is
A static web page (index.html + data/*.json). Search a passage like "John 3:16-36"; it shows the
text (NASB 2020 by default, NLT, NIV, or Reina-Valera 1909, from API.Bible; words of Jesus in red) and three expandable commentary rows:
- Enduring Word (David Guzik): link to the chapter on enduringword.com
- Classic Commentaries: public-domain commentaries stored in the app (seamless, like Matthew Henry), one
  collapsible section each, loaded when opened; a link goes to Bible Hub for the rest (Ellicott, Gill, Pulpit...).
  (BibleRef was removed: it blocks embedding. The Bible Hub embed was replaced by these.)
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

## Bible text (API.Bible)
- Text comes from https://rest.api.bible one chapter (or verse range within one chapter) at a time.
  The key lives in config.js (public; Starter plan = non-commercial only).
- Translation ids are in TRANSLATIONS in build/template.html. NASB 2020 a761ca71e0b3ddcf-01,
  NLT d6e14a625393b4da-01, NIV 78a9f6124f344018-01, Reina-Valera 1909 592420522e16049f-01 (public domain, free on every plan).
- RVR1960 is not offered by API.Bible; it needs a license from Sociedades Biblicas Unidas.
- FUMS (API.Bible's required usage tracker) is loaded from pkg.api.bible and called after each passage.
- Lockman requires the full NASB notice with a clickable www.Lockman.org link on web pages and apps.
- The old KJV/WEB text files (data/{book}.json) were removed; build/build.py still documents how they and build/index.json (verse counts) were made.

## Enduring Word sections
- data/ew-sections.json maps "book-chapter" to [sectionNumber, firstVerse, lastVerse] (999 = runs into
  the next chapter). Built by build/ew_scrape.py (headings' verse numbers only) and build/ew_sections.py.
  The embed opens at #section-N on enduringword.com.

## Translation picker
- A dropdown (#tr-select); the choice is remembered in localStorage (bsc-tr2).

## Classic commentaries data
- data/cl-{code}-{book}.json: {"chapter": [[firstVerse, lastVerse, [["h"|"p", html with <b>/<i> only], ...]], ...]}
  (verse 0 = chapter introduction, shown only for whole-chapter searches). data/cl-index.json lists books per code.
- Built by build/classics.py from CrossWire SWORD modules (all marked Public Domain, or printed before 1600 for
  Geneva): Barnes (NT only), Clarke, JFB, Wesley, MHCC, Geneva, Scofield 1917, PNT (NT only), read with
  build/sword_read.py; and from github.com/samueldotj/bible-commentaries en/poole (Poole 1683-85) and
  en/calvin (CCEL, public domain).
- Matthew Henry's verse markers ("ver. 3, 4", "(ver. 8)") are shown as "(v. 3, 4)" by henryRefs() at display time.
