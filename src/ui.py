# -*- coding: utf-8 -*-
"""Video Factory GUI: dosya seçiciler, metin alanları, Render butonu, log."""
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


def _channels_path():
    return os.path.join(get_app_dir(), CHANNELS_FILE)


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


class VideoFactoryUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Factory - Repost Overlay + TTS")
        self.root.geometry("720x820")
        self.root.minsize(600, 700)
        self.app_dir = get_app_dir()
        self.default_out = os.path.join(self.app_dir, "output")
        self._abort = False
        self._channels = load_channels()
        self.setup_ui()
        self._refresh_channel_list()

    def setup_ui(self):
        main = ttk.Frame(self.root, padding="10")
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(main, text="Video Factory", font=("Arial", 14, "bold")).grid(row=row, column=0, columnspan=2, pady=(0, 10))
        row += 1

        # Video
        ttk.Label(main, text="Video (mp4/mov):").grid(row=row, column=0, sticky="w", padx=(0, 8))
        self.video_var = tk.StringVar()
        f = ttk.Frame(main)
        f.grid(row=row, column=1, sticky="ew")
        f.columnconfigure(0, weight=1)
        ttk.Entry(f, textvariable=self.video_var, width=50).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(f, text="Seç", command=lambda: self._file(self.video_var, "Video", [("Video", "*.mp4 *.mov")]), width=8).grid(row=0, column=1)
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
        self.voice_var = tk.StringVar(value="tr-TR-AhmetNeural")
        self.voice_combo = ttk.Combobox(main, textvariable=self.voice_var, width=28, state="readonly")
        self.voice_combo.grid(row=row, column=1, sticky="w")
        row += 1

        # Çıktı (sabit 1080x1920, 30fps)
        ttk.Label(main, text="Çıktı dosyası:").grid(row=row, column=0, sticky="w", padx=(0, 8))
        self.out_var = tk.StringVar(value=os.path.join(self.default_out, "output.mp4"))
        f = ttk.Frame(main)
        f.grid(row=row, column=1, sticky="ew")
        f.columnconfigure(0, weight=1)
        ttk.Entry(f, textvariable=self.out_var, width=50).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(f, text="Kaydet yeri", command=self._out_file, width=10).grid(row=0, column=1)
        row += 1

        # Render
        btn_f = ttk.Frame(main)
        btn_f.grid(row=row, column=0, columnspan=2, pady=10)
        self.render_btn = ttk.Button(btn_f, text="Render", command=self.do_render, width=14)
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
            self._on_channel_selected()
            d.destroy()
        btn_f = ttk.Frame(f)
        btn_f.grid(row=3, column=0, columnspan=2, pady=16)
        ttk.Button(btn_f, text="Kaydet", command=save, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_f, text="İptal", command=d.destroy, width=10).pack(side=tk.LEFT)

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
                ahmet = next((v["ShortName"] for v in tr if "Ahmet" in v.get("ShortName", "")), None)
                self.root.after(0, lambda: self.voice_combo.config(values=names))
                if ahmet:
                    self.root.after(0, lambda: self.voice_var.set(ahmet))
            except Exception:
                pass
        threading.Thread(target=load, daemon=True).start()

    def log(self, msg: str):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def do_render(self):
        video = self.video_var.get().strip()
        logo = self.logo_var.get().strip()
        comment_img = self.comment_img_var.get().strip()
        comment_txt = self.comment_text.get("1.0", tk.END).strip()
        out = self.out_var.get().strip()

        if not video or not os.path.isfile(video):
            messagebox.showwarning("Eksik", "Video dosyası seçin.")
            return
        if not comment_img or not os.path.isfile(comment_img):
            messagebox.showwarning("Eksik", "Yorum görseli seçin.")
            return
        if not comment_txt:
            messagebox.showwarning("Eksik", "Yorum metni (TTS) girin.")
            return
        if not out:
            messagebox.showwarning("Eksik", "Çıktı dosyası belirtin.")
            return

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

        def run():
            try:
                self.log("TTS üretiliyor...")
                voice = self.voice_var.get()
                if " (" in voice:
                    voice = voice.split(" (")[0]
                tmp_dir = tempfile.mkdtemp(prefix="vf_")
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
                    video_path=video,
                    logo_path=logo_path,
                    channel_name=self.channel_var.get().strip(),
                    username=self.username_var.get().strip(),
                    comment_image_path=comment_img,
                    tts_audio_path=tts_path,
                    tts_duration_sec=duration_sec,
                    output_path=out,
                    log_cb=lambda s: self.root.after(0, lambda m=s: self.log(m)),
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
