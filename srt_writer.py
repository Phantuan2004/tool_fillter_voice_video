"""Ghi các đoạn thoại thành file phụ đề SRT."""

from media_utils import format_srt_time


def write_srt(segments, output_path):
    """Ghi các segment Whisper vào một file SRT."""
    with open(output_path, "w", encoding="utf-8") as output_file:
        for index, segment in enumerate(segments, start=1):
            start_time = format_srt_time(segment.start)
            end_time = format_srt_time(segment.end)
            text = segment.text.strip()
            output_file.write(f"{index}\n")
            output_file.write(f"{start_time} --> {end_time}\n")
            output_file.write(f"{text}\n\n")
