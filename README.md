# AtlasERP 🚀
### Sistema Integral de Punto de Venta y Gestión Comercial (100% Offline)
Desarrollado en **Python** con **PySide6** (Qt), base de datos **SQLite** y generación de reportes en PDF con **fpdf2**.

---

## 📋 Características Principales

1. **100% Operativo Offline**:
   - Toda la lógica, base de datos local SQLite (modo WAL con claves foráneas activas) y generación de reportes funcionan completamente sin internet.
   - En caso de contar con conexión, se puede consultar **DolarAPI** con un solo clic. Si no hay conexión o falla la red, el sistema mantiene la última tasa guardada o permite establecerla manualmente sin bloquear al cajero.

2. **Módulo de Inicio (Home)**:
   - Vista inicial limpia y elegante donde destaca el nombre del sistema (**AtlasERP**).
   - Indicador del estado del turno de caja (Abierto/Cerrado) y la tasa activa del día.
   - Accesos directos a los módulos operativos.

3. **Módulo de Caja (Punto de Venta / P.O.S.)**:
   - **Búsqueda ágil y escaneo**: Búsqueda por nombre o código de barras (presionar *Enter* añade el producto al carrito automáticamente).
   - **Carrito interactivo**: Modificación de cantidades, cálculo en tiempo real de totales en **USD ($)** y **Bolívares (Bs.)**.
   - **Facturación con Múltiples Métodos de Pago**:
     - **USD Efectivo**
     - **Bolívares Efectivo**
     - **Bolívares Tarjeta (Débito / P.O.S.)**
     - **Bolívares Pago Móvil** (*con número de referencia obligatorio*)
     - Permite pagos combinados o divididos (ej. parte en USD efectivo, parte en tarjeta y parte en Pago Móvil).
     - Cálculo de vuelto o cambio exacto.
     - Descuento automático de existencias en inventario.
   - **Función de "Avance de Efectivo"**:
     - Permite al negocio entregar Bolívares en efectivo al cliente y recibir el cobro equivalente mediante **Tarjeta** o **Pago Móvil** (con referencia obligatoria).
     - Validación de efectivo disponible en gaveta antes de autorizar el avance.
     - Posibilidad de configurar porcentaje de comisión por avance.
     - Registro inmediato en el historial de caja y balance del turno.

4. **Módulo de Inventario**:
   - Catálogo completo en formato de tabla con búsqueda reactiva.
   - Gestión integral: **Crear nuevo producto**, **Editar** y **Eliminar**.
   - Precios en USD y cálculo dinámico equivalente en Bolívares según la tasa activa.
   - Alerta visual de existencias bajas (stock mínimo) y productos agotados.
   - Indicadores KPI globales: Total de artículos, unidades totales en existencia, valorización al costo y valorización al precio de venta.

5. **Módulo de Historial de Movimientos y Arqueo de Caja**:
   - Listado cronológico de movimientos con fecha, hora exacta, turno, tipo y método de pago.
   - Filtros por turno (actual / históricos), tipo de movimiento (Venta, Avance, Entrada/Salida manual, Apertura, Cierre) y rango de fechas.
   - **Apertura de Turno**: Registro de base inicial en USD y Bolívares.
   - **Cierre de Turno y Arqueo de Caja**:
     - **Conteo Físico Real** ingresado por el cajero (Efectivo USD y Efectivo Bolívares).
     - **Cálculo Esperado por Sistema**: Considera base inicial, ventas en efectivo, avances entregados e ingresos/egresos manuales.
     - **Verificación de Diferencias**: Detecta automáticamente si la caja está **Cuadrada**, si existe **Faltante** o **Sobrante**.
     - **Contabilización Electrónica**: Totaliza de forma separada lo cobrado en **Tarjeta (P.O.S.)** y **Pago Móvil** para conciliar con los lotes bancarios.

6. **Módulo de Reportes Oficiales en PDF (fpdf2)**:
   - **Reporte de Histórico de Operaciones**:
     - Selector por rango de fechas (con accesos directos "Hoy", "Últimos 7 Días", "Este Mes").
     - Resumen global de ventas USD/BS, desglose por método de pago, avances de efectivo realizados y tabla detallada de cada movimiento.
   - **Reporte de Inventario Actual**:
     - Inventario completo, costos, precios, stock y valorización financiera del negocio.
     - Alertas de reposición de inventario crítico.
   - Visualización directa de los PDF generados y acceso directo a la carpeta de reportes.

7. **Gestión de Tasa de Cambio (DolarAPI + Manual)**:
   - Integración directa con **DolarAPI** (`https://ve.dolarapi.com/v1/dolares/oficial` y `/paralelo`) con timeout de 4 segundos y modo offline seguro.
   - Configuración manual de tasa personalizada en Bolívares por USD.
   - Actualización en tiempo real de todos los precios y totales de la interfaz al cambiar la tasa.

---

## 🛠️ Estructura del Proyecto

```text
AtlasERP/
│── app/
│   ├── database/
│   │   ├── db.py               # Conexión SQLite, tablas, migraciones y seed inicial
│   ├── services/
│   │   ├── exchange_rate.py    # Servicio DolarAPI y configuración de tasa
│   │   ├── inventory_service.py# CRUD y stock de productos
│   │   ├── shift_service.py    # Apertura, arqueo y cierre de turnos
│   │   ├── pos_service.py      # Facturación multi-pago y avances de efectivo
│   │   ├── movement_service.py # Movimientos de caja y filtros
│   │   └── report_service.py   # Generación de reportes PDF con fpdf2
│   ├── ui/
│   │   ├── styles.py           # Hoja de estilos moderna QSS
│   │   ├── main_window.py      # Ventana principal y barra de navegación
│   │   ├── home_view.py        # Módulo de Inicio
│   │   ├── pos_view.py         # Módulo de Caja (Punto de Venta)
│   │   ├── inventory_view.py   # Módulo de Inventario
│   │   ├── history_view.py     # Módulo de Historial y Arqueo
│   │   ├── reports_view.py     # Módulo de Reportes PDF
│   │   └── dialogs/            # Modales de cobro, avance, producto, arqueo y tasa
│   └── utils/
│       └── helpers.py          # Formateadores de moneda (USD/BS), cantidades y fechas
├── data/
│   ├── atlas_erp.db            # Base de datos SQLite local
│   └── reports/                # Documentos PDF generados
├── tests/
│   ├── test_atlas_erp.py       # Pruebas unitarias de servicios y lógica de negocio
│   └── test_ui.py              # Pruebas de inicialización de vistas y modales
├── main.py                     # Punto de entrada de la aplicación
├── requirements.txt            # Dependencias del proyecto
└── README.md
```

---

## 🚀 Instalación y Ejecución

### 1. Activar el entorno virtual e instalar dependencias

```powershell
# En Windows PowerShell:
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Ejecutar la aplicación

```powershell
python main.py
```

O directamente con el ejecutable del entorno virtual:

```powershell
.\.venv\Scripts\python.exe main.py
```

### 3. Ejecutar las pruebas automatizadas

```powershell
.\.venv\Scripts\python.exe -m unittest discover tests
```
