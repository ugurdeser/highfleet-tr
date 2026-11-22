# HighFleet Türkçe Yama — Kaynak Dosyalar

Bu klasör, çeviriyi yeniden üretmek ve geliştirmek için gereken her şeyi içerir.
Oyunun kendi metni burada **yok** — onu kendi kurulumundan üretiyorsun.

Hedef oyun sürümü: **HighFleet 1.16 (Deus In Nobis)**

## Gereksinimler

Python 3.8+. Harici paket yok.

## Nasıl çalışır

`Data/Dialogs/english.seria_enc` bir LCG-XOR akış şifresiyle korunuyor:

```
b = 2531011
her bayt için:  çıktı = (b ^ (b >> 15) ^ bayt) & 0xFF
                b = (b + 214013) & 0xFFFFFFFF
```

Aynı fonksiyon hem şifreler hem çözer. Bu formatın çözümü
[stopnoanime/highfleet-dialog](https://github.com/stopnoanime/highfleet-dialog)
projesine aittir.

Çözülen dosya satır tabanlı bir metin dosyasıdır:

```
#ANAHTAR<TAB>değer
<ANS=cevap metni|HEDEF_ANAHTAR|ETKI=1>
```

`<TAG=...>` ve `{fonksiyon=...}` işaretlemeleri oyun motoruna aittir,
birebir korunmalıdır. `<ANS=...>` içindeki ilk `|` işaretinden **önceki**
kısım oyuncunun gördüğü cevaptır ve çevrilir; sonrası diyalog ağacının
dallanma hedefleridir ve **asla** değiştirilmemelidir.

## Sıfırdan üretim

```bash
# 1) Kendi oyunundaki orijinal dosyayı çöz
python crypt.py "<OYUN>/Data/Dialogs/english.seria_enc" english.seria

# 2) Segmentlere ayır (segments.json + batches/ üretir)
python extract.py

# 3) Türkçeyi birleştir, doğrula, ASCII'ye indir ve kur
set HIGHFLEET_DIR=E:\SteamLibrary\steamapps\common\HighFleet
python build.py --install
```

`build.py` `--install` olmadan çalıştırılırsa yalnızca `turkish.seria`
dosyasını üretir, oyuna dokunmaz. Kurulumdan önce mevcut dosyayı
`.bak` olarak yedekler.

## Doğrulayıcı

`build.py` her çalışmada şunları denetler ve sorun bulursa kurulumu reddeder:

- işaretleme etiketlerinin çokluk kümesi değişmiş mi
- `{glossary=metin,ANAHTAR}` sayısı ve anahtarları korunmuş mu
- `|HEDEF` biçimindeki bütün dallanma hedefleri aynı mı
- `<ANS=...>` hedefleri aynı mı
- ASCII dışı karakter kalmış mı
- hizalama için anlamlı olan baş/son boşluklar korunmuş mu (kaybolmuşsa geri koyar)

`--force` ile denetimi geçebilirsin, ama diyalog ağacını kırma ihtimalin yüksek.

## Klasör düzeni

| Yol | Ne |
|---|---|
| `crypt.py` | şifrele / çöz (aynı işlem) |
| `extract.py` | çözülmüş dosyayı çevrilebilir segmentlere ayırır |
| `build.py` | birleştirir, doğrular, ASCII'ye indirir, kurar |
| `tr/b0NN.txt` | Türkçe metinler, `segment_id<TAB>metin` |
| `tr/_extra.tsv` | satır bazlı ek yamalar, `satır_no<TAB>tam_satır` |

## Türkçe karakter meselesi

Oyun HGE bitmap font kullanıyor (`Media/Fnt/*.fnt` + `Media/Tex/Fnt*.png`).
Karakterler tek baytla indeksleniyor ve `0x80–0xFF` aralığı tamamen
Kiril alfabesine (cp1251) ayrılmış durumda. Türkçe diakritikler için yer yok.

Bu yüzden `tr/` içindeki metinler **tam diakritikli** yazılmıştır ve
`build.py` içindeki `FOLD` tablosu kurulum anında bunları ASCII'ye indirir.

Tam diakritik desteği istiyorsan yapılması gereken:

1. `Media/Tex/Fnt1.png` / `Fnt2.png` atlaslarında kullanılmayan Kiril
   hücrelerine 12 glif çiz (`ç Ç ğ Ğ ı İ ö Ö ş Ş ü Ü`) — mevcut
   `C`, `G`, `I`, `O`, `S`, `U` gliflerinden türetilebilirler
2. İlgili `.fnt` dosyalarında o baytların `Char=` satırlarını yeni
   dikdörtgenlere eşle
3. `build.py` içindeki `FOLD` tablosunu, ASCII'ye indirmek yerine
   seçtiğin bayt değerlerine eşleyecek şekilde değiştir

Çeviri metni zaten diakritikli olduğu için bu değişiklik çeviriyi
yeniden yazmayı gerektirmez.


## Görsel (texture) yaması

Oyunun bazı yazıları diyalog dosyasında değil, doğrudan texture
atlaslarının içine çizilmiştir. `Media/Tex/*.res` dosyaları atlas
içindeki dikdörtgenleri tanımlar:

```
Animation title_exit_eng
{
 texture = Desk1
 rect = 558,3303,211,46
}
```

Adı `_eng` ile biten sprite'lar dilin İngilizce varyantıdır. Oyunda
103 tane vardır, 19 atlasa dağılmışlardır.

`otomatik/` klasöründeki iş hattı bunları Gemini ile Türkçeleştirir:

```bash
python sprite_cikar.py                 # 103 sprite'i PNG olarak disari aktarir
cd otomatik
python pipeline.py --oku --klasor Desk1   # gorseli okur, Turkcesini uretir
python pipeline.py --ciz --klasor Desk1   # Turkce yazili resmi cizdirir
python pipeline.py --uygula               # ciktilari yerine koyar
cd .. && python geri_yukle.py --yaz       # atlaslara isler
```

Ayrıntılar `otomatik/OKUBENI-OTOMATIK.txt` içinde. Gemini API
anahtarı gerekir (`otomatik/anahtar.txt`).

### Dikkat edilen üç şey

**Saydamlık.** Sprite'ların çoğunda iç bölge saydamdır; kart zemini
oyunda alttaki başka bir katmandan gelir. Saydamlığı siyaha
düzleştirip modele göstermek ona "siyah levha" gösterir ve model
onu sadakatle yeniden üretir. Bu yüzden sprite modele beyaz zemine
oturtulmuş halde gönderilir, saydamlık dönen görüntüdeki mürekkep
miktarından yeniden hesaplanır.

**Yazı alfa taşır.** Menü etiketlerinde yazının kendisi alfa taşır.
Orijinal alfa maskesini geri koymak yeni Türkçe kelimeyi eski
İngilizce kelimenin siluetine kırpar. Bu yüzden geri konmaz.

**Kaynak her zaman `_orijinal/`.** `--uygula` çalışma kopyalarının
üzerine yazar; yeniden çizerken çalışma kopyasını kaynak almak
modelin kendi çıktısını tekrar işlemesine yol açar.

### Tutarlılık

Her sprite modele tek başına gider, ötekilerden haberi yoktur.
`otomatik/sozluk.json` tekrar eden terimleri sabitler ve her okuma
çağrısına eklenir. Bir terimi değiştirirsen ilgili sprite'ları
`--sifirla` ile yeniden okutup çizdir.

## Bilinen sınırlar

- Haritadaki şehir isimleri texture'a gömülü, bu boru hattının dışında
- Tersane teknik çizimindeki Kiril başlıklar kasten çevrilmedi
  (İngilizce sürümde de Rusça duruyorlar)
- Oyun güncellenirse anahtar listesi değişebilir; `extract.py` çıktısındaki
  segment sayısını karşılaştırıp yalnızca yeni anahtarları çevirmek yeterli

## Lisans

Kaynak kodu (`*.py`) MIT. Çeviri metni (`tr/`) CC BY-NC-SA 4.0.
HighFleet'in tüm hakları Konstantin Koshutin ve MicroProse'a aittir.
Bu ücretsiz bir hayran çalışmasıdır, satılamaz.
