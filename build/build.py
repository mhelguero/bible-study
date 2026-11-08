import re, json, os, html, sys

DL = '/home/claude/dl'
OUT = '/home/claude/site/data'
os.makedirs(OUT, exist_ok=True)

BOOKS = ["Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges","Ruth","1 Samuel","2 Samuel",
"1 Kings","2 Kings","1 Chronicles","2 Chronicles","Ezra","Nehemiah","Esther","Job","Psalms","Proverbs",
"Ecclesiastes","Song of Solomon","Isaiah","Jeremiah","Lamentations","Ezekiel","Daniel","Hosea","Joel","Amos",
"Obadiah","Jonah","Micah","Nahum","Habakkuk","Zephaniah","Haggai","Zechariah","Malachi","Matthew","Mark","Luke",
"John","Acts","Romans","1 Corinthians","2 Corinthians","Galatians","Ephesians","Philippians","Colossians",
"1 Thessalonians","2 Thessalonians","1 Timothy","2 Timothy","Titus","Philemon","Hebrews","James","1 Peter",
"2 Peter","1 John","2 John","3 John","Jude","Revelation"]

def swordname(b):
    if b == "Revelation": return "Revelation of John"
    m = re.match(r'(\d) (.*)', b)
    if m: return {'1':'I','2':'II','3':'III'}[m.group(1)] + ' ' + m.group(2)
    return b
S2B = {swordname(b): b for b in BOOKS}

def clean(t):
    t = re.sub(r'<note\b.*?</note>', ' ', t, flags=re.S)
    t = re.sub(r'<title\b.*?</title>', '', t, flags=re.S)
    t = re.sub(r'<[^>]+>', '', t)
    t = t.replace('¶', '')
    t = html.unescape(t)
    t = re.sub(r'\s+', ' ', t).strip()
    return re.sub(r' ([,.;:!?])', r'\1', t)

# ---------- Bible text ----------
def load_bible(fn):
    data = {}
    key = None
    for line in open(os.path.join(DL, fn), encoding='utf-8', errors='replace'):
        if line.startswith('$$$'):
            m = re.match(r'\$\$\$(.+) (\d+):(\d+)\s*$', line)
            key = None
            if m and m.group(1) in S2B and int(m.group(2)) > 0 and int(m.group(3)) > 0:
                key = (S2B[m.group(1)], int(m.group(2)), int(m.group(3)))
        elif key:
            # keep the words of Jesus (red letters) as private-use markers
            line = line.replace('<q marker="" who="Jesus">', '').replace('</q>', '')
            txt = clean(line)
            txt = re.sub(r'\s*', ' ', txt)          # merge adjacent quotes
            if txt.count('') > txt.count(''): txt += ''
            txt = re.sub(r'\s+([,.;:!?])', r'\1', txt)
            if txt:
                data.setdefault(key[0], {}).setdefault(key[1], {})[key[2]] = txt
    return data

kjv = load_bible('KJV.imp')
web = load_bible('WEB.imp')
chapcounts = [len(kjv[b]) for b in BOOKS]
print('books', len(kjv), 'chapters', sum(chapcounts))

# ---------- Matthew Henry Concise ----------
full = open(os.path.join(DL, 'mhcc_full.txt'), encoding='utf-8').read()
# drop stray osis <chapter> tags (fragment noise); keep structure via titles/headings
ev_re = re.compile(
    r'(?P<book><title type="x-ms">[^<]*</title>|<div canonical="true" osisID="[^"]+" sID="[^"]+" type="book"/>)'
    r'|<title type="x-s2">Chapter (?P<ch>\d+)</title>'
    r'|<hi type="bold">(?P<vv>Verses? [^<]*)</hi>')

mh = {}   # book -> chapter -> {'intro':str, 'sections':[...]}
bi = 0; ch = 0; pending = True; cur = None; prev_start = 0
buf = []
def flush():
    global buf
    txt = clean(' '.join(buf)); buf = []
    if not txt or cur is None: return
    kind, b, c, rng = cur
    entry = mh.setdefault(b, {}).setdefault(c, {'intro': '', 'sections': []})
    if kind == 'intro':
        entry['intro'] = (entry['intro'] + ' ' + txt).strip()
    else:
        entry['sections'].append({'s': rng[0], 'e': rng[1], 'label': rng[2], 't': txt})

def parse_range(label):
    nums = [int(n) for n in re.findall(r'\d+', label)]
    if not nums: return None
    return (min(nums), max(nums), label.strip())

last = 0
for m in ev_re.finditer(full):
    buf.append(full[last:m.start()]); last = m.end()
    if m.group('book'):
        if not pending:
            flush(); bi += 1; ch = 0; pending = True
            cur = ('intro', BOOKS[bi], 0, None)
        elif cur is None:
            cur = ('intro', BOOKS[bi], 0, None)
    elif m.group('ch'):
        n = int(m.group('ch'))
        flush()
        if pending:
            pending = False
        elif n <= ch or n > chapcounts[bi]:
            bi += 1
        ch = n
        prev_start = 0
        cur = ('intro', BOOKS[bi], ch, None)
    else:
        flush()
        if pending:   # chapter title missing right after a book start
            pending = False; ch = 1; prev_start = 0
        r = parse_range(m.group('vv'))
        if r:
            if r[0] <= prev_start and ch > 0:
                # numbering restarted without a chapter title: next chapter or next book
                if ch < chapcounts[bi]: ch += 1
                else: bi += 1; ch = 1
            prev_start = r[0]
            cur = ('sec', BOOKS[bi], ch, r)
buf.append(full[last:]); flush()

# validate
bad = []
for i, b in enumerate(BOOKS):
    got = sorted(c for c in mh.get(b, {}) if c > 0)
    if not got or got[-1] != chapcounts[i]:
        bad.append((b, chapcounts[i], got[-3:] if got else None))
print('books with chapter mismatch:', bad)
missing = [(b, c) for i, b in enumerate(BOOKS) for c in range(1, chapcounts[i] + 1)
           if not mh.get(b, {}).get(c, {}).get('sections')]
print('chapters without sections:', len(missing), missing[:40])

# ---------- write per-book files ----------
index = []
for i, b in enumerate(BOOKS):
    slug = re.sub(r'[^a-z0-9]+', '-', b.lower()).strip('-')
    obj = {'book': b, 'kjv': {}, 'web': {}}
    for c in range(1, chapcounts[i] + 1):
        nv = max(kjv[b][c])
        obj['kjv'][c] = [kjv[b][c].get(v, '') for v in range(1, nv + 1)]
        wv = web.get(b, {}).get(c, {})
        obj['web'][c] = [wv.get(v, '') for v in range(1, max(wv or {0: 0}) + 1)]
        e = None
        if e:
            secs = e['sections']
            # a section runs until the next heading (some headings are missing in the source)
            for k, s in enumerate(secs):
                nxt = secs[k + 1]['s'] - 1 if k + 1 < len(secs) else nv
                s['e'] = max(min(s['e'], nv), nxt) if nxt >= s['s'] else s['e']
                s['label'] = ('Verse %d' % s['s']) if s['s'] == s['e'] else ('Verses %d–%d' % (s['s'], s['e']))
            obj['mh'][c] = e
    with open(os.path.join(OUT, slug + '.json'), 'w') as f:
        json.dump(obj, f, separators=(',', ':'), ensure_ascii=False)
    index.append({'name': b, 'slug': slug, 'chapters': [len(obj['kjv'][c]) for c in range(1, chapcounts[i] + 1)]})
json.dump(index, open('/home/claude/build/index.json', 'w'), separators=(',', ':'))
print('done')
