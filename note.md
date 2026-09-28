# 1. Cài đặt FFmpeg (bắt buộc để trích xuất âm thanh từ video)
#    Windows: Tải từ https://ffmpeg.org/ và thêm vào PATH
#    MacOS: brew install ffmpeg
#    Linux: sudo apt install ffmpeg

# Cài các thư viện Python trong môi trường ảo
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# Chạy ứng dụng
.venv\Scripts\python main.py
