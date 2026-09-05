"""Dịch vụ tải model Whisper và nhận dạng giọng nói."""

import socket
import time

from faster_whisper import WhisperModel


class WhisperService:
    """Đóng gói việc tải model và chuyển audio thành các đoạn thoại."""

    def __init__(self, model_size, log_callback=None):
        self.model_size = model_size
        self.log_callback = log_callback
        self.model = self._load_model()

    def _log(self, message, level="info"):
        if self.log_callback is not None:
            self.log_callback(message, level)

    def _load_model(self):
        last_error = None
        for attempt in range(1, 4):
            try:
                return WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8",
                )
            except (ConnectionError, OSError, socket.error) as error:
                last_error = error
                if attempt < 3:
                    self._log(
                        f"Kết nối tải model bị gián đoạn, thử lại {attempt + 1}/3...",
                        "warning",
                    )
                    time.sleep(2 * attempt)

        raise RuntimeError(
            "Không thể tải model từ Hugging Face sau 3 lần thử. "
            "Hãy kiểm tra Internet/VPN/firewall rồi chạy lại. "
            f"Chi tiết: {last_error}"
        ) from last_error

    def transcribe(self, audio_path):
        """Nhận dạng audio và trả về các đoạn thoại cùng thông tin ngôn ngữ."""
        segments, info = self.model.transcribe(audio_path, beam_size=5)
        return segments, info
