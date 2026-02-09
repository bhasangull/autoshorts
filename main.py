import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import edge_tts
import asyncio
import threading
import os
import sys


def get_app_dir():
    """Exe veya script çalışma dizinini döndür"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


class TTSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Edge TTS - Ahmet Sesli Metin Okuma")
        self.root.geometry("800x650")
        self.root.resizable(True, True)
        
        self.voice = "tr-TR-AhmetNeural"
        self.save_folder = os.path.expanduser("~\\Documents")
        
        self.setup_ui()
        self.check_voice_availability()
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        title_label = ttk.Label(main_frame, text="Edge TTS - Ahmet Sesli Metin Okuma", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        # Ses seçimi
        voice_frame = ttk.Frame(main_frame)
        voice_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 8))
        voice_frame.columnconfigure(1, weight=1)
        ttk.Label(voice_frame, text="Ses:").grid(row=0, column=0, padx=(0, 10))
        self.voice_var = tk.StringVar(value=self.voice)
        self.voice_combo = ttk.Combobox(voice_frame, textvariable=self.voice_var, 
                                        width=30, state="readonly")
        self.voice_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Ses dosyası adı
        name_frame = ttk.Frame(main_frame)
        name_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 8))
        name_frame.columnconfigure(1, weight=1)
        ttk.Label(name_frame, text="Ses dosyası adı:").grid(row=0, column=0, padx=(0, 10))
        self.filename_var = tk.StringVar(value="ses_cikti")
        self.filename_entry = ttk.Entry(name_frame, textvariable=self.filename_var, width=40)
        self.filename_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Label(name_frame, text=".mp3").grid(row=0, column=2)
        
        # Kayıt klasörü
        folder_frame = ttk.Frame(main_frame)
        folder_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 8))
        folder_frame.columnconfigure(1, weight=1)
        ttk.Label(folder_frame, text="Kayıt klasörü:").grid(row=0, column=0, padx=(0, 10), sticky=tk.W)
        self.folder_var = tk.StringVar(value=self.save_folder)
        self.folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_var, width=50)
        self.folder_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(folder_frame, text="Klasör Seç", command=self.choose_folder, width=12).grid(row=0, column=2)
        
        # Metin girişi
        ttk.Label(main_frame, text="Okunacak Metin:").grid(row=4, column=0, columnspan=2, 
                                                           sticky=tk.W, pady=(10, 5))
        self.text_input = scrolledtext.ScrolledText(main_frame, height=12, wrap=tk.WORD)
        self.text_input.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), 
                            pady=(0, 10))
        
        # Butonlar
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=10)
        self.play_button = ttk.Button(button_frame, text="▶ Oku", command=self.play_audio, width=15)
        self.play_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(button_frame, text="⏹ Durdur", command=self.stop_audio, 
                                       width=15, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        self.save_button = ttk.Button(button_frame, text="💾 Dosyaya Kaydet", 
                                      command=self.save_audio, width=20)
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(main_frame, text="Hazır", relief=tk.SUNKEN)
        self.status_label.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        self.is_playing = False
    
    def choose_folder(self):
        folder = filedialog.askdirectory(title="Ses dosyasının kaydedileceği klasörü seçin",
                                        initialdir=self.folder_var.get())
        if folder:
            self.folder_var.set(folder)
            self.save_folder = folder
    
    def get_voice_short_name(self):
        s = self.voice_var.get()
        return s.split(" (")[0] if " (" in s else s
    
    def get_save_path(self):
        name = self.filename_var.get().strip() or "ses_cikti"
        if not name.endswith(".mp3"):
            name += ".mp3"
        folder = self.folder_var.get().strip() or self.save_folder
        return os.path.join(folder, name)
    
    def check_voice_availability(self):
        def load_voices():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                voices = loop.run_until_complete(edge_tts.list_voices())
                loop.close()
                turkish_voices = [v for v in voices if v["Locale"].startswith("tr-TR")]
                voice_names = [f"{v['ShortName']} ({v['Gender']})" for v in turkish_voices]
                ahmet_voice = None
                for v in turkish_voices:
                    if "Ahmet" in v.get("ShortName", ""):
                        ahmet_voice = v["ShortName"]
                        break
                if ahmet_voice:
                    self.voice = ahmet_voice
                    self.voice_var.set(ahmet_voice)
                self.root.after(0, lambda: self.voice_combo.config(values=voice_names))
                self.root.after(0, lambda: self.update_status("Sesler yüklendi"))
            except Exception as e:
                self.root.after(0, lambda: self.update_status(f"Hata: {str(e)}"))
        threading.Thread(target=load_voices, daemon=True).start()
    
    def update_status(self, message):
        self.status_label.config(text=message)
    
    def play_audio(self):
        text = self.text_input.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Uyarı", "Lütfen okunacak bir metin girin!")
            return
        voice = self.get_voice_short_name()
        app_dir = get_app_dir()
        temp_path = os.path.join(app_dir, "temp_audio.mp3")
        self.is_playing = True
        self.play_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.update_status("Seslendiriliyor...")
        
        def play():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                async def speak():
                    communicate = edge_tts.Communicate(text, voice)
                    await communicate.save(temp_path)
                loop.run_until_complete(speak())
                loop.close()
                if self.is_playing:
                    os.startfile(temp_path)
                    self.root.after(0, lambda: self.update_status("Tamamlandı"))
                else:
                    self.root.after(0, lambda: self.update_status("Durduruldu"))
            except Exception as e:
                self.root.after(0, lambda: self.update_status(f"Hata: {str(e)}"))
                self.root.after(0, lambda: messagebox.showerror("Hata", f"Seslendirme hatası: {str(e)}"))
            finally:
                self.root.after(0, lambda: self.play_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
                self.is_playing = False
        threading.Thread(target=play, daemon=True).start()
    
    def stop_audio(self):
        self.is_playing = False
        self.update_status("Durduruluyor...")
        os.system("taskkill /F /IM wmplayer.exe 2>nul")
        os.system("taskkill /F /IM msedge.exe /FI \"WINDOWTITLE eq *temp_audio*\" 2>nul")
    
    def save_audio(self):
        text = self.text_input.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Uyarı", "Lütfen kaydedilecek bir metin girin!")
            return
        filepath = self.get_save_path()
        folder = os.path.dirname(filepath)
        if not os.path.isdir(folder):
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Hata", f"Klasör oluşturulamadı: {str(e)}")
                return
        voice = self.get_voice_short_name()
        self.update_status("Dosya kaydediliyor...")
        
        def save():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                async def speak():
                    communicate = edge_tts.Communicate(text, voice)
                    await communicate.save(filepath)
                loop.run_until_complete(speak())
                loop.close()
                self.root.after(0, lambda: self.update_status(f"Kaydedildi: {os.path.basename(filepath)}"))
                self.root.after(0, lambda: messagebox.showinfo("Başarılı", f"Dosya kaydedildi:\n{filepath}"))
            except Exception as e:
                self.root.after(0, lambda: self.update_status(f"Hata: {str(e)}"))
                self.root.after(0, lambda: messagebox.showerror("Hata", f"Kaydetme hatası: {str(e)}"))
        threading.Thread(target=save, daemon=True).start()


def main():
    root = tk.Tk()
    app = TTSApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
