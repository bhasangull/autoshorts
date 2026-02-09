# -*- coding: utf-8 -*-
"""Video Factory: entry noktası. GUI (varsayılan) veya CLI."""
import os
import sys
import argparse


def _cli():
    parser = argparse.ArgumentParser(description="Video Factory - Repost overlay + TTS")
    parser.add_argument("--video", required=True, help="Video dosyası (mp4/mov)")
    parser.add_argument("--logo", default="", help="Logo PNG")
    parser.add_argument("--channel_name", default="", help="Kanal adı")
    parser.add_argument("--username", default="", help="Kullanıcı adı")
    parser.add_argument("--comment_image", required=True, help="Yorum görseli (png/jpg)")
    parser.add_argument("--comment_text", required=True, help="Yorum metni (TTS okunacak)")
    parser.add_argument("--out", required=True, help="Çıktı MP4 yolu (1080x1920, 30fps)")
    parser.add_argument("--voice", default="tr-TR-AhmetNeural", help="TTS sesi")
    args = parser.parse_args()

    from src.tts import generate_tts
    from src.render import run_pipeline
    import tempfile

    if not os.path.isfile(args.video):
        print("Hata: Video dosyası bulunamadı:", args.video)
        sys.exit(1)
    if not os.path.isfile(args.comment_image):
        print("Hata: Yorum görseli bulunamadı:", args.comment_image)
        sys.exit(1)

    def log(s):
        print(s)

    tmp = tempfile.mkdtemp(prefix="vf_cli_")
    tts_path = os.path.join(tmp, "tts.mp3")
    try:
        duration_sec = generate_tts(args.comment_text, args.voice, tts_path)
        if duration_sec <= 0:
            print("Hata: TTS üretilemedi veya süre alınamadı.")
            sys.exit(1)
        logo_path = args.logo if args.logo and os.path.isfile(args.logo) else None
        if not logo_path:
            from PIL import Image
            logo_path = os.path.join(tmp, "empty.png")
            Image.new("RGBA", (1, 1), (0, 0, 0, 0)).save(logo_path)
        ok = run_pipeline(
            video_path=args.video,
            logo_path=logo_path,
            channel_name=args.channel_name or "",
            username=args.username or "",
            comment_image_path=args.comment_image,
            tts_audio_path=tts_path,
            tts_duration_sec=duration_sec,
            output_path=args.out,
            log_cb=log,
        )
        if ok:
            print("Tamamlandı:", args.out)
        else:
            sys.exit(1)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def _gui():
    from src.ui import main as ui_main
    ui_main()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].strip().startswith("--"):
        _cli()
    else:
        _gui()
