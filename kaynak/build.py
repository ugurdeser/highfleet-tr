"""Turkce cevirileri birlestirir, ASCII'ye indirir, dogrular, sifreler, oyuna kurar."""
import json, os, re, sys, glob, shutil

GAME = os.environ.get('HIGHFLEET_DIR',
                      r'C:\Program Files (x86)\Steam\steamapps\common\HighFleet')
DEST = os.path.join(GAME, 'Data', 'Dialogs', 'english.seria_enc')

FOLD = str.maketrans({
    'ç': 'c', 'Ç': 'C', 'ğ': 'g', 'Ğ': 'G', 'ı': 'i', 'İ': 'I',
    'ö': 'o', 'Ö': 'O', 'ş': 's', 'Ş': 'S', 'ü': 'u', 'Ü': 'U',
    'â': 'a', 'Â': 'A', 'î': 'i', 'Î': 'I', 'û': 'u', 'Û': 'U',
    '’': "'", '‘': "'", '“': '"', '”': '"', '—': '-', '–': '-', '…': '...',
})

# ceviride birebir korunmasi gereken isaretleme
# ANS haric: <ANS=metin|HEDEF> icindeki metin cevrilir, hedefleri asagida ayrica denetlenir
MARKUP = re.compile(r'<(?!ANS=)[A-Za-z_]+=[^>]*>|<[A-Za-z_]+>|\{(?:font|align|color|animation|shift|max)=[^}]*\}')


def crypt(data):
    out = bytearray(len(data))
    b = 2531011
    for i, c in enumerate(data):
        out[i] = (b ^ (b >> 15) ^ c) & 0xFF
        b = (b + 214013) & 0xFFFFFFFF
    return bytes(out)


segments = json.load(open('segments.json', encoding='utf-8'))
by_id = {s['id']: s for s in segments}

tr = {}
for path in sorted(glob.glob('tr/*.txt')):
    for ln, line in enumerate(open(path, encoding='utf-8').read().split('\n'), 1):
        if not line.strip():
            continue
        sid, _, text = line.partition('\t')
        if not sid.strip().isdigit():
            sys.exit(f'{path}:{ln} id okunamadi: {line[:80]!r}')
        tr[int(sid)] = text

missing = [s['id'] for s in segments if s['id'] not in tr]
print(f'ceviri: {len(tr)}/{len(segments)} segment' + (f' — eksik {len(missing)}' if missing else ' — tamam'))

# --- dogrulama: isaretleme kaybolmus mu?
problems = []
for sid, text in tr.items():
    src = by_id[sid]['text']
    a, b = sorted(MARKUP.findall(src)), sorted(MARKUP.findall(text))
    if a != b:
        problems.append((sid, 'isaretleme', set(a) ^ set(b)))
    ga, gb = src.count('{glossary='), text.count('{glossary=')
    if ga != gb:
        problems.append((sid, 'glossary sayisi', f'{ga} -> {gb}'))
    for m in re.finditer(r'\{glossary=[^,}]*,([^}]*)\}', text):
        if m.group(1) not in src:
            problems.append((sid, 'glossary anahtari', m.group(1)))
    # |HEDEF biciminde gecen butun dallanma hedefleri (ANS sarmalayicisi olmayanlar dahil)
    if sorted(re.findall(r'\|[A-Z][A-Za-z0-9_]*(?:=-?\d+)?', src)) != \
       sorted(re.findall(r'\|[A-Z][A-Za-z0-9_]*(?:=-?\d+)?', text)):
        problems.append((sid, 'dallanma hedefi', src[-60:] + '  ->  ' + text[-60:]))
    # <ANS=metin|HEDEF...> icindeki hedefler degismemeli
    for sa, sb in zip(re.findall(r'<ANS=([^>]*)>', src), re.findall(r'<ANS=([^>]*)>', text)):
        if sa.split('|')[1:] != sb.split('|')[1:]:
            problems.append((sid, 'ANS hedefi', f'{sa.split("|")[1:]} -> {sb.split("|")[1:]}'))

if problems:
    print(f'\n!! {len(problems)} sorun:')
    for p in problems[:25]:
        print('  ', p)
    if '--force' not in sys.argv:
        sys.exit('\nduzeltmeden kurulmadi (--force ile gecebilirsin)')

# --- satirlari yeniden kur
lines = open('english.seria', 'rb').read().decode('latin-1').split('\n')
for s in segments:
    if s['id'] not in tr:
        continue
    text = tr[s['id']].translate(FOLD)
    # hizalama icin anlamli olan bas/son bosluklari cevirmen kaybettiyse geri koy
    src = s['text']
    lead = src[:len(src) - len(src.lstrip())]
    trail = src[len(src.rstrip()):]
    if text.strip():
        text = lead + text.strip() + trail
    bad = [c for c in text if ord(c) > 126]
    if bad:
        sys.exit(f"id {s['id']}: ASCII disi karakter {bad!r}")
    i = s['line']
    if lines[i].startswith('#') and '\t' in lines[i]:
        lines[i] = lines[i].split('\t')[0] + '\t' + text
    else:
        lines[i] = text

# --- satir bazli ek yamalar (Kiril filtresinin yanlislikla atladigi satirlar)
extra = 'tr/_extra.tsv'
if os.path.exists(extra):
    n = 0
    for row in open(extra, encoding='utf-8').read().split('\n'):
        if not row.strip() or row.startswith('#!'):
            continue
        ln, _, text = row.partition('\t')
        lines[int(ln)] = text.translate(FOLD)
        n += 1
    print(f'{n} ek satir yamandi')

out = '\n'.join(lines).encode('latin-1')
open('turkish.seria', 'wb').write(out)
print(f'turkish.seria yazildi ({len(out)} bayt)')

if '--install' in sys.argv:
    shutil.copy(DEST, DEST + '.bak')
    open(DEST, 'wb').write(crypt(out))
    print(f'kuruldu -> {DEST}')
