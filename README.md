# Edge TTS Destekli Yorumlu Video Uygulamaları

Bu repoda iki uygulama vardır:

- **1) EdgeTTS-Ahmet:** Sadece metni Ahmet sesiyle okuyup MP3 üreten basit masaüstü TTS aracı
- **2) VideoFactory:** Video + üst bar + yorum görseli + TTS senkronu ile final video üreten uygulama

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

### 4. EdgeTTS-Ahmet Uygulamasını Çalıştırma (isteğe bağlı)

**Python ile:**
```bash
python main.py
```

**EXE olarak (Python kurmadan):**

1. `build.bat` dosyasını çalıştırın → `dist\EdgeTTS-Ahmet.exe` oluşur
2. `dist\EdgeTTS-Ahmet.exe` dosyasını çalıştırın

Basit TTS aracı için:

1. **Okunacak Metin** alanına metninizi yazın
2. **Ses dosyası adı** kutusuna kaydedeceğiniz dosyanın adını yazın (örn: `bolum_01` → `bolum_01.mp3`)
3. **Kayıt klasörü** satırında hedef klasörü yazın veya **Klasör Seç** ile seçin
4. İsterseniz **Ses** menüsünden farklı bir Türkçe ses seçin (varsayılan: Ahmet)
5. **"▶ Oku"** ile dinleyin, **"💾 Dosyaya Kaydet"** ile seçtiğiniz klasöre ve isimle kaydedin
6. **"⏹ Durdur"** ile seslendirmeyi durdurun

## Gereksinimler

- Python 3.8 veya üzeri
- İnternet bağlantısı (Edge TTS servisi için)
- Windows, macOS veya Linux işletim sistemi

## Sorun Giderme

### "pip komutu bulunamadı" hatası

Python'un PATH'e eklendiğinden emin olun. Kurulum sırasında "Add Python to PATH" seçeneğini işaretlemediyseniz, Python'u yeniden kurun veya PATH'i manuel olarak ekleyin.

### "edge-tts modülü bulunamadı" hatası

Bağımlılıkları tekrar yükleyin:

```bash
pip install edge-tts
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

# Video Factory (Repost Overlay + TTS)

Tek arayüzle video + üst bar (logo, kanal adı, kullanıcı adı) + yorum overlay + TTS senkronlu final video üretir.

## Hızlı çalıştırma

```bash
pip install -r requirements.txt
python -m src.main
```

**EXE:** `build_exe.bat` çalıştır → `dist\VideoFactory.exe`.  
FFmpeg yoksa `ffmpeg.exe` ve `ffprobe.exe` dosyalarını EXE ile aynı klasöre koyun.

## Özellikler (VideoFactory)

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
  - TTS: Edge TTS (varsayılan `tr-TR-AhmetNeural`), sonundaki gereksiz sessizlik otomatik kırpılır
  - Intro süresince sadece TTS, ardından **videonun orijinal sesi** devam eder
  - Sesler AAC 256 kbps olarak encode edilir
- 📐 **Çıktı**:
  - Sabit: **1080x1920, 30 fps, H.264 (mp4)**
- 🧾 **Kanal profilleri**:
  - Logo + kanal adı + kullanıcı adı kayıtlı kanallar olarak saklanır (`channels.json`)
  - Açılışta tek kanal varsa otomatik seçilir
- ⚙️ **Otomatik medya seçimi (isteğe bağlı)**:
  - Son indirilen video (mp4/mov) için **video klasörü** (örn. `Downloads`)
  - Son alınan ekran görüntüsü için **görsel klasörü** (örn. `Pictures/Screenshots`)
  - Checkbox ile aç/kapa; yollar `settings.json` içinde saklanır
- 📝 **Otomatik dosya adı**:
  - Çıktı video dosya adı = yorum metni (boşluk ve Türkçe karakterler korunur, sadece Windows’ta yasak karakterler temizlenir)

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
  - Video (mp4/mov) → boşsa otomatik son indirilen video (auto açık ise)
  - Logo (png), kanal adı, kullanıcı adı (kanal profili üzerinden)
  - Yorum görseli (png/jpg) → boşsa otomatik son ekran görüntüsü (auto açık ise)
  - Yorum metni (TTS ile okunur)
  - Çıktı klasörü (varsayılan `output`); dosya adı yorum metninden otomatik üretilir
- **CLI**:
  - `--video`, `--logo`, `--channel_name`, `--username`, `--comment_image`, `--comment_text`, `--out`
  - Çıktı: 1080x1920, 30 fps mp4

## Lisans

Bu proje açık kaynaklıdır ve serbestçe kullanılabilir.
