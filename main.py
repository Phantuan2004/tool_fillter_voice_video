"""Điểm khởi động của ứng dụng Video to SRT."""

from gui_app import create_app


if __name__ == "__main__":
    application = create_app()
    application.mainloop()
import os
import sys
import threading
import time
import socket
from pathlib import Path
from tkinter import *
from tkinter import ttk, filedialog, messagebox, scrolledtext

# Import các thư viện xử lý
from faster_whisper import WhisperModel
from moviepy import VideoFileClip

class VideoToSRTApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎬 Video to SRT - Tool trích xuất lời thoại")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Biến lưu trạng thái
        self.input_folder = StringVar()
        self.output_folder = StringVar()
        self.model_size = StringVar(value="base")
        self.progress_value = IntVar(value=0)
        self.is_processing = False
        self.video_files = []
        self.processed_files = []
        
        # Tạo giao diện
        self.create_widgets()
        
    def create_widgets(self):
        """Tạo các thành phần giao diện"""
        
        # === Frame chính ===
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=BOTH, expand=True)
        
        # === Phần 1: Chọn thư mục ===
        folder_frame = ttk.LabelFrame(main_frame, text="📁 Thư mục video", padding="10")
        folder_frame.pack(fill=X, pady=(0, 10))
        
        # Input folder
        ttk.Label(folder_frame, text="Thư mục chứa video:").grid(row=0, column=0, sticky=W, pady=5)
        ttk.Entry(folder_frame, textvariable=self.input_folder, width=50).grid(row=0, column=1, padx=5, sticky=EW)
        ttk.Button(folder_frame, text="Chọn thư mục", command=self.select_input_folder).grid(row=0, column=2, padx=5)
        
        # Output folder
        ttk.Label(folder_frame, text="Thư mục lưu SRT:").grid(row=1, column=0, sticky=W, pady=5)
        ttk.Entry(folder_frame, textvariable=self.output_folder, width=50).grid(row=1, column=1, padx=5, sticky=EW)
        ttk.Button(folder_frame, text="Chọn thư mục", command=self.select_output_folder).grid(row=1, column=2, padx=5)
        
        # === Phần 2: Cấu hình ===
        config_frame = ttk.LabelFrame(main_frame, text="⚙️ Cấu hình", padding="10")
        config_frame.pack(fill=X, pady=(0, 10))
        
        # Model size
        ttk.Label(config_frame, text="Model Whisper:").grid(row=0, column=0, sticky=W, pady=5)
        model_combo = ttk.Combobox(
            config_frame, 
            textvariable=self.model_size,
            values=["tiny", "base", "small", "medium"],
            state="readonly",
            width=15
        )
        model_combo.grid(row=0, column=1, sticky=W, padx=5)
        ttk.Label(config_frame, text="(tiny: nhanh nhất, small: chính xác nhất)", font=("Arial", 8)).grid(row=0, column=2, sticky=W)
        
        # === Phần 3: Danh sách video ===
        list_frame = ttk.LabelFrame(main_frame, text="📋 Danh sách video", padding="10")
        list_frame.pack(fill=BOTH, expand=True, pady=(0, 10))
        
        # Tạo khung chứa listbox + scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        self.video_listbox = Listbox(
            list_container,
            yscrollcommand=scrollbar.set,
            selectmode=EXTENDED,
            font=("Arial", 10)
        )
        self.video_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.config(command=self.video_listbox.yview)
        
        # Nút refresh danh sách
        ttk.Button(list_frame, text="🔄 Làm mới danh sách", command=self.refresh_video_list).pack(pady=5)
        
        # === Phần 4: Trạng thái và tiến trình ===
        status_frame = ttk.LabelFrame(main_frame, text="📊 Tiến trình", padding="10")
        status_frame.pack(fill=X, pady=(0, 10))
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            status_frame,
            variable=self.progress_value,
            maximum=100,
            length=400
        )
        self.progress_bar.pack(fill=X, pady=5)
        
        # Label trạng thái
        self.status_label = ttk.Label(status_frame, text="Sẵn sàng", font=("Arial", 10))
        self.status_label.pack(pady=5)
        
        # === Phần 5: Log ===
        log_frame = ttk.LabelFrame(main_frame, text="📝 Nhật ký", padding="10")
        log_frame.pack(fill=BOTH, expand=True, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=8,
            font=("Consolas", 9),
            wrap=WORD
        )
        self.log_text.pack(fill=BOTH, expand=True)
        
        # === Phần 6: Nút điều khiển ===
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=X, pady=1)
        
        self.process_button = ttk.Button(
            button_frame,
            text="🚀 Bắt đầu xử lý",
            command=self.start_processing,
            style="Accent.TButton"
        )
        self.process_button.pack(side=LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="❌ Thoát",
            command=self.root.quit
        ).pack(side=RIGHT, padx=5)
        
        # === Khởi tạo giá trị mặc định ===
        self.input_folder.set(os.getcwd())
        self.output_folder.set(os.path.join(os.getcwd(), "transcripts"))
        
        # Tự động refresh danh sách video khi mở
        self.refresh_video_list()
        
    def select_input_folder(self):
        """Chọn thư mục chứa video"""
        folder = filedialog.askdirectory(title="Chọn thư mục chứa video")
        if folder:
            self.input_folder.set(folder)
            self.refresh_video_list()
    
    def select_output_folder(self):
        """Chọn thư mục lưu file SRT"""
        folder = filedialog.askdirectory(title="Chọn thư mục lưu SRT")
        if folder:
            self.output_folder.set(folder)
    
    def refresh_video_list(self):
        """Làm mới danh sách video trong thư mục"""
        self.video_listbox.delete(0, END)
        folder = self.input_folder.get()
        
        if not os.path.exists(folder):
            self.add_log("❌ Thư mục không tồn tại!", "error")
            return
        
        # Tìm các file video
        extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv']
        video_files = []
        
        for ext in extensions:
            video_files.extend(Path(folder).glob(f"*{ext}"))
        
        self.video_files = sorted(video_files)
        
        if not self.video_files:
            self.add_log("⚠️ Không tìm thấy file video nào trong thư mục", "warning")
        else:
            for video in self.video_files:
                size_mb = os.path.getsize(video) / (1024 * 1024)
                self.video_listbox.insert(END, f"{video.name} ({size_mb:.1f} MB)")
            
            self.add_log(f"✅ Tìm thấy {len(self.video_files)} video", "info")
    
    def add_log(self, message, level="info"):
        """Thêm log vào khung hiển thị"""
        timestamp = time.strftime("%H:%M:%S")
        
        # Màu sắc cho từng loại log
        tags = {
            "info": "INFO",
            "warning": "⚠️ WARNING", 
            "error": "❌ ERROR",
            "success": "✅ SUCCESS"
        }
        
        prefix = tags.get(level, "INFO")
        log_message = f"[{timestamp}] {prefix}: {message}\n"
        
        self.log_text.insert(END, log_message)
        self.log_text.see(END)
        self.root.update()
    
    def update_progress(self, value, status_text):
        """Cập nhật thanh tiến trình và trạng thái"""
        self.progress_value.set(value)
        self.status_label.config(text=status_text)
        self.root.update()

    def load_whisper_model(self, model_size):
        """Tải model với retry để chịu được kết nối Hugging Face chập chờn."""
        last_error = None
        for attempt in range(1, 4):
            try:
                return WhisperModel(
                    model_size,
                    device="cpu",
                    compute_type="int8"
                )
            except (ConnectionError, OSError, socket.error) as error:
                last_error = error
                if attempt < 3:
                    self.add_log(
                        f"Kết nối tải model bị gián đoạn, thử lại {attempt + 1}/3...",
                        "warning"
                    )
                    time.sleep(2 * attempt)

        raise RuntimeError(
            "Không thể tải model từ Hugging Face sau 3 lần thử. "
            "Hãy kiểm tra Internet/VPN/firewall rồi chạy lại. "
            f"Chi tiết: {last_error}"
        ) from last_error
    
    def format_time(self, seconds):
        """Chuyển seconds sang định dạng SRT: HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def extract_audio(self, video_path, audio_path):
        """Trích xuất âm thanh từ video"""
        try:
            video = VideoFileClip(video_path)
            if video.audio is not None:
                video.audio.write_audiofile(
                    audio_path, 
                    fps=16000, 
                    nbytes=2, 
                    codec='pcm_s16le',
                    logger=None
                )
                video.close()
                return True
            return False
        except Exception as e:
            self.add_log(f"Lỗi trích xuất audio: {e}", "error")
            return False
    
    def process_videos(self):
        """Xử lý toàn bộ video trong danh sách"""
        if self.is_processing:
            return
        
        if not self.video_files:
            messagebox.showwarning("Cảnh báo", "Không có video nào để xử lý!")
            return
        
        # Kiểm tra thư mục output
        output_dir = Path(self.output_folder.get())
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Tạo thread xử lý để không treo GUI
        self.is_processing = True
        self.process_button.config(state=DISABLED)
        self.add_log("🚀 Bắt đầu xử lý video...", "info")
        
        # Chạy xử lý trong thread riêng
        threading.Thread(target=self._process_worker, daemon=True).start()
    
    def _process_worker(self):
        """Worker thread xử lý video"""
        try:
            model_size = self.model_size.get()
            output_dir = Path(self.output_folder.get())
            
            # Load model
            self.add_log(f"⏳ Đang tải model {model_size}...", "info")
            self.update_progress(0, f"Đang tải model {model_size}...")
            
            model = self.load_whisper_model(model_size)
            
            self.add_log(f"✅ Model {model_size} đã sẵn sàng", "success")
            
            total_videos = len(self.video_files)
            processed_count = 0
            
            for idx, video_path in enumerate(self.video_files, 1):
                video_name = video_path.stem
                
                # Update progress
                progress = int((idx - 1) / total_videos * 100)
                self.update_progress(progress, f"Đang xử lý: {video_name}")
                self.add_log(f"🎬 [{idx}/{total_videos}] Xử lý: {video_name}", "info")
                
                # Đường dẫn file tạm
                audio_path = output_dir / f"{video_name}_temp.wav"
                srt_path = output_dir / f"{video_name}.srt"
                
                # 1. Trích xuất audio
                if not self.extract_audio(str(video_path), str(audio_path)):
                    self.add_log(f"❌ Không thể trích xuất audio từ {video_name}", "error")
                    continue
                
                # 2. Transcribe
                self.add_log(f"⏳ Đang nhận diện giọng nói: {video_name}", "info")
                segments, info = model.transcribe(str(audio_path), beam_size=5)
                
                # 3. Ghi file SRT
                with open(srt_path, 'w', encoding='utf-8') as f:
                    for i, seg in enumerate(segments, start=1):
                        start_time = self.format_time(seg.start)
                        end_time = self.format_time(seg.end)
                        text = seg.text.strip()
                        f.write(f"{i}\n")
                        f.write(f"{start_time} --> {end_time}\n")
                        f.write(f"{text}\n\n")
                
                # 4. Xóa file audio tạm
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                
                processed_count += 1
                
                self.add_log(f"✅ Đã tạo: {video_name}.srt (Ngôn ngữ: {info.language})", "success")
                
                # Cập nhật progress
                progress = int(idx / total_videos * 100)
                self.update_progress(progress, f"Hoàn thành: {video_name}")
            
            # Hoàn thành
            self.update_progress(100, "✅ Xử lý hoàn tất!")
            self.add_log(f"🎉 Đã xử lý xong {processed_count}/{total_videos} video!", "success")
            
            messagebox.showinfo(
                "Thành công",
                f"Đã xử lý {processed_count}/{total_videos} video!\n\n"
                f"File SRT được lưu tại:\n{output_dir}"
            )
            
        except Exception as e:
            self.add_log(f"❌ Lỗi nghiêm trọng: {e}", "error")
            messagebox.showerror("Lỗi", f"Có lỗi xảy ra:\n{str(e)}")
        
        finally:
            self.is_processing = False
            self.process_button.config(state=NORMAL)
            self.update_progress(0, "Sẵn sàng")
    
    def start_processing(self):
        """Bắt đầu xử lý (gọi từ nút bấm)"""
        if not self.video_files:
            messagebox.showwarning("Cảnh báo", "Không có video nào để xử lý!")
            return
        
        # Xác nhận với người dùng
        answer = messagebox.askyesno(
            "Xác nhận",
            f"Bạn có muốn xử lý {len(self.video_files)} video không?\n\n"
            f"Model: {self.model_size.get()}\n"
            f"Thư mục lưu: {self.output_folder.get()}"
        )
        
        if answer:
            self.process_videos()

# ==================== CHẠY ỨNG DỤNG ====================
if __name__ == "__main__":
    root = Tk()
    
    # Set style cho nút
    style = ttk.Style()
    style.theme_use('clam')
    style.configure('Accent.TButton', font=('Arial', 10, 'bold'))
    
    app = VideoToSRTApp(root)
    root.mainloop()