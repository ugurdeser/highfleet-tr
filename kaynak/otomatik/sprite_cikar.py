"""Oyundaki Ingilizce gomulu sprite'lari tek tek PNG olarak disari aktarir."""
import os, re, glob, json, csv
from PIL import Image

GAME = os.environ.get('HIGHFLEET_DIR', r'E:\SteamLibrary\steamapps\common\HighFleet')
OUT = os.path.expanduser(r'~\Desktop\HighFleet-Menu-Resimleri')

ANIM = re.compile(r'Animation\s+([A-Za-z0-9_]+)\s*\{(.*?)\}', re.S)

os.makedirs(OUT, exist_ok=True)
manifest = []
atlas_cache = {}

for res_path in sorted(glob.glob(os.path.join(GAME, 'Media', 'Tex*', '*.res'))):
    body = open(res_path, encoding='latin-1').read()
    # bu .res hangi png'yi kullaniyor
    tex = {}
    for m in re.finditer(r'Texture\s+(\w+)\s*\{(.*?)\}', body, re.S):
        fn = re.search(r'filename\s*=\s*(\S+)', m.group(2))
        if fn:
            tex[m.group(1)] = fn.group(1).strip()

    for m in ANIM.finditer(body):
        name, blk = m.group(1), m.group(2)
        if not name.lower().endswith('_eng'):
            continue
        t = re.search(r'texture\s*=\s*(\w+)', blk)
        r = re.search(r'rect\s*=\s*(\d+),(\d+),(\d+),(\d+)', blk)
        if not (t and r and t.group(1) in tex):
            continue
        png_rel = tex[t.group(1)].replace('/', os.sep)
        png_abs = os.path.join(GAME, png_rel)
        if png_abs not in atlas_cache:
            atlas_cache[png_abs] = Image.open(png_abs).convert('RGBA')
        atlas = atlas_cache[png_abs]

        x, y, w, h = (int(v) for v in r.groups())
        fr = re.search(r'frames\s*=\s*(\d+)', blk)
        frames = int(fr.group(1)) if fr else 1
        total_w = w * frames

        crop = atlas.crop((x, y, x + total_w, y + h))
        sub = os.path.join(OUT, os.path.splitext(os.path.basename(png_rel))[0])
        os.makedirs(sub, exist_ok=True)
        out_png = os.path.join(sub, name + '.png')
        crop.save(out_png)

        manifest.append({
            'dosya': os.path.relpath(out_png, OUT).replace(os.sep, '/'),
            'atlas': png_rel.replace(os.sep, '/'),
            'anim': name, 'x': x, 'y': y, 'w': w, 'h': h,
            'frames': frames, 'genislik_toplam': total_w,
        })

json.dump(manifest, open(os.path.join(OUT, 'manifest.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
with open(os.path.join(OUT, 'liste.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    wcsv = csv.DictWriter(f, fieldnames=list(manifest[0].keys()), delimiter=';')
    wcsv.writeheader()
    wcsv.writerows(manifest)

print(f'{len(manifest)} sprite cikarildi -> {OUT}')
multi = [m for m in manifest if m['frames'] > 1]
print(f'  cok kareli (dikkat): {len(multi)}')
for m in multi:
    print('   ', m['dosya'], m['frames'], 'kare')
