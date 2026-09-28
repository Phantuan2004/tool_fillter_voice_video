"""Điểm khởi động của ứng dụng Video to SRT."""

import sys

from PyQt6.QtWidgets import QApplication

from gui_app import create_app


if __name__ == "__main__":
    application = QApplication(sys.argv)
    window = create_app()
    window.show()
    sys.exit(application.exec())
