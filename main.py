"""Điểm khởi động của ứng dụng Video to SRT."""

from gui_app import create_app


if __name__ == "__main__":
    application = create_app()
    application.mainloop()
