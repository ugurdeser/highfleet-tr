r"""HighFleet sprite'larini Gemini ile otomatik Turkcelestiren is hatti.

n8n mantigi: her sprite bir "is". Isler sirayla yurur, durumu durum.json'a
yazilir, program yarida kesilirse kaldigi yerden devam eder.

AKIS
  1. OKU    gemini-2.5-flash goruntuyu okur -> Ingilizce metni + Turkce
            karsiligini JSON olarak dondurur      -> ceviri.json
  2. CIZ    gemini-2.5-flash-image orijinal resmi + hedef metni alir,
            yazisi Turkce olan yeni resmi uretir  -> cikti/
  3. UYGULA onayladigin ciktilar calisma PNG'lerinin uzerine kopyalanir,
            sonra ust klasordeki geri_yukle.py atlaslara yazar.

Adim 1 ile 2 arasinda ceviri.json'u elle duzenleyebilirsin; ne yazarsa
resme o cizilir.

KULLANIM
  set GEMINI_API_KEY=...
  python pipeline.py --oku              butun sprite'lari okut+cevir
  python pipeline.py --oku --klasor Desk1
  python pipeline.py --ciz --klasor Desk1
  python pipeline.py --uygula           onaylananlari yerine koy
  python pipeline.py --durum            ozet
  python pipeline.py --sifirla dosya.png   tek isi bastan yaptir

SECENEKLER
  --klasor AD     sadece o atlas klasoru (Desk1, Mapmode1, ...)
  --dosya AD      tek sprite (title_exit_eng)
  --limit N       en fazla N is isle (deneme icin)
  --bekle SN      istekler arasi bekleme (varsayilan 4 sn)
  --alfa-serbest  orijinal seffaflik maskesini zorlama
"""
import os, sys, json, time, base64, io, shutil, argparse, urllib.request, urllib.error
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(HERE)                      # HighFleet-Menu-Resimleri
CIKTI = os.path.join(HERE, 'cikti')
KARS = os.path.join(HERE, 'karsilastirma')
KARS_URET = False   # --karsilastirma ile acilir
DURUM_YOL = os.path.join(HERE, 'durum.json')
CEVIRI_YOL = os.path.join(HERE, 'ceviri.json')
SOZLUK_YOL = os.path.join(HERE, 'sozluk.json')

API = 'https://generativelanguage.googleapis.com/v1beta/models'
MODEL_OKU = 'gemini-3.6-flash'
MODEL_CIZ = 'gemini-3.1-flash-image'

def _anahtar_bul():
    """Once ortam degiskeni, sonra yanindaki anahtar.txt dosyasi."""
    a = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if a and a.strip():
        return a.strip()
    yol = os.path.join(HERE, 'anahtar.txt')
    if os.path.exists(yol):
        for satir in open(yol, encoding='utf-8-sig'):
            satir = satir.strip()
            if satir and not satir.startswith('#'):
                return satir
    return None


ANAHTAR = _anahtar_bul()


# ----------------------------------------------------------------- yardimci
def json_oku(yol, varsayilan):
    if os.path.exists(yol):
        with open(yol, encoding='utf-8') as f:
            return json.load(f)
    return varsayilan


def json_yaz(yol, veri):
    gecici = yol + '.tmp'
    with open(gecici, 'w', encoding='utf-8') as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)
    os.replace(gecici, yol)


def istek(model, govde, deneme=4):
    """Gemini REST cagrisi. 429/5xx'te artan bekleme ile tekrar dener."""
    if not ANAHTAR:
        raise SystemExit(
            'API anahtari bulunamadi.\n\n'
            '  1) Ucretsiz anahtar al:  https://aistudio.google.com/apikey\n'
            '  2) Su dosyayi olustur, icine anahtari tek satir yapistir:\n'
            f'     {os.path.join(HERE, "anahtar.txt")}\n\n'
            '  (Alternatifi:  set GEMINI_API_KEY=AIza... )')
    url = f'{API}/{model}:generateContent'
    veri = json.dumps(govde).encode('utf-8')
    son = None
    for i in range(deneme):
        req = urllib.request.Request(url, data=veri, headers={
            'Content-Type': 'application/json',
            'x-goog-api-key': ANAHTAR,
        })
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            govdeh = e.read().decode('utf-8', 'replace')[:400]
            son = f'HTTP {e.code}: {govdeh}'
            if e.code in (429, 500, 502, 503, 504) and i < deneme - 1:
                b = 5 * (2 ** i)
                print(f'      ...{e.code}, {b} sn bekleyip tekrar')
                time.sleep(b)
                continue
            raise RuntimeError(son)
        except Exception as e:                       # ag hatasi
            son = str(e)
            if i < deneme - 1:
                time.sleep(5 * (2 ** i))
                continue
            raise RuntimeError(son)
    raise RuntimeError(son)


def kaynak_yol(m):
    """Sprite'in DOKUNULMAMIS halinin yolu.

    --uygula calisma kopyalarinin uzerine yazdigi icin, yeniden cizerken
    calisma kopyasini kaynak almak modelin kendi ciktisini tekrar
    uretmesine yol acar. Kaynak her zaman _orijinal/ olmali.
    """
    rel = m['dosya'].replace('/', os.sep)
    ok = os.path.join(KOK, '_orijinal', rel)
    return ok if os.path.exists(ok) else os.path.join(KOK, rel)


def png_b64(yol):
    with open(yol, 'rb') as f:
        return base64.b64encode(f.read()).decode('ascii')


def isler(args):
    man = json_oku(os.path.join(KOK, 'manifest.json'), [])
    out = []
    for m in man:
        klasor, ad = m['dosya'].split('/', 1)
        ad = os.path.splitext(ad)[0]
        if args.klasor and klasor.lower() != args.klasor.lower():
            continue
        if args.dosya and args.dosya.lower() not in ad.lower():
            continue
        out.append(m)
    return out


# ------------------------------------------------------------------ 1. OKU
OKU_TALIMAT = """Bu görsel, HighFleet adlı oyunun arayüzünden kesilmiş bir parçadır.

ÖNCE SINIFLANDIR. "icerik" alanına şunlardan tam birini yaz:

  "yazi_yok"  : Görselde hiç okunabilir yazı yok. Sadece simge, çizim,
                doku, çerçeve, ölçek çizgisi, sayı kadranı vb. var.
                Tek tük harf gibi duran ama kelime oluşturmayan
                işaretler de yazı sayılmaz.
  "rusca"     : Yazının tamamı Rusça / Kiril alfabesinde.
  "ingilizce" : Yazının tamamı İngilizce.
  "karisik"   : Hem İngilizce hem Rusça yazı var.

SONRA, sınıfa göre:

- "yazi_yok" veya "rusca" ise: "ingilizce" ve "turkce" alanlarını boş
  bırak. Bu görsele dokunulmayacak. ÇEVİRİ ÜRETME.

- "ingilizce" ise: metni harfi harfine oku ve Türkçesini ver.

- "karisik" ise: SADECE İngilizce kısmı çevir. Kiril alfabesindeki
  her şeyi olduğu gibi, harfi harfine koru. "turkce" alanına
  görselin son halinde yazması gereken metnin tamamını yaz:
  Rusça kısımlar aynen, İngilizce kısımlar Türkçeleşmiş olarak.

Çeviri kuralları:
1. Oyun; 1950'ler Sovyet estetiğinde, askeri, ciddi ve sert bir havada
   geçen bir hava filosu savaş oyunudur. Askeri terimleri Türk Silahlı
   Kuvvetleri kullanımına yakın seç. Kısa ve tok yaz, süsleme yapma.
2. Metin sabit genişlikte bir kutuya sığmak zorunda. Türkçe karşılık,
   İngilizce metinden en fazla %15 daha uzun olabilir. Sığmıyorsa daha
   kısa bir eşanlamlı seç.
3. Türkçe karakterleri (ç ğ ı İ ö ş ü) serbestçe kullan.
4. Özel adları, gemi adlarını, model kodlarını ve sayıları çevirme.
5. Satır yapısını koru: kaç satırsa o kadar satır, aynı sırada.

AYRICA yazının YÖNÜNÜ bildir. "yon" alanına şunlardan birini yaz:
  0   : yazı yatay, soldan sağa okunuyor (normal durum)
  90  : yazı 90 derece döndürülmüş, YUKARIDAN AŞAĞI okunuyor
        (okumak için başını sağa yatırman gerekir)
  270 : yazı 90 derece ters döndürülmüş, AŞAĞIDAN YUKARI okunuyor
        (okumak için başını sola yatırman gerekir)
Yazı yoksa 0 yaz.

SADECE şu biçimde JSON döndür, başka hiçbir şey yazma:
{"icerik": "...", "yon": 0, "ingilizce": "...", "turkce": "...", "not": "kısa gerekçe veya boş"}"""


def sozluk_metni():
    """Terim sozlugunu prompta eklenecek metne cevirir.

    Her sprite modele tek basina gidiyor ve otekilerden haberi yok; sozluk
    olmadan ayni Ingilizce terim farkli sprite'larda farkli cevriliyor.
    """
    d = json_oku(SOZLUK_YOL, {})
    ciftler = [(k, v) for k, v in d.items() if not k.startswith('_')]
    if not ciftler:
        return ''
    satir = '\n'.join(f'  {k} = {v}' for k, v in ciftler)
    return ('\n\nZORUNLU TERIM SOZLUGU. Bu terimler gorselde geciyorsa '
            'karsisindaki Turkce karsiligi AYNEN kullan, baska bir esanlamli '
            'secme. Oyunun tamami boyunca tutarli olmasi gerekiyor:\n' + satir)


def adim_oku(m, ceviri):
    yol = kaynak_yol(m)
    y = istek(MODEL_OKU, {
        'contents': [{'parts': [
            {'text': OKU_TALIMAT + sozluk_metni()},
            {'text': f"Bu görselin piksel ölçüsü: {m['genislik_toplam']}x{m['h']}."},
            {'inline_data': {'mime_type': 'image/png', 'data': png_b64(yol)}},
        ]}],
        'generationConfig': {'temperature': 0.2, 'responseMimeType': 'application/json'},
    })
    try:
        ham = y['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError):
        raise RuntimeError('beklenmeyen yanit: ' + json.dumps(y)[:300])
    d = json.loads(ham)
    icerik = (d.get('icerik') or '').strip().lower()
    if icerik not in ('yazi_yok', 'rusca', 'ingilizce', 'karisik'):
        # model sinifi vermediyse metne bakip kendimiz karar verelim
        ing = (d.get('ingilizce') or '').strip()
        icerik = 'ingilizce' if ing else 'yazi_yok'
    try:
        yon = int(d.get('yon', 0) or 0)
    except (TypeError, ValueError):
        yon = 0
    if yon not in (0, 90, 270):
        yon = 0
    ceviri[m['dosya']] = {
        'icerik': icerik,
        'yon': yon,
        'ingilizce': (d.get('ingilizce') or '').strip(),
        'turkce': (d.get('turkce') or '').strip(),
        'not': (d.get('not') or '').strip(),
        'olcu': f"{m['genislik_toplam']}x{m['h']}",
    }
    return ceviri[m['dosya']]


# Cizilecek olanlar: sadece Ingilizce ya da karisik icerik.
# Yazisi olmayan ve tamami Rusca olan sprite'lara dokunulmaz.
CIZILIR = ('ingilizce', 'karisik')


# ------------------------------------------------------------------ 2. CIZ
def sprite_analiz(orj):
    """Sprite'in saydamlik ve renk yapisini cikarir.

    Oyunun sprite'larinin cogunda ic bolge SAYDAMDIR: kart zemini alttaki
    baska bir sprite'tan gelir, bu dosyada sadece cerceve ve yazi durur.
    Saydamligi siyaha duzlestirip modele gostermek, modele "siyah levha"
    gosterir ve model onu sadakatle yeniden uretir. Bu yuzden sprite'i
    oyundaki gercek gorunumune, yani BEYAZ zemine yerlestirip gonderiyoruz;
    donen goruntuden saydamligi murekkep miktarina gore geri kuruyoruz.
    """
    a = np.asarray(orj, dtype=np.float32)
    alfa = a[..., 3]
    saydam_oran = float((alfa < 128).mean())
    baskin_alfa = int(np.bincount(alfa.round().astype(np.int64).ravel(),
                                  minlength=256).argmax())
    opak = alfa > 128
    if opak.sum() < 8:
        return {'saydam_oran': saydam_oran, 'baskin_alfa': baskin_alfa,
                'zemin': (255, 255, 255), 'metin': (200, 200, 200),
                'koyu_zemin': False}
    lum = a[..., :3].mean(2)
    zl = float(np.bincount(lum[opak].round().astype(np.int64), minlength=256).argmax())
    yakin = opak & (np.abs(lum - zl) <= 1)
    zemin = tuple(int(v) for v in a[..., :3][yakin].mean(0)) if yakin.any() else (255, 255, 255)
    fark = np.abs(lum - zl)
    ic = opak & (fark > max(8.0, float(fark[opak].max()) * 0.4))
    metin = tuple(int(v) for v in a[..., :3][ic].mean(0)) if ic.any() else (200, 200, 200)
    # Saydam zeminli sprite'larda yazi = tam opak pikseller. Zemin RGB'si
    # alfa=0 altinda anlamsiz (cogu zaman siyah) oldugu icin yukaridaki
    # olcum yaniltici olabilir.
    tam_opak = alfa > 200
    if (alfa < 32).mean() >= 0.25 and tam_opak.sum() >= 8:
        metin = tuple(int(v) for v in a[..., :3][tam_opak].mean(0))
    return {'saydam_oran': saydam_oran, 'baskin_alfa': baskin_alfa,
            'zemin': zemin, 'metin': metin, 'koyu_zemin': zl < 110}


def ciz_talimat(ing, tr, w, h, K, bilgi, saydam):
    zem = bilgi['zemin']
    met = bilgi['metin']
    if saydam:
        zemin_notu = (
            'Görselin geniş düz alanı BEYAZ (255,255,255) zemindir; oyunda\n'
            'buranın altında başka bir katman vardır. Beyaz kalmalı,\n'
            'koyulaştırma, renk verme, doku ekleme.')
    else:
        zemin_notu = (
            f'Görselin zemini RGB{zem} rengindedir ve aynen korunmalıdır.\n'
            'Zemindeki doku, yıpranma, leke ve gölgeler birebir aynı kalsın.')

    return f"""Bu bir video oyununun arayüzünden alınmış bir parçadır,
{K} kat büyütülmüş halde veriyorum ({w*K}x{h*K} piksel).

Üzerinde şu yazı var:
{ing}

Aynı görselin, yazısı şu olan halini üret:
{tr}

{zemin_notu}

Ölçülen renkler: zemin RGB{zem}, yazı RGB{met}.
Bu görselin kontrastı düşüktür; yazıyı koyulaştırma, zemini koyulaştırma.

Kesin kurallar:
- Çıktı {w*K}x{h*K} piksel olsun, en-boy oranı değişmesin.
- YALNIZCA harfler değişsin. Çerçeveler, kenarlıklar, çizgiler, simgeler,
  oklar, sayı kadranları, çizimler ve dokular birebir aynı kalsın.
- Yazının rengi, kalınlığı, harf yüksekliği, harf aralığı, hizası ve
  dikey konumu orijinaliyle aynı olsun.
- Satır sayısı ve satırların yeri aynı kalsın.
- Bu bir bitmap piksel yazı tipidir ve {K} kat büyütülmüştür; harf
  kenarları basamaklı ve keskin olsun. Yumuşatma, gölge, kabartma yok.
- Kiril alfabesiyle (Rusça) yazılmış bir kısım varsa ONA DOKUNMA;
  harfleri, konumu ve biçimi birebir aynı kalsın.
- Yazı, orijinal yazının kapladığı alanın dışına taşmasın.
- Türkçe karakterleri (Ç Ğ İ Ö Ş Ü ı) doğru çiz.
- Yeni çerçeve, kenar boşluğu, filigran, açıklama EKLEME.

Sadece görseli döndür."""


def adim_ciz(m, tr, alfa_koru=True):
    """Sprite'i Gemini'ye cizdirir ve saydamligini geri kurar."""
    yol = kaynak_yol(m)
    orj = Image.open(yol).convert('RGBA')
    w, h = m['genislik_toplam'], m['h']
    bilgi = sprite_analiz(orj)
    # Sprite'in ZEMINI saydam mi? Olcut: baskin (en sik) alfa degeri.
    #   EXIT dugmesi  -> piksellerin cogu alfa=0  : zemin saydam, murekkep anahtarla
    #   mektup/poster -> piksellerin cogu alfa=255: zemin opak, alfayi oldugu gibi birak
    # Sadece 'saydam piksel orani'na bakmak yanlisti: kenarinda saydam pay olan
    # opak bir kagidi saydam zemin sanip kagidin kendisini siliyordu.
    # Zemin saydam mi? Iki olcutten biri yeterli:
    #   - baskin (en sik) alfa degeri saydam, ya da
    #   - piksellerin dortte birinden fazlasi saydam
    # Ikinci sart sart: yumusak gecisli (antialias) yazi sprite'larinda alfa
    # cok sayida ara degere yayilir ve 255 en sik deger cikabilir, oysa
    # sprite gercekte saydam zeminlidir.
    saydam = bilgi['baskin_alfa'] < 128 or bilgi['saydam_oran'] >= 0.25

    if saydam:
        zem = Image.new('RGBA', (w, h), (255, 255, 255, 255))
        zem.alpha_composite(orj)
        girdi = zem.convert('RGB')
    else:
        girdi = orj.convert('RGB')

    # Bazi sprite'larda yazi 90 derece dondurulmustur (ince dikey seritler).
    # Modele dondurulmus yazi gonderirsen yatay yazi geri dondurur. Bu yuzden
    # once yaziyi yatay hale getiriyoruz, sonucu da geri donduruyoruz.
    yon = int(tr.get('yon', 0) or 0)
    if yon == 90:
        girdi = girdi.transpose(Image.ROTATE_90)
    elif yon == 270:
        girdi = girdi.transpose(Image.ROTATE_270)
    gw, gh = girdi.size
    # Cok kucuk sprite'larda buyuk K, modeli 10 kat buyuk goruntu dondurmeye
    # itiyor; geri kuculturken ince yazi eziliyor. Kisa kenari kucuk olanlarda
    # buyutmeyi kisiyoruz.
    kucuk_sprite = min(gw, gh) <= 60
    hedef_uzun = 1000 if kucuk_sprite else 1800
    K = max(2, min(12, int(round(hedef_uzun / max(gw, gh)))))
    if kucuk_sprite:
        K = max(K, int(round(160 / max(1, min(gw, gh)))))   # kisa kenar ~160px
    girdi = girdi.resize((gw * K, gh * K), Image.NEAREST)
    buf = io.BytesIO(); girdi.save(buf, 'PNG')

    y = istek(MODEL_CIZ, {
        'contents': [{'parts': [
            {'text': ciz_talimat(tr['ingilizce'], tr['turkce'], gw, gh, K, bilgi, saydam)},
            {'inline_data': {'mime_type': 'image/png',
                             'data': base64.b64encode(buf.getvalue()).decode('ascii')}},
        ]}],
        'generationConfig': {'responseModalities': ['IMAGE']},
    })
    ham = None
    for p in y.get('candidates', [{}])[0].get('content', {}).get('parts', []):
        d = p.get('inline_data') or p.get('inlineData')
        if d and d.get('data'):
            ham = base64.b64decode(d['data'])
            break
    if ham is None:
        sebep = y.get('candidates', [{}])[0].get('finishReason', '?')
        raise RuntimeError(f'model goruntu dondurmedi (finishReason={sebep})')

    im = Image.open(io.BytesIO(ham)).convert('RGB')
    uyari = []
    if im.size != (gw * K, gh * K):
        uyari.append(f'model {im.size[0]}x{im.size[1]} dondurdu ({gw*K}x{gh*K} istenmisti)')
    im = im.resize((gw, gh), Image.LANCZOS)
    if yon == 90:                      # gonderirken dondurmustuk, geri al
        im = im.transpose(Image.ROTATE_270)
    elif yon == 270:
        im = im.transpose(Image.ROTATE_90)
    kucuk = np.asarray(im).astype(np.float32)

    if saydam and alfa_koru:
        # murekkep anahtarlama: cikti zemininden sapan her piksel opak olur
        lum = kucuk.mean(2)
        zl = float(np.bincount(lum.round().astype(np.int64).ravel(), minlength=256).argmax())
        sapma = np.clip(np.abs(lum - zl) / max(6.0, abs(zl) * 0.06), 0, 1)
        rgb = np.clip(kucuk, 0, 255)
        if kucuk_sprite:
            # Kucultmeden sonra ince yazi grilesip okunmaz hale geliyor.
            # Kenarlari keskinlestir ve yazi rengini orijinaline sabitle.
            sapma = np.clip((sapma - 0.42) * 2.6 + 0.42, 0, 1)
            met = np.array(bilgi['metin'], dtype=np.float32)
            kuvvet = sapma[..., None]
            rgb = rgb * (1 - kuvvet) + met * kuvvet
        alfa = (sapma * 255).astype(np.uint8)
        yeni = Image.fromarray(np.dstack([rgb.astype(np.uint8), alfa]), 'RGBA')
        o = np.asarray(orj)
        ortusme = float(((o[..., 3] > 128) == (alfa > 128)).mean())
        # NOT: burada orijinal alfaya GERI DONULMEZ. Bu sprite'ta yazinin
        # kendisi alfa tasir; orijinal maskeyi geri koymak yeni Turkce
        # kelimeyi eski Ingilizce kelimenin siluetine kirpardi. Kelime
        # uzunlugu degistiginde ortusmenin dusmesi zaten beklenen seydir.
        # Kagit silinme hatasi artik baskin_alfa testiyle onleniyor.
        if ortusme < 0.60:
            uyari.append(f'saydamlik ortusmesi cok dusuk: %{ortusme*100:.0f}'
                         ' (metin uzunlugu degistiyse normal, yine de goz at)')
        elif ortusme < 0.85:
            uyari.append(f'saydamlik ortusmesi dusuk: %{ortusme*100:.0f}')
    else:
        yeni = Image.fromarray(np.clip(kucuk, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
        yeni.putalpha(orj.getchannel('A'))

    hedef = os.path.join(CIKTI, m['dosya'].replace('/', os.sep))
    os.makedirs(os.path.dirname(hedef), exist_ok=True)
    yeni.save(hedef)
    karsilastirma(yol, hedef, m)
    return uyari


def karsilastirma(eski_yol, yeni_yol, m):
    if not KARS_URET:
        return
    """Ustte orijinal, altta yeni; damali zemin uzerinde."""
    a = Image.open(eski_yol).convert('RGBA')
    b = Image.open(yeni_yol).convert('RGBA')
    p, w, h = 8, m['genislik_toplam'], m['h']
    tuval = Image.new('RGBA', (w + p * 2, h * 2 + p * 3), (255, 255, 255, 255))
    for y in range(0, tuval.size[1], 8):            # damali zemin
        for x in range(0, tuval.size[0], 8):
            if (x // 8 + y // 8) % 2:
                tuval.paste((214, 214, 214, 255), (x, y, min(x + 8, tuval.size[0]),
                                                   min(y + 8, tuval.size[1])))
    tuval.alpha_composite(a, (p, p))
    tuval.alpha_composite(b, (p, h + p * 2))
    os.makedirs(KARS, exist_ok=True)
    ad = m['dosya'].replace('/', '__')
    tuval.save(os.path.join(KARS, ad))


# --------------------------------------------------------------- 3. UYGULA
def adim_uygula(liste):
    n = 0
    for m in liste:
        c = os.path.join(CIKTI, m['dosya'].replace('/', os.sep))
        if not os.path.exists(c):
            continue
        im = Image.open(c)
        if im.size != (m['genislik_toplam'], m['h']):
            print(f"  ATLANDI {m['dosya']}: boyut {im.size}")
            continue
        shutil.copy2(c, os.path.join(KOK, m['dosya'].replace('/', os.sep)))
        n += 1
    print(f'\n{n} sprite calisma dosyalarina kopyalandi.')
    print('Simdi ust klasorde:  python geri_yukle.py        (kontrol)')
    print('                     python geri_yukle.py --yaz  (oyuna yaz)')


# ------------------------------------------------------------------- ana
def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('--oku', action='store_true')
    ap.add_argument('--ciz', action='store_true')
    ap.add_argument('--uygula', action='store_true')
    ap.add_argument('--durum', action='store_true')
    ap.add_argument('--sifirla')
    ap.add_argument('--klasor')
    ap.add_argument('--dosya')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--bekle', type=float, default=4.0)
    ap.add_argument('--model-oku', default=None)
    ap.add_argument('--model-ciz', default=None,
                    help='cizim modeli (varsayilan gemini-3-pro-image)')
    ap.add_argument('--alfa-serbest', action='store_true')
    ap.add_argument('--karsilastirma', action='store_true',
                    help='yan yana karsilastirma sayfasi da uret')
    ap.add_argument('-h', '--help', action='store_true')
    a = ap.parse_args()
    if a.help or not any([a.oku, a.ciz, a.uygula, a.durum, a.sifirla]):
        print(__doc__)
        return

    global MODEL_CIZ, MODEL_OKU, KARS_URET
    KARS_URET = bool(a.karsilastirma)
    if a.model_ciz:
        MODEL_CIZ = a.model_ciz
    if a.model_oku:
        MODEL_OKU = a.model_oku

    durum = json_oku(DURUM_YOL, {})
    ceviri = json_oku(CEVIRI_YOL, {})
    liste = isler(a)
    if not liste:
        print('Eslesen sprite yok.')
        return

    if a.sifirla:
        n = 0
        for k in list(durum):
            if a.sifirla.lower() in k.lower():
                durum.pop(k); n += 1
        json_yaz(DURUM_YOL, durum)
        print(f'{n} isin durumu sifirlandi.')
        return

    if a.durum:
        say, ic = {}, {}
        for m in liste:
            d = durum.get(m['dosya'], {})
            asama = d.get('asama', 'bekliyor')
            say[asama] = say.get(asama, 0) + 1
            if asama == 'dokunulmaz':
                k = d.get('icerik', '?')
                ic[k] = ic.get(k, 0) + 1
        print(f'{len(liste)} is')
        for k, v in sorted(say.items()):
            ek = ''
            if k == 'dokunulmaz' and ic:
                ek = '   (' + ', '.join(f'{a}: {b}' for a, b in sorted(ic.items())) + ')'
            print(f'  {k:12s} {v}{ek}')
        hata = [k for k, v in durum.items() if v.get('hata')]
        if hata:
            print(f'\nHatali {len(hata)}:')
            for k in hata[:15]:
                print(f'  {k}: {durum[k]["hata"][:110]}')
        return

    if a.uygula:
        adim_uygula(liste)
        return

    yapilan = 0
    for i, m in enumerate(liste, 1):
        d = m['dosya']
        st = durum.setdefault(d, {'asama': 'bekliyor'})
        if a.limit and yapilan >= a.limit:
            break

        if a.oku and st.get('asama') in (None, 'bekliyor', 'hata'):
            print(f'[{i}/{len(liste)}] OKU  {d}')
            try:
                r = adim_oku(m, ceviri)
                if r['icerik'] not in CIZILIR or not r['turkce']:
                    st.update(asama='dokunulmaz', icerik=r['icerik'], hata=None)
                    aciklama = {'yazi_yok': 'yazi yok, dokunulmayacak',
                                'rusca': 'Rusca, oldugu gibi birakilacak'}
                    print(f'      -- {aciklama.get(r["icerik"], "cevrilecek metin yok")}')
                else:
                    st.update(asama='okundu', icerik=r['icerik'], hata=None)
                    etiket = ' [karisik: Rusca kisim korunuyor]' if r['icerik'] == 'karisik' else ''
                    print(f'      "{r["ingilizce"]}"  ->  "{r["turkce"]}"{etiket}'
                          + (f'   ({r["not"]})' if r['not'] else ''))
            except Exception as e:
                st.update(asama='hata', hata=str(e)[:400])
                print(f'      HATA: {e}')
            json_yaz(CEVIRI_YOL, ceviri); json_yaz(DURUM_YOL, durum)
            yapilan += 1
            time.sleep(a.bekle)

        if a.ciz and st.get('asama') == 'okundu':
            tr = ceviri.get(d)
            if not tr or not tr.get('turkce') or tr.get('icerik') not in CIZILIR:
                st.update(asama='dokunulmaz', hata=None)
                json_yaz(DURUM_YOL, durum)
                continue
            print(f'[{i}/{len(liste)}] CIZ  {d}  -> "{tr["turkce"]}"')
            try:
                uyari = adim_ciz(m, tr, alfa_koru=not a.alfa_serbest)
                st.update(asama='cizildi', hata=None, uyari=uyari or None)
                for u in uyari:
                    print(f'      not: {u}')
            except Exception as e:
                st.update(asama='ciz_hata', hata=str(e)[:400])
                print(f'      HATA: {e}')
            json_yaz(DURUM_YOL, durum)
            yapilan += 1
            time.sleep(a.bekle)

    json_yaz(DURUM_YOL, durum)
    print(f'\nBitti. Bu turda {yapilan} is islendi.')
    if a.ciz:
        print(f'Ciktilar : {CIKTI}')
        print(f'Karsilastirma: {KARS}   (ustte orijinal, altta yeni)')


if __name__ == '__main__':
    main()
