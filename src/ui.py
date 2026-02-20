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
        # TikTok: HEVC + sessiz video yerine, AVC + m4a ses tercih et
        # Örnek: bv*[vcodec^=avc]+ba[ext=m4a]/b[ext=mp4]/b
        "format": "bv*[vcodec^=avc]+ba[ext=m4a]/b[ext=mp4]/b",
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

    # yt-dlp'nin, uygulama ile gelen ffmpeg'i kullanabilmesi için
    try:
        ffmpeg_bin = get_ffmpeg()
        # get_ffmpeg tam yol döndürüyor ise dizinini ver
        if os.path.isabs(ffmpeg_bin):
            opts["ffmpeg_location"] = os.path.dirname(ffmpeg_bin)
    except Exception:
        pass
    
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
        self.root.geometry("680x780")
        self.root.minsize(580, 660)
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
        self.comment_count = max(1, min(3, int(self._settings.get("comment_count", 1))))
        layout_cfg = self._settings.get("layout", {})
        self.post_text = layout_cfg.get("post_text", "")
        self.avatar_size_ratio = float(layout_cfg.get("avatar_size_ratio", 0.70))
        self.header_padding_ratio = float(layout_cfg.get("header_padding_ratio", 0.04))
        self.comment_text_size_ratio = float(layout_cfg.get("comment_text_size_ratio", 0.95))
        self._apply_theme()
        self.setup_ui()
        self._refresh_channel_list()

    def _apply_theme(self):
        style = ttk.Style()
        style.theme_use("clam")
        BG = "#f5f5f5"
        ACCENT = "#2563eb"
        self.root.configure(bg=BG)
        style.configure(".", background=BG, font=("Segoe UI", 10))
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", padding=[14, 6], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab",
                   background=[("selected", "#ffffff"), ("!selected", "#e0e0e0")],
                   foreground=[("selected", ACCENT), ("!selected", "#555")])
        style.configure("TLabelframe", background="#ffffff", borderwidth=1, relief="solid")
        style.configure("TLabelframe.Label", background="#ffffff", foreground="#333", font=("Segoe UI", 9, "bold"))
        style.configure("TButton", padding=[8, 4])
        style.configure("Accent.TButton", foreground="#fff", background=ACCENT, font=("Segoe UI", 11, "bold"))
        style.map("Accent.TButton",
                   background=[("active", "#1d4ed8"), ("!active", ACCENT)])
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), foreground=ACCENT, background=BG)

    def setup_ui(self):
        outer = ttk.Frame(self.root, padding="8")
        outer.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        ttk.Label(outer, text="AutoShorts", style="Title.TLabel").grid(row=0, column=0, pady=(0, 6))

        nb = ttk.Notebook(outer)
        nb.grid(row=1, column=0, sticky="nsew")
        outer.rowconfigure(1, weight=1)

        # ── Tab 1: Video Oluştur ──
        tab_main = ttk.Frame(nb, padding="8")
        nb.add(tab_main, text="  Video Oluştur  ")
        tab_main.columnconfigure(0, weight=1)
        self._build_main_tab(tab_main)

        # ── Tab 2: Ayarlar ──
        tab_settings = ttk.Frame(nb, padding="8")
        nb.add(tab_settings, text="  Ayarlar  ")
        tab_settings.columnconfigure(0, weight=1)
        self._build_settings_tab(tab_settings)

        self._load_voices()

    # ─────────────────── TAB 1: ANA ───────────────────
    def _build_main_tab(self, parent):
        row = 0

        # — Video Kaynağı —
        src_frame = ttk.LabelFrame(parent, text="Video Kaynağı", padding="8")
        src_frame.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        src_frame.columnconfigure(1, weight=1)
        row += 1

        self.use_tiktok_url_var = tk.BooleanVar(value=self.use_tiktok_url)
        ttk.Checkbutton(src_frame, text="TikTok URL kullan", variable=self.use_tiktok_url_var, command=self._toggle_video_source).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

        self.url_frame = ttk.Frame(src_frame)
        self.url_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.url_frame.columnconfigure(1, weight=1)
        ttk.Label(self.url_frame, text="URL:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.tiktok_url_var = tk.StringVar()
        ttk.Entry(self.url_frame, textvariable=self.tiktok_url_var).grid(row=0, column=1, sticky="ew")
        if not self.use_tiktok_url:
            self.url_frame.grid_remove()

        self.video_frame = ttk.Frame(src_frame)
        self.video_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.video_frame.columnconfigure(1, weight=1)
        ttk.Label(self.video_frame, text="Dosya:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.video_var = tk.StringVar()
        ttk.Entry(self.video_frame, textvariable=self.video_var).grid(row=0, column=1, sticky="ew", padx=(0, 4))
        ttk.Button(self.video_frame, text="Seç", command=lambda: self._file(self.video_var, "Video", [("Video", "*.mp4 *.mov")]), width=6).grid(row=0, column=2)
        if self.use_tiktok_url:
            self.video_frame.grid_remove()

        self.auto_video_var = tk.BooleanVar(value=self.auto_video_enabled)
        self.chk_auto_video = ttk.Checkbutton(src_frame, text="Otomatik (son indirilen)", variable=self.auto_video_var, command=self._toggle_auto_video)
        self.chk_auto_video.grid(row=3, column=0, columnspan=2, sticky="w", pady=(2, 0))
        if self.use_tiktok_url:
            self.chk_auto_video.grid_remove()

        # — Kanal + Post —
        chan_frame = ttk.LabelFrame(parent, text="Kanal & Post", padding="8")
        chan_frame.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        chan_frame.columnconfigure(1, weight=1)
        row += 1

        ttk.Label(chan_frame, text="Kanal:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        f_chan = ttk.Frame(chan_frame)
        f_chan.grid(row=0, column=1, sticky="ew")
        f_chan.columnconfigure(0, weight=1)
        self.channel_choice_var = tk.StringVar()
        self.channel_combo = ttk.Combobox(f_chan, textvariable=self.channel_choice_var, state="readonly")
        self.channel_combo.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.channel_combo.bind("<<ComboboxSelected>>", self._on_channel_selected)
        ttk.Button(f_chan, text="+ Yeni", command=self._new_channel_dialog, width=7).grid(row=0, column=1)

        self.logo_var = tk.StringVar()
        self.channel_var = tk.StringVar()
        self.username_var = tk.StringVar()

        ttk.Label(chan_frame, text="Post metni:").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=(4, 0))
        self.post_text_var = tk.StringVar(value=self.post_text)
        ttk.Entry(chan_frame, textvariable=self.post_text_var).grid(row=1, column=1, sticky="ew", pady=(4, 0))

        # — Yorumlar —
        comments_frame = ttk.LabelFrame(parent, text="Yorumlar", padding="8")
        comments_frame.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        comments_frame.columnconfigure(1, weight=1)
        row += 1

        ttk.Label(comments_frame, text="Sayı:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.comment_count_var = tk.StringVar(value=str(self.comment_count))
        f_count = ttk.Frame(comments_frame)
        f_count.grid(row=0, column=1, sticky="w")
        count_combo = ttk.Combobox(f_count, textvariable=self.comment_count_var, values=("1", "2", "3"), width=4, state="readonly")
        count_combo.pack(side=tk.LEFT)
        count_combo.bind("<<ComboboxSelected>>", self._on_comment_count_changed)

        self.auto_image_var = tk.BooleanVar(value=self.auto_image_enabled)
        ttk.Checkbutton(f_count, text="Otomatik görsel", variable=self.auto_image_var, command=self._toggle_auto_image).pack(side=tk.LEFT, padx=(12, 0))

        ttk.Label(comments_frame, text="TTS sesi:").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=(4, 0))
        self.voice_var = tk.StringVar(value="tr-TR-AhmetNeural")
        self.voice_combo = ttk.Combobox(comments_frame, textvariable=self.voice_var, state="readonly")
        self.voice_combo.grid(row=1, column=1, sticky="ew", pady=(4, 0))

        self.comment_blocks = []
        self._comments_container = ttk.Frame(comments_frame)
        self._comments_container.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self._comments_container.columnconfigure(0, weight=1)
        for i in range(3):
            block = {}
            bf = ttk.Frame(self._comments_container, padding="4")
            bf.grid(row=i, column=0, sticky="ew", pady=(0, 4))
            bf.columnconfigure(1, weight=1)
            ttk.Label(bf, text=f"#{i+1}", font=("Segoe UI", 9, "bold"), width=3).grid(row=0, column=0, rowspan=2, sticky="n", padx=(0, 4))
            txt = scrolledtext.ScrolledText(bf, height=2, wrap=tk.WORD, font=("Segoe UI", 9))
            txt.grid(row=0, column=1, sticky="ew", pady=(0, 2))
            img_var = tk.StringVar()
            f_img = ttk.Frame(bf)
            f_img.grid(row=1, column=1, sticky="ew")
            f_img.columnconfigure(0, weight=1)
            ttk.Entry(f_img, textvariable=img_var, font=("Segoe UI", 8)).grid(row=0, column=0, sticky="ew", padx=(0, 4))
            ttk.Button(f_img, text="Görsel", command=lambda v=img_var, idx=i: self._file(v, f"Yorum {idx+1}", [("Görsel", "*.png *.jpg *.jpeg")]), width=6).grid(row=0, column=1)
            block["frame"] = bf
            block["text"] = txt
            block["img_var"] = img_var
            self.comment_blocks.append(block)
        self._show_comment_blocks()

        # — Başlat + Log —
        action_frame = ttk.Frame(parent)
        action_frame.grid(row=row, column=0, sticky="ew", pady=(0, 4))
        action_frame.columnconfigure(1, weight=1)
        row += 1

        self.out_var = tk.StringVar(value=os.path.join(self.default_out, "output.mp4"))

        self.render_btn = ttk.Button(action_frame, text="Videoyu Oluştur", command=self.do_render, style="Accent.TButton", width=18)
        self.render_btn.grid(row=0, column=0, padx=(0, 8))
        f_out = ttk.Frame(action_frame)
        f_out.grid(row=0, column=1, sticky="ew")
        f_out.columnconfigure(0, weight=1)
        ttk.Entry(f_out, textvariable=self.out_var, font=("Segoe UI", 8)).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(f_out, text="...", command=self._out_file, width=3).grid(row=0, column=1)

        self.log_text = scrolledtext.ScrolledText(parent, height=10, wrap=tk.WORD, font=("Consolas", 8), bg="#1e1e1e", fg="#d4d4d4", insertbackground="#fff")
        self.log_text.grid(row=row, column=0, sticky="nsew", pady=(0, 0))
        parent.rowconfigure(row, weight=1)

    # ─────────────────── TAB 2: AYARLAR ───────────────────
    def _build_settings_tab(self, parent):
        row = 0

        # — Kalite —
        q_frame = ttk.LabelFrame(parent, text="Video Kalitesi", padding="8")
        q_frame.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        q_frame.columnconfigure(1, weight=1)
        row += 1

        ttk.Label(q_frame, text="Çözünürlük:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.quality_resolution_var = tk.StringVar(value=self.quality_resolution)
        res_combo = ttk.Combobox(q_frame, textvariable=self.quality_resolution_var, values=("720p", "1080p"), width=8, state="readonly")
        res_combo.grid(row=0, column=1, sticky="w")
        res_combo.bind("<<ComboboxSelected>>", lambda e: self._save_quality_settings())

        ttk.Label(q_frame, text="FPS:").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=(4, 0))
        self.quality_fps_var = tk.StringVar(value=self.quality_fps)
        fps_combo = ttk.Combobox(q_frame, textvariable=self.quality_fps_var, values=("30", "60"), width=8, state="readonly")
        fps_combo.grid(row=1, column=1, sticky="w", pady=(4, 0))
        fps_combo.bind("<<ComboboxSelected>>", lambda e: self._save_quality_settings())

        # — Layout —
        l_frame = ttk.LabelFrame(parent, text="Layout", padding="8")
        l_frame.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        l_frame.columnconfigure(1, weight=1)
        row += 1

        labels = ["Avatar boyutu (%)", "Kenar boşluğu (%)", "Yorum genişliği (%)"]
        defaults = [self.avatar_size_ratio * 100, self.header_padding_ratio * 100, self.comment_text_size_ratio * 100]
        ranges = [(40, 90), (2, 8), (70, 100)]
        self.avatar_size_var = tk.DoubleVar(value=defaults[0])
        self.header_padding_var = tk.DoubleVar(value=defaults[1])
        self.comment_text_size_var = tk.DoubleVar(value=defaults[2])
        vars_ = [self.avatar_size_var, self.header_padding_var, self.comment_text_size_var]

        for i, (lbl, var, (lo, hi)) in enumerate(zip(labels, vars_, ranges)):
            ttk.Label(l_frame, text=lbl + ":").grid(row=i, column=0, sticky="w", padx=(0, 6), pady=2)
            sp = ttk.Spinbox(l_frame, from_=lo, to=hi, textvariable=var, width=8)
            sp.grid(row=i, column=1, sticky="w", pady=2)
            sp.bind("<FocusOut>", lambda e: self._save_layout_settings())

        # — Klasörler —
        f_frame = ttk.LabelFrame(parent, text="Otomatik Klasörler", padding="8")
        f_frame.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        f_frame.columnconfigure(1, weight=1)
        row += 1

        ttk.Label(f_frame, text="Video klasörü:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.video_folder_var = tk.StringVar(value=self.video_folder)
        f_vf = ttk.Frame(f_frame)
        f_vf.grid(row=0, column=1, sticky="ew")
        f_vf.columnconfigure(0, weight=1)
        ttk.Entry(f_vf, textvariable=self.video_folder_var).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(f_vf, text="...", command=self._choose_video_folder, width=3).grid(row=0, column=1)

        ttk.Label(f_frame, text="Görsel klasörü:").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=(4, 0))
        self.image_folder_var = tk.StringVar(value=self.image_folder)
        f_if = ttk.Frame(f_frame)
        f_if.grid(row=1, column=1, sticky="ew", pady=(4, 0))
        f_if.columnconfigure(0, weight=1)
        ttk.Entry(f_if, textvariable=self.image_folder_var).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(f_if, text="...", command=self._choose_image_folder, width=3).grid(row=0, column=1)

        # — Cookies —
        c_frame = ttk.LabelFrame(parent, text="TikTok Cookies", padding="8")
        c_frame.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        c_frame.columnconfigure(1, weight=1)
        row += 1

        ttk.Label(c_frame, text="cookies.txt:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.cookies_var = tk.StringVar(value=self.cookies_file)
        f_ck = ttk.Frame(c_frame)
        f_ck.grid(row=0, column=1, sticky="ew")
        f_ck.columnconfigure(0, weight=1)
        ttk.Entry(f_ck, textvariable=self.cookies_var).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(f_ck, text="...", command=self._choose_cookies, width=3).grid(row=0, column=1)

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

    def _toggle_auto_video(self):
        v = self.auto_video_var.get()
        if v:
            self.use_tiktok_url_var.set(False)
            self._toggle_video_source()
            self.auto_video_var.set(True)
        self.auto_video_enabled = self.auto_video_var.get()
        self._settings["auto_video_enabled"] = self.auto_video_enabled
        save_settings(self._settings)

    def _toggle_auto_image(self):
        self.auto_image_enabled = self.auto_image_var.get()
        self._settings["auto_image_enabled"] = self.auto_image_enabled
        save_settings(self._settings)

    def _on_comment_count_changed(self, event=None):
        try:
            n = int(self.comment_count_var.get())
            if 1 <= n <= 3:
                self.comment_count = n
                self._settings["comment_count"] = self.comment_count
                save_settings(self._settings)
                self._show_comment_blocks()
        except (ValueError, TypeError):
            pass

    def _show_comment_blocks(self):
        n = getattr(self, "comment_count", 1)
        if not hasattr(self, "comment_blocks"):
            return
        for i, block in enumerate(self.comment_blocks):
            if i < n:
                block["frame"].grid()
            else:
                block["frame"].grid_remove()

    def _save_quality_settings(self):
        self.quality_resolution = self.quality_resolution_var.get()
        self.quality_fps = self.quality_fps_var.get()
        self._settings["quality_resolution"] = self.quality_resolution
        self._settings["quality_fps"] = self.quality_fps
        save_settings(self._settings)

    def _save_layout_settings(self):
        if not hasattr(self, "post_text_var"):
            return
        self.post_text = self.post_text_var.get().strip()
        self.avatar_size_ratio = self.avatar_size_var.get() / 100.0
        self.header_padding_ratio = self.header_padding_var.get() / 100.0
        self.comment_text_size_ratio = self.comment_text_size_var.get() / 100.0
        if "layout" not in self._settings:
            self._settings["layout"] = {}
        self._settings["layout"]["post_text"] = self.post_text
        self._settings["layout"]["avatar_size_ratio"] = self.avatar_size_ratio
        self._settings["layout"]["header_padding_ratio"] = self.header_padding_ratio
        self._settings["layout"]["comment_text_size_ratio"] = self.comment_text_size_ratio
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
        """Otomatik video (dosya modunda) ve otomatik görsel: N en son görsel (N = yorum sayısı)."""
        def latest_videos(folder, limit=1):
            if not folder or not os.path.isdir(folder):
                return []
            exts = [".mp4", ".mov"]
            candidates = []
            try:
                for entry in os.scandir(folder):
                    if not entry.is_file():
                        continue
                    if entry.name.lower().endswith(tuple(exts)):
                        candidates.append((entry.stat().st_mtime, entry.path))
                candidates.sort(key=lambda x: -x[0])
                return [p for (_, p) in candidates[:limit]]
            except Exception:
                return []

        def latest_images_sorted(folder, limit):
            """En son eklenen N görseli getirir (mtime en büyük = en yeni). Sıra: [en_yeni, ..., en_eski_olan_N]."""
            if not folder or not os.path.isdir(folder):
                return []
            exts = [".png", ".jpg", ".jpeg"]
            candidates = []
            try:
                for entry in os.scandir(folder):
                    if not entry.is_file():
                        continue
                    if entry.name.lower().endswith(tuple(exts)):
                        candidates.append((entry.stat().st_mtime, entry.path))
                candidates.sort(key=lambda x: -x[0])
                return [p for (_, p) in candidates[:limit]]
            except Exception:
                return []

        use_url = self.use_tiktok_url_var.get()
        if not use_url and self.auto_video_var.get():
            if not self.video_var.get().strip() or not os.path.isfile(self.video_var.get().strip()):
                vids = latest_videos(self.video_folder_var.get().strip(), 1)
                if vids:
                    self.video_var.set(vids[0])

        n_comments = getattr(self, "comment_count", 1)
        if self.auto_image_var.get() and hasattr(self, "comment_blocks"):
            folder = self.image_folder_var.get().strip()
            images = latest_images_sorted(folder, n_comments)
            # Kullanıcı önce Yorum 1 metnini yazıp SS alır (en eski), son Yorum 3 (en yeni).
            # images = [en_yeni, 2., 3.] -> Yorum 1 = en eski = images[n-1], Yorum 2 = images[n-2], Yorum 3 = images[0]
            for i in range(n_comments):
                if i < len(self.comment_blocks):
                    var = self.comment_blocks[i]["img_var"]
                    if not var.get().strip() or not os.path.isfile(var.get().strip()):
                        idx_img = n_comments - 1 - i
                        if 0 <= idx_img < len(images):
                            var.set(images[idx_img])

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
                # Varsayılan: erkek sesi (Ahmet) varsa onu seç, yoksa ilk Türkçe ses
                default_voice = next((v["ShortName"] for v in tr if "Ahmet" in v.get("ShortName", "")), tr[0]["ShortName"] if tr else None)
                self.root.after(0, lambda: self.voice_combo.config(values=names))
                if default_voice:
                    self.root.after(0, lambda: self.voice_var.set(default_voice))
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
        out = self.out_var.get().strip()

        try:
            n = max(1, min(3, int(self.comment_count_var.get())))
        except (ValueError, TypeError):
            n = 1

        texts = []
        images = []
        for i in range(n):
            if i >= len(self.comment_blocks):
                break
            block = self.comment_blocks[i]
            t = block["text"].get("1.0", tk.END).strip()
            img = block["img_var"].get().strip()
            texts.append(t)
            images.append(img)

        if n != len(texts) or n != len(images):
            messagebox.showwarning("Eksik", "Yorum alanları okunamadı.")
            return

        if not use_url and (not video or not os.path.isfile(video)):
            self._auto_pick_media()
            video = self.video_var.get().strip()
        if use_url and not tiktok_url:
            messagebox.showwarning("Eksik", "TikTok URL girin.")
            return
        if not use_url and (not video or not os.path.isfile(video)):
            messagebox.showwarning("Eksik", "Video dosyası seçin veya TikTok URL kullanın.")
            return

        if self.auto_image_var.get():
            self._auto_pick_media()
            for i in range(n):
                images[i] = self.comment_blocks[i]["img_var"].get().strip()

        for i in range(n):
            if not texts[i]:
                messagebox.showwarning("Eksik", "Yorum " + str(i + 1) + " için TTS metni girin.")
                return
            if not images[i] or not os.path.isfile(images[i]):
                if self.auto_image_var.get():
                    folder = self.image_folder_var.get().strip()
                    exts = [".png", ".jpg", ".jpeg"]
                    count = 0
                    if folder and os.path.isdir(folder):
                        for e in os.scandir(folder):
                            if e.is_file() and e.name.lower().endswith(tuple(exts)):
                                count += 1
                    messagebox.showerror("Eksik", "Otomatik görsel: " + str(n) + " adet görsel gerekli, " + str(count) + " adet bulundu. Görsel klasörünü kontrol edin.")
                else:
                    messagebox.showwarning("Eksik", "Yorum " + str(i + 1) + " için görsel seçin.")
                return

        base_dir = os.path.dirname(out) if out else self.default_out
        if not base_dir:
            base_dir = self.default_out
        os.makedirs(base_dir, exist_ok=True)
        name_raw = texts[0].strip() or "video"
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

                voice = self.voice_var.get()
                if " (" in voice:
                    voice = voice.split(" (")[0]

                comment_segments = []
                for i in range(n):
                    self.root.after(0, lambda ii=i: self.log("TTS " + str(ii + 1) + " üretiliyor..."))
                    tts_path = os.path.join(tmp_dir, "tts_" + str(i) + ".mp3")
                    duration_sec = generate_tts(texts[i], voice, tts_path)
                    if duration_sec <= 0:
                        self.root.after(0, lambda: self.log("Hata: TTS süresi alınamadı (yorum " + str(i + 1) + ")."))
                        return
                    comment_segments.append({
                        "comment_image_path": images[i],
                        "tts_audio_path": tts_path,
                        "tts_duration_sec": duration_sec,
                    })

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
                    comment_segments=comment_segments,
                    output_path=out,
                    log_cb=lambda s: self.root.after(0, lambda m=s: self.log(m)),
                    quality_resolution=quality_resolution,
                    quality_fps=quality_fps,
                    post_text=self.post_text_var.get().strip(),
                    avatar_size_ratio=self.avatar_size_var.get() / 100.0,
                    header_padding_ratio=self.header_padding_var.get() / 100.0,
                    comment_text_size_ratio=self.comment_text_size_var.get() / 100.0,
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
