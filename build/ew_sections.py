"""Turn the raw Enduring Word heading scrape into data/ew-sections.json.

Input: {"john-3": [[sectionNumber, "16-21"], ...]} (only the bracketed verse numbers
from each heading, no commentary text). Output: {"john-3": [[sectionNumber, start, end], ...]},
end = 999 when a section runs into the next chapter.
"""
import json, re, sys
raw = json.load(open(sys.argv[1]))
R = re.compile(r'^(?:(\d+):)?(\d+)[a-c]?(?:\s*[-–]\s*(?:(\d+):)?(\d+)[a-c]?)?$')
out, skipped = {}, 0
for key, secs in raw.items():
    ch = int(key.rsplit('-', 1)[1]); rows = []
    for sid, txt in secs:
        m = R.match(txt.replace(' ', ''))
        if not m: skipped += bool(txt); continue
        sc, s, ec, e = m.groups()
        if sc and int(sc) != ch: continue
        s = int(s); e = int(e) if e else s
        if ec and int(ec) > ch: e = 999
        if e < s: continue
        rows.append([sid, s, e])
    if rows: out[key] = rows
json.dump(out, open(sys.argv[2], 'w'), separators=(',', ':'))
print('chapters', len(out), 'skipped non-verse headings', skipped)
