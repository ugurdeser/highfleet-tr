"""HighFleet english.seria -> cevrilebilir segmentleri batch dosyalarina ayirir."""
import json, os, re

SRC = 'english.seria'
OUT = 'batches'

# cp1252 tipografik karakterleri ASCII'ye indir (dosya zaten ASCII'ye gidecek)
NORM = {
    '\x91': "'", '\x92': "'", '\x93': '"', '\x94': '"',
    '\x96': '-', '\x97': '-', '\x85': '...', '\xa0': ' ',
}

raw = open(SRC, 'rb').read().decode('latin-1')
lines = raw.split('\n')


def norm(s):
    for k, v in NORM.items():
        s = s.replace(k, v)
    return s


def has_cyrillic(s):
    return any(0xC0 <= ord(c) <= 0xFF for c in s)


segments = []   # {id, line, key, text}
for i, line in enumerate(lines):
    if not line.strip():
        continue
    if line.startswith('#'):
        if '\t' not in line:
            continue                      # bolum basligi / bos anahtar
        key, _, val = line.partition('\t')
        key = key[1:]
        if not val.strip():
            continue
    elif line.startswith('<') or line.startswith('{'):
        key, val = '(devam)', line        # <ANS=...> gibi bagimsiz satirlar
    else:
        key, val = '(duz)', line
    if has_cyrillic(val):
        continue                          # Rusca telsiz metni: dokunma
    segments.append({'id': len(segments), 'line': i, 'key': key, 'text': norm(val)})

os.makedirs(OUT, exist_ok=True)
json.dump(segments, open('segments.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)

# ~9000 karakterlik gruplara bol
batch, size, n = [], 0, 0
def flush():
    global batch, size, n
    if not batch:
        return
    with open(f'{OUT}/b{n:03d}.txt', 'w', encoding='utf-8') as f:
        for s in batch:
            f.write(f"{s['id']}\t{s['key']}\t{s['text']}\n")
    n += 1
    batch, size = [], 0

for s in segments:
    if size + len(s['text']) > 9000 and batch:
        flush()
    batch.append(s)
    size += len(s['text'])
flush()

print(f'{len(segments)} segment, {sum(len(s["text"]) for s in segments)} karakter, {n} batch')
