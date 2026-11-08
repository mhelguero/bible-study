"""Build per-book Matthew Henry (Complete) files with a verse range on every paragraph.

Henry marks what he is discussing with "v. 16", "ver. 16-18", "v. 20, 21" etc. Each paragraph gets
the range of the most recent forward marker; unmarked paragraphs inherit it, cut short where the
next marker begins, so a search can stop where Henry moves on to the next verse.
"""
import json, os, re, sys

SRC = sys.argv[1]          # en/henry
OUT = sys.argv[2]          # site/data
CODES = ("GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER LAM "
         "EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP "
         "COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV").split()
index = json.load(open('/home/claude/build/index.json'))
assert len(index) == len(CODES)

MARK = re.compile(r'^\(?\s*(?:again\s+)?(?:v|vs|ver|verse|verses)\.?\s*\d', re.I)

def unit_range(rng, book, ch, nverses):
    # "JHN.3.1-21", "JHN.3.16", "JHN.3.36-4.2", "JHN.3"
    parts = rng.split('.')
    if len(parts) < 3: return None
    m = re.match(r'(\d+)(?:-(\d+)(?:\.(\d+))?)?$', '.'.join(parts[2:]))
    if not m: return None
    s = int(m.group(1))
    if m.group(3):  e = nverses                     # runs into the next chapter
    elif m.group(2): e = int(m.group(2))
    else: e = s
    return s, min(e, nverses)

def marker_range(r, prefix, nverses):
    if not r['ref'].startswith(prefix): return None
    if not MARK.match(r['text'].strip()): return None
    tail = r['ref'][len(prefix):]
    if not re.match(r'^[\d,\- ]+$', tail): return None
    nums = [int(n) for n in re.findall(r'\d+', tail)]
    if not nums: return None
    if 'to the end' in r['text']: nums.append(nverses)
    return min(nums), min(max(nums), nverses)

total = 0
for code, b in zip(CODES, index):
    out = {}
    for c, nverses in enumerate(b['chapters'], 1):
        fn = os.path.join(SRC, code, f'{c}.json')
        if not os.path.exists(fn): continue
        d = json.load(open(fn))
        prefix = f'{code}.{c}.'
        units = []
        for u in d['units']:
            paras = u['paragraphs']
            if u['kind'] == 'chapter':
                units.append({'k': 'c', 'p': [[0, 0, p['text']] for p in paras]})
                continue
            if u['kind'] != 'passage': continue
            ur = unit_range(u['range'], code, c, nverses)
            if not ur: continue
            us, ue = ur
            cur = (us, us)
            rows = []   # [start, end, text, explicit, heading]
            for p in paras:
                ms = [m for m in (marker_range(r, prefix, nverses) for r in p.get('refs', [])) if m]
                ms = [m for m in ms if us <= m[0] <= ue and m[0] >= cur[0]]
                explicit = bool(ms)
                if ms:
                    cur = (min(m[0] for m in ms), max(m[1] for m in ms))
                rows.append([cur[0], cur[1], p['text'], explicit, bool(p.get('heading'))])
            # inherited paragraphs stop where the next marker begins
            nxt = None
            for row in reversed(rows):
                if not row[3] and nxt is not None and nxt > row[0]:
                    row[1] = min(row[1], nxt - 1)
                if row[3]:
                    nxt = row[0]
            units.append({'k': 'p', 's': us, 'e': ue, 't': u.get('title', ''),
                          'p': [[r[0], r[1], r[2]] + ([1] if r[4] else []) for r in rows]})
        out[c] = units
    path = os.path.join(OUT, f'mhc-{b["slug"]}.json')
    with open(path, 'w') as f:
        json.dump(out, f, separators=(',', ':'), ensure_ascii=False)
    total += os.path.getsize(path)
    if len(out) != len(b['chapters']):
        print('chapter gap', b['name'], len(out), len(b['chapters']))
print('total MB', round(total / 1e6, 1))
