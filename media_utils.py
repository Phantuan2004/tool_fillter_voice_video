"""Các hàm làm việc với file video và audio."""

import os
from pathlib import Path

from moviepy import VideoFileClip

VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv")


def find_video_files(folder):
    """Trả về danh sách video trong một thư mục, đã sắp xếp theo tên."""
    folder_path = Path(folder)
    video_files = [
        path
        for extension in VIDEO_EXTENSIONS
        for path in folder_path.glob(f"*{extension}")
    ]
    return sorted(video_files)


def extract_audio(video_path, audio_path):
    """Trích xuất audio thành WAV PCM 16 kHz."""
    video = None
    try:
        video = VideoFileClip(video_path)
        if video.audio is None:
            return False

        video.audio.write_audiofile(
            audio_path,
            fps=16000,
            nbytes=2,
            codec="pcm_s16le",
            logger=None,
        )
        return True
    finally:
        if video is not None:
            video.close()


def format_srt_time(seconds):
    """Đổi số giây thành định dạng thời gian của SRT."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def remove_file(path):
    """Xóa file nếu file đó tồn tại."""
    if os.path.exists(path):
        os.remove(path)
