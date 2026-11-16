import datetime


def format_usd(amount: float) -> str:
    """Formatea monto a formato USD: $ 1,234.56"""
    try:
        val = float(amount or 0.0)
        return f"$ {val:,.2f}"
    except (ValueError, TypeError):
        return "$ 0.00"


def format_bs(amount: float) -> str:
    """Formatea monto a formato Bolívares con separadores estilo venezolano: Bs. 1.234,56"""
    try:
        val = float(amount or 0.0)
        # Formato estándar con comas y puntos intercambiados para formato latino
        formatted = f"{val:,.2f}"
        # Invertir , y .
        parts = formatted.split(".")
        integer_part = parts[0].replace(",", ".")
        decimal_part = parts[1]
        return f"Bs. {integer_part},{decimal_part}"
    except (ValueError, TypeError):
        return "Bs. 0,00"


def format_qty(qty: float, unit: str = "") -> str:
    """Formatea cantidades: entero si no tiene decimales (ej: 1 en vez de 1,00), o con decimales limpios para KG."""
    try:
        val = float(qty or 0.0)
        u = f" {unit.strip().upper()}" if unit and unit.strip() else ""
        if val.is_integer():
            return f"{int(val)}{u}"
        formatted = f"{val:.3f}".rstrip("0").rstrip(".")
        formatted = formatted.replace(".", ",")
        return f"{formatted}{u}"
    except (ValueError, TypeError):
        return "0"


def parse_float(val: any, default: float = 0.0) -> float:
    """Convierte texto o número a float de forma segura admitiendo coma o punto decimal"""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(" ", "").replace("$", "").replace("Bs.", "").replace("Bs", "")
    if not s:
        return default
    # Si tiene comas y puntos, manejar separador
    if "," in s and "." in s:
        # e.g., 1,234.56 o 1.234,56
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return default


def now_iso() -> str:
    """Devuelve la fecha y hora actual en formato ISO legible"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_dt_display(iso_str: str) -> str:
    """Convierte fecha ISO (YYYY-MM-DD HH:MM:SS) a formato DD/MM/YYYY hh:mm A"""
    if not iso_str:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(iso_str.replace("Z", ""))
        return dt.strftime("%d/%m/%Y %I:%M %p")
    except Exception:
        return str(iso_str)
