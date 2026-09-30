import sys
import asyncio

# Solución para compatibilidad de red en Windows con Python moderno
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
from datetime import datetime, date
import os
import requests
import json
import io
import re
import time

# Configuración de la página y diseño estético
st.set_page_config(
    page_title="Control de Inventario - Bepensa / Coca-Cola",
    page_icon="❄️",
    layout="wide"
)

# Estilos CSS personalizados (incluyendo la corrección de altura y flexibilidad para evitar saltos al cargar componentes)
st.markdown("""
    <style>
    /* Forzar que el contenedor principal ocupe toda la altura y actúe como columna flexible */
    [data-testid="stAppViewContainer"] > .main {
        display: flex;
        flex-direction: column;
        min-height: 100vh;
        background-color: #FF7A00;
    }
    
    /* Hacer que el bloque de contenido crezca de manera ordenada */
    [data-testid="stAppViewContainer"] > .main > .block-container {
        flex: 1;
    }
    
    /* Personalización de la barra lateral (Sidebar) a color degradado */
    [data-testid="stSidebar"]{
        background: linear-gradient(
            180deg,
            #003B5C 0%,
            #002A42 100%
        );
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    
    /* Contenedor superior del sidebar para mantener ordenado el menú */
    [data-testid="stSidebar"] > div:first-child {
        display: flex;
        flex-direction: column;
        flex-grow: 1;
    }

    /* Cambiar el color de los textos y títulos dentro del Sidebar para que resalten */
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] p {
        color: #FFFFFF !important;
    }
    
    /* Estilo para el selectbox y elementos interactivos del sidebar */
    [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {
        background-color: #ffffff;
        color: #111827;
        border-radius: 8px;
    }
    [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] * {
        color: #111827 !important;
    }

    /* Color personalizado para el botón de Iniciar Sesión (#E60012) */
    div.stFormSubmitButton > button {
        background-color: #E60012 !important;
        color: white !important;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: bold;
        border: none;
        width: 100%;
    }
    div.stFormSubmitButton > button:hover {
        background-color: #001d2d !important;
        color: white !important;
    }

    /* Tarjetas KPI de Equipos Disponibles (Solo muestran el número) */
    .kpi-card-1 { background-color: #eff6ff; border-left: 5px solid #3b82f6; padding: 16px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }

    /* Tarjetas KPI de Inventario General - Resumen Ejecutivo originales con sus textos y colores */
    .kpi-exec-1 { background-color: #eff6ff; border-left: 5px solid #3b82f6; padding: 16px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .kpi-exec-2 { background-color: #ffedd5; border-left: 5px solid #f97316; padding: 16px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .kpi-exec-3 { background-color: #fee2e2; border-left: 5px solid #ef4444; padding: 16px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .kpi-exec-4 { background-color: #dcfce7; border-left: 5px solid #22c55e; padding: 16px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .kpi-exec-5 { background-color: #f3e8ff; border-left: 5px solid #a855f7; padding: 16px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }

    div.stButton > button {
        background-color: #E60012;
        color: white;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: bold;
        border: none;
    }
    div.stButton > button:hover {
        background-color: #C5000F;
        color: white;
    }

    div.stDownloadButton > button {
        background-color: #111827;
        color: white;
        border-radius: 8px;
        font-weight: bold;
    }
    div.stDownloadButton > button:hover {
        background-color: #374151;
        color: white;
    }
    h1, h2, h3 {
        color: #111827;
    }
    </style>
""", unsafe_allow_html=True)

# Archivos CSV locales y URL de Google Apps Script integrada
INVENTARIO_FILE = "inventario_refrigeradores.csv"
HISTORIAL_FILE = "historial_movimientos.csv"
LEVANTAMIENTOS_FILE = "levantamientos.csv"
SOLICITUDES_FILE = "solicitudes.csv"
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbz0uHPmSFwpgWRhmDApRKHyQyP1FK10d8vy3TlG5UNi5RpqhgpnZbBDEL8q93s9MfVf7Q/exec"

# Definición de las 3 personas autorizadas actualizadas
USUARIOS_AUTORIZADOS = {
    "evelasquezg": "Bepensa2026!",
    "siencinop": "Bepensa2026!",
    "edriverac": "Bepensa2026!"
}

OPCIONES_PROYECTOS = [
    "Normal", "Cambio", "Documental", "Fisico", "Prospera", 
    "ICE", "ICE Cambio", "CIC", "CIC Cambio", "Fast Start", 
    "Fast Start Cambio", "Milenio", "Premise", "Uso Interno"
]

OPCIONES_STATUS_SOL = [
    "Pendiente", "Entregado", "Levantado", "Cancelado", "Realizado", "Transferido"
]

OPCIONES_MOVIMIENTO_SOL = [
    "Entrega", "Levantamiento", "Reubicación"
]

def obtener_status_validos(movimiento):
    """Devuelve estrictamente los estatus permitidos según el tipo de movimiento."""
    mov = str(movimiento).strip().lower()
    if mov == "levantamiento":
        return ["Pendiente", "Levantado", "Cancelado"]
    elif mov == "reubicación" or mov == "reubicacion":
        return ["Pendiente", "Realizado", "Cancelado"]
    elif mov == "entrega":
        return ["Pendiente", "Entregado", "Cancelado", "Transferido"]
    return ["Pendiente"]

# Inicializar estados de sesión para controlar el movimiento y el estatus por defecto
if 'form_movimiento' not in st.session_state:
    st.session_state['form_movimiento'] = "Entrega"
if 'form_status' not in st.session_state:
    st.session_state['form_status'] = "Pendiente"

def actualizar_estatus_formulario():
    """Callback que se ejecuta únicamente cuando cambia el selectbox de Movimiento."""
    nuevo_mov = st.session_state.get('widget_movimiento', "Entrega")
    validos = obtener_status_validos(nuevo_mov)
    st.session_state['form_movimiento'] = nuevo_mov
    if st.session_state.get('widget_status') not in validos:
        st.session_state['form_status'] = validos[0]

OPCIONES_CANALES_SOL = [
    "Tradicional", "Moderno", "AP20L", "PostMix", "Vending", "HoReCa", "Cedis", "Uso Interno", "Eventos Especiales", "Otro"
]

ICONOS_CANALES = {
    "Tradicional": "🛒",
    "Moderno": "🏬",
    "AP20L": "📦",
    "PostMix": "🥤",
    "Vending": "🤖",
    "HoReCa": "🏨"
}

TIPOS_EQUIPO = [
    "Enfriador",
    "Hidro",
    "PostMix",
    "Vending"
]

OPCIONES_IMAGEN = [
    "Coca-Cola",
    "Hidratación",
    "Monster",
    "Bacardí",
    "Santa Clara",
    "Coca-Cola Black",
    "Topo Chico Mineral",
    "Topo Chico Hard Seltzer",
    "Cristal",
    "Sin Imagen"
]

UBICACIONES = [
    "En almacén de Comodatos",
    "En almacén de Publicidad",
    "En patios",
    "En taller",
    "Uso Interno",
    "En proceso de Baja",
    "Asignado a Cliente"
]

ESTATUS = [
    "Nuevo",
    "Reparado",
    "Para Reparar",
    "Para Baja",
    "En Uso"
]

UBICACIONES_VALIDAS_ESTADIA = [
    "En patios",
    "En almacén de Comodatos",
    "En almacén de Publicidad"
]

ESQUEMA_COLUMNAS = ["Serie", "Modelo", "Tipo", "Imagen", "Canal", "Ubicación", "Estatus", "Ultimo_Movimiento"]
COLUMNAS_SOLICITUDES = ["Fecha_Entregado", "Status", "Fecha_Recibido", "Proyecto", "CUC", "Cliente", "Jefe_de_Venta", "Supervisor", "Movimiento", "Equipo", "Modelo", "Serie", "Canal", "Ruta", "Motivo", "Observaciones"]
COLUMNAS_LEVANTAMIENTOS = ["Fecha", "CUC", "Cliente", "Modelo", "Serie", "Tipo", "Imagen", "Canal", "Status", "Motivo", "Ubicación", "Ruta", "Jefe_de_Venta", "Solicitado"]

def limpiar_y_mapear_columnas(df, esquema_objetivo):
    """Mapeo flexible y automático de columnas para asegurar compatibilidad con cualquier Excel."""
    df_L = df.copy()
    df_L.columns = [str(c).strip() for c in df_L.columns]
    mapa_encontrado = {}
    for col_orig in df_L.columns:
        c_low = col_orig.lower()
        for col_obj in esquema_objetivo:
            o_low = col_obj.lower()
            if c_low == o_low or o_low in c_low or c_low in o_low:
                if col_obj not in mapa_encontrado.values():
                    mapa_encontrado[col_orig] = col_obj
    df_L = df_L.rename(columns=mapa_encontrado)
    for col in esquema_objetivo:
        if col not in df_L.columns:
            df_L[col] = ""
    return df_L[esquema_objetivo]

def cargar_datos():
    try:
        response = requests.get(WEB_APP_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                df = pd.DataFrame(data, dtype=str)
            else:
                df = pd.DataFrame(columns=ESQUEMA_COLUMNAS)
        else:
            df = pd.DataFrame(columns=ESQUEMA_COLUMNAS)
    except Exception:
        if os.path.exists(INVENTARIO_FILE):
            try:
                df = pd.read_csv(INVENTARIO_FILE, dtype=str)
            except Exception:
                df = pd.DataFrame(columns=ESQUEMA_COLUMNAS)
        else:
            df = pd.DataFrame(columns=ESQUEMA_COLUMNAS)
        
    df = limpiar_y_mapear_columnas(df, ESQUEMA_COLUMNAS)

    def limpiar_fecha_estricta(val):
        val_s = str(val).strip()
        if not val_s or val_s.lower() == 'nan' or val_s.lower() == 'nat':
            return datetime.now().strftime("%Y-%m-%d")
        
        dt_parsed = pd.to_datetime(val_s, errors='coerce')
        if not pd.isna(dt_parsed):
            return dt_parsed.strftime("%Y-%m-%d")
            
        if re.match(r'^\d{4}-\d{2}-\d{2}$', val_s):
            return val_s
            
        return val_s[:10]

    df["Ultimo_Movimiento"] = df["Ultimo_Movimiento"].apply(limpiar_fecha_estricta)
    df["Ultimo_Movimiento"] = df["Ultimo_Movimiento"].astype(str)
    
    if not df.empty and 'Serie' in df.columns:
        df = df.drop_duplicates(subset=['Serie'], keep='last').reset_index(drop=True)
        
    return df

def cargar_historial():
    if os.path.exists(HISTORIAL_FILE):
        try:
            df_h = pd.read_csv(HISTORIAL_FILE, dtype=str)
        except Exception:
            df_h = pd.DataFrame(columns=["Fecha_Hora", "Usuario", "Serie", "Modelo", "Tipo_Movimiento", "Detalles"])
    else:
        df_h = pd.DataFrame(columns=["Fecha_Hora", "Usuario", "Serie", "Modelo", "Tipo_Movimiento", "Detalles"])
    
    if "Usuario" not in df_h.columns:
        df_h["Usuario"] = "Sistema / Desconocido"
        
    rutas = []
    motivos = []
    for idx, row in df_h.iterrows():
        detalles = str(row.get('Detalles', ''))
        match_ruta = re.search(r'Ruta:\s*([^\|]+)', detalles)
        if match_ruta:
            rutas.append(match_ruta.group(1).strip())
        else:
            rutas.append("")
            
        match_motivo = re.search(r'Motivo:\s*(.+)$', detalles)
        if match_motivo:
            motivos.append(match_motivo.group(1).strip())
        else:
            motivos.append("")
            
    df_h['Ruta'] = rutas
    df_h['Motivo'] = motivos
    
    return df_h

def cargar_levantamientos():
    if os.path.exists(LEVANTAMIENTOS_FILE):
        try:
            df_lev = pd.read_csv(LEVANTAMIENTOS_FILE, dtype=str)
        except Exception:
            df_lev = pd.DataFrame(columns=COLUMNAS_LEVANTAMIENTOS)
    else:
        df_lev = pd.DataFrame(columns=COLUMNAS_LEVANTAMIENTOS)
    
    df_lev = limpiar_y_mapear_columnas(df_lev, COLUMNAS_LEVANTAMIENTOS)
    return df_lev

def cargar_solicitudes():
    if os.path.exists(SOLICITUDES_FILE):
        try:
            df_sol = pd.read_csv(SOLICITUDES_FILE, dtype=str)
        except Exception:
            df_sol = pd.DataFrame(columns=COLUMNAS_SOLICITUDES)
    else:
        df_sol = pd.DataFrame(columns=COLUMNAS_SOLICITUDES)
        
    df_sol = limpiar_y_mapear_columnas(df_sol, COLUMNAS_SOLICITUDES)
    return df_sol

def guardar_datos(df):
    if not df.empty and 'Serie' in df.columns:
        df = df.drop_duplicates(subset=['Serie'], keep='last').reset_index(drop=True)
    try:
        df.to_csv(INVENTARIO_FILE, index=False)
    except PermissionError:
        st.error(f"⚠️ Error de permiso: El archivo '{INVENTARIO_FILE}' está abierto en Excel u otro programa. Ciérralo para guardar.")
        return
    try:
        records = df.to_dict(orient="records")
        requests.post(WEB_APP_URL, json=records, timeout=10)
    except Exception as e:
        st.error(f"⚠️ Error al sincronizar con Google Sheets: {e}")

def guardar_solicitudes_seguro(df_sol):
    try:
        df_sol.to_csv(SOLICITUDES_FILE, index=False)
        return True
    except PermissionError:
        st.error(f"⚠️ Error: No se pudo guardar porque el archivo '{SOLICITUDES_FILE}' está abierto en Excel. Por favor, ciérralo e inténtalo de nuevo.")
        return False

def registrar_historial(serie, modelo, tipo_movimiento, detalles):
    usuario_actual = st.session_state.get('usuario_actual', 'Sistema')
    df_h = cargar_historial()
    nuevo_mov = pd.DataFrame([{
        "Fecha_Hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Usuario": str(usuario_actual),
        "Serie": str(serie),
        "Modelo": str(modelo),
        "Tipo_Movimiento": tipo_movimiento,
        "Detalles": detalles
    }])
    df_h = pd.concat([df_h, nuevo_mov], ignore_index=True)
    columnas_guardar = ["Fecha_Hora", "Usuario", "Serie", "Modelo", "Tipo_Movimiento", "Detalles"]
    try:
        df_h[columnas_guardar].to_csv(HISTORIAL_FILE, index=False)
    except PermissionError:
        pass

def calcular_dias_sin_movimiento(df):
    if df.empty:
        return df
    
    df_calc = df.copy()
    fecha_actual = datetime.now().date()
    
    dias_lista = []
    for fecha_str in df_calc['Ultimo_Movimiento']:
        try:
            val_limpia = str(fecha_str).strip()
            f_mov = datetime.strptime(val_limpia, "%Y-%m-%d").date()
            dias = (fecha_actual - f_mov).days
            dias_lista.append(max(0, dias))
        except Exception:
            dias_lista.append(0)
        
    df_calc['Días sin movimiento'] = dias_lista
    return df_calc

def colorear_ubicaciones(val):
    val_lower = str(val).strip()
    if val_lower in ["En almacén de Comodatos", "En almacén de Publicidad"]:
        return 'background-color: #d1fae5; color: #065f46; font-weight: bold;'
    elif val_lower == "En patios":
        return 'background-color: #fef3c7; color: #92400e; font-weight: bold;'
    elif val_lower == "En proceso de Baja":
        return 'background-color: #fee2e2; color: #991b1b; font-weight: bold;'
    elif val_lower == "En taller":
        return 'background-color: #ffedd5; color: #9a3412; font-weight: bold;'
    elif val_lower in ["Uso Interno", "Asignado a Cliente"]:
        return 'background-color: #dbeafe; color: #1e40af; font-weight: bold;'
    return ''

def colorear_dias(val):
    try:
        if float(val) > 40:
            return 'background-color: #fee2e2; color: #991b1b; font-weight: bold;'
    except (ValueError, TypeError):
        pass
    return ''

df_inv = cargar_datos()

# --- GESTIÓN DE SESIÓN EN LA BARRA LATERAL ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False
if 'usuario_actual' not in st.session_state:
    st.session_state['usuario_actual'] = ""

st.sidebar.markdown("<h2 style='color: white; text-align: center;'>❄️ Bepensa</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='text-align: center; color: white;'><b>Control de Inventario</b></p>", unsafe_allow_html=True)
st.sidebar.markdown("---")

if st.session_state['autenticado']:
    st.sidebar.success(f"🔓 Sesión Activa: {st.session_state['usuario_actual']}")
    # Menú para administradores en el orden exacto solicitado
    menu = st.sidebar.selectbox(
        "Menú de Navegación",
        [
            "📊 Inventario General",
            "📦 Equipos Disponibles",
            "📈 Estadía",
            "📋 Solicitudes",
            "📝 Levantamientos",
            "📥 Registrar Entrada",
            "📤 Registrar Salida",
            "✏️ Editar / Eliminar",
            "📜 Historial de Movimientos",
            "💾 Exportar a Excel"
        ]
    )
    if st.sidebar.button("🔒 Cerrar Sesión"):
        st.session_state['autenticado'] = False
        st.session_state['usuario_actual'] = ""
        st.rerun()
else:
    # Menú para usuarios generales (Equipos Disponibles primero, luego Estadía)
    menu = st.sidebar.selectbox(
        "Menú de Navegación",
        [
            "📦 Equipos Disponibles",
            "📈 Estadía"
        ]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("<p style='color: #FFFFFF; font-weight: bold; text-align: center;'>🔒 Acceso Administrativo</p>", unsafe_allow_html=True)
    
    with st.sidebar.form("form_login"):
        user_input = st.text_input("👤 Usuario:").strip()
        pass_input = st.text_input("🔑 Contraseña:", type="password").strip()
        btn_login = st.form_submit_button("Iniciar Sesión")
        
        if btn_login:
            if user_input in USUARIOS_AUTORIZADOS and USUARIOS_AUTORIZADOS[user_input] == pass_input:
                st.session_state['autenticado'] = True
                st.session_state['usuario_actual'] = user_input
                st.success("✅ ¡Acceso concedido!")
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos.")

# Pie de página fijo al fondo de la barra lateral (Copyright)
st.sidebar.markdown("<div style='flex-grow: 1;'></div>", unsafe_allow_html=True)
st.sidebar.markdown("---")
st.sidebar.markdown(
    """<p style='text-align: center; font-size: 12px; color: #FFFFFF; line-height: 1.4; margin-bottom: 10px;'>
    🛠️️ <b>Desarrollado y diseñado por:</b><br>
    Eduardo Rivera Chulin<br><br>
    © 2026 Bepensa / Coca-Cola.<br>
    Todos los derechos reservados.
    </p>""", 
    unsafe_allow_html=True
)

# Encabezado principal
col_titulo, col_logo = st.columns([4, 1])

with col_titulo:
    st.markdown("<h1 style='color: #E60012; margin-top: 0;'>❄ Control de Inventarios de Capacidades</h1>", unsafe_allow_html=True)

with col_logo:
    if os.path.exists("Logo_Bepensa.png"):
        st.image("Logo_Bepensa.png", width=160)
    else:
        st.warning("⚠️ No se encontró 'Logo_Bepensa.png' en la carpeta.")

st.markdown("---")

# 1. EQUIPOS DISPONIBLES (PÚBLICO Y PRIMERA OPCIÓN PARA GENERALES)
if menu == "📦 Equipos Disponibles":
    st.subheader("📦 Reporte de Equipos Disponibles")
    st.markdown("Equipos listos para distribución (Almacén de Comodatos, Almacén de Publicidad o Patios con estatus Nuevo/Reparado).")
    
    canales_validos_kpi = [c for c in OPCIONES_CANALES_SOL if c not in ["Otro", "Uso Interno", "Eventos Especiales", "Cedis"]]
    
    opciones_disp_filtro = canales_validos_kpi

    canal_disp_seleccionado = st.selectbox("🎯 Seleccione el Canal a visualizar:", opciones_disp_filtro)
    st.markdown("---")

    if not df_inv.empty:
        condicion_disponibles = (
            (df_inv['Ubicación'].isin(["En almacén de Comodatos", "En almacén de Publicidad"])) |
            ((df_inv['Ubicación'] == "En patios") & (df_inv['Estatus'].isin(["Nuevo", "Reparado"])))
        )
        df_disp_global = df_inv[condicion_disponibles & (df_inv['Canal'] != "Cedis")].copy()
    else:
        df_disp_global = pd.DataFrame(columns=ESQUEMA_COLUMNAS)

    st.markdown("### 📊 Disponibilidad")
    
    if not df_disp_global.empty:
        canales_disp_mostrar = [canal_disp_seleccionado]
        
        totales_kpi_canales = {}
        dataframes_canales_filtrados = {}

        for c_d in canales_disp_mostrar:
            df_c_disp = df_disp_global[df_disp_global['Canal'] == c_d]
            if not df_c_disp.empty:
                f_col1, f_col2, f_col3 = st.columns(3)
                
                modelos_disp = ["Todos"] + sorted(df_c_disp['Modelo'].dropna().unique().tolist())
                with f_col1:
                    sel_modelo = st.selectbox(f"🧊 Filtrar Modelo ({c_d}):", modelos_disp, key=f"mod_{c_d}")
                
                df_f1 = df_c_disp.copy()
                if sel_modelo != "Todos":
                    df_f1 = df_f1[df_f1['Modelo'] == sel_modelo]
                
                imagenes_disp = ["Todos"] + sorted(df_f1['Imagen'].dropna().unique().tolist())
                with f_col2:
                    sel_imagen = st.selectbox(f"🖼️ Filtrar Imagen ({c_d}):", imagenes_disp, key=f"img_{c_d}")
                
                df_f2 = df_f1.copy()
                if sel_imagen != "Todos":
                    df_f2 = df_f2[df_f2['Imagen'] == sel_imagen]
                
                estatus_disp = ["Todos"] + sorted(df_f2['Estatus'].dropna().unique().tolist())
                with f_col3:
                    sel_estatus = st.selectbox(f"⚡ Filtrar Estatus ({c_d}):", estatus_disp, key=f"est_{c_d}")
                
                df_tabla_filtrada = df_f2.copy()
                if sel_estatus != "Todos":
                    df_tabla_filtrada = df_tabla_filtrada[df_tabla_filtrada['Estatus'] == sel_estatus]
                
                totales_kpi_canales[c_d] = len(df_tabla_filtrada)
                dataframes_canales_filtrados[c_d] = df_tabla_filtrada
            else:
                totales_kpi_canales[c_d] = 0
                dataframes_canales_filtrados[c_d] = pd.DataFrame()

        cols_kpi = st.columns(min(len(canales_disp_mostrar), 4) if len(canales_disp_mostrar) > 0 else 1)
        for i, c_kpi in enumerate(canales_disp_mostrar):
            cant_canal = totales_kpi_canales.get(c_kpi, 0)
            col_actual = cols_kpi[i % len(cols_kpi)]
            with col_actual:
                st.markdown(f"""
                    <div class="kpi-card-1" style="margin-bottom: 12px;">
                        <span style="font-size: 26px; font-weight: bold; color: #1e3a8a;">{cant_canal}</span>
                    </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        for c_d in canales_disp_mostrar:
            icono_c = ICONOS_CANALES.get(c_d, "🏪")
            st.markdown(f"### {icono_c} {c_d}")
            
            df_tabla_filtrada = dataframes_canales_filtrados.get(c_d, pd.DataFrame())
            if not df_tabla_filtrada.empty:
                st.dataframe(df_tabla_filtrada.groupby(['Tipo', 'Modelo', 'Imagen', 'Estatus']).size().reset_index(name='Cantidad Disponible'), use_container_width=True, hide_index=True)
            else:
                st.info(f"ℹ️ No hay equipos disponibles que coincidan con los filtros seleccionados para {c_d}.")
    else:
        st.info("ℹ️ No hay equipos disponibles en el inventario que cumplan con los criterios actuales.")

# 2. ESTADÍA (PÚBLICO)
elif menu == "📈 Estadía":
    if not df_inv.empty:
        st.markdown("### 🗺️ Mapa de Saturación por Ubicación (Ubicación > Canal > Modelo > Imagen)")
        fig_treemap = px.treemap(
            df_inv,
            path=['Ubicación', 'Canal', 'Modelo', 'Imagen'],
            color='Ubicación',
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig_treemap.update_traces(textinfo="label+value+percent parent")
        fig_treemap.update_layout(margin=dict(t=20, l=10, r=10, b=10), height=480)
        st.plotly_chart(fig_treemap, use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)

    st.subheader("📈 Promedio de Estadía y Saturación de Equipos")
    st.markdown("Análisis del promedio de días sin movimiento y saturación de inventario por ubicación, canal, modelos e imágenes. Las barras que superan los **40 días** se destacan en **Rojo ⚠**.")
    st.markdown("---")
    
    opciones_estadia_filtro = [c for c in OPCIONES_CANALES_SOL if c not in ["Otro", "Uso Interno", "Eventos Especiales", "Cedis"]]
    canal_estadia_seleccionado = st.selectbox("🎯 Seleccione el Canal a visualizar:", opciones_estadia_filtro)
    st.markdown("---")
    
    df_con_dias = calcular_dias_sin_movimiento(df_inv)
    
    if not df_con_dias.empty:
        df_con_dias['Días sin movimiento'] = pd.to_numeric(df_con_dias['Días sin movimiento'], errors='coerce')
        
        st.markdown("""
            <style>
            div.stButton > button:first-child {
                background-color: #FF7A00;
                color: white;
            }
            div.stButton > button:first-child:hover {
                background-color: #e06d00;
                color: white;
            }
            </style>
        """, unsafe_allow_html=True)
        
        c_val = canal_estadia_seleccionado
        
        col_t_title, col_t_btn1, col_t_btn2 = st.columns([2, 1, 1])
        with col_t_title:
            st.markdown(f"### 🏬 Canal {c_val}")
        
        key_btn_ubicacion = f"btn_ubicacion_{c_val}"
        key_btn_modelo = f"btn_modelo_{c_val}"
        
        if key_btn_ubicacion not in st.session_state:
            st.session_state[key_btn_ubicacion] = True
        if key_btn_modelo not in st.session_state:
            st.session_state[key_btn_modelo] = False

        def toggle_ubicacion(k_ub=key_btn_ubicacion, k_mod=key_btn_modelo):
            st.session_state[k_ub] = True
            st.session_state[k_mod] = False

        def toggle_modelo(k_ub=key_btn_ubicacion, k_mod=key_btn_modelo):
            st.session_state[k_mod] = True
            st.session_state[k_ub] = False

        with col_t_btn1:
            st.button(f"📍 Por Ubicación ({c_val})", key=f"click_ub_{c_val}", on_click=toggle_ubicacion)
        with col_t_btn2:
            st.button(f"📊 Por Modelo e Imagen ({c_val})", key=f"click_mod_{c_val}", on_click=toggle_modelo)
        
        df_canal = df_con_dias[
            (df_con_dias['Canal'] == c_val) & 
            (~df_con_dias['Ubicación'].isin(['Uso Interno', 'En proceso de Baja', 'Asignado a Cliente']))
        ].copy()
        
        if not df_canal.empty:
            if st.session_state[key_btn_ubicacion]:
                df_prom_mean = df_canal.groupby('Ubicación')['Días sin movimiento'].mean().reset_index()
                df_prom_count = df_canal.groupby('Ubicación')['Días sin movimiento'].count().reset_index()
                df_prom = pd.merge(df_prom_mean, df_prom_count, on='Ubicación')
                df_prom.columns = ['Ubicación', 'Promedio de Días', 'Cantidad']
                df_prom = df_prom[['Ubicación', 'Cantidad', 'Promedio de Días']]
                df_prom = df_prom.sort_values(by='Promedio de Días', ascending=False)
                
                fig_c, ax_c = plt.subplots(figsize=(10, 4.5))
                colores_c = ['#E60012' if x > 40 else '#2563eb' for x in df_prom['Promedio de Días']]
                bars_c = ax_c.bar(df_prom['Ubicación'], df_prom['Promedio de Días'], color=colores_c, width=0.55, edgecolor='black', linewidth=0.8)
                ax_c.axhline(40, color='#dc2626', linestyle='--', linewidth=1.5, label='Límite de Alerta (40 días)')
                
                for bar in bars_c:
                    yval = bar.get_height()
                    alerta_txt = f" ⚠️️ ({yval:.1f}d)" if yval > 40 else f" ({yval:.1f}d)"
                    ax_c.text(bar.get_x() + bar.get_width()/2.0, yval + 1, alerta_txt, ha='center', va='bottom', fontsize=9, fontweight='bold', color='#111827')

                ax_c.set_ylabel('Promedio de Días', fontsize=10, fontweight='bold')
                ax_c.set_xlabel('Ubicación', fontsize=10, fontweight='bold')
                ax_c.set_title(f'Estadía Promedio - Canal {c_val} (Por Ubicación)', fontsize=12, fontweight='bold', pad=12)
                plt.xticks(rotation=15, ha='right')
                ax_c.grid(axis='y', linestyle=':', alpha=0.6)
                ax_c.legend(loc='upper right')
                st.pyplot(fig_c)
                
                df_c_tabla = df_prom.copy()
                df_c_tabla['Estado de Alerta'] = df_c_tabla['Promedio de Días'].apply(lambda x: "🚨 Alerta: Supera los 40 días" if x > 40 else "✅ Normal")
                df_c_tabla['Promedio de Días'] = df_c_tabla['Promedio de Días'].round(1)
                st.dataframe(df_c_tabla, use_container_width=True, hide_index=True)

            elif st.session_state[key_btn_modelo]:
                df_modelo_grafica = df_canal.groupby('Modelo')['Días sin movimiento'].mean().reset_index()
                df_modelo_grafica.columns = ['Modelo', 'Promedio de Días']
                df_modelo_grafica = df_modelo_grafica.sort_values(by='Promedio de Días', ascending=False)
                
                fig_m, ax_m = plt.subplots(figsize=(10, 4.5))
                colores_m = ['#E60012' if x > 40 else '#2563eb' for x in df_modelo_grafica['Promedio de Días']]
                bars_m = ax_m.bar(df_modelo_grafica['Modelo'], df_modelo_grafica['Promedio de Días'], color=colores_m, width=0.55, edgecolor='black', linewidth=0.8)
                ax_m.axhline(40, color='#dc2626', linestyle='--', linewidth=1.5, label='Límite de Alerta (40 días)')
                
                for bar in bars_m:
                    yval = bar.get_height()
                    alerta_txt = f" ⚠️ ({yval:.1f}d)" if yval > 40 else f" ({yval:.1f}d)"
                    ax_m.text(bar.get_x() + bar.get_width()/2.0, yval + 1, alerta_txt, ha='center', va='bottom', fontsize=9, fontweight='bold', color='#111827')

                ax_m.set_ylabel('Promedio de Días', fontsize=10, fontweight='bold')
                ax_m.set_xlabel('Modelo', fontsize=10, fontweight='bold')
                ax_m.set_title(f'Estadía Promedio - Canal {c_val} (Por Modelo)', fontsize=12, fontweight='bold', pad=12)
                plt.xticks(rotation=25, ha='right')
                ax_m.grid(axis='y', linestyle=':', alpha=0.6)
                ax_m.legend(loc='upper right')
                st.pyplot(fig_m)

                st.markdown(f"#### 🧊 Desglose por Modelo e Imagen - Canal {c_val}")
                df_modelo_imagen_mean = df_canal.groupby(['Modelo', 'Imagen'])['Días sin movimiento'].mean().reset_index()
                df_modelo_imagen_count = df_canal.groupby(['Modelo', 'Imagen'])['Días sin movimiento'].count().reset_index()
                df_modelo_imagen = pd.merge(df_modelo_imagen_mean, df_modelo_imagen_count, on=['Modelo', 'Imagen'])
                df_modelo_imagen.columns = ['Modelo', 'Imagen', 'Promedio de Días', 'Cantidad']
                df_modelo_imagen = df_modelo_imagen[['Modelo', 'Imagen', 'Cantidad', 'Promedio de Días']]
                df_modelo_imagen = df_modelo_imagen.sort_values(by='Promedio de Días', ascending=False)
                
                df_m_tabla = df_modelo_imagen.copy()
                df_m_tabla['Estado de Alerta'] = df_m_tabla['Promedio de Días'].apply(lambda x: "🚨 Alerta: Supera los 40 días" if x > 40 else "✅ Normal")
                df_m_tabla['Promedio de Días'] = df_m_tabla['Promedio de Días'].round(1)
                st.dataframe(df_m_tabla, use_container_width=True, hide_index=True)

            if st.session_state.get('autenticado', False):
                with st.expander(f"🔍 Ver el listado exacto de Series de Equipos - Canal {c_val}"):
                    df_detalle_series = df_canal[['Serie', 'Tipo', 'Modelo', 'Imagen', 'Ubicación', 'Estatus', 'Días sin movimiento', 'Ultimo_Movimiento']].copy()
                    df_detalle_series['Días sin movimiento'] = pd.to_numeric(df_detalle_series['Días sin movimiento'], errors='coerce')
                    df_detalle_series = df_detalle_series.sort_values(by='Días sin movimiento', ascending=False)
                    df_detalle_series = df_detalle_series.rename(columns={'Ultimo_Movimiento': 'Último Movimiento'})
                    
                    df_series_estilizado = df_detalle_series.style.map(colorear_ubicaciones, subset=['Ubicación']).map(colorear_dias, subset=['Días sin movimiento'])
                    st.dataframe(df_series_estilizado, use_container_width=True, hide_index=True)

        else:
            st.info(f"ℹ️ No hay equipos registrados para el Canal {c_val}.")
    else:
        st.info("ℹ No hay datos suficientes en el inventario.")

# 3. INVENTARIO GENERAL Y BUSCADOR (SOLO ADMINISTRADORES)
elif menu == "📊 Inventario General" and st.session_state['autenticado']:
    st.subheader("📋 Inventario Actual de Equipos")
    
    df_con_dias = calcular_dias_sin_movimiento(df_inv)
    
    with st.expander("🔍 Filtros Avanzados y Búsqueda Rápida", expanded=True):
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            busqueda = st.text_input("🔍 Buscar Serie o Modelo:").strip()
            filtro_tipo = st.selectbox("📌 Filtrar por Tipo:", ["Todos"] + TIPOS_EQUIPO)
        with f_col2:
            filtro_imagen = st.selectbox("🖼 Filtrar por Imagen:", ["Todos"] + OPCIONES_IMAGEN)
            filtro_canal = st.selectbox("🏬 Filtrar por Canal:", ["Todos"] + [c for c in OPCIONES_CANALES_SOL if c not in ["Otro", "Uso Interno", "Eventos Especiales"]])
        with f_col3:
            filtro_ubicacion = st.selectbox("📍 Filtrar por Ubicación:", ["Todos"] + UBICACIONES)
            filtro_estatus = st.selectbox("⚡ Filtrar por Estatus:", ["Todos"] + ESTATUS)

    df_filtrado = df_con_dias.copy()

    if busqueda:
        df_filtrado = df_filtrado[
            df_filtrado['Serie'].str.contains(busqueda, case=False, na=False) | 
            df_filtrado['Modelo'].str.contains(busqueda, case=False, na=False)
        ]
    if filtro_tipo != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Tipo'] == filtro_tipo]
    if filtro_imagen != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Imagen'] == filtro_imagen]
    if filtro_canal != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Canal'] == filtro_canal]
    if filtro_ubicacion != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Ubicación'] == filtro_ubicacion]
    if filtro_estatus != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Estatus'] == filtro_estatus]

    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("### 📊 Resumen Ejecutivo")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total_eq = len(df_filtrado)
    en_taller = len(df_filtrado[df_filtrado['Ubicación'] == 'En taller']) if not df_filtrado.empty else 0
    para_reparar = len(df_filtrado[(df_filtrado['Estatus'] == 'Para Reparar') & (df_filtrado['Ubicación'] != 'En taller')]) if not df_filtrado.empty else 0
    nuevos = len(df_filtrado[df_filtrado['Estatus'] == 'Nuevo']) if not df_filtrado.empty else 0
    reparados = len(df_filtrado[df_filtrado['Estatus'] == 'Reparado']) if not df_filtrado.empty else 0

    with col1:
        st.markdown(f"""
            <div class="kpi-exec-1">
                <span style="font-size: 14px; color: #1e3a8a; font-weight: bold;">Total de Equipos</span><br>
                <span style="font-size: 26px; font-weight: bold; color: #1e3a8a;">{total_eq}</span>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div class="kpi-exec-2">
                <span style="font-size: 14px; color: #9a3412; font-weight: bold;">En Taller</span><br>
                <span style="font-size: 26px; font-weight: bold; color: #9a3412;">{en_taller}</span>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
            <div class="kpi-exec-3">
                <span style="font-size: 14px; color: #991b1b; font-weight: bold;">Para Reparar</span><br>
                <span style="font-size: 26px; font-weight: bold; color: #991b1b;">{para_reparar}</span>
            </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
            <div class="kpi-exec-4">
                <span style="font-size: 14px; color: #065f46; font-weight: bold;">Nuevos</span><br>
                <span style="font-size: 26px; font-weight: bold; color: #065f46;">{nuevos}</span>
            </div>
        """, unsafe_allow_html=True)
    with col5:
        st.markdown(f"""
            <div class="kpi-exec-5">
                <span style="font-size: 14px; color: #6b21a8; font-weight: bold;">Reparados</span><br>
                <span style="font-size: 26px; font-weight: bold; color: #6b21a8;">{reparados}</span>
            </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)

    columnas_visibles = ["Serie", "Modelo", "Tipo", "Imagen", "Canal", "Ubicación", "Estatus", "Días sin movimiento", "Ultimo_Movimiento"]
    df_filtrado = df_filtrado[[col for col in columnas_visibles if col in df_filtrado.columns]]
    
    if not df_filtrado.empty and 'Días sin movimiento' in df_filtrado.columns:
        df_filtrado['Días sin movimiento'] = pd.to_numeric(df_filtrado['Días sin movimiento'], errors='coerce')
        df_filtrado = df_filtrado.sort_values(by='Días sin movimiento', ascending=False)
    
    if not df_filtrado.empty:
        df_mostrar = df_filtrado.copy()
        if 'Ultimo_Movimiento' in df_mostrar.columns:
            df_mostrar['Ultimo_Movimiento'] = pd.to_datetime(df_mostrar['Ultimo_Movimiento'], errors='coerce').dt.strftime('%Y-%m-%d').fillna(df_mostrar['Ultimo_Movimiento'])
            df_mostrar = df_mostrar.rename(columns={'Ultimo_Movimiento': 'Último Movimiento'})

        df_estilizado = df_mostrar.style.map(colorear_ubicaciones, subset=['Ubicación'])
        if 'Días sin movimiento' in df_filtrado.columns:
            df_estilizado = df_estilizado.map(colorear_dias, subset=['Días sin movimiento'])
        st.dataframe(df_estilizado, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

# 4. SOLICITUDES (SOLO ADMINISTRADORES)
elif menu == "📋 Solicitudes" and st.session_state['autenticado']:
    st.subheader("📋 Registro de Solicitudes y Entregas de Equipos")
    
    modo_solicitud = st.radio(
        "Selecciona una acción:", 
        [
            "➕ Registrar Nueva Solicitud", 
            "🔍 Actualizar o Eliminar Solicitudes",
            "📊 Historial de Solicitudes OK",
            "📂 Importar Archivo Excel de Solicitudes"
        ], 
        horizontal=True
    )
    st.markdown("---")
    
    df_sol = cargar_solicitudes()
    
    if modo_solicitud == "➕ Registrar Nueva Solicitud":
        col_m1, _ = st.columns([2, 2])
        with col_m1:
            movimiento = st.selectbox(
                "🔄 Movimiento:", 
                OPCIONES_MOVIMIENTO_SOL, 
                key="widget_movimiento", 
                on_change=actualizar_estatus_formulario
            )
        
        st.markdown("---")
        
        with st.form("form_solicitud_nueva_ordenada", clear_on_submit=False):
            col_s1, col_s2, col_s3 = st.columns(3)
            
            with col_s1:
                status_permitidos_nuevos = obtener_status_validos(st.session_state['form_movimiento'])
                idx_st_default = 0
                if st.session_state['form_status'] in status_permitidos_nuevos:
                    idx_st_default = status_permitidos_nuevos.index(st.session_state['form_status'])
                status_sol = st.selectbox("⚡ Status:", status_permitidos_nuevos, index=idx_st_default, key="widget_status")
                
                incluir_fecha_entregado = st.checkbox("¿Asignar Fecha de Realizado ahora?", value=False)
                fecha_entregado = st.date_input("📅 Fecha de Realizado", value=date.today())
                fecha_recibido = st.date_input("📅 Fecha de Recibido", value=date.today())
                proyecto = st.selectbox("📁 Proyecto:", OPCIONES_PROYECTOS)
                cuc = st.text_input("🔢 CUC:").strip()

            with col_s2:
                cliente_sol = st.text_input("🏢 Nombre de Cliente:").strip()
                jefe_sol = st.text_input("👤 Jefe de Venta:").strip()
                supervisor = st.text_input("👔 Supervisor (Opcional):").strip()
                equipo_tipo = st.selectbox("📌 Equipo:", TIPOS_EQUIPO)
                modelo_sol = st.text_input("🧊 Modelo:").strip()

            with col_s3:
                serie_sol = st.text_input("🏷 Número de Serie (Opcional):").strip()
                canal_sol = st.selectbox("🏬 Canal:", OPCIONES_CANALES_SOL)
                ruta_sol = st.text_input("🚚 Ruta (Opcional):").strip()
                motivo_sol = st.text_input("📝 Motivo:").strip()

            observaciones = st.text_area("💬 Observaciones (Obligatorio si Canal es 'Otro'):").strip()
            
            submit_sol = st.form_submit_button("💾 Guardar Solicitud")
            
            if submit_sol:
                movimiento_final = st.session_state['form_movimiento']
                status_validos_actuales = obtener_status_validos(movimiento_final)
                
                if status_sol not in status_validos_actuales:
                    st.error(f"❌ ADVERTENCIA: Los datos son incorrectos. Para el movimiento '{movimiento_final}' NO está permitido el estatus '{status_sol}'. Opciones válidas: {', '.join(status_validos_actuales)}. Corríjalo para continuar.")
                    st.stop()
                elif canal_sol == "Otro" and not observaciones:
                    st.error("⚠️ El campo Observaciones es obligatorio cuando el Canal es 'Otro'.")
                    st.stop()
                elif not cuc or not modelo_sol or not cliente_sol:
                    st.error("⚠️ Por favor, ingresa al menos el CUC, el Modelo y el Cliente.")
                    st.stop()
                elif status_sol.lower() in ["entregado", "realizado", "transferido", "levantado"] and not incluir_fecha_entregado:
                    st.error(f"❌ No se guardaron los cambios: Seleccionó el estatus '{status_sol}' pero no activó ni asignó la Fecha de Realizado. La solicitud no puede avanzar de estatus sin su respectiva fecha.")
                    st.stop()
                else:
                    fecha_e_str = fecha_entregado.strftime("%Y-%m-%d") if incluir_fecha_entregado else ""
                    fecha_r_str = fecha_recibido.strftime("%Y-%m-%d")
                    
                    nueva_sol = pd.DataFrame([{
                        "Fecha_Entregado": fecha_e_str, "Status": status_sol, "Fecha_Recibido": fecha_r_str,
                        "Proyecto": proyecto, "CUC": cuc, "Cliente": cliente_sol, "Jefe_de_Venta": jefe_sol,
                        "Supervisor": supervisor, "Movimiento": movimiento_final, "Equipo": equipo_tipo,
                        "Modelo": modelo_sol, "Serie": serie_sol, "Canal": canal_sol, "Ruta": ruta_sol,
                        "Motivo": motivo_sol, "Observaciones": observaciones
                    }])
                    df_sol = pd.concat([df_sol, nueva_sol], ignore_index=True)
                    
                    if guardar_solicitudes_seguro(df_sol):
                        status_ok_lista = ["Entregado", "Realizado", "Transferido", "Levantado"]
                        if status_sol in status_ok_lista and serie_sol:
                            if not df_inv.empty and serie_sol in df_inv['Serie'].values:
                                idx = df_inv[df_inv['Serie'] == serie_sol].index[0]
                                df_inv.loc[idx, 'Ubicación'] = "Asignado a Cliente"
                                df_inv.loc[idx, 'Estatus'] = "En Uso"
                                if incluir_fecha_entregado and fecha_e_str:
                                    df_inv.loc[idx, 'Ultimo_Movimiento'] = fecha_e_str
                                guardar_datos(df_inv)
                                registrar_historial(serie_sol, modelo_sol, f"SOLICITUD {status_sol.upper()}", f"Cliente: {cliente_sol} | Ruta: {ruta_sol} | CUC: {cuc}")
                                st.success(f"✅ ¡Solicitud guardada y procesada! La serie {serie_sol} fue dada de baja de equipos disponibles al cambiar a '{status_sol}'.")
                        else:
                            st.success("✅ ¡Solicitud guardada correctamente!")

    elif modo_solicitud == "🔍 Actualizar o Eliminar Solicitudes":
        st.markdown("#### 🔍 Buscar Solicitud en el Sistema")
        
        with st.form("form_buscar_canal"):
            b_canal = st.selectbox("🏬 Filtrar por Canal:", ["Todos"] + OPCIONES_CANALES_SOL)
            b_cuc_busqueda = st.text_input("🔢 O busque por CUC exacto (Opcional):").strip()
            btn_buscar = st.form_submit_button("Buscar Solicitud")
            
        if btn_buscar:
            df_pend_busq = df_sol.copy()
            
            if b_canal != "Todos":
                df_pend_busq = df_pend_busq[df_pend_busq['Canal'] == b_canal]
            if b_cuc_busqueda:
                df_pend_busq = df_pend_busq[df_pend_busq['CUC'].str.contains(b_cuc_busqueda, case=False, na=False)]

            st.session_state['df_pend_busq_resultado'] = df_pend_busq

        if 'df_pend_busq_resultado' in st.session_state:
            df_pend_busq = st.session_state['df_pend_busq_resultado']
            
            if df_pend_busq.empty:
                st.warning("⚠️ No se encontraron solicitudes con los criterios seleccionados.")
            else:
                total_pendientes = len(df_pend_busq[df_pend_busq['Status'].str.strip().str.lower() == 'pendiente'])
                st.success(f"✅ Se encontraron {total_pendientes} solicitudes pendientes.")
                
                st.markdown("##### 📋 Listado de Solicitudes Encontradas:")
                df_mostrar_pend = df_pend_busq[['CUC', 'Cliente', 'Modelo', 'Serie', 'Canal', 'Jefe_de_Venta', 'Status']].copy()
                df_mostrar_pend = df_mostrar_pend.rename(columns={'Jefe_de_Venta': 'Jefe de Venta'})
                st.dataframe(df_mostrar_pend, use_container_width=True, hide_index=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                opciones_indices = df_pend_busq.index.tolist()
                
                def format_opcion(idx_item):
                    r = df_sol.loc[idx_item]
                    serie_txt = f" | Serie: {r['Serie']}" if str(r['Serie']).strip() else " | Sin Serie"
                    status_txt = f" | Status: {r['Status']}"
                    return f"CUC: {r['CUC']} - Cliente: {r['Cliente']} (Modelo: {r['Modelo']}{serie_txt}{status_txt})"

                idx_seleccionado = st.selectbox(
                    "📌 Seleccione la solicitud que desea actualizar, cambiar a pendiente/cancelar o eliminar individualmente:", 
                    opciones_indices, 
                    format_func=format_opcion
                )
                
                if idx_seleccionado < len(df_sol):
                    row_sel = df_sol.loc[idx_seleccionado]
                    
                    st.markdown("---")
                    st.markdown(f"**Editando Solicitud de:** 🏢 `{row_sel['Cliente']}` | **CUC:** `{row_sel['CUC']}` | **Estatus Actual:** `{row_sel['Status']}`")
                    
                    key_sesion_mov = f"edit_mov_{idx_seleccionado}"
                    key_sesion_stat = f"edit_stat_{idx_seleccionado}"
                    
                    movimiento_original = str(row_sel.get('Movimiento', 'Entrega')).strip()
                    if movimiento_original not in OPCIONES_MOVIMIENTO_SOL:
                        movimiento_original = "Entrega"
                        
                    if key_sesion_mov not in st.session_state:
                        st.session_state[key_sesion_mov] = movimiento_original
                        
                    def callback_cambio_mov():
                        m_actual = st.session_state.get(key_sesion_mov, "Entrega")
                        val_s = obtener_status_validos(m_actual)
                        if st.session_state.get(key_sesion_stat) not in val_s:
                            st.session_state[key_sesion_stat] = val_s[0]

                    col_sel_m1, _ = st.columns([2, 2])
                    with col_sel_m1:
                        movimiento_edit = st.selectbox(
                            "🔄 Movimiento:", 
                            OPCIONES_MOVIMIENTO_SOL, 
                            index=OPCIONES_MOVIMIENTO_SOL.index(st.session_state[key_sesion_mov]) if st.session_state[key_sesion_mov] in OPCIONES_MOVIMIENTO_SOL else 0,
                            key=key_sesion_mov,
                            on_change=callback_cambio_mov
                        )
                    
                    st.markdown("---")
                    
                    with st.form("form_actualizar_o_entregar"):
                        col_ed1, col_ed2, col_ed3 = st.columns(3)
                        
                        dt_ent_val = str(row_sel.get('Fecha_Entregado', '')).strip()
                        has_entregado_orig = bool(dt_ent_val and dt_ent_val.lower() != 'nan' and dt_ent_val != '')
                        try:
                            dt_ent = datetime.strptime(dt_ent_val, "%Y-%m-%d").date() if has_entregado_orig else date.today()
                        except ValueError:
                            dt_ent = date.today()

                        with col_ed1:
                            status_permitidos_edit = obtener_status_validos(movimiento_edit)
                            status_actual_val = row_sel['Status']
                            
                            if key_sesion_stat not in st.session_state:
                                if status_actual_val in status_permitidos_edit:
                                    st.session_state[key_sesion_stat] = status_actual_val
                                else:
                                    st.session_state[key_sesion_stat] = status_permitidos_edit[0]
                            elif st.session_state[key_sesion_stat] not in status_permitidos_edit:
                                st.session_state[key_sesion_stat] = status_permitidos_edit[0]
                                
                            idx_status_default = status_permitidos_edit.index(st.session_state[key_sesion_stat]) if st.session_state[key_sesion_stat] in status_permitidos_edit else 0

                            status_edit = st.selectbox("⚡ Status:", status_permitidos_edit, index=idx_status_default, key=key_sesion_stat)
                            
                            incluir_fecha_entregado_edit = st.checkbox("¿Asignar Fecha de Realizado ahora?", value=has_entregado_orig, key=f"chk_ent_{idx_seleccionado}")
                            f_entregado_edit = st.date_input("📅 Fecha de Realizado", value=dt_ent, key=f"f_ent_{idx_seleccionado}")
                            
                            idx_proy = OPCIONES_PROYECTOS.index(row_sel['Proyecto']) if row_sel['Proyecto'] in OPCIONES_PROYECTOS else 0
                            proyecto_edit = st.selectbox("📁 Proyecto:", OPCIONES_PROYECTOS, index=idx_proy, key=f"proy_{idx_seleccionado}")
                            
                            cuc_edit = st.text_input("🔢 CUC:", value=str(row_sel.get('CUC', '')), key=f"cuc_{idx_seleccionado}").strip()

                        with col_ed2:
                            cliente_edit = st.text_input("🏢 Nombre de Cliente:", value=str(row_sel.get('Cliente', '')), key=f"cli_{idx_seleccionado}").strip()
                            jefe_edit = st.text_input("👤 Jefe de Venta:", value=str(row_sel.get('Jefe_de_Venta', '')), key=f"jefe_{idx_seleccionado}").strip()
                            supervisor_edit = st.text_input("👔 Supervisor:", value=str(row_sel.get('Supervisor', '')), key=f"sup_{idx_seleccionado}").strip()
                            
                            idx_eq = TIPOS_EQUIPO.index(row_sel['Equipo']) if row_sel['Equipo'] in TIPOS_EQUIPO else 0
                            equipo_edit = st.selectbox("📌 Equipo:", TIPOS_EQUIPO, index=idx_eq, key=f"eq_{idx_seleccionado}")
                            
                            modelo_edit = st.text_input("🧊 Modelo:", value=str(row_sel.get('Modelo', '')), key=f"mod_{idx_seleccionado}").strip()

                        with col_ed3:
                            serie_edit = st.text_input("🏷️ Número de Serie:", value=str(row_sel.get('Serie', '')), key=f"ser_{idx_seleccionado}").strip()
                            
                            idx_canal = OPCIONES_CANALES_SOL.index(row_sel['Canal']) if row_sel['Canal'] in OPCIONES_CANALES_SOL else 0
                            canal_edit = st.selectbox("🏬 Canal:", OPCIONES_CANALES_SOL, index=idx_canal, key=f"can_{idx_seleccionado}")
                            
                            ruta_edit = st.text_input("🚚 Ruta:", value=str(row_sel.get('Ruta', '')), key=f"rut_{idx_seleccionado}").strip()
                            motivo_edit = st.text_input("📝 Motivo:", value=str(row_sel.get('Motivo', '')), key=f"mot_{idx_seleccionado}").strip()

                        observaciones_edit = st.text_area("💬 Observaciones:", value=str(row_sel.get('Observaciones', '')), key=f"obs_{idx_seleccionado}").strip()
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            btn_actualizar = st.form_submit_button("💾 Guardar Cambios en la Solicitud")
                        with col_btn2:
                            btn_eliminar_individual = st.form_submit_button("🗑 Eliminar esta Solicitud")
                        
                        if btn_actualizar:
                            status_validos_verificacion = obtener_status_validos(movimiento_edit)
                            
                            if status_edit not in status_validos_verificacion:
                                st.error(f"❌ ADVERTENCIA: Los datos son incorrectos. Para el movimiento '{movimiento_edit}' NO está permitido el estatus '{status_edit}'. Opciones válidas: {', '.join(status_validos_verificacion)}. Corríjalo para continuar.")
                            elif canal_edit == "Otro" and not observaciones_edit:
                                st.error("⚠️ El campo Observaciones es obligatorio cuando el Canal es 'Otro'.")
                            elif not cuc_edit or not modelo_edit or not cliente_edit:
                                st.error("⚠️ Por favor, ingresa al menos el CUC, el Modelo y el Cliente.")
                            elif status_edit.lower() in ["entregado", "realizado", "transferido", "levantado"] and not incluir_fecha_entregado_edit:
                                st.error(f"❌ No se guardaron los cambios: Seleccionó el estatus '{status_edit}' pero no activó ni asignó la Fecha de Realizado.")
                            else:
                                f_rec_str = str(row_sel.get('Fecha_Recibido', ''))
                                f_ent_str = f_entregado_edit.strftime("%Y-%m-%d") if incluir_fecha_entregado_edit else ""
                                
                                df_sol.loc[idx_seleccionado, 'Fecha_Recibido'] = f_rec_str
                                df_sol.loc[idx_seleccionado, 'Fecha_Entregado'] = f_ent_str
                                df_sol.loc[idx_seleccionado, 'Status'] = status_edit
                                df_sol.loc[idx_seleccionado, 'Proyecto'] = proyecto_edit
                                df_sol.loc[idx_seleccionado, 'CUC'] = cuc_edit
                                df_sol.loc[idx_seleccionado, 'Cliente'] = cliente_edit
                                df_sol.loc[idx_seleccionado, 'Jefe_de_Venta'] = jefe_edit
                                df_sol.loc[idx_seleccionado, 'Supervisor'] = supervisor_edit
                                df_sol.loc[idx_seleccionado, 'Movimiento'] = movimiento_edit
                                df_sol.loc[idx_seleccionado, 'Equipo'] = equipo_edit
                                df_sol.loc[idx_seleccionado, 'Modelo'] = modelo_edit
                                df_sol.loc[idx_seleccionado, 'Serie'] = serie_edit
                                df_sol.loc[idx_seleccionado, 'Canal'] = canal_edit
                                df_sol.loc[idx_seleccionado, 'Ruta'] = ruta_edit
                                df_sol.loc[idx_seleccionado, 'Motivo'] = motivo_edit
                                df_sol.loc[idx_seleccionado, 'Observaciones'] = observaciones_edit
                                
                                if guardar_solicitudes_seguro(df_sol):
                                    status_ok_lista = ["Entregado", "Realizado", "Transferido", "Levantado"]
                                    if status_edit in status_ok_lista and serie_edit:
                                        if not df_inv.empty and serie_edit in df_inv['Serie'].values:
                                            idx_inv = df_inv[df_inv['Serie'] == serie_edit].index[0]
                                            df_inv.loc[idx_inv, 'Ubicación'] = "Asignado a Cliente"
                                            df_inv.loc[idx_inv, 'Estatus'] = "En Uso"
                                            df_inv.loc[idx_inv, 'Ultimo_Movimiento'] = f_ent_str if f_ent_str else datetime.now().strftime("%Y-%m-%d")
                                            guardar_datos(df_inv)
                                            registrar_historial(serie_edit, modelo_edit, f"SOLICITUD {status_edit.upper()}", f"Cliente: {cliente_edit} | CUC: {cuc_edit}")
                                    
                                    st.success("🎉 ¡Cambios guardados con éxito! La solicitud ha sido actualizada y sincronizada correctamente en el sistema.")
                                    if 'df_pend_busq_resultado' in st.session_state:
                                        del st.session_state['df_pend_busq_resultado']
                                    time.sleep(2.5)
                                    st.rerun()
                                else:
                                    st.error("❌ Error: No se pudieron guardar los cambios en la solicitud.")

                        if btn_eliminar_individual:
                            cliente_borrado = row_sel['Cliente']
                            cuc_borrado = row_sel['CUC']
                            df_sol = df_sol.drop(idx_seleccionado).reset_index(drop=True)
                            if guardar_solicitudes_seguro(df_sol):
                                st.success(f"🗑 ¡Solicitud eliminada con éxito! El registro del cliente '{cliente_borrado}' (CUC: {cuc_borrado}) fue dado de baja definitivamente del sistema.")
                                if 'df_pend_busq_resultado' in st.session_state:
                                    del st.session_state['df_pend_busq_resultado']
                                time.sleep(2.5)
                                st.rerun()
                            else:
                                st.error("❌ Error: No se pudo eliminar la solicitud.")

    elif modo_solicitud == "📊 Historial de Solicitudes OK":
        st.markdown("#### 📊 Historial de Solicitudes (Entregadas, Transferidas, Realizadas o Levantadas)")
        
        filtro_cuc_ok = st.text_input("🔍 Filtrar por CUC:").strip()
        st.markdown("---")

        if not df_sol.empty:
            status_filtrar = ['Entregado', 'Transferido', 'Realizado', 'Levantado']
            generadas_df = df_sol[df_sol['Status'].isin(status_filtrar)].copy()
            if not generadas_df.empty:
                def limpiar_fecha_para_mostrar(val):
                    val_s = str(val).strip()
                    if not val_s or val_s.lower() == 'nan' or val_s.lower() == 'nat':
                        return ""
                    if re.match(r'^\d{4}-\d{2}-\d{2}$', val_s[:10]):
                        return val_s[:10]
                    dt_parsed = pd.to_datetime(val_s, errors='coerce', dayfirst=True)
                    if not pd.isna(dt_parsed):
                        return dt_parsed.strftime('%Y-%m-%d')
                    return val_s[:10]

                if 'Fecha_Entregado' in generadas_df.columns:
                    generadas_df['Fecha_Entregado'] = generadas_df['Fecha_Entregado'].apply(limpiar_fecha_para_mostrar)

                if filtro_cuc_ok:
                    generadas_df = generadas_df[generadas_df['CUC'].str.contains(filtro_cuc_ok, case=False, na=False)]

                df_mostrar_gen = generadas_df[['Fecha_Entregado', 'CUC', 'Cliente', 'Modelo', 'Serie', 'Canal', 'Jefe_de_Venta', 'Supervisor', 'Ruta', 'Status']].copy()
                df_mostrar_gen = df_mostrar_gen.rename(columns={
                    'Fecha_Entregado': 'Fecha Realizado',
                    'Jefe_de_Venta': 'Jefe de Venta'
                })
                
                if not df_mostrar_gen.empty:
                    st.dataframe(df_mostrar_gen, use_container_width=True, hide_index=True)
                else:
                    st.warning("⚠️ No se encontraron solicitudes que coincidan con el CUC buscado.")
            else:
                st.info("ℹ️ No hay solicitudes con estatus Entregado, Transferido, Realizado o Levantado registradas todavía.")
        else:
            st.info("ℹ El archivo de solicitudes está vacío.")

    elif modo_solicitud == "📂 Importar Archivo Excel de Solicitudes":
        st.markdown("#### 📂 Subir y Sincronizar Archivo Excel (.xlsx) de Solicitudes")
        st.markdown("Selecciona o arrastra tu archivo Excel actualizado con las solicitudes.")
        
        archivo_subido = st.file_uploader("📂 Sube tu archivo Excel de solicitudes", type=["xlsx", "xls"])
        
        if archivo_subido is not None:
            try:
                df_importado = pd.read_excel(archivo_subido, dtype=str)
                df_importado = df_importado.fillna("")
                df_importado = limpiar_y_mapear_columnas(df_importado, COLUMNAS_SOLICITUDES)
                
                if st.button("🚀 Confirmar e Importar Datos"):
                    if guardar_solicitudes_seguro(df_importado):
                        st.success(f"🎉 ¡Se han importado exitosamente {len(df_importado)} registros desde tu archivo Excel!")
                        st.dataframe(df_importado.head(10), use_container_width=True)
            except Exception as e:
                st.error(f"⚠ Error al leer el archivo Excel: {e}")

# 5. LEVANTAMIENTOS (SOLO ADMINISTRADORES)
elif menu == "📝 Levantamientos" and st.session_state['autenticado']:
    st.subheader("📝 Gestión de Levantamientos (Equipos Recolectados)")
    
    modo_levantamiento = st.radio(
        "Selecciona una acción:", 
        [
            "➕ Registrar Levantamiento", 
            "📊 Equipos Levantados"
        ], 
        horizontal=True
    )
    st.markdown("---")
    
    if modo_levantamiento == "➕ Registrar Levantamiento":
        st.markdown("Registra los equipos levantados. Si el estatus indica 'Levantado', el equipo se integra al inventario general, y solo pasa a Equipos Disponibles si su Estatus es 'Reparado' o 'Nuevo'.")
        
        with st.form("form_levantamiento", clear_on_submit=True):
            col_l1, col_l2 = st.columns(2)
            with col_l1:
                fecha_lev = st.date_input("📅 Fecha de Levantamiento", value=date.today())
                cuc_lev = st.text_input("🔢 CUC:").strip()
                cliente = st.text_input("🏢 Cliente / Negocio:").strip()
                modelo = st.text_input("🧊 Modelo del Equipo:").strip()
                serie = st.text_input("🏷️ Número de Serie:").strip()
                tipo = st.selectbox("📌 Tipo de Equipo:", TIPOS_EQUIPO)
                imagen = st.selectbox("🖼️ Imagen / Marca:", OPCIONES_IMAGEN)
            with col_l2:
                canal = st.selectbox("🏬 Canal:", [c for c in OPCIONES_CANALES_SOL if c != "Otro"])
                status_lev = st.selectbox("⚡ Estatus del Equipo:", ESTATUS)
                motivo = st.text_input("📝 Motivo del Levantamiento:").strip()
                ubicacion = st.selectbox("📍 Ubicación Inicial (ej. En taller):", UBICACIONES, index=3)
                ruta = st.text_input("🚚 Ruta:").strip()
                jefe_venta = st.text_input("👤 Jefe de Venta:").strip()
                solicitado = st.selectbox("📨 Solicitado vía:", ["Whatsapp", "Correo", "Solicitud"])
                
            submit_lev = st.form_submit_button("Guardar Levantamiento e Ingresar al Sistema")
            
            if submit_lev:
                if not serie or not modelo or not cliente or not cuc_lev:
                    st.error("⚠️ Por favor, completa el CUC, la Serie, el Modelo y el Cliente.")
                else:
                    fecha_str = fecha_lev.strftime("%Y-%m-%d")
                    
                    df_lev = cargar_levantamientos()
                    nuevo_lev = pd.DataFrame([{
                        "Fecha": fecha_str, "CUC": cuc_lev, "Cliente": cliente, "Modelo": modelo,
                        "Serie": serie, "Tipo": tipo, "Imagen": imagen, "Canal": canal,
                        "Status": status_lev, "Motivo": motivo, "Ubicación": ubicacion,
                        "Ruta": ruta, "Jefe_de_Venta": jefe_venta, "Solicitado": solicitado
                    }])
                    df_lev = pd.concat([df_lev, nuevo_lev], ignore_index=True)
                    try:
                        df_lev.to_csv(LEVANTAMIENTOS_FILE, index=False)
                    except PermissionError:
                        st.error("⚠️ Error: El archivo 'levantamientos.csv' está abierto en Excel. Ciérralo para guardar.")
                    
                    if status_lev.lower() not in ["pendiente", "cancelado"]:
                        if not df_inv.empty and serie in df_inv['Serie'].values:
                            idx = df_inv[df_inv['Serie'] == serie].index[0]
                            df_inv.loc[idx, 'Modelo'] = modelo
                            df_inv.loc[idx, 'Tipo'] = tipo
                            df_inv.loc[idx, 'Imagen'] = imagen
                            df_inv.loc[idx, 'Canal'] = canal
                            df_inv.loc[idx, 'Ubicación'] = ubicacion
                            df_inv.loc[idx, 'Estatus'] = status_lev
                            df_inv.loc[idx, 'Ultimo_Movimiento'] = fecha_str
                        else:
                            nueva_inv = pd.DataFrame([{
                                "Serie": serie, "Modelo": modelo, "Tipo": tipo, "Imagen": imagen,
                                "Canal": canal, "Ubicación": ubicacion, "Estatus": status_lev, "Ultimo_Movimiento": fecha_str
                            }])
                            df_inv = pd.concat([df_inv, nueva_inv], ignore_index=True)
                        guardar_datos(df_inv)
                    else:
                        if not df_inv.empty and serie in df_inv['Serie'].values:
                            df_inv = df_inv[df_inv['Serie'] != serie].reset_index(drop=True)
                            guardar_datos(df_inv)

                    registrar_historial(serie, modelo, "LEVANTAMIENTO", f"Cliente: {cliente} | CUC: {cuc_lev} | Status: {status_lev} | Tipo: {tipo} | Ubicación: {ubicacion}")
                    st.success(f"✅ ¡Levantamiento de la serie {serie} (CUC: {cuc_lev}) registrado correctamente!")

    elif modo_levantamiento == "📊 Equipos Levantados":
        st.markdown("#### 📊 Historial de Equipos Levantados")
        
        filtro_cuc_lev = st.text_input("🔍 Filtrar por CUC:").strip()
        st.markdown("---")

        df_lev_historial = cargar_levantamientos()
        if not df_lev_historial.empty:
            if filtro_cuc_lev:
                df_lev_historial = df_lev_historial[df_lev_historial['CUC'].str.contains(filtro_cuc_lev, case=False, na=False)]
            
            total_lev = len(df_lev_historial)
            st.success(f"✅ Se encontraron {total_lev} registros de equipos levantados.")
            
            df_mostrar_lev = df_lev_historial[['Fecha', 'CUC', 'Cliente', 'Modelo', 'Serie', 'Canal', 'Status', 'Ubicación', 'Ruta', 'Jefe_de_Venta']].copy()
            df_mostrar_lev = df_mostrar_lev.rename(columns={'Jefe_de_Venta': 'Jefe de Venta'})
            
            if not df_mostrar_lev.empty:
                st.dataframe(df_mostrar_lev, use_container_width=True, hide_index=True)
            else:
                st.warning("⚠️ No se encontraron equipos levantados que coincidan con el CUC buscado.")
        else:
            st.info("ℹ Aún no hay equipos levantados registrados en el sistema.")

# 6. REGISTRAR ENTRADA (SOLO ADMINISTRADORES)
elif menu == "📥 Registrar Entrada" and st.session_state['autenticado']:
    st.subheader("📥 Registrar Entrada de Equipos")
    
    modo_entrada = st.radio(
        "Selecciona el método de entrada:",
        [
            "➕ Entrada Individual",
            "📂 Carga Masiva (Excel)"
        ],
        horizontal=True
    )
    st.markdown("---")
    
    if modo_entrada == "➕ Entrada Individual":
        with st.form("form_entrada", clear_on_submit=True):
            serie = st.text_input("🏷️ Número de Serie:").strip()
            modelo = st.text_input("🧊 Modelo del Equipo:").strip()
            tipo = st.selectbox("📌 Tipo de Equipo:", TIPOS_EQUIPO)
            imagen = st.selectbox("🖼️ Imagen / Marca:", OPCIONES_IMAGEN)
            canal = st.selectbox("🏬 Canal:", [c for c in OPCIONES_CANALES_SOL if c != "Otro"])
            ubicacion = st.selectbox("📍 Ubicación inicial", UBICACIONES)
            estatus = st.selectbox("⚡ Estatus inicial", ESTATUS)
            fecha_entrada = st.date_input("📅 Fecha de entrada / Último movimiento", value=date.today())
            
            submit = st.form_submit_button("Registrar Entrada en Sistema")
            
            if submit:
                if not serie or not modelo:
                    st.error("⚠️ Por favor, completa la serie y el modelo.")
                else:
                    fecha_str = fecha_entrada.strftime("%Y-%m-%d")
                    if not df_inv.empty and serie in df_inv['Serie'].values:
                        idx = df_inv[df_inv['Serie'] == serie].index[0]
                        df_inv.loc[idx, 'Modelo'] = modelo
                        df_inv.loc[idx, 'Tipo'] = tipo
                        df_inv.loc[idx, 'Imagen'] = imagen
                        df_inv.loc[idx, 'Canal'] = canal
                        df_inv.loc[idx, 'Ubicación'] = ubicacion
                        df_inv.loc[idx, 'Estatus'] = estatus
                        df_inv.loc[idx, 'Ultimo_Movimiento'] = fecha_str
                    else:
                        nueva_fila = pd.DataFrame([{
                            "Serie": serie,
                            "Modelo": modelo,
                            "Tipo": tipo,
                            "Imagen": imagen,
                            "Canal": canal,
                            "Ubicación": ubicacion,
                            "Estatus": estatus,
                            "Ultimo_Movimiento": fecha_str
                        }])
                        df_inv = pd.concat([df_inv, nueva_fila], ignore_index=True)
                    guardar_datos(df_inv)
                    registrar_historial(serie, modelo, "ENTRADA", f"Tipo: {tipo} | Imagen: {imagen} | Canal: {canal} | Ubicación: {ubicacion} | Estatus: {estatus} | Fecha: {fecha_str}")
                    st.success("¡Se ha registrado la entrada del equipo correctamente en el inventario sin duplicados!")

    elif modo_entrada == "📂 Carga Masiva (Excel)":
        st.markdown("Sube un archivo Excel (.xlsx o .xls) con múltiples equipos para darles entrada de forma masiva.")
        archivo_entrada_masiva = st.file_uploader("📂 Selecciona tu archivo Excel de entradas", type=["xlsx", "xls"], key="uploader_entrada_masiva")
        
        if archivo_entrada_masiva is not None:
            try:
                df_subido_masivo = pd.read_excel(archivo_entrada_masiva, dtype=str).fillna("")
                df_subido_masivo = limpiar_y_mapear_columnas(df_subido_masivo, ESQUEMA_COLUMNAS)
                
                st.markdown("##### 🔍 Vista previa de los datos a cargar:")
                st.dataframe(df_subido_masivo.head(5), use_container_width=True)
                
                if st.button("🚀 Confirmar e Importar Entradas Masivas"):
                    count_nuevos = 0
                    for _, row in df_subido_masivo.iterrows():
                        s_val = str(row.get('Serie', '')).strip()
                        m_val = str(row.get('Modelo', '')).strip()
                        if s_val and m_val:
                            t_val = str(row.get('Tipo', 'Enfriador'))
                            i_val = str(row.get('Imagen', 'Sin Imagen'))
                            c_val = str(row.get('Canal', 'Tradicional'))
                            u_val = str(row.get('Ubicación', 'En almacén de Comodatos'))
                            e_val = str(row.get('Estatus', 'Nuevo'))
                            f_val = str(row.get('Ultimo_Movimiento', datetime.now().strftime("%Y-%m-%d")))
                            
                            if not df_inv.empty and s_val in df_inv['Serie'].values:
                                idx = df_inv[df_inv['Serie'] == s_val].index[0]
                                df_inv.loc[idx, 'Modelo'] = m_val
                                df_inv.loc[idx, 'Tipo'] = t_val
                                df_inv.loc[idx, 'Imagen'] = i_val
                                df_inv.loc[idx, 'Canal'] = c_val
                                df_inv.loc[idx, 'Ubicación'] = u_val
                                df_inv.loc[idx, 'Estatus'] = e_val
                                df_inv.loc[idx, 'Ultimo_Movimiento'] = f_val
                            else:
                                nueva_f = pd.DataFrame([{
                                    "Serie": s_val, "Modelo": m_val, "Tipo": t_val, "Imagen": i_val,
                                    "Canal": c_val, "Ubicación": u_val, "Estatus": e_val, "Ultimo_Movimiento": f_val
                                }])
                                df_inv = pd.concat([df_inv, nueva_f], ignore_index=True)
                            count_nuevos += 1
                            registrar_historial(s_val, m_val, "ENTRADA MASIVA", f"Carga masiva desde archivo Excel. Ubicación: {u_val} | Estatus: {e_val}")
                    
                    guardar_datos(df_inv)
                    st.balloons()
                    st.success(f"🎉 ¡Se procesaron e importaron exitosamente {count_nuevos} equipos al inventario general!")
            except Exception as e:
                st.error(f"⚠️ Ocurrió un error al procesar el archivo Excel: {e}")

# 7. REGISTRAR SALIDA (SOLO ADMINISTRADORES)
elif menu == "📤 Registrar Salida" and st.session_state['autenticado']:
    st.subheader("📤 Salida de Equipos del Inventario")
    
    serie_buscar = st.text_input("Escriba la serie del equipo para dar salida:").strip()
    
    if serie_buscar:
        equipo = df_inv[df_inv['Serie'] == serie_buscar]
        if equipo.empty:
            st.warning("⚠️ No se encontró ningún equipo con esa serie en el inventario.")
        else:
            modelo_actual_eq = str(equipo.iloc[0]['Modelo'])
            tipo_actual_eq = str(equipo.iloc[0]['Tipo']) if 'Tipo' in equipo.columns else 'Enfriador'
            imagen_actual_eq = str(equipo.iloc[0]['Imagen']) if 'Imagen' in equipo.columns else 'Sin Imagen'
            canal_actual_eq = str(equipo.iloc[0]['Canal'])
            ubicacion_actual_eq = str(equipo.iloc[0]['Ubicación'])
            estatus_actual_eq = str(equipo.iloc[0]['Estatus'])
            
            st.info(f"📌 Equipo encontrado -> Tipo: **{tipo_actual_eq}** | Modelo: **{modelo_actual_eq}** | Imagen: **{imagen_actual_eq}** | Canal: **{canal_actual_eq}** | Ubicación: **{ubicacion_actual_eq}** | Estatus: **{estatus_actual_eq}**")
            
            with st.form("form_salida"):
                fecha_salida = st.date_input("📅 Fecha de salida", value=date.today())
                ruta_salida = st.text_input("🚚 Ruta:")
                motivo_salida = st.text_input("📝 Motivo de la salida / Destino:")
                
                btn_confirmar_salida = st.form_submit_button("Confirmar salida")
                
                if btn_confirmar_salida:
                    idx = df_inv[df_inv['Serie'] == serie_buscar].index[0]
                    fecha_str = fecha_salida.strftime("%Y-%m-%d")
                    
                    registrar_historial(
                        serie_buscar, 
                        modelo_actual_eq, 
                        "SALIDA", 
                        f"Tipo: {tipo_actual_eq} | Imagen: {imagen_actual_eq} | Canal: {canal_actual_eq} | Ubicación anterior: {ubicacion_actual_eq} | Estatus anterior: {estatus_actual_eq} | Fecha Salida: {fecha_str} | Ruta: {ruta_salida} | Motivo: {motivo_salida}"
                    )
                    
                    df_inv = df_inv.drop(idx).reset_index(drop=True)
                    guardar_datos(df_inv)
                    st.success(f"✅ ¡Salida confirmada! El equipo con serie {serie_buscar} ha sido eliminado del inventario general.")

# 8. EDITAR / ELIMINAR EQUIPO (SOLO ADMINISTRADORES)
elif menu == "✏️ Editar / Eliminar" and st.session_state['autenticado']:
    st.subheader("✏️ Gestión, Corrección y Depuración de Equipos")
    
    serie_edit = st.text_input("🔍 Ingrese la serie del equipo a editar o eliminar:").strip()
    
    if serie_edit:
        equipo = df_inv[df_inv['Serie'] == serie_edit]
        if equipo.empty:
            st.warning("⚠️ No se encontró el equipo en la base de datos.")
        else:
            idx = df_inv[df_inv['Serie'] == serie_edit].index[0]
            
            with st.form("form_editar"):
                mod_modelo = st.text_input("🧊 Modelo", value=str(df_inv.loc[idx, 'Modelo']))
                
                tipo_actual = str(df_inv.loc[idx, 'Tipo']) if 'Tipo' in df_inv.columns else 'Enfriador'
                idx_tipo = TIPOS_EQUIPO.index(tipo_actual) if tipo_actual in TIPOS_EQUIPO else 0
                mod_tipo = st.selectbox("📌 Tipo de Equipo", TIPOS_EQUIPO, index=idx_tipo)
                
                imagen_actual = str(df_inv.loc[idx, 'Imagen']) if 'Imagen' in df_inv.columns else 'Sin Imagen'
                idx_imagen = OPCIONES_IMAGEN.index(imagen_actual) if imagen_actual in OPCIONES_IMAGEN else 0
                mod_imagen = st.selectbox("🖼️ Imagen / Marca", OPCIONES_IMAGEN, index=idx_imagen)
                
                canales_inv_opc = [c for c in OPCIONES_CANALES_SOL if c != "Otro"]
                canal_actual = str(df_inv.loc[idx, 'Canal'])
                idx_canal = canales_inv_opc.index(canal_actual) if canal_actual in canales_inv_opc else 0
                mod_canal = st.selectbox("🏬 Canal", canales_inv_opc, index=idx_canal)
                
                mod_ubicacion = st.selectbox("📍 Ubicación", UBICACIONES, index=UBICACIONES.index(df_inv.loc[idx, 'Ubicación']) if df_inv.loc[idx, 'Ubicación'] in UBICACIONES else 0)
                mod_estatus = st.selectbox("⚡ Estatus", ESTATUS, index=ESTATUS.index(df_inv.loc[idx, 'Estatus']) if df_inv.loc[idx, 'Estatus'] in ESTATUS else 0)
                
                fecha_actual_reg = str(df_inv.loc[idx, 'Ultimo_Movimiento'])[:10]
                try:
                    dt_default = datetime.strptime(fecha_actual_reg, "%Y-%m-%d").date()
                except ValueError:
                    dt_default = date.today()
                
                mod_fecha = st.date_input("📅 Fecha de Último Movimiento", value=dt_default)
                
                col1, col2 = st.columns(2)
                with col1:
                    btn_guardar = st.form_submit_button("💾 Guardar Cambios")
                with col2:
                    btn_eliminar = st.form_submit_button("🗑️ Eliminar Equipo")
                
                if btn_guardar:
                    df_inv.loc[idx, 'Modelo'] = mod_modelo
                    df_inv.loc[idx, 'Tipo'] = mod_tipo
                    df_inv.loc[idx, 'Imagen'] = mod_imagen
                    df_inv.loc[idx, 'Canal'] = mod_canal
                    df_inv.loc[idx, 'Ubicación'] = mod_ubicacion
                    df_inv.loc[idx, 'Estatus'] = mod_estatus
                    df_inv.loc[idx, 'Ultimo_Movimiento'] = mod_fecha.strftime("%Y-%m-%d")
                        
                    guardar_datos(df_inv)
                    registrar_historial(serie_edit, mod_modelo, "EDICIÓN", f"Datos modificados. Tipo: {mod_tipo} | Imagen: {mod_imagen} | Canal: {mod_canal} | Fecha Movimiento: {mod_fecha.strftime('%Y-%m-%d')}")
                    st.success("✅ ¡Datos actualizados con éxito!")
                
                if btn_eliminar:
                    modelo_eliminado = df_inv.loc[idx, 'Modelo']
                    df_inv = df_inv.drop(idx).reset_index(drop=True)
                    guardar_datos(df_inv)
                    registrar_historial(serie_edit, modelo_eliminado, "ELIMINACIÓN", "Equipo eliminado del inventario.")
                    st.success("🗑️ ¡Equipo eliminado permanentemente del sistema!")

# 9. HISTORIAL DE MOVIMIENTOS (SOLO ADMINISTRADORES)
elif menu == "📜 Historial de Movimientos" and st.session_state['autenticado']:
    st.subheader("📜 Bitácora de Entradas, Salidas y Cambios de Ubicación")
    df_h = cargar_historial()
    if df_h.empty:
        st.info("ℹ️ Aún no hay movimientos registrados en la bitácora.")
    else:
        columnas_ordenadas = ["Fecha_Hora", "Usuario", "Serie", "Modelo", "Tipo_Movimiento", "Ruta", "Motivo", "Detalles"]
        df_h = df_h[[col for col in columnas_ordenadas if col in df_h.columns]]
        st.dataframe(df_h.sort_values(by="Fecha_Hora", ascending=False), use_container_width=True, hide_index=True)

# 10. EXPORTAR A EXCEL (SOLO ADMINISTRADORES)
elif menu == "💾 Exportar a Excel" and st.session_state['autenticado']:
    st.subheader("💾 Exportar e Importar Base de Datos Completa")
    
    sub_pestana = st.radio("Selecciona una opción:", ["📥 Exportar a Excel", "📂 Importar Base de Datos Completa"], horizontal=True)
    st.markdown("---")
    
    if sub_pestana == "📥 Exportar a Excel":
        st.markdown("Genera un archivo completo con el inventario actual, levantamientos, solicitudes y la bitácora de movimientos en pestañas separadas.")
        if st.button("📥 Generar Archivo Excel"):
            output_file = "Reporte_Inventario_Capacidades_Bepensa.xlsx"
            df_export = calcular_dias_sin_movimiento(df_inv)
            
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df_export.to_excel(writer, sheet_name='Inventario Actual', index=False)
                
                df_lev_exp = cargar_levantamientos()
                if not df_lev_exp.empty:
                    df_lev_exp.to_excel(writer, sheet_name='Levantamientos', index=False)
                    
                df_sol_exp = cargar_solicitudes()
                if not df_sol_exp.empty:
                    df_sol_exp.to_excel(writer, sheet_name='Solicitudes', index=False)
                    
                df_h = cargar_historial()
                if not df_h.empty:
                    columnas_excel = ["Fecha_Hora", "Usuario", "Serie", "Modelo", "Tipo_Movimiento", "Ruta", "Motivo", "Detalles"]
                    df_h = df_h[[col for col in columnas_excel if col in df_h.columns]]
                    df_h.to_excel(writer, sheet_name='Historial Movimientos', index=False)
                
            with open(output_file, "rb") as f:
                st.download_button(
                    label="📥 Click Aquí para Descargar el Archivo",
                    data=f,
                    file_name=output_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            st.success("✅ ¡Archivo Excel generado correctamente con todas las pestañas!")
            
    elif sub_pestana == "📂 Importar Base de Datos Completa":
        st.markdown("Sube tu archivo Excel y **selecciona manualmente qué pestaña de tu archivo corresponde a cada apartado** de la aplicación.")
        
        archivo_completo = st.file_uploader("📂 Selecciona tu archivo Excel con múltiples pestañas", type=["xlsx", "xls"])
        
        if archivo_completo is not None:
            try:
                xls = pd.ExcelFile(archivo_completo)
                nombres_hojas = xls.sheet_names
                
                st.markdown("---")
                st.markdown("### 📌 Mapeo Manual de Pestañas")
                
                opciones_hojas_vacio = ["(No importar esta sección)"] + nombres_hojas
                
                hoja_inventario = st.selectbox("🏢 Selecciona la pestaña de tu Excel que corresponde al **Inventario Actual**:", opciones_hojas_vacio)
                hoja_levantamientos = st.selectbox("📝 Selecciona la pestaña de tu Excel que corresponde a **Levantamientos**:", opciones_hojas_vacio)
                hoja_solicitudes = st.selectbox("📋 Selecciona la pestaña de tu Excel que corresponde a **Solicitudes**:", opciones_hojas_vacio)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("🚀 Ejecutar Importación Seleccionada"):
                    import_count = 0
                    
                    if hoja_inventario != "(No importar esta sección)":
                        df_temp = pd.read_excel(xls, sheet_name=hoja_inventario, dtype=str).fillna("")
                        df_temp = limpiar_y_mapear_columnas(df_temp, ESQUEMA_COLUMNAS)
                        guardar_datos(df_temp)
                        import_count += 1
                        st.success(f"✅ Inventario Actualizado: {len(df_temp)} registros importados desde la pestaña '{hoja_inventario}'.")
                        
                    if hoja_levantamientos != "(No importar esta sección)":
                        df_temp = pd.read_excel(xls, sheet_name=hoja_levantamientos, dtype=str).fillna("")
                        df_temp = limpiar_y_mapear_columnas(df_temp, COLUMNAS_LEVANTAMIENTOS)
                        df_temp.to_csv(LEVANTAMIENTOS_FILE, index=False)
                        import_count += 1
                        st.success(f"✅ Levantamientos Actualizados: {len(df_temp)} registros importados desde la pestaña '{hoja_levantamientos}'.")
                        
                    if hoja_solicitudes != "(No importar esta sección)":
                        df_temp = pd.read_excel(xls, sheet_name=hoja_solicitudes, dtype=str).fillna("")
                        df_temp = limpiar_y_mapear_columnas(df_temp, COLUMNAS_SOLICITUDES)
                        guardar_solicitudes_seguro(df_temp)
                        import_count += 1
                        st.success(f"✅ Solicitudes Actualizadas: {len(df_temp)} registros importados desde la pestaña '{hoja_solicitudes}'.")
                        
                    if import_count > 0:
                        st.balloons()
                        st.success("🎉 ¡Todas las pestañas seleccionadas se han importado y reflejado correctamente en el sistema!")
                        time.sleep(3)
                        st.rerun()
                    else:
                        st.warning("⚠️ Debes seleccionar al menos una pestaña para importar.")
            except Exception as e:
                st.error(f"⚠️ Error al leer el archivo Excel: {e}")