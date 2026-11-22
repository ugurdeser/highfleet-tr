r"""HighFleet Turkce Yama - gorsel (texture) kurulumu.

Oyunun bazi yazilari diyalog dosyasinda degil, dogrudan texture atlaslarinin
icine cizilmistir: ana menu, posterler, paneller, uyari levhalari. Bu betik
o sprite'larin Turkcelestirilmis hallerini SENIN kendi atlaslarina isler.

Tam atlaslar dagitilmaz (177 MB tutardi ve oyunun dokunulmamis sanat
varliklarini gereksizce cogaltirdi); sadece degisen sprite'lar dagitilir ve
burada yerlerine yapistirilir.

KULLANIM
    python yama_uygula.py             kontrol eder, hicbir sey yazmaz
    python yama_uygula.py --yaz       atlaslara yazar
    python yama_uygula.py --geri-al   yedeklerden geri doner

Oyun otomatik bulunamazsa:
    set HIGHFLEET_DIR=D:\Steam\steamapps\common\HighFleet
    python yama_uygula.py --yaz

GEREKSINIM: Python 3.8+ ve Pillow  ->  pip install pillow
"""
import os
import sys
import json
import shutil

try:
    from PIL import Image
except ImportError:
    sys.exit('Pillow kurulu degil.\n\n    pip install pillow\n\n'
             'Python yoksa: https://www.python.org/downloads/ '
             '(kurulumda "Add Python to PATH" isaretli olsun)')

HERE = os.path.dirname(os.path.abspath(__file__))
YAZ = '--yaz' in sys.argv
GERI = '--geri-al' in sys.argv

ARANACAK = [
    r'{d}:\Program Files (x86)\Steam\steamapps\common\HighFleet',
    r'{d}:\Steam\steamapps\common\HighFleet',
    r'{d}:\SteamLibrary\steamapps\common\HighFleet',
    r'{d}:\Games\Steam\steamapps\common\HighFleet',
    r'{d}:\SteamGames\steamapps\common\HighFleet',
]


def oyunu_bul():
    ort = os.environ.get('HIGHFLEET_DIR')
    if ort and os.path.exists(os.path.join(ort, 'Highfleet.exe')):
        return ort
    for d in 'CDEFGH':
        for kalip in ARANACAK:
            yol = kalip.format(d=d)
            if os.path.exists(os.path.join(yol, 'Highfleet.exe')):
                return yol
    return None


def main():
    oyun = oyunu_bul()
    if not oyun:
        print('Oyun otomatik bulunamadi.')
        print('Steam > HighFleet > sag tik > Yonet > Yerel dosyalara goz at')
        print('diyerek acilan klasorun yolunu yapistir:')
        oyun = input('HighFleet klasoru: ').strip().strip('"')
        if not os.path.exists(os.path.join(oyun, 'Highfleet.exe')):
            sys.exit('Bu klasorde Highfleet.exe yok: ' + oyun)
    print('Oyun bulundu:', oyun)

    man = json.load(open(os.path.join(HERE, 'manifest.json'), encoding='utf-8'))
    atlaslar = sorted({m['atlas'] for m in man})

    # --- geri alma
    if GERI:
        n = 0
        for rel in atlaslar:
            ap = os.path.join(oyun, rel.replace('/', os.sep))
            if os.path.exists(ap + '.orig'):
                shutil.copy2(ap + '.orig', ap)
                print('geri alindi:', rel)
                n += 1
        print(f'\n{n} atlas orijinaline dondu.' if n else
              '\nYedek bulunamadi. Steam > HighFleet > Yonet > '
              'Oyun dosyalarinin butunlugunu dogrula.')
        return

    # --- dogrulama
    hata = []
    for m in man:
        p = os.path.join(HERE, m['dosya'].replace('/', os.sep))
        if not os.path.exists(p):
            hata.append(f"{m['dosya']}: yama dosyasi eksik")
            continue
        if Image.open(p).size != (m['genislik_toplam'], m['h']):
            hata.append(f"{m['dosya']}: yanlis olcu")
    for rel in atlaslar:
        if not os.path.exists(os.path.join(oyun, rel.replace('/', os.sep))):
            hata.append(f'{rel}: oyunda bulunamadi')
    if hata:
        print('\n!! SORUNLAR:')
        for h in hata:
            print('  ', h)
        sys.exit(1)

    print(f'{len(man)} sprite, {len(atlaslar)} atlas. Hepsi dogrulandi.')
    if not YAZ:
        print('\nKontrol modu, hicbir sey yazilmadi.')
        print('Kurmak icin:  python yama_uygula.py --yaz')
        return

    # --- yazma
    acik = {}
    for rel in atlaslar:
        ap = os.path.join(oyun, rel.replace('/', os.sep))
        if not os.path.exists(ap + '.orig'):
            shutil.copy2(ap, ap + '.orig')
            print('yedeklendi:', rel + '.orig')
        # yedek varsa ondan basla: ust uste yama binmesin
        acik[ap] = Image.open(ap + '.orig').convert('RGBA')

    for m in man:
        ap = os.path.join(oyun, m['atlas'].replace('/', os.sep))
        im = Image.open(os.path.join(HERE, m['dosya'].replace('/', os.sep))).convert('RGBA')
        acik[ap].paste(im, (m['x'], m['y']))

    for ap, img in acik.items():
        img.save(ap)
        print('yazildi:', os.path.relpath(ap, oyun))

    print(f'\n{len(man)} sprite islendi. Oyunu yeniden baslat.')
    print('Geri almak icin:  python yama_uygula.py --geri-al')


if __name__ == '__main__':
    try:
        main()
    except PermissionError:
        print('\nHATA: Dosyaya yazilamadi. Oyun kapali mi? '
              'Gerekirse komut istemini yonetici olarak ac.')
    # Cift tiklayinca pencere kapanmasin diye bekle; borulu/otomatik
    # calistirmada stdin olmayabilir, o zaman sessizce gec.
    try:
        input('\nCikmak icin Enter...')
    except EOFError:
        pass
