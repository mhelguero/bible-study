"""Build data/cl-{code}-{book}.json for the public-domain classic commentaries.

Usage: python3 build/classics.py MODULES_DIR REPO_DIR
  MODULES_DIR  unzipped CrossWire modules (Barnes, Clarke, JFB, Wesley, MHCC, Geneva, Scofield, PNT),
               from https://crosswire.org/ftpmirror/pub/sword/packages/rawzip/{name}.zip
  REPO_DIR     a clone of github.com/samueldotj/bible-commentaries (en/poole, en/calvin JSON)

Output per commentary and book: {"chapter": [[firstVerse, lastVerse, [[kind, html], ...]], ...]}
  verse 0 = the chapter's introduction; kind "h" = heading, "p" = paragraph; html uses only <b> and <i>.
"""
import html, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sword_read import read_module, INDEX

ROOT = Path(__file__).resolve().parent.parent
USFM = 'GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER LAM EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV'.split()
SLUG = {u: b['slug'] for u, b in zip(USFM, INDEX)}

SWORD = {'barnes': 'Barnes', 'clarke': 'Clarke', 'jfb': 'JFB', 'wesley': 'Wesley', 'mhcc': 'MHCC',
         'geneva': 'Geneva', 'scofield': 'Scofield', 'pnt': 'PNT'}
BR = ' '  # paragraph break marker while cleaning

def inline(s):
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\s+([,.;:!?])', r'\1', s)
    return s

def to_items(raw, geneva=False):
    t = raw
    t = re.sub(r'(?s)<note\b.*?</note>', '', t)
    if geneva:  # Geneva repeats the KJV verse (with {a} markers) before <br />; keep only the notes
        parts = re.split(r'<br\s*/?>', t, maxsplit=1)
        if len(parts) == 2 and re.search(r'\{\w+\}', parts[0]): t = parts[1]
    t = re.sub(r'(?s)<title\b[^>]*>(.*?)</title>', lambda m: f'{BR}\u0001{m.group(1)}{BR}', t)
    t = re.sub(r'<row>', BR, t); t = re.sub(r'</cell>\s*<cell>', ' ', t)
    t = re.sub(r'<item\b[^>]*>', BR, t)
    t = re.sub(r'<div\b[^>]*type="x-p"[^>]*/>|<p\b[^>]*>|</p>|(?:<br\s*/?>\s*){1,}|<lb\b[^>]*/>|<div\b[^>]*/>', BR, t)
    t = re.sub(r'<hi type="bold">|<b>', '\u0002', t); t = re.sub(r'<hi type="italic">|<i>', '\u0003', t)
    t = re.sub(r'</hi>', '\u0004', t); t = t.replace('</b>', '\u0005').replace('</i>', '\u0006')
    t = re.sub(r'<[^>]+>', '', t)
    t = html.unescape(t)
    t = html.escape(t, quote=False)
    t = t.replace('\u0002', '<b>').replace('\u0005', '</b>').replace('\u0003', '<i>').replace('\u0006', '</i>')
    t = t.replace('\u0004', '</b>')  # OSIS </hi> closes bold or italic; fixed below
    items = []
    for chunk in t.split(BR):
        head = '\u0001' in chunk
        chunk = inline(chunk.replace('\u0001', ''))
        chunk = balance(chunk)
        plain = re.sub(r'<[^>]+>', '', chunk).strip()
        if not plain or re.fullmatch(r'(?i)chapter\s+\d+\.?', plain): continue  # the app already shows the chapter
        items.append(['h' if head else 'p', chunk])
    return items

def balance(s):
    # make <b>/<i> well formed after </hi> guessing: rebuild with a stack
    out, stack = [], []
    for tok in re.split(r'(</?[bi]>)', s):
        m = re.fullmatch(r'<(/?)([bi])>', tok)
        if not m: out.append(tok); continue
        close, tag = m.groups()
        if not close: stack.append(tag); out.append(tok)
        elif stack:
            out.append(f'</{stack.pop()}>')
    out += [f'</{t}>' for t in reversed(stack)]
    return re.sub(r'<([bi])>\s*</\1>', '', ''.join(out))

def from_sword(mods, code):
    conf, ents = read_module(mods / SWORD[code])
    n_verses = {b['slug']: b['chapters'] for b in INDEX}
    books = {}
    for book, ch, v1, v2, raw in ents:
        if ch == 0: continue  # book introductions are skipped
        items = to_items(raw, geneva=(code == 'geneva'))
        if not items: continue
        if v1 > 0:  # some modules index a note under fewer verses than its own "Verses 9-21" headings cover
            for kind, h in items:
                m = re.match(r'(?:<b>)?\s*Verses?\s+(\d+)(?:\s*[-–]\s*(\d+))?\b', h)
                if m and int(m.group(1)) >= v1: v2 = max(v2, int(m.group(2) or m.group(1)))
            v2 = min(v2, n_verses[book][ch - 1])
        books.setdefault(book, {}).setdefault(str(ch), []).append([v1, v2, items])
    if code == 'mhcc':  # Henry's concise notes are whole sections: each runs until the next one starts
        for slug, chs in books.items():
            for ch, units in chs.items():
                us = sorted([u for u in units if u[0] > 0], key=lambda u: u[0])
                for a, b in zip(us, us[1:] + [None]):
                    a[1] = max(a[1], (b[0] - 1) if b else n_verses[slug][int(ch) - 1])
    return conf.get('Description', code), books

def from_repo(repo, code):
    books = {}
    for f in sorted((repo / 'en' / code).glob('*/*.json')):
        if f.stem == 'intro': continue
        d = json.loads(f.read_text())
        slug = SLUG[d['book']]; ch = d['chapter']
        for u in d['units']:
            rng = u['range'].split('.')
            if len(rng) < 3: v1 = v2 = 0
            else:
                a = rng[2].split('-'); v1 = int(a[0]); v2 = int(a[1]) if len(a) > 1 and '.' not in rng[2] else v1
                if '-' in u['range'] and len(u['range'].split('-')[1].split('.')) > 1: v2 = 999
            items = [['h', html.escape(u['title'])]] if u.get('title') else []
            for p in u['paragraphs']:
                if p.get('footnote'): continue
                txt = html.escape(p['text'], quote=False)
                if p.get('anchor') and not p['text'].startswith(p['anchor']): txt = f"<b>{html.escape(p['anchor'], quote=False)}</b> {txt}"
                items.append(['h' if p.get('heading') else 'p', txt.replace('\n', ' ')])
            if items: books.setdefault(slug, {}).setdefault(str(ch), []).append([v1, v2, items])
    return books

def main():
    mods, repo = Path(sys.argv[1]), Path(sys.argv[2])
    out = ROOT / 'data'; total = 0
    for code in list(SWORD) + ['poole', 'calvin']:
        books = from_repo(repo, code) if code in ('poole', 'calvin') else from_sword(mods, code)[1]
        for slug, chs in books.items():
            p = out / f'cl-{code}-{slug}.json'
            p.write_text(json.dumps(chs, ensure_ascii=False, separators=(',', ':')))
            total += p.stat().st_size
        print(code, 'books', len(books))
    print('total MB', round(total / 1e6, 1))

if __name__ == '__main__':
    main()
