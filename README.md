# AutoShorts

TikTok / kısa video + üst bar (logo, kanal) + yorum overlay + TTS senkronlu kısa video üreten masaüstü uygulaması.

*(İsteğe bağlı: `main.py` ile sadece metni seslendirip MP3 üreten basit TTS aracı da projede bulunur.)*

## Kurulum

### 1. Python Kurulumu

Eğer Python yüklü değilse:

1. [Python'un resmi web sitesinden](https://www.python.org/downloads/) Python 3.8 veya üzeri bir sürümü indirin
2. İndirdiğiniz kurulum dosyasını çalıştırın
3. **ÖNEMLİ:** Kurulum sırasında "Add Python to PATH" seçeneğini işaretleyin
4. Kurulumu tamamlayın

### 2. Projeyi İndirme

Projeyi bilgisayarınıza indirin veya klonlayın.

### 3. Bağımlılıkları Yükleme

Proje klasörüne gidin ve terminal/komut istemcisinde şu komutu çalıştırın:

```bash
pip install -r requirements.txt
```

Eğer `pip` komutu çalışmazsa, şunu deneyin:

```bash
python -m pip install -r requirements.txt
```

veya

```bash
python3 -m pip install -r requirements.txt
```

### 4. Basit TTS aracı (isteğe bağlı)

**Python ile:**
```bash
python main.py
```

**EXE olarak:** TTS aracı için ayrı bir build betiği kullanılabilir; ana uygulama `build.bat` ile `dist\AutoShorts.exe` olarak derlenir.

Basit TTS aracı kullanımı:

1. **Okunacak Metin** alanına metninizi yazın
2. **Ses dosyası adı** kutusuna kaydedeceğiniz dosyanın adını yazın (örn: `bolum_01` → `bolum_01.mp3`)
3. **Kayıt klasörü** satırında hedef klasörü yazın veya **Klasör Seç** ile seçin
4. İsterseniz **Ses** menüsünden farklı bir Türkçe ses seçin
5. **"▶ Oku"** ile dinleyin, **"💾 Dosyaya Kaydet"** ile seçtiğiniz klasöre ve isimle kaydedin
6. **"⏹ Durdur"** ile seslendirmeyi durdurun

## Gereksinimler

- Python 3.8 veya üzeri
- İnternet bağlantısı (TTS servisi için)
- Windows, macOS veya Linux işletim sistemi

## Sorun Giderme

### "pip komutu bulunamadı" hatası

Python'un PATH'e eklendiğinden emin olun. Kurulum sırasında "Add Python to PATH" seçeneğini işaretlemediyseniz, Python'u yeniden kurun veya PATH'i manuel olarak ekleyin.

### "TTS modülü bulunamadı" hatası

Bağımlılıkları tekrar yükleyin:

```bash
pip install -r requirements.txt
```

### Ses çalmıyor

- İnternet bağlantınızı kontrol edin
- Windows Media Player veya varsayılan ses çalıcınızın çalıştığından emin olun
- Ses seviyesinin açık olduğundan emin olun

## Notlar

- İlk çalıştırmada ses listesi yüklenirken kısa bir gecikme olabilir
- Uygulama çalışırken geçici bir `temp_audio.mp3` dosyası oluşturulur (ses çalma için)
- Kaydedilen dosyalar seçtiğiniz konuma kaydedilir

---

# AutoShorts (Ana uygulama)

Tek arayüzle video + üst bar (logo, kanal adı, kullanıcı adı) + yorum overlay + TTS senkronlu kısa video üretir. **Başlat** tek tuşla TikTok URL’den indirip render yapılabilir.

## Hızlı çalıştırma

```bash
pip install -r requirements.txt
python -m src.main
```

**EXE:** `pyinstaller VideoFactory.spec` veya ilgili build betiği → `dist\AutoShorts.exe`.  
**Gereksinimler:** FFmpeg (PATH’te veya EXE ile aynı klasörde `ffmpeg.exe`, `ffprobe.exe`). TikTok indirme için `yt-dlp` (requirements.txt ile yüklenir).

## Özellikler (AutoShorts)

- 🎬 **Intro + ana video**:
  - Intro: videonun ilk karesi + header bar + yorum görseli, **TTS süresi boyunca** sabit
  - Sonra video **0. saniyeden** başlayarak header bar ile birlikte oynar
- 🧊 **Üst bar (header)**:
  - Sol: logo (PNG)
  - Sağ: kanal adı (büyük), altında kullanıcı adı (küçük)
  - Yarı saydam koyu arka plan, çözünürlüğe göre otomatik ölçek
- 💬 **Yorum overlay**:
  - Ekranın ortasına yakın, üst bardan sonra kalan alanda
  - Ekran genişliğinin ~%85’ini geçmeyecek şekilde otomatik ölçek
- 🔊 **Ses**:
  - TTS: Türkçe ses (varsayılan listeden ilk ses), sonundaki gereksiz sessizlik otomatik kırpılır
  - Intro süresince sadece TTS, ardından **videonun orijinal sesi** devam eder
  - Sesler AAC 256 kbps olarak encode edilir
- 📐 **Çıktı**: **Çözünürlük** (720p veya 1080p) ve **FPS** (30 veya 60) ayrı seçilir; seçimler `settings.json`’da kalıcıdır.
- **Video kaynağı**:
  - **TikTok URL**: “TikTok URL kullan” işaretlenince sadece URL kutusu görünür; **Başlat**’ta yt-dlp ile indirilir.
  - **Dosya**: URL kapalıyken video yolu + “Seç” ile dosya seçimi.
  - **Otomatik video** (ayrı kutu): Son indirilen video için video klasörü; sadece TikTok URL kapalıyken kullanılır.
  - **Otomatik görsel** (ayrı kutu): Son ekran görüntüsü için görsel klasörü.
- **Cookies (cookies.txt)**: TikTok indirme için opsiyonel. GUI’den dosya seçilir veya `settings.json` → `downloader.cookies_file`. JSON formatındaki cookie dosyaları otomatik olarak Netscape formatına dönüştürülür. Chrome açıkken tarayıcı cookie’si kilitli olabileceği için cookies.txt kullanmanız önerilir.
- 🧾 **Kanal profilleri**: Yeni kanal ekleme (logo + kanal adı + kullanıcı adı); `channels.json`’a yazılır, uygulama kapansa da yüklenir.
- 📝 **Otomatik dosya adı**: Çıktı video dosya adı = yorum metni (boşluk ve Türkçe karakterler korunur, yasak karakterler temizlenir).

## Örnek CLI

```bash
python -m src.main \
  --video video.mp4 \
  --logo logo.png \
  --channel_name "Kanal" \
  --username "@kullanici" \
  --comment_image yorum.png \
  --comment_text "Okunacak yorum metni" \
  --out cikti.mp4
```

## Girdiler

- **GUI**:
  - **Video kaynağı**: TikTok URL veya video dosyası (mp4/mov). Otomatik video/görsel için ayrı checkbox’lar ve klasör seçimi.
  - Logo (png), kanal adı, kullanıcı adı (kanal profili üzerinden; yeni kanal eklenebilir).
  - Yorum görseli (png/jpg), yorum metni (TTS ile okunur).
  - Çıktı dosyası (varsayılan `output`); dosya adı yorum metninden otomatik üretilir.
  - **Çözünürlük**: 720p veya 1080p. **FPS**: 30 veya 60.
  - **Cookies (cookies.txt)**: Opsiyonel; TikTok indirme için. JSON formatı otomatik Netscape’e dönüştürülür.
- **CLI**:
  - `--video`, `--logo`, `--channel_name`, `--username`, `--comment_image`, `--comment_text`, `--out`
  - Çıktı: Seçilen çözünürlük (720p: 720×1280, 1080p: 1080×1920) ve FPS (30 veya 60), mp4

## AutoShorts – Sorun giderme

- **TikTok indirilemiyor**: cookies.txt kullanın (Netscape veya JSON formatı; JSON otomatik dönüştürülür). Chrome açıksa tarayıcı cookie’si kilitli olabileceği için cookies.txt tercih edin.
- **FFmpeg bulunamadı**: FFmpeg’i indirip PATH’e ekleyin veya `ffmpeg.exe` / `ffprobe.exe` dosyalarını uygulama/EXE klasörüne koyun.
- **Yeni kanal kaydedilmiyor**: `channels.json` dosyasının yazılabilir olduğundan emin olun (uygulama/EXE ile aynı dizinde oluşturulur).

## Lisans

Bu proje açık kaynaklıdır ve serbestçe kullanılabilir.
