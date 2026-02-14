# AutoShorts

TikTok ve kısa videolar için üst bar (logo, kanal), yorum overlay ve TTS ile senkronlu kısa video üreten masaüstü uygulaması.

## Kurulum

- Python 3.8+
- Proje klasöründe: `pip install -r requirements.txt`
- Çalıştırma: `python -m src.main`
- EXE: `build.bat` veya `pyinstaller VideoFactory.spec` → `dist\AutoShorts.exe`
- FFmpeg gerekli (PATH veya exe yanında `ffmpeg.exe`, `ffprobe.exe`). TikTok indirme için `yt-dlp` requirements ile yüklenir.

## Ana özellikler

- **Başlat** tek tuşla: Video kaynağı (TikTok URL veya dosya) + yorum(lar) + TTS ile indirme ve render.
- **Video kaynağı**: TikTok URL (yt-dlp) veya yerel dosya. TikTok URL ile otomatik video kapalı; dosya modunda otomatik video (son indirilen) ve otomatik görsel ayrı checkbox’lar.
- **Yorum sayısı (1, 2 veya 3)**: Arayüzde “Yorum sayısı” ile 1, 2 veya 3 seçilir. Seçilen sayı kadar yorum alanı gösterilir.
- **Dinamik yorum alanları**: Her blokta TTS metni (çok satırlı, zorunlu) ve görsel (png/jpg) + Seç butonu.
- **Doğrulama**: Başlat’ta her görünen yorum için TTS metni dolu olmalı. Otomatik görsel kapalıysa her yorum için geçerli görsel gerekir.
- **Otomatik görsel**: Açıksa, görsel klasöründen en son değiştirilme tarihine göre en yeni N görsel alınır. **Sıra:** Yorum 1 = klasörde en eski (ilk aldığınız SS), Yorum 2 = ikinci, Yorum 3 = en yeni (son aldığınız SS). Klasörde N’den az görsel varsa hata (kaç gerekli / kaç bulundu).
- **Yorum yerleşimi**: Video süresi D saniye, N yorum için yerleşim eşit aralıklı: **Yorum 1** başta (t=0), **Yorum 2** D/(N+1), **Yorum 3** 2*D/(N+1) (N=3’te 0, D/4, D/2). Yorum klipleri bu zamanlara göre kesilip ana videoya eklenir; segment süreleri taşarsa clamp/overlap düzeltmesi uygulanır.
- **Ayarlar**: Yorum sayısı, otomatik görsel, görsel klasörü `settings.json`’da saklanır.
- **Çıktı**: Çözünürlük (720p / 1080p) ve FPS (30 / 60) ayrı seçilir. Ses AAC 256k.
- **Cookies**: TikTok için opsiyonel cookies.txt (GUI veya `settings.json` → `downloader.cookies_file`). JSON cookie dosyası Netscape formatına otomatik dönüştürülür.
- **Kanal profilleri**: Yeni kanal (logo, kanal adı, kullanıcı adı) `channels.json`’a yazılır.

## Kısa kullanım

1. Video: TikTok URL kullan veya dosya seç (gerekirse otomatik video/görsel aç).
2. Yorum sayısı: 1, 2 veya 3 seç.
3. Her “Yorum N” için TTS metnini yaz, görseli seç veya otomatik görsel ile klasörden al (ilk aldığın SS = Yorum 1, son aldığın = Yorum 3).
4. Kanal seç (veya yeni kanal ekle), çıktı yolunu ayarla, Başlat’a bas.

## CLI (tek yorum)

```bash
python -m src.main --video video.mp4 --logo logo.png --channel_name "Kanal" --username "@kullanici" --comment_image yorum.png --comment_text "Okunacak yorum metni" --out cikti.mp4
```

Çıktı varsayılan 1080p, 30 fps.

## Sorun giderme

- **TikTok indirilemiyor**: cookies.txt kullanın (Netscape veya JSON). Chrome açıkken cookies kilitli olabileceği için cookies.txt önerilir.
- **FFmpeg bulunamadı**: PATH’e ekleyin veya `ffmpeg.exe` / `ffprobe.exe`’yi uygulama/EXE klasörüne koyun.
- **Otomatik görsel: “N adet gerekli, M adet bulundu”**: Görsel klasöründe yeterli sayıda png/jpg/jpeg yok; N görsel ekleyin veya yorum sayısını düşürün.
- **Yeni kanal kaydedilmiyor**: Uygulama/EXE ile aynı dizinde `channels.json` yazılabilir olmalı.

## İsteğe bağlı: Basit TTS aracı

Sadece metni sese çevirip MP3 kaydetmek için: `python main.py`. Türkçe ses seçilir, metin yazılıp kaydedilir.

## Lisans

Proje açık kaynaklıdır, serbestçe kullanılabilir.
