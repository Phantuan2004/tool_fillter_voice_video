"""Điểm khởi động của ứng dụng Video to SRT."""

import sys

from PyQt6.QtWidgets import QApplication

from gui_app import create_app


def main():
    """Khởi động ứng dụng PyQt6."""
    application = QApplication(sys.argv)
    window = create_app()
    window.show()
    sys.exit(application.exec())


if __name__ == "__main__":
    # Chạy với hot-reload trong môi trường dev: tự động restart khi
    # phát hiện thay đổi file .py trong thư mục dự án.
    # Thêm flag --no-reload để chạy bình thường (ví dụ: khi đóng gói).
    if "--no-reload" in sys.argv:
        main()
    else:
        try:
            from py_hot_reload import run_with_reloader

            run_with_reloader(
                main,
                interval=1,          # kiểm tra thay đổi mỗi 1 giây
                verbose=True,        # in thông báo khi reload
                ignore_venv_and_python_lib=True,
            )
        except ImportError:
            # Nếu py-hot-reload chưa cài, chạy bình thường
            main()
