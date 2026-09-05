"""Giao diện Tkinter cho công cụ chuyển video thành phụ đề."""

import os
import threading
import time
from pathlib import Path
from tkinter import END, EXTENDED, LEFT, RIGHT, BOTH, BOTTOM, DISABLED, NORMAL, X, Y, W
from tkinter import IntVar, Listbox, StringVar, Tk, filedialog, messagebox, scrolledtext
from tkinter import ttk

from media_utils import extract_audio, find_video_files, remove_file
from srt_writer import write_srt
from whisper_service import WhisperService


class VideoToSRTApp:
    """Điều phối giao diện và quy trình xử lý video."""

    def __init__(self, root):
        self.root = root
        self.root.title("🎬 Video to SRT - Tool trích xuất lời thoại")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        self.input_folder = StringVar()
        self.output_folder = StringVar()
        self.model_size = StringVar(value="base")
        self.progress_value = IntVar(value=0)
        self.is_processing = False
        self.video_files = []

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=BOTH, expand=True)

        folder_frame = ttk.LabelFrame(main_frame, text="📁 Thư mục video", padding="10")
        folder_frame.pack(fill=X, pady=(0, 10))
        ttk.Label(folder_frame, text="Thư mục chứa video:").grid(row=0, column=0, sticky=W, pady=5)
        ttk.Entry(folder_frame, textvariable=self.input_folder, width=50).grid(row=0, column=1, padx=5, sticky="ew")
        ttk.Button(folder_frame, text="Chọn thư mục", command=self.select_input_folder).grid(row=0, column=2, padx=5)
        ttk.Label(folder_frame, text="Thư mục lưu SRT:").grid(row=1, column=0, sticky=W, pady=5)
        ttk.Entry(folder_frame, textvariable=self.output_folder, width=50).grid(row=1, column=1, padx=5, sticky="ew")
        ttk.Button(folder_frame, text="Chọn thư mục", command=self.select_output_folder).grid(row=1, column=2, padx=5)

        config_frame = ttk.LabelFrame(main_frame, text="⚙️ Cấu hình", padding="10")
        config_frame.pack(fill=X, pady=(0, 10))
        ttk.Label(config_frame, text="Model Whisper:").grid(row=0, column=0, sticky=W, pady=5)
        ttk.Combobox(
            config_frame,
            textvariable=self.model_size,
            values=["tiny", "base", "small", "medium"],
            state="readonly",
            width=15,
        ).grid(row=0, column=1, sticky=W, padx=5)
        ttk.Label(config_frame, text="(tiny: nhanh nhất, small: chính xác hơn)").grid(row=0, column=2, sticky=W)

        list_frame = ttk.LabelFrame(main_frame, text="📋 Danh sách video", padding="10")
        list_frame.pack(fill=BOTH, expand=True, pady=(0, 10))
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.video_listbox = Listbox(
            list_container,
            yscrollcommand=scrollbar.set,
            selectmode=EXTENDED,
            font=("Arial", 10),
        )
        self.video_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.config(command=self.video_listbox.yview)
        ttk.Button(list_frame, text="🔄 Làm mới danh sách", command=self.refresh_video_list).pack(pady=5)

        status_frame = ttk.LabelFrame(main_frame, text="📊 Tiến trình", padding="10")
        status_frame.pack(fill=X, pady=(0, 10))
        ttk.Progressbar(status_frame, variable=self.progress_value, maximum=100, length=400).pack(fill=X, pady=5)
        self.status_label = ttk.Label(status_frame, text="Sẵn sàng", font=("Arial", 10))
        self.status_label.pack(pady=5)

        log_frame = ttk.LabelFrame(main_frame, text="📝 Nhật ký", padding="10")
        log_frame.pack(fill=BOTH, expand=True, pady=(0, 10))
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, font=("Consolas", 9), wrap="word")
        self.log_text.pack(fill=BOTH, expand=True)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=X, pady=1)
        self.process_button = ttk.Button(button_frame, text="🚀 Bắt đầu xử lý", command=self.start_processing)
        self.process_button.pack(side=LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Thoát", command=self.root.quit).pack(side=RIGHT, padx=5)

        self.input_folder.set(os.getcwd())
        self.output_folder.set(os.path.join(os.getcwd(), "transcripts"))
        self.refresh_video_list()

    def select_input_folder(self):
        folder = filedialog.askdirectory(title="Chon thu muc chua video")
        if folder:
            self.input_folder.set(folder)
            self.refresh_video_list()

    def select_output_folder(self):
        folder = filedialog.askdirectory(title="Chon thu muc luu SRT")
        if folder:
            self.output_folder.set(folder)

    def refresh_video_list(self):
        self.video_listbox.delete(0, END)
        folder = self.input_folder.get()
        if not os.path.exists(folder):
            self.add_log("Thu muc khong ton tai!", "error")
            return

        self.video_files = find_video_files(folder)
        if not self.video_files:
            self.add_log("Khong tim thay file video nao trong thu muc", "warning")
            return

        for video in self.video_files:
            size_mb = os.path.getsize(video) / (1024 * 1024)
            self.video_listbox.insert(END, f"{video.name} ({size_mb:.1f} MB)")
        self.add_log(f"Tim thay {len(self.video_files)} video", "info")

    def add_log(self, message, level="info"):
        timestamp = time.strftime("%H:%M:%S")
        prefixes = {
            "info": "INFO",
            "warning": "WARNING",
            "error": "ERROR",
            "success": "SUCCESS",
        }
        log_message = f"[{timestamp}] {prefixes.get(level, 'INFO')}: {message}\n"
        self.log_text.insert(END, log_message)
        self.log_text.see(END)
        self.root.update()

    def update_progress(self, value, status_text):
        self.progress_value.set(value)
        self.status_label.config(text=status_text)
        self.root.update()

    def process_videos(self):
        if self.is_processing:
            return
        if not self.video_files:
            messagebox.showwarning("Canh bao", "Khong co video nao de xu ly!")
            return

        output_dir = Path(self.output_folder.get())
        output_dir.mkdir(parents=True, exist_ok=True)
        self.is_processing = True
        self.process_button.config(state=DISABLED)
        self.add_log("Bat dau xu ly video...", "info")
        threading.Thread(target=self._process_worker, daemon=True).start()

    def _process_worker(self):
        try:
            model_size = self.model_size.get()
            output_dir = Path(self.output_folder.get())
            self.add_log(f"Dang tai model {model_size}...", "info")
            self.update_progress(0, f"Dang tai model {model_size}...")
            whisper = WhisperService(model_size, self.add_log)
            self.add_log(f"Model {model_size} da san sang", "success")

            total_videos = len(self.video_files)
            processed_count = 0
            for index, video_path in enumerate(self.video_files, 1):
                video_name = video_path.stem
                self.update_progress(int((index - 1) / total_videos * 100), f"Dang xu ly: {video_name}")
                self.add_log(f"[{index}/{total_videos}] Xu ly: {video_name}", "info")
                audio_path = output_dir / f"{video_name}_temp.wav"
                srt_path = output_dir / f"{video_name}.srt"

                try:
                    if not extract_audio(str(video_path), str(audio_path)):
                        self.add_log(f"Khong the trich xuat audio tu {video_name}", "error")
                        continue
                    self.add_log(f"Dang nhan dien giong noi: {video_name}", "info")
                    segments, info = whisper.transcribe(str(audio_path))
                    write_srt(segments, str(srt_path))
                    processed_count += 1
                    self.add_log(f"Da tao: {video_name}.srt (Ngon ngu: {info.language})", "success")
                finally:
                    remove_file(audio_path)

                self.update_progress(int(index / total_videos * 100), f"Hoan thanh: {video_name}")

            self.update_progress(100, "Xu ly hoan tat!")
            self.add_log(f"Da xu ly xong {processed_count}/{total_videos} video!", "success")
            messagebox.showinfo("Thanh cong", f"Da xu ly {processed_count}/{total_videos} video!\n\nFile SRT luu tai:\n{output_dir}")
        except Exception as error:
            self.add_log(f"Loi nghiem trong: {error}", "error")
            messagebox.showerror("Loi", f"Co loi xay ra:\n{error}")
        finally:
            self.is_processing = False
            self.process_button.config(state=NORMAL)
            self.update_progress(0, "San sang")

    def start_processing(self):
        if not self.video_files:
            messagebox.showwarning("Canh bao", "Khong co video nao de xu ly!")
            return
        answer = messagebox.askyesno(
            "Xac nhan",
            f"Ban co muon xu ly {len(self.video_files)} video khong?\n\n"
            f"Model: {self.model_size.get()}\n"
            f"Thu muc luu: {self.output_folder.get()}",
        )
        if answer:
            self.process_videos()


def create_app():
    """Tạo cửa sổ ứng dụng và áp dụng giao diện mặc định."""
    root = Tk()
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Accent.TButton", font=("Arial", 10, "bold"))
    VideoToSRTApp(root)
    return root
