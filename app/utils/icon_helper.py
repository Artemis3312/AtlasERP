from pathlib import Path
from typing import Optional
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray, QSize, Qt

ICON_BASE_DIR = Path(__file__).resolve().parent.parent.parent / "img" / "icons"


def get_icon(name: str, color: Optional[str] = None, size: int = 24) -> QIcon:
    """
    Carga un archivo SVG y opcionalmente reemplaza 'currentColor' con el color deseado.
    """
    svg_path = ICON_BASE_DIR / f"{name}.svg"
    if not svg_path.exists():
        return QIcon()

    if not color:
        return QIcon(str(svg_path))

    try:
        svg_text = svg_path.read_text(encoding="utf-8")
        tinted_text = svg_text.replace("currentColor", color)
        renderer = QSvgRenderer(QByteArray(tinted_text.encode("utf-8")))

        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        renderer.render(painter)
        painter.end()

        return QIcon(pix)
    except Exception:
        return QIcon(str(svg_path))


def get_stateful_icon(name: str, normal_color: str = "#E2DAC2", active_color: str = "#222A2A", size: int = 24) -> QIcon:
    """
    Crea un QIcon con estados: color normal y color seleccionado/activo.
    """
    svg_path = ICON_BASE_DIR / f"{name}.svg"
    if not svg_path.exists():
        return QIcon()

    try:
        svg_text = svg_path.read_text(encoding="utf-8")
        icon = QIcon()

        # Normal
        norm_svg = svg_text.replace("currentColor", normal_color)
        r_norm = QSvgRenderer(QByteArray(norm_svg.encode("utf-8")))
        pix_norm = QPixmap(size, size)
        pix_norm.fill(Qt.transparent)
        p1 = QPainter(pix_norm)
        r_norm.render(p1)
        p1.end()
        icon.addPixmap(pix_norm, QIcon.Normal, QIcon.Off)

        # On / Checked
        act_svg = svg_text.replace("currentColor", active_color)
        r_act = QSvgRenderer(QByteArray(act_svg.encode("utf-8")))
        pix_act = QPixmap(size, size)
        pix_act.fill(Qt.transparent)
        p2 = QPainter(pix_act)
        r_act.render(p2)
        p2.end()
        icon.addPixmap(pix_act, QIcon.Normal, QIcon.On)
        icon.addPixmap(pix_act, QIcon.Active, QIcon.On)

        return icon
    except Exception:
        return QIcon(str(svg_path))
