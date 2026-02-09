# -*- coding: utf-8 -*-
"""FFmpeg tabanlı video pipeline: intro + header bar + yorum overlay, concat."""
import os
import sys
import subprocess
import tempfile
import shutil
from typing import Optional, Callable

from src.tts import get_audio_duration_seconds

# PIL header görseli için
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = ImageDraw = ImageFont = None


def get_app_dir():
    """Exe veya proje kök dizini (ffmpeg.exe burada aranır)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_resource_dir():
    """Bundle içi asset'ler (font vb.) frozen ise _MEIPASS."""
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        return sys._MEIPASS
    return get_app_dir()


def get_ffmpeg():
    app_dir = get_app_dir()
    for name in ("ffmpeg.exe", "ffmpeg"):
        path = os.path.join(app_dir, name)
        if os.path.isfile(path):
            return path
    return "ffmpeg"


def get_ffprobe():
    app_dir = get_app_dir()
    for name in ("ffprobe.exe", "ffprobe"):
        path = os.path.join(app_dir, name)
        if os.path.isfile(path):
            return path
    return "ffprobe"


def _run(cmd: list, log_cb: Optional[Callable[[str], None]] = None, timeout: Optional[int] = None):
    if log_cb:
        log_cb(" ".join(cmd))
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    out_lines = []
    for line in iter(p.stdout.readline, ""):
        out_lines.append(line)
        if log_cb:
            log_cb(line.rstrip())
    p.wait()
    if p.returncode != 0 and log_cb:
        log_cb(f"[HATA] Çıkış kodu: {p.returncode}")
    # Sadece exit code döndür (run_pipeline içinde 0 ile karşılaştırıyoruz)
    return p.returncode


def get_video_info(video_path: str) -> dict:
    """width, height, r_frame_rate (fps string), duration, has_audio."""
    ffprobe = get_ffprobe()
    cmd = [
        ffprobe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate",
        "-show_entries", "format=duration",
        "-of", "json",
        video_path,
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=30)
        import json
        d = json.loads(out)
        streams = d.get("streams", [])
        fmt = d.get("format", {})
        w = h = 0
        r_frame_rate = "30/1"
        for s in streams:
            if "width" in s:
                w = int(s["width"])
                h = int(s["height"])
                r_frame_rate = s.get("r_frame_rate", r_frame_rate)
                break
        duration = float(fmt.get("duration", 0))
        cmd2 = [ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path]
        r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=10)
        has_audio = r2.returncode == 0 and "audio" in (r2.stdout or "")
        return {"width": w, "height": h, "r_frame_rate": r_frame_rate, "duration": duration, "has_audio": has_audio}
    except Exception as e:
        return {"width": 0, "height": 0, "r_frame_rate": "30/1", "duration": 0, "has_audio": False, "error": str(e)}


def _parse_fps(r_frame_rate: str) -> float:
    try:
        if "/" in r_frame_rate:
            a, b = r_frame_rate.split("/", 1)
            return float(a) / float(b) if float(b) else 30.0
        return float(r_frame_rate)
    except Exception:
        return 30.0


def _font_path():
    """Türkçe destekleyen font: assets/fonts, sonra Windows Segoe UI, sonra Arial."""
    app_dir = get_resource_dir()
    for name in ("Roboto-Regular.ttf", "Inter-Regular.ttf", "NotoSans-Regular.ttf"):
        p = os.path.join(app_dir, "assets", "fonts", name)
        if os.path.isfile(p):
            return p
    if sys.platform == "win32":
        for name in ("segoeui.ttf", "arial.ttf"):
            p = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", name)
            if os.path.isfile(p):
                return p
    return None


def create_header_png(
    width: int,
    height: int,
    logo_path: str,
    channel_name: str,
    username: str,
    out_path: str,
    bar_opacity: float = 0.4,
) -> None:
    """Üst bar PNG: logo + kanal adı + kullanıcı adı. Bar yüksekliği min(W,H)*0.10 civarı."""
    if not Image or not ImageDraw:
        raise RuntimeError("Pillow (PIL) yüklü değil. pip install Pillow")
    m = min(width, height)
    padding = max(4, int(m * 0.02))
    channel_font_size = max(14, int(m * 0.035))
    username_font_size = max(12, int(m * 0.028))
    header_h = max(40, int(m * 0.10))

    font_path = _font_path()
    try:
        font_channel = ImageFont.truetype(font_path, channel_font_size) if font_path else ImageFont.load_default()
        font_username = ImageFont.truetype(font_path, username_font_size) if font_path else ImageFont.load_default()
    except Exception:
        font_channel = font_username = ImageFont.load_default()

    # Logo yüksekliği = header_h, genişlik orantılı
    logo_h = header_h
    logo_img = None
    if os.path.isfile(logo_path):
        try:
            logo_img = Image.open(logo_path).convert("RGBA")
            lw, lh = logo_img.size
            scale = logo_h / max(lh, 1)
            new_lw = int(lw * scale)
            logo_img = logo_img.resize((new_lw, logo_h), Image.Resampling.LANCZOS)
        except Exception:
            logo_img = None
    logo_w = logo_img.size[0] if logo_img else 0
    text_x = logo_w + padding * 2

    # Metin boyutları
    channel_bbox = font_channel.getbbox(channel_name or " ")
    ch_w = channel_bbox[2] - channel_bbox[0]
    ch_h = channel_bbox[3] - channel_bbox[1]
    user_bbox = font_username.getbbox(username or " ")
    uh = user_bbox[3] - user_bbox[1]
    text_block_h = ch_h + 2 + uh
    bar_h = max(header_h, text_block_h + padding * 2)

    # Bar genişliği = video genişliği
    bar_w = width
    img = Image.new("RGBA", (bar_w, bar_h), (0, 0, 0, int(255 * bar_opacity)))
    draw = ImageDraw.Draw(img)

    if logo_img:
        img.paste(logo_img, (padding, (bar_h - logo_h) // 2), logo_img)

    draw.text((text_x, padding), channel_name or "", fill=(255, 255, 255), font=font_channel)
    draw.text((text_x, padding + ch_h + 2), username or "", fill=(200, 200, 200), font=font_username)

    img.save(out_path, "PNG")


# Sabit çıktı: 1080x1920, 30 fps
OUT_W, OUT_H, OUT_FPS = 1080, 1920, 30


def run_pipeline(
    video_path: str,
    logo_path: str,
    channel_name: str,
    username: str,
    comment_image_path: str,
    tts_audio_path: str,
    tts_duration_sec: float,
    output_path: str,
    log_cb: Optional[Callable[[str], None]] = None,
) -> bool:
    """
    Intro (ilk frame + header + yorum, TTS süresi) + main (video + header, orijinal ses).
    Çıktı her zaman 1080x1920, 30 fps.
    """
    def log(s):
        if log_cb:
            log_cb(s)

    ffmpeg = get_ffmpeg()
    ffprobe = get_ffprobe()
    info = get_video_info(video_path)
    if info.get("width", 0) == 0:
        log("Hata: Video bilgisi alınamadı.")
        return False

    out_w, out_h, fps = OUT_W, OUT_H, OUT_FPS

    tmpdir = tempfile.mkdtemp(prefix="tts_video_")
    try:
        first_frame = os.path.join(tmpdir, "first.png")
        header_png = os.path.join(tmpdir, "header.png")
        intro_mp4 = os.path.join(tmpdir, "intro.mp4")
        main_mp4 = os.path.join(tmpdir, "main.mp4")
        list_txt = os.path.join(tmpdir, "list.txt")
        tts_trimmed = os.path.join(tmpdir, "tts_trimmed.mp3")

        # 0) TTS sonundaki sessizliği kırp (yüksek kalite: 256k MP3)
        _run([
            ffmpeg, "-y", "-i", tts_audio_path,
            "-af", "silenceremove=stop_periods=1:stop_duration=0.15:stop_threshold=-40dB",
            "-c:a", "libmp3lame", "-b:a", "256k", tts_trimmed,
        ], log_cb=log, timeout=30)
        tts_duration_use = get_audio_duration_seconds(tts_trimmed) if os.path.isfile(tts_trimmed) else tts_duration_sec
        if tts_duration_use <= 0:
            tts_duration_use = tts_duration_sec
        tts_audio_use = tts_trimmed if os.path.isfile(tts_trimmed) else tts_audio_path
        if tts_audio_use != tts_trimmed:
            tts_duration_use = tts_duration_sec

        # 1) İlk kare (tek dosya için -update 1)
        _run([ffmpeg, "-y", "-i", video_path, "-vframes", "1", "-f", "image2", "-update", "1", first_frame], log_cb=log, timeout=30)
        if not os.path.isfile(first_frame):
            log("Hata: İlk kare çıkarılamadı.")
            return False

        # 2) Header PNG
        create_header_png(out_w, out_h, logo_path, channel_name, username, header_png)
        if not os.path.isfile(header_png):
            log("Hata: Header oluşturulamadı.")
            return False

        # Yorum görseli max genişlik %85, Y ~ %55 (merkez)
        comment_max_w = int(out_w * 0.85)
        comment_x = "(main_w-overlay_w)/2"
        comment_y = "main_h*0.55-overlay_h/2"

        # 3) Intro: loop first frame + header + comment, süre = kırpılmış TTS süresi, ses = kırpılmış TTS
        filter_intro = (
            f"[0:v]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2,setsar=1[base];"
            f"[base][1:v]overlay=0:0[with_header];"
            f"[2:v]scale={comment_max_w}:-1[comment];"
            f"[with_header][comment]overlay={comment_x}:{comment_y}[v]"
        )
        cmd_intro = [
            ffmpeg, "-y",
            "-loop", "1", "-i", first_frame,
            "-i", header_png,
            "-i", comment_image_path,
            "-i", tts_audio_use,
            "-filter_complex", filter_intro,
            "-map", "[v]", "-map", "3:a",
            "-t", str(tts_duration_use),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps),
            "-c:a", "aac", "-b:a", "256k", "-ar", "44100", "-ac", "2",
            "-shortest", intro_mp4,
        ]
        if _run(cmd_intro, log_cb=log, timeout=300) != 0:
            log("Hata: Intro segment oluşturulamadı.")
            return False

        # 4) Main: video baştan (0. saniye) sonuna kadar, 1080x1920 + header overlay. Ses = videonun orijinal sesi.
        main_duration = max(0.1, info.get("duration", 0))
        filter_main = f"[0:v]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2,setsar=1[scaled];[scaled][1:v]overlay=0:0[v]"
        has_audio = info.get("has_audio", True)
        if has_audio:
            cmd_main = [
                ffmpeg, "-y", "-i", video_path,
                "-i", header_png,
                "-filter_complex", filter_main,
                "-map", "[v]", "-map", "0:a",
                "-t", str(main_duration),
                "-c:a", "aac", "-b:a", "256k", "-ar", "44100", "-ac", "2", main_mp4,
            ]
        else:
            filter_main = f"[0:v]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2,setsar=1[scaled];[scaled][2:v]overlay=0:0[v];[1:a]atrim=0:" + str(main_duration) + ",asetpts=PTS-STARTPTS[a]"
            cmd_main = [
                ffmpeg, "-y", "-i", video_path,
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-i", header_png,
                "-filter_complex", filter_main,
                "-map", "[v]", "-map", "[a]", "-t", str(main_duration),
                "-c:a", "aac", "-b:a", "256k", main_mp4,
            ]
        if _run(cmd_main, log_cb=log, timeout=600) != 0:
            log("Hata: Main segment oluşturulamadı.")
            return False

        # 5) Concat intro + main (Windows için path'te \\ -> /)
        def path_for_concat(p):
            return p.replace("\\", "/").replace("'", "'\\''")
        with open(list_txt, "w", encoding="utf-8") as f:
            f.write("file '" + path_for_concat(intro_mp4) + "'\n")
            f.write("file '" + path_for_concat(main_mp4) + "'\n")

        out_dir = os.path.dirname(output_path)
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        # Her iki segment aynı formatta (1080x1920, 30fps, AAC 44100 stereo); copy ile birleştir
        cmd_concat = [
            ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_txt,
            "-c", "copy", output_path,
        ]
        if _run(cmd_concat, log_cb=log, timeout=300) != 0:
            log("Hata: Birleştirme yapılamadı.")
            return False

        log("Render tamamlandı: " + output_path)
        return True
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
