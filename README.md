# Edge TTS Destekli Yorumlu Youtube Shorts Yapma Uygulaması

Bu uygulama, Microsoft Edge TTS servisini kullanarak Türkçe metinleri "Ahmet" sesiyle seslendiren bir masaüstü uygulamasıdır.

## Özellikler

- ✨ Modern ve kullanıcı dostu arayüz
- 🎤 Ahmet sesiyle Türkçe metin okuma
- 📝 Ses dosyasına isim verebilme
- 📁 Kayıt klasörü seçebilme
- 💾 Ses dosyasını MP3 formatında kaydetme
- ⏹️ Seslendirmeyi durdurma özelliği
- 🔄 Diğer Türkçe sesleri seçebilme
- 📦 EXE dosyası oluşturma (Python kurmadan çalıştırma)

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

### 4. Uygulamayı Çalıştırma

**Python ile:**
```bash
python main.py
```

**EXE olarak (Python kurmadan):** Önce EXE oluşturun, sonra `dist\EdgeTTS-Ahmet.exe` dosyasını çalıştırın.

#### EXE Dosyası Oluşturma

1. Proje klasöründe **Komut İstemi** veya **PowerShell** açın
2. Bağımlılıkları yükleyin: `pip install -r requirements.txt`
3. `build.bat` dosyasını çalıştırın (çift tıklayın veya `build.bat` yazın)
4. İşlem bitince EXE dosyası `dist\EdgeTTS-Ahmet.exe` konumunda oluşur
5. Bu EXE'yi istediğiniz yere kopyalayıp Python olmayan bilgisayarlarda da çalıştırabilirsiniz

Manuel build için:
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "EdgeTTS-Ahmet" --collect-all edge_tts main.py
```

## Kullanım

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

EXE: `build_exe.bat` çalıştır → `dist\VideoFactory.exe`. FFmpeg yoksa [ffmpeg](https://ffmpeg.org/download.html) indirip `ffmpeg.exe` ve `ffprobe.exe` dosyalarını EXE ile aynı klasöre koyun.

## Örnek CLI

```bash
python -m src.main --video video.mp4 --logo logo.png --channel_name "Kanal" --username "@kullanici" --comment_image yorum.png --comment_text "Okunacak yorum metni" --out cikti.mp4 --mute_video_audio true
```

## Girdiler

- Video (mp4/mov), logo (png), kanal adı, kullanıcı adı
- Yorum görseli (png/jpg), yorum metni (TTS ile okunur)
- Video orijinal sesi: açık/kapalı (varsayılan kapalı)
- Çıktı yolu, opsiyonel çözünürlük/fps

## Lisans

Bu proje açık kaynaklıdır ve serbestçe kullanılabilir.
