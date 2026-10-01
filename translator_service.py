"""Dịch vụ dịch các đoạn thoại SRT sang ngôn ngữ đích."""

import time

from deep_translator import GoogleTranslator

# Mapping tên hiển thị -> mã ngôn ngữ Google Translate
LANGUAGE_CODES = {
    "Tiếng Anh (English)": "en",
    "Tiếng Việt": "vi",
    "Tiếng Nhật (日本語)": "ja",
    "Tiếng Hàn (한국어)": "ko",
}


class TranslatorService:
    """Dịch danh sách đoạn text sang ngôn ngữ đích bằng Google Translate."""

    def __init__(self, target_language_name, log_callback=None):
        """
        Args:
            target_language_name: Tên ngôn ngữ hiển thị (key trong LANGUAGE_CODES).
            log_callback: Hàm log(message, level) để báo tiến trình.
        """
        self.target_lang = LANGUAGE_CODES[target_language_name]
        self.target_lang_name = target_language_name
        self.log_callback = log_callback
        self._translator = GoogleTranslator(source="auto", target=self.target_lang)

    def _log(self, message, level="info"):
        if self.log_callback:
            self.log_callback(message, level)

    def translate_segments(self, segments):
        """Dịch danh sách segment (list of dict có key 'text') sang ngôn ngữ đích.

        Args:
            segments: list of dict với keys: index, start, end, text

        Returns:
            list of dict giống segments nhưng 'text' đã được dịch.
        """
        translated = []
        total = len(segments)
        for i, seg in enumerate(segments, 1):
            original_text = seg["text"].strip()
            if not original_text:
                translated.append({**seg, "text": ""})
                continue
            try:
                result = self._translator.translate(original_text)
                translated.append({**seg, "text": result or original_text})
            except Exception as error:
                self._log(
                    f"  Lỗi dịch đoạn {i}/{total}: {error} — giữ nguyên gốc",
                    "warning",
                )
                translated.append({**seg, "text": original_text})
                time.sleep(0.5)  # chờ tránh rate-limit trước khi tiếp tục
            # Nghỉ nhỏ để tránh bị block khi dịch nhiều đoạn liên tiếp
            time.sleep(0.05)
        return translated
