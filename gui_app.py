"""PyQt6 interface for converting videos into subtitles."""

import os
import threading
import time
from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from media_utils import extract_audio, find_video_files, remove_file
from srt_writer import write_srt
from whisper_service import WhisperService


class VideoToSRTApp(QMainWindow):
    """Main window and video processing workflow."""

    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(int, int, str)
    error_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video to SRT | Trích xuất lời thoại")
        self.resize(1000, 820)
        self.setMinimumSize(760, 660)

        self.is_processing = False
        self.video_files = []
        self._build_ui()
        self._apply_theme()

        self.log_signal.connect(self.add_log)
        self.progress_signal.connect(self.update_progress)
        self.finished_signal.connect(self._on_processing_finished)
        self.error_signal.connect(self._on_processing_error)

        self.input_folder.setText(os.getcwd())
        self.output_folder.setText(os.path.join(os.getcwd(), "transcripts"))
        self.refresh_video_list()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        heading = QHBoxLayout()
        title_block = QVBoxLayout()
        eyebrow = QLabel("VIDEO / TRANSCRIPTION")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("Video to SRT")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Trích xuất lời thoại và tạo phụ đề bằng Whisper")
        subtitle.setObjectName("muted")
        title_block.addWidget(eyebrow)
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        heading.addLayout(title_block)
        heading.addStretch()
        layout.addLayout(heading)

        settings_row = QHBoxLayout()
        settings_row.setSpacing(14)

        folder_group = QGroupBox("Thư mục")
        folder_layout = QFormLayout(folder_group)
        folder_layout.setContentsMargins(16, 20, 16, 14)
        folder_layout.setHorizontalSpacing(12)
        folder_layout.setVerticalSpacing(10)
        self.input_folder = QLineEdit()
        self.output_folder = QLineEdit()
        self.input_folder.setClearButtonEnabled(True)
        self.output_folder.setClearButtonEnabled(True)
        input_row = self._folder_row(self.input_folder, self.select_input_folder)
        output_row = self._folder_row(self.output_folder, self.select_output_folder)
        folder_layout.addRow("Nguồn video", input_row)
        folder_layout.addRow("Lưu phụ đề", output_row)

        config_group = QGroupBox("Cấu hình")
        config_layout = QVBoxLayout(config_group)
        config_layout.setContentsMargins(16, 20, 16, 14)
        config_layout.setSpacing(9)
        model_label = QLabel("Model Whisper")
        self.model_size = QComboBox()
        self.model_size.addItems(["tiny", "base", "small", "medium"])
        self.model_size.setCurrentText("base")
        model_hint = QLabel("tiny nhanh hơn · small chính xác hơn")
        model_hint.setObjectName("muted")
        config_layout.addWidget(model_label)
        config_layout.addWidget(self.model_size)
        config_layout.addWidget(model_hint)
        config_layout.addStretch()

        settings_row.addWidget(folder_group, 3)
        settings_row.addWidget(config_group, 1)
        layout.addLayout(settings_row)

        videos_group = QGroupBox("Danh sách video")
        videos_layout = QVBoxLayout(videos_group)
        videos_layout.setContentsMargins(12, 18, 12, 12)
        self.video_list = QListWidget()
        self.video_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.video_list.setAlternatingRowColors(True)
        list_actions = QHBoxLayout()
        self.video_count = QLabel("0 video")
        self.video_count.setObjectName("muted")
        refresh_button = QPushButton("Làm mới danh sách")
        refresh_button.setObjectName("secondaryButton")
        refresh_button.clicked.connect(self.refresh_video_list)
        list_actions.addWidget(self.video_count)
        list_actions.addStretch()
        list_actions.addWidget(refresh_button)
        videos_layout.addWidget(self.video_list, 1)
        videos_layout.addLayout(list_actions)
        layout.addWidget(videos_group, 3)

        progress_group = QGroupBox("Tiến trình")
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setContentsMargins(16, 18, 16, 14)
        progress_layout.setSpacing(9)
        self.status_label = QLabel("Sẵn sàng")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.progress_bar)
        layout.addWidget(progress_group)

        log_group = QGroupBox("Nhật ký")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(12, 18, 12, 12)
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(1500)
        self.log_text.setPlaceholderText("Nhật ký xử lý sẽ hiển thị tại đây")
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group, 2)

        actions = QHBoxLayout()
        self.process_button = QPushButton("Bắt đầu xử lý")
        self.process_button.setObjectName("primaryButton")
        self.process_button.clicked.connect(self.start_processing)
        exit_button = QPushButton("Thoát")
        exit_button.setObjectName("secondaryButton")
        exit_button.clicked.connect(self.close)
        actions.addWidget(self.process_button)
        actions.addStretch()
        actions.addWidget(exit_button)
        layout.addLayout(actions)

    def _folder_row(self, line_edit, browse_callback):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        browse_button = QPushButton("Chọn...")
        browse_button.setObjectName("secondaryButton")
        browse_button.clicked.connect(browse_callback)
        row_layout.addWidget(line_edit, 1)
        row_layout.addWidget(browse_button)
        return row

    def _apply_theme(self):
        self.setStyleSheet(
            """
            QWidget {
                background-color: #0a1113;
                color: #e3efed;
                font-family: "Segoe UI";
                font-size: 10pt;
            }
            QLabel#eyebrow {
                color: #50d6c2;
                font-size: 9pt;
                font-weight: 700;
            }
            QLabel#pageTitle {
                color: #f0f7f6;
                font-size: 23pt;
                font-weight: 700;
            }
            QLabel#muted { color: #8ba5a2; }
            QGroupBox {
                background-color: #111b1e;
                border: 1px solid #2b4548;
                border-radius: 7px;
                margin-top: 10px;
                padding-top: 5px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #b5cfcb;
            }
            QLineEdit, QComboBox, QListWidget, QPlainTextEdit {
                background-color: #0b1315;
                border: 1px solid #30494c;
                border-radius: 5px;
                padding: 8px;
                selection-background-color: #176f68;
            }
            QLineEdit:focus, QComboBox:focus, QListWidget:focus,
            QPlainTextEdit:focus { border: 1px solid #42cbb8; }
            QListWidget { alternate-background-color: #101a1c; }
            QListWidget::item { padding: 7px 8px; border-radius: 3px; }
            QListWidget::item:selected { background-color: #155a55; color: #f0fffc; }
            QPlainTextEdit { color: #b9cfca; font-family: Consolas; font-size: 9pt; }
            QPushButton {
                min-height: 20px;
                padding: 7px 13px;
                border: 1px solid #365457;
                border-radius: 5px;
                background-color: #172528;
                color: #dceae7;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #203638; border-color: #4d7778; }
            QPushButton:disabled { color: #6d8280; background-color: #131d1f; }
            QPushButton#primaryButton {
                background-color: #147b72;
                border-color: #23988c;
                color: #f3fffd;
                padding: 9px 18px;
            }
            QPushButton#primaryButton:hover { background-color: #199286; }
            QPushButton#secondaryButton { background-color: #142023; }
            QProgressBar {
                min-height: 12px;
                max-height: 12px;
                background-color: #091012;
                border: 1px solid #2b4548;
                border-radius: 6px;
                text-align: center;
            }
            QProgressBar::chunk { background-color: #32c6b2; border-radius: 5px; }
            QScrollBar:vertical {
                width: 10px;
                background: #0b1315;
                margin: 2px;
            }
            QScrollBar::handle:vertical { background: #34585a; min-height: 24px; border-radius: 4px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            """
        )

    def select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục chứa video", self.input_folder.text())
        if folder:
            self.input_folder.setText(folder)
            self.refresh_video_list()

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu SRT", self.output_folder.text())
        if folder:
            self.output_folder.setText(folder)

    def refresh_video_list(self):
        self.video_list.clear()
        folder = self.input_folder.text()
        if not os.path.exists(folder):
            self.video_count.setText("Thư mục không tồn tại")
            self.add_log("Thư mục không tồn tại!", "error")
            return

        self.video_files = find_video_files(folder)
        for video in self.video_files:
            size_mb = os.path.getsize(video) / (1024 * 1024)
            self.video_list.addItem(f"{video.name}    ·    {size_mb:.1f} MB")
        self.video_count.setText(f"{len(self.video_files)} video")
        if self.video_files:
            self.add_log(f"Tìm thấy {len(self.video_files)} video", "info")
        else:
            self.add_log("Không tìm thấy file video nào trong thư mục", "warning")

    def add_log(self, message, level="info"):
        timestamp = time.strftime("%H:%M:%S")
        prefixes = {"info": "INFO", "warning": "WARNING", "error": "ERROR", "success": "SUCCESS"}
        self.log_text.appendPlainText(f"[{timestamp}] {prefixes.get(level, 'INFO')}: {message}")

    def update_progress(self, value, status_text):
        self.progress_bar.setValue(value)
        self.status_label.setText(status_text)

    def start_processing(self):
        if not self.video_files:
            QMessageBox.warning(self, "Cảnh báo", "Không có video nào để xử lý!")
            return

        answer = QMessageBox.question(
            self,
            "Xác nhận xử lý",
            f"Bạn muốn xử lý {len(self.video_files)} video?\n\n"
            f"Model: {self.model_size.currentText()}\n"
            f"Thư mục lưu: {self.output_folder.text()}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.process_videos()

    def process_videos(self):
        if self.is_processing:
            return
        if not self.video_files:
            QMessageBox.warning(self, "Cảnh báo", "Không có video nào để xử lý!")
            return

        output_dir = Path(self.output_folder.text())
        output_dir.mkdir(parents=True, exist_ok=True)
        self.is_processing = True
        self.process_button.setEnabled(False)
        self.add_log("Bắt đầu xử lý video...", "info")
        worker = threading.Thread(
            target=self._process_worker,
            args=(list(self.video_files), self.model_size.currentText(), output_dir),
            daemon=True,
        )
        worker.start()

    def _process_worker(self, video_files, model_size, output_dir):
        processed_count = 0
        try:
            self.log_signal.emit(f"Đang tải model {model_size}...", "info")
            self.progress_signal.emit(0, f"Đang tải model {model_size}...")
            whisper = WhisperService(model_size, self.log_signal.emit)
            self.log_signal.emit(f"Model {model_size} đã sẵn sàng", "success")

            total_videos = len(video_files)
            for index, video_path in enumerate(video_files, 1):
                video_name = video_path.stem
                self.progress_signal.emit(int((index - 1) / total_videos * 100), f"Đang xử lý: {video_name}")
                self.log_signal.emit(f"[{index}/{total_videos}] Xử lý: {video_name}", "info")
                audio_path = output_dir / f"{video_name}_temp.wav"
                srt_path = output_dir / f"{video_name}.srt"

                try:
                    if not extract_audio(str(video_path), str(audio_path)):
                        self.log_signal.emit(f"Không thể trích xuất audio từ {video_name}", "error")
                        continue
                    self.log_signal.emit(f"Đang nhận dạng giọng nói: {video_name}", "info")
                    segments, info = whisper.transcribe(str(audio_path))
                    write_srt(segments, str(srt_path))
                    processed_count += 1
                    self.log_signal.emit(f"Đã tạo: {video_name}.srt (Ngôn ngữ: {info.language})", "success")
                finally:
                    remove_file(audio_path)

                self.progress_signal.emit(int(index / total_videos * 100), f"Hoàn thành: {video_name}")

            self.progress_signal.emit(100, "Xử lý hoàn tất!")
            self.log_signal.emit(f"Đã xử lý xong {processed_count}/{total_videos} video!", "success")
            self.finished_signal.emit(processed_count, total_videos, str(output_dir))
        except Exception as error:
            self.log_signal.emit(f"Lỗi nghiêm trọng: {error}", "error")
            self.error_signal.emit(str(error))
        finally:
            self.finished_signal.emit(-1, -1, "")

    def _on_processing_finished(self, processed_count, total_videos, output_dir):
        if processed_count >= 0:
            QMessageBox.information(
                self,
                "Thành công",
                f"Đã xử lý {processed_count}/{total_videos} video!\n\nFile SRT lưu tại:\n{output_dir}",
            )
            return
        self.is_processing = False
        self.process_button.setEnabled(True)

    def _on_processing_error(self, error):
        QMessageBox.critical(self, "Lỗi", f"Có lỗi xảy ra:\n{error}")


def create_app():
    """Create the main application window."""
    return VideoToSRTApp()
