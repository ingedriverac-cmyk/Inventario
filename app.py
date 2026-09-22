import sys
import asyncio

# Solución para compatibilidad de red en Windows con Python moderno
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, date
import os
import requests
import json
import re
from PIL import Image
import numpy as np

# Intentar importar pyzbar y cv2 para el lector de códigos de barras por cámara
try:
    import cv2
    from pyzbar import pyzbar
    VISION_DISPONIBLE = True
except ImportError:
    VISION_DISPONIBLE = False

# Configuración de la página y diseño estético
st.set_page_config(
    page_title="Control de Inventario - Bepensa / Coca-Cola",
    page_icon="❄️",
    layout="wide"
)

# Estilos CSS personalizados (Sidebar naranja y tarjetas de KPI estilizadas)
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    
    /* Personalización de la barra lateral (Sidebar) a color naranja */
    [data-testid="stSidebar"] {
        background-color: #FF7A00; /* Color naranja vibrante */
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

    /* Tarjetas KPI con estilos personalizados de colores */
    .kpi-card-1 { background-color: #eff6ff; border-left: 5px solid #3b82f6; padding: 16px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .kpi-card-2 { background-color: #ffedd5; border-left: 5px solid #f97316; padding: 16px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .kpi-card-3 { background-color: #fee2e2; border-left: 5px solid #ef4444; padding: 16px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .kpi-card-4 { background-color: #dcfce7; border-left: 5px solid #22c55e; padding: 16px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .kpi-card-5 { background-color: #f3e8ff; border-left: 5px solid #a855f7; padding: 16px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }

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

# Archivos CSV locales y URL de Google Apps Script integrada actualizada
INVENTARIO_FILE = "inventario_refrigeradores.csv"
HISTORIAL_FILE = "historial_movimientos.csv"
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbz0uHPmSFwpgWRhmDApRKHyQyP1FK10d8vy3TlG5UNi5RpqhgpnZbBDEL8q93s9MfVf7Q/exec"

# Opciones fijas de Canales
CANALES = [
    "Moderno",
    "Tradicional",
    "Hoteles",
    "Vending",
    "AP20L"
]

# Opciones fijas de Ubicaciones
UBICACIONES = [
    "En almacén de Comodatos",
    "En almacén de Publicidad",
    "En patios",
    "En taller",
    "Uso Interno",
    "En proceso de Baja"
]

ESTATUS = [
    "Nuevo",
    "Reparado",
    "Para Reparar",
    "Para Baja",
    "En Uso"
]

# Esquema oficial simplificado (Sin Fecha_Registro)
ESQUEMA_COLUMNAS = ["Serie", "Modelo", "Canal", "Ubicación", "Estatus", "Ultimo_Movimiento"]

# Funciones de carga y guardado sincronizadas con Google Sheets
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
            df = pd.read_csv(INVENTARIO_FILE, dtype=str)
        else:
            df = pd.DataFrame(columns=ESQUEMA_COLUMNAS)
        
    for col in ESQUEMA_COLUMNAS:
        if col not in df.columns:
            df[col] = ""

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
    
    df = df[[c for c in ESQUEMA_COLUMNAS if c in df.columns]]
    return df

def cargar_historial():
    if os.path.exists(HISTORIAL_FILE):
        return pd.read_csv(HISTORIAL_FILE, dtype=str)
    else:
        return pd.DataFrame(columns=["Fecha_Hora", "Serie", "Modelo", "Tipo_Movimiento", "Detalles"])

def guardar_datos(df):
    df.to_csv(INVENTARIO_FILE, index=False)
    try:
        records = df.to_dict(orient="records")
        requests.post(WEB_APP_URL, json=records, timeout=10)
    except Exception as e:
        st.error(f"⚠️ Error al sincronizar con Google Sheets: {e}")

def registrar_historial(serie, modelo, tipo_movimiento, detalles):
    df_h = cargar_historial()
    nuevo_mov = pd.DataFrame([{
        "Fecha_Hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Serie": str(serie),
        "Modelo": str(modelo),
        "Tipo_Movimiento": tipo_movimiento,
        "Detalles": detalles
    }])
    df_h = pd.concat([df_h, nuevo_mov], ignore_index=True)
    df_h.to_csv(HISTORIAL_FILE, index=False)

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

# Función auxiliar para decodificar códigos de barras desde imagen de cámara
def escanear_codigo_barras(key_suffix):
    serie_detectada = ""
    if VISION_DISPONIBLE:
        with st.expander("📷 Escanear código de barras con la cámara"):
            foto = st.camera_input("Apunta la cámara al código de barras de la serie", key=f"cam_{key_suffix}")
            if foto is not None:
                try:
                    bytes_data = foto.getvalue()
                    np_arr = np.frombuffer(bytes_data, np.uint8)
                    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                    
                    # Decodificar códigos de barras o QR
                    codigos = pyzbar.decode(img)
                    if codigos:
                        serie_detectada = codigos[0].data.decode('utf-8').strip()
                        st.success(f"✅ ¡Código detectado con éxito: **{serie_detectada}**!")
                    else:
                        st.warning("⚠️ No se detectó ningún código de barras legible en la foto. Intenta de nuevo con mejor iluminación.")
                except Exception as e:
                    st.error(f"Error al procesar la imagen: {e}")
    return serie_detectada

# Funciones de estilo de celdas
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
    elif val_lower == "Uso Interno":
        return 'background-color: #dbeafe; color: #1e40af; font-weight: bold;'
    return ''

def colorear_dias(val):
    try:
        if float(val) > 40:
            return 'background-color: #fee2e2; color: #991b1b; font-weight: bold;'
    except (ValueError, TypeError):
        pass
    return ''

# Cargar inventario actual
df_inv = cargar_datos()

# --- BARRA LATERAL PERSONALIZADA ---
st.sidebar.markdown("<h2 style='color: white; text-align: center;'>❄️ Bepensa</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='text-align: center; color: white;'><b>Control de Refrigeradores</b></p>", unsafe_allow_html=True)
st.sidebar.markdown("---")

menu = st.sidebar.selectbox(
    "Menú de Navegación",
    [
        "📊 Inventario General", 
        "📈 Estadía", 
        "📦 Equipos Disponibles", 
        "📥 Registrar Entrada", 
        "📤 Salida de Equipos", 
        "✏️ Editar / Eliminar", 
        "📜 Historial de Movimientos", 
        "💾 Exportar a Excel"
    ]
)

# Encabezado principal
col_titulo, col_logo = st.columns([4, 1])
with col_titulo:
    st.markdown("<h1 style='color: #E60012; margin-top: 0;'>❄️ Control de Inventarios de Refrigeradores</h1>", unsafe_allow_html=True)
with col_logo:
    if os.path.exists("Logo_Bepensa.png"):
        st.image("Logo_Bepensa.png", width=160)
    else:
        st.warning("⚠️ No se encontró 'Logo_Bepensa.png' en la carpeta.")

st.markdown("---")

# 1. INVENTARIO GENERAL Y BUSCADOR (CON OPCIÓN DE CÁMARA)
if menu == "📊 Inventario General":
    st.subheader("📋 Inventario Actual de Equipos")
    
    df_con_dias = calcular_dias_sin_movimiento(df_inv)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    total_eq = len(df_inv)
    en_taller = len(df_inv[df_inv['Ubicación'] == 'En taller']) if not df_inv.empty else 0
    para_reparar = len(df_inv[(df_inv['Estatus'] == 'Para Reparar') & (df_inv['Ubicación'] != 'En taller')]) if not df_inv.empty else 0
    nuevos = len(df_inv[df_inv['Estatus'] == 'Nuevo']) if not df_inv.empty else 0
    reparados = len(df_inv[df_inv['Estatus'] == 'Reparado']) if not df_inv.empty else 0

    with col1:
        st.markdown(f"""
            <div class="kpi-card-1">
                <span style="font-size: 14px; color: #1e3a8a; font-weight: bold;">Total de Equipos</span><br>
                <span style="font-size: 26px; font-weight: bold; color: #1e3a8a;">{total_eq}</span>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div class="kpi-card-2">
                <span style="font-size: 14px; color: #9a3412; font-weight: bold;">En Taller</span><br>
                <span style="font-size: 26px; font-weight: bold; color: #9a3412;">{en_taller}</span>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
            <div class="kpi-card-3">
                <span style="font-size: 14px; color: #991b1b; font-weight: bold;">Para Reparar</span><br>
                <span style="font-size: 26px; font-weight: bold; color: #991b1b;">{para_reparar}</span>
            </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
            <div class="kpi-card-4">
                <span style="font-size: 14px; color: #065f46; font-weight: bold;">Nuevos</span><br>
                <span style="font-size: 26px; font-weight: bold; color: #065f46;">{nuevos}</span>
            </div>
        """, unsafe_allow_html=True)
    with col5:
        st.markdown(f"""
            <div class="kpi-card-5">
                <span style="font-size: 14px; color: #6b21a8; font-weight: bold;">Reparados</span><br>
                <span style="font-size: 26px; font-weight: bold; color: #6b21a8;">{reparados}</span>
            </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Opcional de escáner para el buscador general
    serie_scandeada_gen = escanear_codigo_barras("buscador_general")
    default_busqueda = serie_scandeada_gen if serie_scandeada_gen else ""
    
    busqueda = st.text_input("🔍 Buscar por número de serie o modelo:", value=default_busqueda).strip()
    
    if busqueda:
        df_filtrado = df_con_dias[
            df_con_dias['Serie'].str.contains(busqueda, case=False, na=False) | 
            df_con_dias['Modelo'].str.contains(busqueda, case=False, na=False)
        ]
    else:
        df_filtrado = df_con_dias
        
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        cant_trad_hot = len(df_filtrado[
            df_filtrado['Canal'].isin(['Tradicional', 'Hoteles']) & 
            (~df_filtrado['Ubicación'].isin(['Uso Interno', 'En taller', 'En proceso de Baja']))
        ]) if not df_filtrado.empty else 0
        st.metric(label="Canal Tradicional", value=cant_trad_hot)
    with col_c2:
        cant_moderno = len(df_filtrado[df_filtrado['Canal'] == 'Moderno']) if not df_filtrado.empty else 0
        st.metric(label="Canal Moderno", value=cant_moderno)
        
    st.markdown("<br>", unsafe_allow_html=True)

    columnas_visibles = ["Serie", "Modelo", "Canal", "Ubicación", "Estatus", "Días sin movimiento", "Ultimo_Movimiento"]
    df_filtrado = df_filtrado[[col for col in columnas_visibles if col in df_filtrado.columns]]
    
    if not df_filtrado.empty:
        df_mostrar = df_filtrado.copy()
        if 'Ultimo_Movimiento' in df_mostrar.columns:
            df_mostrar['Ultimo_Movimiento'] = pd.to_datetime(df_mostrar['Ultimo_Movimiento'], errors='coerce').dt.strftime('%Y-%m-%d').fillna(df_mostrar['Ultimo_Movimiento'])

        df_estilizado = df_mostrar.style.map(colorear_ubicaciones, subset=['Ubicación'])
        if 'Días sin movimiento' in df_mostrar.columns:
            df_estilizado = df_estilizado.map(colorear_dias, subset=['Días sin movimiento'])
        st.dataframe(df_estilizado, use_container_width=True)
    else:
        st.dataframe(df_filtrado, use_container_width=True)

# 2. ESTADÍA
elif menu == "📈 Estadía":
    st.subheader("📈 Promedio de Días en Estadía por Canal")
    st.markdown("Análisis del promedio de días sin movimiento agrupados por ubicación, divididos por canal de operación.")
    st.markdown("---")
    
    df_con_dias = calcular_dias_sin_movimiento(df_inv)
    
    if not df_con_dias.empty:
        df_con_dias['Días sin movimiento'] = pd.to_numeric(df_con_dias['Días sin movimiento'], errors='coerce')
        
        st.markdown("### 🏬 Canal Tradicional")
        df_trad = df_con_dias[
            (df_con_dias['Canal'] == 'Tradicional') & 
            (~df_con_dias['Ubicación'].isin(['Uso Interno', 'En proceso de Baja']))
        ].copy()
        
        if not df_trad.empty:
            df_prom_trad = df_trad.groupby('Ubicación')['Días sin movimiento'].mean().reset_index()
            df_prom_trad.columns = ['Ubicación', 'Promedio de Días']
            
            fig_t, ax_t = plt.subplots(figsize=(10, 4.5))
            colores_t = ['#E60012' if x > 40 else '#2563eb' for x in df_prom_trad['Promedio de Días']]
            bars_t = ax_t.bar(df_prom_trad['Ubicación'], df_prom_trad['Promedio de Días'], color=colores_t, width=0.55, edgecolor='black', linewidth=0.8)
            ax_t.axhline(40, color='#dc2626', linestyle='--', linewidth=1.5, label='Límite de Alerta (40 días)')
            
            for bar in bars_t:
                yval = bar.get_height()
                alerta_txt = f" ⚠️ ({yval:.1f}d)" if yval > 40 else f" ({yval:.1f}d)"
                ax_t.text(bar.get_x() + bar.get_width()/2.0, yval + 1, alerta_txt, ha='center', va='bottom', fontsize=9, fontweight='bold', color='#111827')

            ax_t.set_ylabel('Promedio de Días', fontsize=10, fontweight='bold')
            ax_t.set_xlabel('Ubicación', fontsize=10, fontweight='bold')
            ax_t.set_title('Estadía Promedio - Canal Tradicional', fontsize=12, fontweight='bold', pad=12)
            plt.xticks(rotation=15, ha='right')
            ax_t.grid(axis='y', linestyle=':', alpha=0.6)
            ax_t.legend(loc='upper right')
            st.pyplot(fig_t)
            
            df_t_tabla = df_prom_trad.copy()
            df_t_tabla['Estado de Alerta'] = df_t_tabla['Promedio de Días'].apply(lambda x: "🚨 Alerta: Supera los 40 días" if x > 40 else "✅ Normal")
            df_t_tabla['Promedio de Días'] = df_t_tabla['Promedio de Días'].round(1)
            st.dataframe(df_t_tabla, use_container_width=True)
        else:
            st.info("ℹ️ No hay equipos registrados para el Canal Tradicional.")
            
        st.markdown("<br><hr><br>", unsafe_allow_html=True)
        
        st.markdown("### 🛒 Canal Moderno")
        df_mod = df_con_dias[
            (df_con_dias['Canal'] == 'Moderno') & 
            (~df_con_dias['Ubicación'].isin(['Uso Interno', 'En proceso de Baja']))
        ].copy()
        
        if not df_mod.empty:
            df_prom_mod = df_mod.groupby('Ubicación')['Días sin movimiento'].mean().reset_index()
            df_prom_mod.columns = ['Ubicación', 'Promedio de Días']
            
            fig_m, ax_m = plt.subplots(figsize=(10, 4.5))
            colores_m = ['#E60012' if x > 40 else '#10b981' for x in df_prom_mod['Promedio de Días']]
            bars_m = ax_m.bar(df_prom_mod['Ubicación'], df_prom_mod['Promedio de Días'], color=colores_m, width=0.55, edgecolor='black', linewidth=0.8)
            ax_m.axhline(40, color='#dc2626', linestyle='--', linewidth=1.5, label='Límite de Alerta (40 días)')
            
            for bar in bars_m:
                yval = bar.get_height()
                alerta_txt = f" ⚠️ ({yval:.1f}d)" if yval > 40 else f" ({yval:.1f}d)"
                ax_m.text(bar.get_x() + bar.get_width()/2.0, yval + 1, alerta_txt, ha='center', va='bottom', fontsize=9, fontweight='bold', color='#111827')

            ax_m.set_ylabel('Promedio de Días', fontsize=10, fontweight='bold')
            ax_m.set_xlabel('Ubicación', fontsize=10, fontweight='bold')
            ax_m.set_title('Estadía Promedio - Canal Moderno', fontsize=12, fontweight='bold', pad=12)
            plt.xticks(rotation=15, ha='right')
            ax_m.grid(axis='y', linestyle=':', alpha=0.6)
            ax_m.legend(loc='upper right')
            st.pyplot(fig_m)
            
            df_m_tabla = df_prom_mod.copy()
            df_m_tabla['Estado de Alerta'] = df_m_tabla['Promedio de Días'].apply(lambda x: "🚨 Alerta: Supera los 40 días" if x > 40 else "✅ Normal")
            df_m_tabla['Promedio de Días'] = df_m_tabla['Promedio de Días'].round(1)
            st.dataframe(df_m_tabla, use_container_width=True)
        else:
            st.info("ℹ️ No hay equipos registrados para el Canal Moderno.")
    else:
        st.info("ℹ️ No hay datos suficientes en el inventario.")

# 3. EQUIPOS DISPONIBLES
elif menu == "📦 Equipos Disponibles":
    st.subheader("📦 Reporte de Equipos Disponibles")
    st.markdown("Equipos listos para distribución por canal.")
    st.markdown("---")
    
    if not df_inv.empty:
        condicion_disponibles = (
            (df_inv['Ubicación'].isin(["En almacén de Comodatos", "En almacén de Publicidad"])) |
            ((df_inv['Ubicación'] == "En patios") & (df_inv['Estatus'] == "Reparado"))
        )
        df_disp = df_inv[condicion_disponibles].copy()
        
        st.markdown("### 🏬 Canal Tradicional")
        df_trad_disp = df_disp[df_disp['Canal'] == 'Tradicional']
        if not df_trad_disp.empty:
            st.dataframe(df_trad_disp.groupby(['Modelo', 'Estatus']).size().reset_index(name='Cantidad Disponible'), use_container_width=True)
        else:
            st.info("ℹ️ No hay equipos disponibles para el Canal Tradicional.")
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown("### 🛒 Canal Moderno")
        df_mod_disp = df_disp[df_disp['Canal'] == 'Moderno']
        if not df_mod_disp.empty:
            st.dataframe(df_mod_disp.groupby(['Modelo', 'Estatus']).size().reset_index(name='Cantidad Disponible'), use_container_width=True)
        else:
            st.info("ℹ️ No hay equipos disponibles para el Canal Moderno.")
    else:
        st.info("ℹ️ El inventario se encuentra vacío actualmente.")

# 4. REGISTRAR ENTRADA (CON ESCÁNER DE CÁMARA)
elif menu == "📥 Registrar Entrada":
    st.subheader("📥 Registrar Entrada de Nuevo Equipo")
    
    # Escáner de cámara para entrada
    serie_scandeada_ent = escanear_codigo_barras("registrar_entrada")
    default_serie = serie_scandeada_ent if serie_scandeada_ent else ""
    
    with st.form("form_entrada", clear_on_submit=True):
        serie = st.text_input("🏷️ Número de Serie (Escribe o escanea arriba):", value=default_serie).strip()
        modelo = st.text_input("🧊 Modelo del Refrigerador:").strip()
        canal = st.selectbox("🏬 Canal:", CANALES)
        ubicacion = st.selectbox("📍 Ubicación inicial", UBICACIONES)
        estatus = st.selectbox("⚡ Estatus inicial", ESTATUS)
        fecha_entrada = st.date_input("📅 Fecha de entrada / Último movimiento", value=date.today())
        
        submit = st.form_submit_button("Registrar Entrada en Sistema")
        
        if submit:
            if not serie or not modelo:
                st.error("⚠️ Por favor, completa la serie y el modelo.")
            elif not df_inv.empty and serie in df_inv['Serie'].values:
                st.error(f"❌ ¡El equipo con serie '{serie}' ya se encuentra registrado en el inventario!")
            else:
                fecha_str = fecha_entrada.strftime("%Y-%m-%d")
                nueva_fila = pd.DataFrame([{
                    "Serie": serie,
                    "Modelo": modelo,
                    "Canal": canal,
                    "Ubicación": ubicacion,
                    "Estatus": estatus,
                    "Ultimo_Movimiento": fecha_str
                }])
                df_inv = pd.concat([df_inv, nueva_fila], ignore_index=True)
                guardar_datos(df_inv)
                registrar_historial(serie, modelo, "ENTRADA", f"Canal: {canal} | Ubicación: {ubicacion} | Estatus: {estatus} | Fecha: {fecha_str}")
                st.success("¡Se ha generado un nuevo registro en el inventario!")

# 5. SALIDA DE EQUIPOS (CON ESCÁNER DE CÁMARA)
elif menu == "📤 Salida de Equipos":
    st.subheader("📤 Salida de Equipos del Inventario")
    
    # Escáner de cámara para salida
    serie_scandeada_sal = escanear_codigo_barras("salida_equipos")
    default_salida = serie_scandeada_sal if serie_scandeada_sal else ""
    
    serie_buscar = st.text_input("🔍 Escribe o escanea la serie del equipo para dar salida:", value=default_salida).strip()
    
    if serie_buscar:
        equipo = df_inv[df_inv['Serie'] == serie_buscar]
        if equipo.empty:
            st.warning("⚠️ No se encontró ningún equipo con esa serie en el inventario.")
        else:
            modelo_actual_eq = str(equipo.iloc[0]['Modelo'])
            canal_actual_eq = str(equipo.iloc[0]['Canal'])
            ubicacion_actual_eq = str(equipo.iloc[0]['Ubicación'])
            estatus_actual_eq = str(equipo.iloc[0]['Estatus'])
            
            st.info(f"📌 Equipo encontrado -> Modelo: **{modelo_actual_eq}** | Canal: **{canal_actual_eq}** | Ubicación: **{ubicacion_actual_eq}** | Estatus: **{estatus_actual_eq}**")
            
            with st.form("form_salida"):
                fecha_salida = st.date_input("📅 Fecha de salida", value=date.today())
                motivo_salida = st.text_input("📝 Motivo de la salida / Destino (Opcional):")
                
                btn_confirmar_salida = st.form_submit_button("Confirmar salida")
                
                if btn_confirmar_salida:
                    idx = df_inv[df_inv['Serie'] == serie_buscar].index[0]
                    fecha_str = fecha_salida.strftime("%Y-%m-%d")
                    
                    registrar_historial(
                        serie_buscar, 
                        modelo_actual_eq, 
                        "SALIDA", 
                        f"Canal: {canal_actual_eq} | Ubicación anterior: {ubicacion_actual_eq} | Estatus anterior: {estatus_actual_eq} | Fecha Salida: {fecha_str}. Motivo: {motivo_salida}"
                    )
                    
                    df_inv = df_inv.drop(idx).reset_index(drop=True)
                    guardar_datos(df_inv)
                    st.success(f"✅ ¡Salida confirmada! El equipo con serie {serie_buscar} ha sido eliminado del inventario general.")

# 6. EDITAR / ELIMINAR EQUIPO
elif menu == "✏️ Editar / Eliminar":
    st.subheader("✏️ Gestión, Corrección y Depuración de Equipos")
    
    serie_scandeada_edit = escanear_codigo_barras("editar_equipo")
    default_edit = serie_scandeada_edit if serie_scandeada_edit else ""
    
    serie_edit = st.text_input("🔍 Ingrese o escanee la serie del equipo a editar o eliminar:", value=default_edit).strip()
    
    if serie_edit:
        equipo = df_inv[df_inv['Serie'] == serie_edit]
        if equipo.empty:
            st.warning("⚠️ No se encontró el equipo en la base de datos.")
        else:
            idx = df_inv[df_inv['Serie'] == serie_edit].index[0]
            
            with st.form("form_editar"):
                mod_modelo = st.text_input("🧊 Modelo", value=str(df_inv.loc[idx, 'Modelo']))
                
                canal_actual = str(df_inv.loc[idx, 'Canal'])
                idx_canal = CANALES.index(canal_actual) if canal_actual in CANALES else 0
                mod_canal = st.selectbox("🏬 Canal", CANALES, index=idx_canal)
                
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
                    df_inv.loc[idx, 'Canal'] = mod_canal
                    df_inv.loc[idx, 'Ubicación'] = mod_ubicacion
                    df_inv.loc[idx, 'Estatus'] = mod_estatus
                    df_inv.loc[idx, 'Ultimo_Movimiento'] = mod_fecha.strftime("%Y-%m-%d")
                        
                    guardar_datos(df_inv)
                    registrar_historial(serie_edit, mod_modelo, "EDICIÓN", f"Datos modificados. Canal: {mod_canal} | Fecha Movimiento: {mod_fecha.strftime('%Y-%m-%d')}")
                    st.success("✅ ¡Datos aktualizados con éxito!")
                
                if btn_eliminar:
                    modelo_eliminado = df_inv.loc[idx, 'Modelo']
                    df_inv = df_inv.drop(idx).reset_index(drop=True)
                    guardar_datos(df_inv)
                    registrar_historial(serie_edit, modelo_eliminado, "ELIMINACIÓN", "Equipo eliminado del inventario.")
                    st.success("🗑️ ¡Equipo eliminado permanentemente del sistema!")

# 7. HISTORIAL DE MOVIMIENTOS
elif menu == "📜 Historial de Movimientos":
    st.subheader("📜 Bitácora de Entradas, Salidas y Cambios de Ubicación")
    df_h = cargar_historial()
    if df_h.empty:
        st.info("ℹ️ Aún no hay movimientos registrados en la bitácora.")
    else:
        st.dataframe(df_h.sort_values(by="Fecha_Hora", ascending=False), use_container_width=True)

# 8. EXPORTAR A EXCEL
elif menu == "💾 Exportar a Excel":
    st.subheader("💾 Exportar Base de Datos a Formato Excel")
    st.markdown("Genera un archivo completo con el inventario actual y la bitácora de movimientos.")
    
    if st.button("📥 Generar Archivo Excel"):
        output_file = "Reporte_Inventario_Refrigeradores_Bepensa.xlsx"
        df_export = calcular_dias_sin_movimiento(df_inv)
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df_export.to_excel(writer, sheet_name='Inventario Actual', index=False)
            df_h = cargar_historial()
            df_h.to_excel(writer, sheet_name='Historial Movimientos', index=False)
            
        with open(output_file, "rb") as f:
            st.download_button(
                label="📥 Click Aquí para Descargar el Archivo",
                data=f,
                file_name=output_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        st.success("✅ ¡Archivo Excel generado correctamente!")