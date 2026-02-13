# -*- coding: utf-8 -*-
"""AutoShorts GUI: dosya seçiciler, metin alanları, Başlat butonu, log."""
import os
import sys
import json
import threading
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# Proje kökü
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tts import generate_tts, get_audio_duration_seconds
from src.render import run_pipeline, get_video_info, get_ffmpeg


def get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


CHANNELS_FILE = "channels.json"
SETTINGS_FILE = "settings.json"


def _channels_path():
    return os.path.join(get_app_dir(), CHANNELS_FILE)


def _settings_path():
    return os.path.join(get_app_dir(), SETTINGS_FILE)


def load_channels():
    path = _channels_path()
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_channels(channels):
    path = _channels_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(channels, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_settings():
    path = _settings_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(settings: dict):
    path = _settings_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def download_tiktok_video(url: str, out_dir: str, cookies_file: str = "", log_cb=None) -> str:
    """yt-dlp ile TikTok URL'den video indirir. İndirilen dosya yolunu döner, hata durumunda None."""
    try:
        import yt_dlp
    except ImportError:
        if log_cb:
            log_cb("yt-dlp yüklü değil. pip install yt-dlp")
        return None
    
    # Chrome açık mı kontrol et (Windows)
    chrome_running = False
    if sys.platform == "win32":
        try:
            import subprocess
            result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq chrome.exe"], 
                                 capture_output=True, text=True, timeout=2)
            chrome_running = "chrome.exe" in result.stdout
        except Exception:
            pass
    
    out_tmpl = os.path.join(out_dir, "tiktok_dl.%(ext)s")
    opts = {
        "outtmpl": out_tmpl,
        "format": "best[ext=mp4]/best",
        "quiet": False,  # Hata mesajlarını görmek için False
        "no_warnings": False,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "referer": "https://www.tiktok.com/",
        "extractor_args": {
            "tiktok": {
                "webpage_download": True,
            }
        },
    }
    
    # Öncelik: cookies.txt varsa onu kullan
    if cookies_file and os.path.isfile(cookies_file):
        if log_cb:
            log_cb(f"Cookies.txt kullanılıyor: {cookies_file}")
        # Cookies.txt formatını kontrol et ve gerekirse dönüştür
        try:
            with open(cookies_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                # JSON formatında mı kontrol et
                if content.startswith("[") or content.startswith("{"):
                    if log_cb:
                        log_cb("JSON formatı tespit edildi, Netscape formatına dönüştürülüyor...")
                    # JSON'u Netscape formatına dönüştür
                    try:
                        cookies_json = json.loads(content)
                        # Liste değilse liste yap
                        if isinstance(cookies_json, dict):
                            cookies_json = [cookies_json]
                        elif not isinstance(cookies_json, list):
                            cookies_json = []
                        # Geçici Netscape format dosyası oluştur
                        netscape_file = os.path.join(out_dir, "cookies_netscape.txt")
                        with open(netscape_file, "w", encoding="utf-8") as nf:
                            nf.write("# Netscape HTTP Cookie File\n")
                            nf.write("# This file was generated from JSON format\n\n")
                            for cookie in cookies_json:
                                domain = cookie.get("domain", "").strip()
                                if not domain:
                                    continue
                                # Netscape format: domain, includeSubdomains, path, secure, expiration, name, value
                                include_sub = "TRUE" if domain.startswith(".") else "FALSE"
                                path = cookie.get("path", "/")
                                secure = "TRUE" if cookie.get("secure", False) else "FALSE"
                                exp = int(cookie.get("expirationDate", 0)) if cookie.get("expirationDate") else 0
                                name = cookie.get("name", "")
                                value = cookie.get("value", "")
                                if name and value:
                                    nf.write(f"{domain}\t{include_sub}\t{path}\t{secure}\t{exp}\t{name}\t{value}\n")
                        opts["cookiefile"] = netscape_file
                        if log_cb:
                            log_cb(f"Netscape formatına dönüştürüldü: {netscape_file}")
                    except Exception as e:
                        if log_cb:
                            log_cb(f"JSON dönüştürme hatası: {e}")
                        opts["cookiefile"] = cookies_file
                else:
                    # Zaten Netscape formatı
                    if "tiktok.com" in content.lower() or "sessionid" in content.lower():
                        if log_cb:
                            log_cb("Cookies.txt TikTok cookie'leri içeriyor.")
                    opts["cookiefile"] = cookies_file
        except Exception as e:
            if log_cb:
                log_cb(f"Cookies.txt okunamadı: {e}")
            opts["cookiefile"] = cookies_file
    elif not chrome_running:
        # Chrome kapalı, cookie'leri çekebiliriz
        if log_cb:
            log_cb("Chrome'dan cookie çekiliyor...")
        opts["cookiesfrombrowser"] = ("chrome",)
    else:
        # Chrome açık ve cookies.txt yok
        if log_cb:
            log_cb("UYARI: Chrome açık ve cookies.txt yok. Cookie olmadan deneniyor...")
    
    # TikTok için ekstra ayarlar
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            if log_cb:
                log_cb(f"İndirme başlatılıyor: {url}")
            ydl.download([url])
        # İndirilen dosyayı bul
        for f in os.listdir(out_dir):
            if f.startswith("tiktok_dl.") and f.lower().endswith((".mp4", ".webm", ".mov")):
                path = os.path.join(out_dir, f)
                if log_cb:
                    log_cb(f"İndirme tamamlandı: {path}")
                return path
        if log_cb:
            log_cb("HATA: İndirilen dosya bulunamadı.")
        return None
    except Exception as e:
        err_msg = str(e)
        if log_cb:
            log_cb(f"İndirme hatası: {err_msg}")
            # TikTok özel hatalar
            if "sign in" in err_msg.lower() or "login" in err_msg.lower():
                log_cb("TikTok giriş gerektiriyor. cookies.txt dosyanızı kontrol edin.")
                log_cb("Cookies.txt'de 'sessionid' cookie'si olmalı.")
            elif "cookie" in err_msg.lower():
                log_cb("Cookie hatası. cookies.txt formatını kontrol edin (Netscape formatı).")
            elif "unavailable" in err_msg.lower() or "private" in err_msg.lower():
                log_cb("Video erişilemez veya özel. Giriş yapmış cookies.txt kullanın.")
        return None


class VideoFactoryUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AutoShorts")
        self.root.geometry("720x820")
        self.root.minsize(600, 700)
        self.app_dir = get_app_dir()
        self.default_out = os.path.join(self.app_dir, "output")
        self._abort = False
        self._channels = load_channels()
        self._settings = load_settings()
        default_video = os.path.join(os.path.expanduser("~"), "Downloads")
        default_image = os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots")
        self.auto_video_enabled = bool(self._settings.get("auto_video_enabled", False))
        self.auto_image_enabled = bool(self._settings.get("auto_image_enabled", False))
        self.video_folder = self._settings.get("video_folder", default_video)
        self.image_folder = self._settings.get("image_folder", default_image)
        self.use_tiktok_url = bool(self._settings.get("use_tiktok_url", False))
        self.quality_resolution = self._settings.get("quality_resolution", "1080p")
        self.quality_fps = self._settings.get("quality_fps", "30")
        self.cookies_file = (self._settings.get("downloader") or {}).get("cookies_file", "")
        self.setup_ui()
        self._refresh_channel_list()

    def setup_ui(self):
        main = ttk.Frame(self.root, padding="10")
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(main, text="AutoShorts", font=("Arial", 14, "bold")).grid(row=row, column=0, columnspan=2, pady=(0, 10))
        row += 1

        # Video kaynağı: TikTok URL veya dosya (birbirini dışlar)
        self.use_tiktok_url_var = tk.BooleanVar(value=self.use_tiktok_url)
        ttk.Checkbutton(main, text="TikTok URL kullan", variable=self.use_tiktok_url_var, command=self._toggle_video_source).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        self.url_frame = ttk.Frame(main)
        self.url_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
        self.url_frame.columnconfigure(1, weight=1)
        ttk.Label(self.url_frame, text="TikTok URL:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.tiktok_url_var = tk.StringVar()
        ttk.Entry(self.url_frame, textvariable=self.tiktok_url_var, width=55).grid(row=0, column=1, sticky="ew", padx=(0, 5))
        if not self.use_tiktok_url:
            self.url_frame.grid_remove()
        row += 1

        self.video_frame = ttk.Frame(main)
        self.video_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
        self.video_frame.columnconfigure(1, weight=1)
        ttk.Label(self.video_frame, text="Video (mp4/mov):").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.video_var = tk.StringVar()
        f_vid = ttk.Frame(self.video_frame)
        f_vid.grid(row=0, column=1, sticky="ew")
        f_vid.columnconfigure(0, weight=1)
        ttk.Entry(f_vid, textvariable=self.video_var, width=50).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(f_vid, text="Seç", command=lambda: self._file(self.video_var, "Video", [("Video", "*.mp4 *.mov")]), width=8).grid(row=0, column=1)
        if self.use_tiktok_url:
            self.video_frame.grid_remove()
        row += 1

        self.auto_video_var = tk.BooleanVar(value=self.auto_video_enabled)
        self.chk_auto_video = ttk.Checkbutton(main, text="Otomatik video (son indirilen)", variable=self.auto_video_var, command=self._toggle_auto_video)
        self.chk_auto_video.grid(row=row, column=0, columnspan=2, sticky="w")
        if self.use_tiktok_url:
            self.chk_auto_video.grid_remove()
        row += 1

        self.auto_image_var = tk.BooleanVar(value=self.auto_image_enabled)
        ttk.Checkbutton(main, text="Otomatik görsel (son ekran görüntüsü)", variable=self.auto_image_var, command=self._toggle_auto_image).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        # Video klasörü (sadece otomatik video aktifken)
        self.auto_video_frame = ttk.Frame(main)
        self.auto_video_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        self.auto_video_frame.columnconfigure(1, weight=1)
        ttk.Label(self.auto_video_frame, text="Video klasörü:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.video_folder_var = tk.StringVar(value=self.video_folder)
        f_v = ttk.Frame(self.auto_video_frame)
        f_v.grid(row=0, column=1, sticky="ew")
        f_v.columnconfigure(0, weight=1)
        ttk.Entry(f_v, textvariable=self.video_folder_var, width=50).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(f_v, text="Seç", command=self._choose_video_folder, width=8).grid(row=0, column=1)
        if not self.auto_video_enabled:
            self.auto_video_frame.grid_remove()
        row += 1

        # Görsel klasörü (sadece otomatik görsel aktifken)
        self.auto_image_frame = ttk.Frame(main)
        self.auto_image_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(4, 4))
        self.auto_image_frame.columnconfigure(1, weight=1)
        ttk.Label(self.auto_image_frame, text="Görsel klasörü:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.image_folder_var = tk.StringVar(value=self.image_folder)
        f_i = ttk.Frame(self.auto_image_frame)
        f_i.grid(row=0, column=1, sticky="ew")
        f_i.columnconfigure(0, weight=1)
        ttk.Entry(f_i, textvariable=self.image_folder_var, width=50).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(f_i, text="Seç", command=self._choose_image_folder, width=8).grid(row=0, column=1)
        if not self.auto_image_enabled:
            self.auto_image_frame.grid_remove()
        row += 1

        # Kanal seçimi
        ttk.Label(main, text="Kanal:").grid(row=row, column=0, sticky="w", padx=(0, 8))
        f_chan = ttk.Frame(main)
        f_chan.grid(row=row, column=1, sticky="ew")
        f_chan.columnconfigure(0, weight=1)
        self.channel_choice_var = tk.StringVar()
        self.channel_combo = ttk.Combobox(f_chan, textvariable=self.channel_choice_var, width=35, state="readonly")
        self.channel_combo.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.channel_combo.bind("<<ComboboxSelected>>", self._on_channel_selected)
        ttk.Button(f_chan, text="Yeni kanal", command=self._new_channel_dialog, width=10).grid(row=0, column=1)
        row += 1

        self.logo_var = tk.StringVar()
        self.channel_var = tk.StringVar()
        self.username_var = tk.StringVar()

        # Yorum görseli
        ttk.Label(main, text="Yorum görseli (png/jpg):").grid(row=row, column=0, sticky="w", padx=(0, 8))
        self.comment_img_var = tk.StringVar()
        f = ttk.Frame(main)
        f.grid(row=row, column=1, sticky="ew")
        f.columnconfigure(0, weight=1)
        ttk.Entry(f, textvariable=self.comment_img_var, width=50).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(f, text="Seç", command=lambda: self._file(self.comment_img_var, "Yorum görseli", [("Görsel", "*.png *.jpg *.jpeg")]), width=8).grid(row=0, column=1)
        row += 1

        # Yorum metni (TTS)
        ttk.Label(main, text="Yorum metni (TTS):").grid(row=row, column=0, sticky="nw", padx=(0, 8), pady=(4, 0))
        self.comment_text_var = tk.StringVar()
        self.comment_text = scrolledtext.ScrolledText(main, height=4, width=50, wrap=tk.WORD)
        self.comment_text.grid(row=row, column=1, sticky="ew", pady=(4, 4))
        row += 1

        # TTS ses
        ttk.Label(main, text="TTS sesi:").grid(row=row, column=0, sticky="w", padx=(0, 8))
        self.voice_var = tk.StringVar(value="tr-TR-EmelNeural")
        self.voice_combo = ttk.Combobox(main, textvariable=self.voice_var, width=28, state="readonly")
        self.voice_combo.grid(row=row, column=1, sticky="w")
        row += 1

        # Çıktı
        ttk.Label(main, text="Çıktı dosyası:").grid(row=row, column=0, sticky="w", padx=(0, 8))
        self.out_var = tk.StringVar(value=os.path.join(self.default_out, "output.mp4"))
        f = ttk.Frame(main)
        f.grid(row=row, column=1, sticky="ew")
        f.columnconfigure(0, weight=1)
        ttk.Entry(f, textvariable=self.out_var, width=50).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(f, text="Kaydet yeri", command=self._out_file, width=10).grid(row=0, column=1)
        row += 1

        # Çözünürlük (720p / 1080p)
        ttk.Label(main, text="Çözünürlük:").grid(row=row, column=0, sticky="w", padx=(0, 8))
        self.quality_resolution_var = tk.StringVar(value=self.quality_resolution)
        res_combo = ttk.Combobox(main, textvariable=self.quality_resolution_var, values=("720p", "1080p"), width=8, state="readonly")
        res_combo.grid(row=row, column=1, sticky="w")
        res_combo.bind("<<ComboboxSelected>>", lambda e: self._save_quality_settings())
        row += 1
        # FPS (30 / 60)
        ttk.Label(main, text="FPS:").grid(row=row, column=0, sticky="w", padx=(0, 8))
        self.quality_fps_var = tk.StringVar(value=self.quality_fps)
        fps_combo = ttk.Combobox(main, textvariable=self.quality_fps_var, values=("30", "60"), width=8, state="readonly")
        fps_combo.grid(row=row, column=1, sticky="w")
        fps_combo.bind("<<ComboboxSelected>>", lambda e: self._save_quality_settings())
        row += 1

        # Cookies (opsiyonel)
        ttk.Label(main, text="Cookies (cookies.txt):").grid(row=row, column=0, sticky="w", padx=(0, 8))
        self.cookies_var = tk.StringVar(value=self.cookies_file)
        f_cook = ttk.Frame(main)
        f_cook.grid(row=row, column=1, sticky="ew")
        f_cook.columnconfigure(0, weight=1)
        ttk.Entry(f_cook, textvariable=self.cookies_var, width=40).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(f_cook, text="Seç", command=self._choose_cookies, width=8).grid(row=0, column=1)
        row += 1

        # Başlat
        btn_f = ttk.Frame(main)
        btn_f.grid(row=row, column=0, columnspan=2, pady=10)
        self.render_btn = ttk.Button(btn_f, text="Başlat", command=self.do_render, width=14)
        self.render_btn.pack(side=tk.LEFT, padx=5)
        row += 1

        # Log
        ttk.Label(main, text="Log:").grid(row=row, column=0, sticky="nw", padx=(0, 8))
        self.log_text = scrolledtext.ScrolledText(main, height=14, wrap=tk.WORD)
        self.log_text.grid(row=row, column=1, sticky="nsew", pady=(4, 0))
        main.rowconfigure(row, weight=1)
        row += 1

        self._load_voices()

    def _refresh_channel_list(self):
        self._channels = load_channels()
        names = [c.get("channel_name", "") for c in self._channels]
        self.channel_combo["values"] = names
        if not names:
            self.channel_choice_var.set("")
            self.logo_var.set("")
            self.channel_var.set("")
            self.username_var.set("")
            return
        if len(names) == 1:
            self.channel_choice_var.set(names[0])
            self._apply_channel(0)
        else:
            cur = self.channel_choice_var.get()
            if cur in names:
                self._apply_channel(names.index(cur))
            else:
                self.channel_choice_var.set(names[0])
                self._apply_channel(0)

    def _apply_channel(self, index):
        if 0 <= index < len(self._channels):
            c = self._channels[index]
            self.logo_var.set(c.get("logo_path", ""))
            self.channel_var.set(c.get("channel_name", ""))
            self.username_var.set(c.get("username", ""))

    def _on_channel_selected(self, event=None):
        sel = self.channel_choice_var.get()
        names = [c.get("channel_name", "") for c in self._channels]
        if sel in names:
            self._apply_channel(names.index(sel))

    def _new_channel_dialog(self):
        d = tk.Toplevel(self.root)
        d.title("Yeni kanal")
        d.geometry("480x200")
        d.transient(self.root)
        d.grab_set()
        f = ttk.Frame(d, padding="12")
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text="Logo (png):").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        logo_var = tk.StringVar()
        fe = ttk.Frame(f)
        fe.grid(row=0, column=1, sticky="ew")
        fe.columnconfigure(0, weight=1)
        ttk.Entry(fe, textvariable=logo_var, width=40).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(fe, text="Seç", command=lambda: self._file(logo_var, "Logo", [("PNG", "*.png")])).grid(row=0, column=1)
        ttk.Label(f, text="Kanal adı:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        chan_var = tk.StringVar()
        ttk.Entry(f, textvariable=chan_var, width=42).grid(row=1, column=1, sticky="w", pady=4)
        ttk.Label(f, text="Kullanıcı adı:").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        user_var = tk.StringVar()
        ttk.Entry(f, textvariable=user_var, width=42).grid(row=2, column=1, sticky="w", pady=4)
        def save():
            cn = chan_var.get().strip()
            if not cn:
                messagebox.showwarning("Eksik", "Kanal adı girin.", parent=d)
                return
            self._channels.append({
                "channel_name": cn,
                "username": user_var.get().strip(),
                "logo_path": logo_var.get().strip(),
            })
            save_channels(self._channels)
            self._refresh_channel_list()
            self.channel_choice_var.set(cn)
            self._apply_channel(len(self._channels) - 1)
            d.destroy()
        btn_f = ttk.Frame(f)
        btn_f.grid(row=3, column=0, columnspan=2, pady=16)
        ttk.Button(btn_f, text="Kaydet", command=save, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_f, text="İptal", command=d.destroy, width=10).pack(side=tk.LEFT)

    def _toggle_video_source(self):
        use_url = self.use_tiktok_url_var.get()
        self.use_tiktok_url = use_url
        self._settings["use_tiktok_url"] = use_url
        save_settings(self._settings)
        if use_url:
            self.auto_video_var.set(False)
            self.auto_video_enabled = False
            self._settings["auto_video_enabled"] = False
            save_settings(self._settings)
            self.url_frame.grid()
            self.video_frame.grid_remove()
            self.chk_auto_video.grid_remove()
        else:
            self.url_frame.grid_remove()
            self.video_frame.grid()
            self.chk_auto_video.grid()
        self._show_hide_auto_frame()

    def _toggle_auto_video(self):
        v = self.auto_video_var.get()
        if v:
            self.use_tiktok_url_var.set(False)
            self._toggle_video_source()
            self.auto_video_var.set(True)
        self.auto_video_enabled = self.auto_video_var.get()
        self._settings["auto_video_enabled"] = self.auto_video_enabled
        save_settings(self._settings)
        self._show_hide_auto_frame()

    def _toggle_auto_image(self):
        self.auto_image_enabled = self.auto_image_var.get()
        self._settings["auto_image_enabled"] = self.auto_image_enabled
        save_settings(self._settings)
        self._show_hide_auto_frame()

    def _show_hide_auto_frame(self):
        if self.auto_video_var.get():
            self.auto_video_frame.grid()
        else:
            self.auto_video_frame.grid_remove()
        if self.auto_image_var.get():
            self.auto_image_frame.grid()
        else:
            self.auto_image_frame.grid_remove()

    def _save_quality_settings(self):
        self.quality_resolution = self.quality_resolution_var.get()
        self.quality_fps = self.quality_fps_var.get()
        self._settings["quality_resolution"] = self.quality_resolution
        self._settings["quality_fps"] = self.quality_fps
        save_settings(self._settings)

    def _choose_cookies(self):
        path = filedialog.askopenfilename(title="Cookies (cookies.txt)", filetypes=[("Text", "*.txt"), ("Tümü", "*.*")])
        if path:
            self.cookies_var.set(path)
            self._settings.setdefault("downloader", {})["cookies_file"] = path
            save_settings(self._settings)

    def _choose_video_folder(self):
        path = filedialog.askdirectory(title="Video klasörünü seç (indirilen videolar)")
        if path:
            self.video_folder = path
            self.video_folder_var.set(path)
            self._settings["video_folder"] = path
            save_settings(self._settings)

    def _choose_image_folder(self):
        path = filedialog.askdirectory(title="Görsel klasörünü seç (ekran görüntüleri)")
        if path:
            self.image_folder = path
            self.image_folder_var.set(path)
            self._settings["image_folder"] = path
            save_settings(self._settings)

    def _auto_pick_media(self):
        """Otomatik video (dosya modunda) ve/veya otomatik görsel seçimi."""
        def latest_with_ext(folder, exts):
            if not folder or not os.path.isdir(folder):
                return None
            latest_path = None
            latest_time = -1
            try:
                for entry in os.scandir(folder):
                    if not entry.is_file():
                        continue
                    lower = entry.name.lower()
                    if any(lower.endswith(e) for e in exts):
                        t = entry.stat().st_mtime
                        if t > latest_time:
                            latest_time = t
                            latest_path = entry.path
            except Exception:
                return None
            return latest_path

        use_url = self.use_tiktok_url_var.get()
        if not use_url and self.auto_video_var.get():
            if not self.video_var.get().strip() or not os.path.isfile(self.video_var.get().strip()):
                vid = latest_with_ext(self.video_folder_var.get().strip(), [".mp4", ".mov"])
                if vid:
                    self.video_var.set(vid)

        if self.auto_image_var.get():
            if not self.comment_img_var.get().strip() or not os.path.isfile(self.comment_img_var.get().strip()):
                img = latest_with_ext(self.image_folder_var.get().strip(), [".png", ".jpg", ".jpeg"])
                if img:
                    self.comment_img_var.set(img)

    def _file(self, var: tk.StringVar, title: str, types: list):
        path = filedialog.askopenfilename(title=title, filetypes=types)
        if path:
            var.set(path)

    def _out_file(self):
        path = filedialog.asksaveasfilename(
            title="Çıktı video",
            defaultextension=".mp4",
            filetypes=[("MP4", "*.mp4")],
            initialdir=os.path.dirname(self.out_var.get()) or self.default_out,
        )
        if path:
            self.out_var.set(path)

    def _load_voices(self):
        def load():
            try:
                import asyncio
                import edge_tts
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                voices = loop.run_until_complete(edge_tts.list_voices())
                loop.close()
                tr = [v for v in voices if v["Locale"].startswith("tr-TR")]
                names = [f"{v['ShortName']} ({v['Gender']})" for v in tr]
                first_tr = tr[0]["ShortName"] if tr else None
                self.root.after(0, lambda: self.voice_combo.config(values=names))
                if first_tr:
                    self.root.after(0, lambda: self.voice_var.set(first_tr))
            except Exception:
                pass
        threading.Thread(target=load, daemon=True).start()

    def log(self, msg: str):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def do_render(self):
        use_url = self.use_tiktok_url_var.get()
        video = self.video_var.get().strip()
        tiktok_url = self.tiktok_url_var.get().strip()
        logo = self.logo_var.get().strip()
        comment_img = self.comment_img_var.get().strip()
        comment_txt = self.comment_text.get("1.0", tk.END).strip()
        out = self.out_var.get().strip()

        # Video kaynağı: (a) dosya seçiliyse onu kullan (b) URL modunda URL'den indir (c) otomatik dene (d) hata
        if not use_url:
            if (not video or not os.path.isfile(video)) or (not comment_img or not os.path.isfile(comment_img)):
                self._auto_pick_media()
                video = self.video_var.get().strip()
            if not video or not os.path.isfile(video):
                messagebox.showwarning("Eksik", "Video dosyası seçin veya TikTok URL kullanın.")
                return
        else:
            if not tiktok_url:
                messagebox.showwarning("Eksik", "TikTok URL girin.")
                return

        if not comment_img or not os.path.isfile(comment_img):
            self._auto_pick_media()
            comment_img = self.comment_img_var.get().strip()
        if not comment_img or not os.path.isfile(comment_img):
            messagebox.showwarning("Eksik", "Yorum görseli seçin.")
            return
        if not comment_txt:
            messagebox.showwarning("Eksik", "Yorum metni (TTS) girin.")
            return

        base_dir = os.path.dirname(out) if out else self.default_out
        if not base_dir:
            base_dir = self.default_out
        os.makedirs(base_dir, exist_ok=True)
        name_raw = comment_txt.strip() or "video"
        if len(name_raw) > 80:
            name_raw = name_raw[:80].rstrip()
        invalid = '<>:"/\\|?*'
        safe_name = "".join(("_" if ch in invalid else ch) for ch in name_raw).strip().rstrip(".") or "video"
        out = os.path.join(base_dir, safe_name + ".mp4")
        self.out_var.set(out)

        ffmpeg = get_ffmpeg()
        if ffmpeg == "ffmpeg":
            try:
                import shutil
                if not shutil.which("ffmpeg"):
                    messagebox.showerror("Hata", "FFmpeg bulunamadı. PATH'e ekleyin veya exe yanına ffmpeg.exe koyun.")
                    return
            except Exception:
                pass

        self._abort = False
        self.render_btn.config(state=tk.DISABLED)
        self.log_text.delete("1.0", tk.END)
        cookies_file = self.cookies_var.get().strip()
        quality_resolution = self.quality_resolution_var.get()
        quality_fps = self.quality_fps_var.get()

        def run():
            tmp_dir = tempfile.mkdtemp(prefix="vf_")
            video_path = video
            try:
                if use_url:
                    self.root.after(0, lambda: self.log("TikTok videosu indiriliyor..."))
                    video_path = download_tiktok_video(
                        tiktok_url, tmp_dir, cookies_file,
                        log_cb=lambda s: self.root.after(0, lambda m=s: self.log(m)),
                    )
                    if not video_path or not os.path.isfile(video_path):
                        self.root.after(0, lambda: messagebox.showerror("Hata", "Video indirilemedi. Gerekirse cookies.txt ekleyin."))
                        return
                    self.root.after(0, lambda: self.log("İndirme tamamlandı."))

                self.log("TTS üretiliyor...")
                voice = self.voice_var.get()
                if " (" in voice:
                    voice = voice.split(" (")[0]
                tts_path = os.path.join(tmp_dir, "tts.mp3")
                duration_sec = generate_tts(comment_txt, voice, tts_path)
                if duration_sec <= 0:
                    self.root.after(0, lambda: self.log("Hata: TTS süresi alınamadı."))
                    return
                self.root.after(0, lambda: self.log(f"TTS süresi: {duration_sec:.2f} sn"))

                logo_path = logo if (logo and os.path.isfile(logo)) else ""
                if not logo_path:
                    try:
                        from PIL import Image
                        logo_path = os.path.join(tmp_dir, "empty_logo.png")
                        Image.new("RGBA", (1, 1), (0, 0, 0, 0)).save(logo_path)
                    except Exception:
                        logo_path = os.path.join(tmp_dir, "empty_logo.png")
                        open(logo_path, "wb").write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")

                ok = run_pipeline(
                    video_path=video_path,
                    logo_path=logo_path,
                    channel_name=self.channel_var.get().strip(),
                    username=self.username_var.get().strip(),
                    comment_image_path=comment_img,
                    tts_audio_path=tts_path,
                    tts_duration_sec=duration_sec,
                    output_path=out,
                    log_cb=lambda s: self.root.after(0, lambda m=s: self.log(m)),
                    quality_resolution=quality_resolution,
                    quality_fps=quality_fps,
                )
                if ok:
                    self.root.after(0, lambda: messagebox.showinfo("Tamam", f"Video kaydedildi:\n{out}"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Hata", "Render başarısız. Loga bakın."))
            except Exception as e:
                self.root.after(0, lambda: self.log("Hata: " + str(e)))
                self.root.after(0, lambda: messagebox.showerror("Hata", str(e)))
            finally:
                try:
                    import shutil
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                except Exception:
                    pass
                self.root.after(0, lambda: self.render_btn.config(state=tk.NORMAL))

        threading.Thread(target=run, daemon=True).start()


def main():
    root = tk.Tk()
    VideoFactoryUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
