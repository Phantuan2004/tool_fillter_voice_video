"""Ghi các đoạn thoại thành file phụ đề SRT."""

from media_utils import format_srt_time


def segments_to_list(segments):
    """Vật chất hoá generator của Whisper thành list of dict chuẩn.

    Returns:
        list of dict: [{"index": int, "start": float, "end": float, "text": str}]
    """
    result = []
    for i, seg in enumerate(segments, start=1):
        result.append({
            "index": i,
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
        })
    return result


def write_srt(segments, output_path):
    """Ghi danh sách segment (list of dict) vào file SRT.

    Args:
        segments: list of dict với keys: index, start, end, text
        output_path: đường dẫn file .srt đầu ra
    """
    with open(output_path, "w", encoding="utf-8") as output_file:
        for seg in segments:
            start_time = format_srt_time(seg["start"])
            end_time = format_srt_time(seg["end"])
            text = seg["text"]
            output_file.write(f"{seg['index']}\n")
            output_file.write(f"{start_time} --> {end_time}\n")
            output_file.write(f"{text}\n\n")
