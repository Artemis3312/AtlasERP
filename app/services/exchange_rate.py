import requests
from typing import Tuple, Dict, Any
from ..database.db import get_connection
from ..utils.helpers import now_iso, parse_float

DOLARAPI_OFICIAL_URL = "https://ve.dolarapi.com/v1/dolares/oficial"
DOLARAPI_PARALELO_URL = "https://ve.dolarapi.com/v1/dolares/paralelo"


class ExchangeRateService:
    @staticmethod
    def get_rate_info() -> Dict[str, Any]:
        """Obtiene la tasa activa, fuente y fecha de actualización desde SQLite."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM settings WHERE key IN ('exchange_rate', 'rate_source', 'rate_updated_at')")
        rows = dict(cursor.fetchall())
        conn.close()

        rate = parse_float(rows.get("exchange_rate", "911.62"), 911.62)
        source = rows.get("rate_source", "MANUAL")
        updated_at = rows.get("rate_updated_at", now_iso())

        return {
            "rate": rate,
            "source": source,
            "updated_at": updated_at
        }

    @staticmethod
    def get_active_rate() -> float:
        """Devuelve únicamente el valor flotante de la tasa activa."""
        return ExchangeRateService.get_rate_info()["rate"]

    @staticmethod
    def set_rate(rate: float, source: str = "MANUAL") -> bool:
        """Guarda la nueva tasa en la base de datos local SQLite."""
        if rate <= 0:
            return False
        conn = get_connection()
        cursor = conn.cursor()
        ts = now_iso()
        cursor.execute("UPDATE settings SET value = ?, updated_at = ? WHERE key = 'exchange_rate'", (str(round(rate, 4)), ts))
        cursor.execute("UPDATE settings SET value = ?, updated_at = ? WHERE key = 'rate_source'", (source, ts))
        cursor.execute("UPDATE settings SET value = ?, updated_at = ? WHERE key = 'rate_updated_at'", (ts, ts))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def fetch_from_dolarapi(source_type: str = "oficial", auto_save: bool = True) -> Tuple[bool, float, str]:
        """
        Consulta la API de DolarAPI de forma segura con timeout de 4 segundos.
        Si está offline o falla, no se bloquea y devuelve mensaje descriptivo.
        """
        url = DOLARAPI_OFICIAL_URL if source_type == "oficial" else DOLARAPI_PARALELO_URL
        label = "Oficial (BCV)" if source_type == "oficial" else "Paralelo"

        try:
            resp = requests.get(url, timeout=4.0)
            if resp.status_code == 200:
                data = resp.json()
                rate_val = parse_float(data.get("promedio", 0.0))
                if rate_val > 0:
                    if auto_save:
                        ExchangeRateService.set_rate(rate_val, source=f"DOLARAPI_{source_type.upper()}")
                    return True, rate_val, f"Tasa {label} actualizada exitosamente desde DolarAPI."
                else:
                    return False, ExchangeRateService.get_active_rate(), "DolarAPI no devolvió un promedio válido."
            else:
                return False, ExchangeRateService.get_active_rate(), f"DolarAPI respondió con código {resp.status_code}."
        except requests.exceptions.Timeout:
            return False, ExchangeRateService.get_active_rate(), "Tiempo de espera agotado al consultar DolarAPI (Modo Offline activo)."
        except requests.exceptions.RequestException as e:
            return False, ExchangeRateService.get_active_rate(), f"Sin conexión a internet o error de red: usando tasa local ({ExchangeRateService.get_active_rate():.2f})."
        except Exception as e:
            return False, ExchangeRateService.get_active_rate(), f"Error inesperado al consultar tasa: {str(e)}"
