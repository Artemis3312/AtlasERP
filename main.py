import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from app.database.db import init_db
from app.ui.main_window import MainWindow


def main():
    # Inicializar Base de Datos SQLite (100% Offline)
    init_db()

    # Habilitar soporte High-DPI
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("AtlasERP")
    app.setOrganizationName("Atlas")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
