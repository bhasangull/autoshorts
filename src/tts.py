# -*- coding: utf-8 -*-
"""TTS modülü: edge-tts ile metin -> ses, süre ölçümü."""
import asyncio
import edge_tts
import os
import sys
import subprocess


def get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_ffprobe():
    """Bundled veya sistem ffprobe yolunu döndür."""
    app_dir = get_app_dir()
    for name in ("ffprobe.exe", "ffprobe"):
        path = os.path.join(app_dir, name)
        if os.path.isfile(path):
            return path
    return "ffprobe"


def get_audio_duration_seconds(audio_path: str) -> float:
    """MP3/WAV süresini saniye cinsinden döndür (ffprobe)."""
    ffprobe = get_ffprobe()
    cmd = [
        ffprobe,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=10)
        return float(out.strip())
    except Exception:
        return 0.0


async def generate_tts_async(text: str, voice: str, output_path: str) -> None:
    """Metni ses dosyasına yazar."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def generate_tts(text: str, voice: str, output_path: str) -> float:
    """
    TTS üretir, dosyaya yazar, süreyi (saniye) döndürür.
    voice örn: tr-TR-EmelNeural
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(generate_tts_async(text, voice, output_path))
        return get_audio_duration_seconds(output_path)
    finally:
        loop.close()
