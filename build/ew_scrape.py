import json, re, time, urllib.request, html, sys, os
idx = json.load(open('/home/user/bible-study/build/index.json'))
out_path = 'ew-sections.json'
out = json.load(open(out_path)) if os.path.exists(out_path) else {}
fails = []
H = re.compile(r'<h[2-6][^>]*\bid="(section-\d+)"[^>]*>(.*?)</h[2-6]>', re.S)
def slug(name): return 'psalm' if name == 'Psalms' else name.lower().replace(' ', '-')
for b in idx:
    for c in range(1, len(b['chapters']) + 1):
        key = f"{b['slug']}-{c}"
        if key in out: continue
        url = f"https://enduringword.com/bible-commentary/{slug(b['name'])}-{c}/"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (bible-study personal app; section index)'})
            s = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'replace')
        except Exception as e:
            fails.append([key, url, str(e)[:80]]); print('FAIL', key, e, flush=True); time.sleep(1); continue
        secs = []
        for sid, inner in H.findall(s):
            t = html.unescape(re.sub(r'<[^>]+>', '', inner)).strip()
            m = re.search(r'\(([^)]*\d[^)]*)\)', t)
            secs.append([int(sid.split('-')[1]), m.group(1).strip() if m else ''])
        out[key] = secs
        if len(out) % 25 == 0:
            json.dump(out, open(out_path, 'w')); print(len(out), key, flush=True)
        time.sleep(0.4)
json.dump(out, open(out_path, 'w')); json.dump(fails, open('fails.json', 'w'))
print('DONE', len(out), 'fails', len(fails))
