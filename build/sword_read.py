"""Minimal reader for CrossWire SWORD compressed commentary modules (ModDrv zCom / zCom4).

Each testament has three files in the module's data folder:
  {ot,nt}.bzs  blocks: offset, compressed size, uncompressed size (3 x uint32)
  {ot,nt}.bzv  one slot per KJV position: block, offset in block, size
               (uint32, uint32, uint16 for zCom; 3 x uint32 for zCom4)
  {ot,nt}.bzz  zlib-compressed blocks
Slot order: module heading, testament heading, then per book its intro, and per chapter its
intro followed by its verses. A comment covering several verses is stored once; the following
verses point at the same block/offset/size.
"""
import json, struct, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
INDEX = json.loads((HERE / 'index.json').read_text())  # KJV books in order, with verses per chapter

def _ext(data_dir, t):
    # 'b' = book-sized blocks (.bzs/.bzv/.bzz), 'c' = chapter-sized (.czs/...), 'v' = verse-sized; same layout
    for k in 'bcv':
        if (data_dir / f'{t}.{k}zv').exists(): return k
    return None

def _testament(data_dir, t, books, wide):
    k = _ext(data_dir, t)
    bzs = (data_dir / f'{t}.{k}zs').read_bytes(); bzv = (data_dir / f'{t}.{k}zv').read_bytes(); bzz = (data_dir / f'{t}.{k}zz').read_bytes()
    blocks = [struct.unpack_from('<III', bzs, i) for i in range(0, len(bzs), 12)]
    cache = {}
    def block(n):
        if n not in cache:
            off, size, _ = blocks[n]; cache[n] = zlib.decompress(bzz[off:off + size])
        return cache[n]
    fmt, w = ('<III', 12) if wide else ('<IIH', 10)
    index = [struct.unpack_from(fmt, bzv, i) for i in range(0, len(bzv), w)]
    pos = []
    for b in books:
        pos.append((b['slug'], 0, 0))
        for c, n in enumerate(b['chapters'], 1):
            pos.append((b['slug'], c, 0)); pos += [(b['slug'], c, v) for v in range(1, n + 1)]
    if len(index) != len(pos) + 2:
        raise ValueError(f'{t}: {len(index)} slots, expected {len(pos) + 2}')
    out, last = [], None
    for (book, ch, v), key in zip(pos, index[2:]):
        if key[2] == 0: last = None; continue
        if v > 0 and key == last and out[-1][0] == book and out[-1][1] == ch:
            out[-1][3] = v; continue
        n, off, size = key
        out.append([book, ch, v, v, block(n)[off:off + size].decode('utf-8', 'replace')])
        last = key if v > 0 else None
    return out

def read_module(mod_dir):
    mod_dir = Path(mod_dir)
    conf = {}
    for line in next((mod_dir / 'mods.d').glob('*.conf')).read_text(errors='replace').splitlines():
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1); conf.setdefault(k.strip(), v.strip())
    drv = conf['ModDrv'].lower(); assert drv in ('zcom', 'zcom4'), drv
    data = mod_dir / conf['DataPath'].lstrip('./')
    ents = []
    if _ext(data, 'ot'): ents += _testament(data, 'ot', INDEX[:39], drv == 'zcom4')
    if _ext(data, 'nt'): ents += _testament(data, 'nt', INDEX[39:], drv == 'zcom4')
    return conf, ents  # [book_slug, chapter, verse_start, verse_end, raw markup]
