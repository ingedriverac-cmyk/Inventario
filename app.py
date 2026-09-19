import sys
import asyncio

# Solución para compatibilidad de red en Windows con Python moderno
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import streamlit as st
import pandas as pd
from datetime import datetime, date
import os

# Configuración de la página y diseño estético
st.set_page_config(
    page_title="Control de Inventario - Bepensa / Coca-Cola",
    page_icon="🥤",
    layout="wide"
)

# Estilos CSS personalizados con la paleta corporativa y colores de fondo
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 5px solid #E60012;
        text-align: center;
    }
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

# Archivos CSV para persistencia de datos
INVENTARIO_FILE = "inventario_refrigeradores.csv"
HISTORIAL_FILE = "historial_movimientos.csv"

# Opciones fijas de Canales (incluyendo AP20L)
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

# Funciones para cargar y guardar datos
def cargar_datos():
    if os.path.exists(INVENTARIO_FILE):
        df = pd.read_csv(INVENTARIO_FILE, dtype=str)
        if "Ultimo_Movimiento" not in df.columns:
            df["Ultimo_Movimiento"] = df.get("Fecha_Registro", datetime.now().strftime("%Y-%m-%d"))
        else:
            # Limpiar por si quedó algún registro anterior con hora
            df["Ultimo_Movimiento"] = df["Ultimo_Movimiento"].astype(str).str.split().str[0]
        if "Canal" not in df.columns:
            df["Canal"] = "Tradicional"  # Valor por defecto si el archivo anterior no lo tenía
        return df
    else:
        return pd.DataFrame(columns=["Serie", "Modelo", "Canal", "Ubicación", "Estatus", "Fecha_Registro", "Ultimo_Movimiento"])

def cargar_historial():
    if os.path.exists(HISTORIAL_FILE):
        return pd.read_csv(HISTORIAL_FILE, dtype=str)
    else:
        return pd.DataFrame(columns=["Fecha_Hora", "Serie", "Modelo", "Tipo_Movimiento", "Detalles"])

def guardar_datos(df):
    df.to_csv(INVENTARIO_FILE, index=False)

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

# Función para calcular los días sin movimiento (usando formato de fecha pura YYYY-MM-DD)
def calcular_dias_sin_movimiento(df):
    if df.empty:
        return df
    
    df_calc = df.copy()
    fecha_actual = datetime.now().date()
    
    dias_lista = []
    for fecha_str in df_calc['Ultimo_Movimiento']:
        try:
            # Intentar parsear como fecha pura
            f_mov = datetime.strptime(str(fecha_str).split()[0], "%Y-%m-%d").date()
        except ValueError:
            f_mov = fecha_actual
                
        dias = (fecha_actual - f_mov).days
        dias_lista.append(max(0, dias))
        
    df_calc['Días sin movimiento'] = dias_lista
    return df_calc

# Función para colorear la columna de Ubicación según tus reglas
def colorear_ubicaciones(val):
    val_lower = str(val).strip()
    if val_lower in ["En almacén de Comodatos", "En almacén de Publicidad"]:
        return 'background-color: #d1fae5; color: #065f46; font-weight: bold;'  # Verde suave
    elif val_lower == "En patios":
        return 'background-color: #fef3c7; color: #92400e; font-weight: bold;'  # Amarillo suave
    elif val_lower == "En proceso de Baja":
        return 'background-color: #fee2e2; color: #991b1b; font-weight: bold;'  # Rojo suave
    elif val_lower == "En taller":
        return 'background-color: #ffedd5; color: #9a3412; font-weight: bold;'  # Naranja suave
    elif val_lower == "Uso Interno":
        return 'background-color: #dbeafe; color: #1e40af; font-weight: bold;'  # Azul suave
    return ''

# Función para colorear los días sin movimiento si pasan de 40
def colorear_dias(val):
    try:
        if float(val) > 40:
            return 'background-color: #fee2e2; color: #991b1b; font-weight: bold;' # Rojo suave
    except (ValueError, TypeError):
        pass
    return ''

# Cargar inventario actual
df_inv = cargar_datos()

# --- BARRA LATERAL PERSONALIZADA ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3067/3067403.png", width=110)
st.sidebar.title("🥤 Control Bepensa")
st.sidebar.markdown("**Gestión de Refrigeradores**")
st.sidebar.markdown("---")

menu = st.sidebar.selectbox(
    "Menú de Navegación",
    [
        "📊 Inventario General", 
        "📈 Estadía", 
        "📥 Registrar Entrada", 
        "🔄 Actualizar / Salida", 
        "✏️ Editar / Eliminar", 
        "📜 Historial de Movimientos", 
        "💾 Exportar a Excel"
    ]
)

# Encabezado principal
st.markdown("<h1 style='color: #E60012;'>🥤 Control de Inventarios de Refrigeradores - Bepensa</h1>", unsafe_allow_html=True)
st.markdown("---")

# 1. INVENTARIO GENERAL Y BUSCADOR
if menu == "📊 Inventario General":
    st.subheader("📋 Inventario Actual de Equipos")
    
    df_con_dias = calcular_dias_sin_movimiento(df_inv)
    
    # Tarjetas de resumen rápido (KPIs)
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric(label="Total de Equipos", value=len(df_inv))
    with col2:
        en_taller = len(df_inv[df_inv['Ubicación'] == 'En taller']) if not df_inv.empty else 0
        st.metric(label="En Taller", value=en_taller)
    with col3:
        para_reparar = len(df_inv[(df_inv['Estatus'] == 'Para Reparar') & (df_inv['Ubicación'] != 'En taller')]) if not df_inv.empty else 0
        st.metric(label="Para Reparar", value=para_reparar)
    with col4:
        nuevos = len(df_inv[df_inv['Estatus'] == 'Nuevo']) if not df_inv.empty else 0
        st.metric(label="Nuevos", value=nuevos)
    with col5:
        reparados = len(df_inv[df_inv['Estatus'] == 'Reparado']) if not df_inv.empty else 0
        st.metric(label="Reparados", value=reparados)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Buscador rápido por serie o modelo
    busqueda = st.text_input("🔍 Buscar por número de serie o modelo:").strip()
    
    if busqueda:
        df_filtrado = df_con_dias[
            df_con_dias['Serie'].str.contains(busqueda, case=False, na=False) | 
            df_con_dias['Modelo'].str.contains(busqueda, case=False, na=False)
        ]
    else:
        df_filtrado = df_con_dias
        
    # Mostrar tarjetas de conteo por canal filtrado
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

    # Reordenar columnas para la visualización en la app
    columnas_visibles = ["Serie", "Modelo", "Canal", "Ubicación", "Estatus", "Días sin movimiento", "Ultimo_Movimiento"]
    df_filtrado = df_filtrado[[col for col in columnas_visibles if col in df_filtrado.columns]]
    
    # Aplicar estilos de color a la tabla en las columnas correspondientes
    if not df_filtrado.empty:
        df_estilizado = df_filtrado.style.map(colorear_ubicaciones, subset=['Ubicación'])
        if 'Días sin movimiento' in df_filtrado.columns:
            df_estilizado = df_estilizado.map(colorear_dias, subset=['Días sin movimiento'])
        st.dataframe(df_estilizado, use_container_width=True)
    else:
        st.dataframe(df_filtrado, use_container_width=True)

# 2. ESTADÍA (GRÁFICA EXCLUSIVA)
elif menu == "📈 Estadía":
    st.subheader("📈 Promedio de Días en Estadía - Canal Tradicional")
    st.markdown("Gráfica analítica que muestra el promedio de días sin movimiento de los equipos pertenecientes al **Canal Tradicional**, excluyendo aquellos en *Uso Interno* o *En proceso de Baja*, agrupados por su ubicación actual.")
    st.markdown("---")
    
    df_con_dias = calcular_dias_sin_movimiento(df_inv)
    
    if not df_con_dias.empty:
        # Filtrar solo Canal Tradicional, excluyendo Uso Interno y En proceso de Baja
        df_trad = df_con_dias[
            (df_con_dias['Canal'] == 'Tradicional') & 
            (~df_con_dias['Ubicación'].isin(['Uso Interno', 'En proceso de Baja']))
        ].copy()
        
        if not df_trad.empty:
            # Asegurar tipo numérico para la columna de días
            df_trad['Días sin movimiento'] = pd.to_numeric(df_trad['Días sin movimiento'], errors='coerce')
            
            # Calcular el promedio por ubicación
            df_promedio = df_trad.groupby('Ubicación')['Días sin movimiento'].mean().reset_index()
            df_promedio.columns = ['Ubicación', 'Promedio de Días']
            df_promedio = df_promedio.set_index('Ubicación')
            
            # Mostrar gráfica de barras interactiva en Streamlit
            st.bar_chart(df_promedio)
        else:
            st.info("ℹ️ No hay equipos registrados que cumplan con los filtros de Canal Tradicional (sin Uso Interno ni En proceso de Baja).")
    else:
        st.info("ℹ️ No hay datos suficientes en el inventario para generar la gráfica.")

# 3. REGISTRAR ENTRADA
elif menu == "📥 Registrar Entrada":
    st.subheader("📥 Registrar Entrada de Nuevo Equipo")
    
    with st.form("form_entrada", clear_on_submit=True):
        serie = st.text_input("🏷️ Número de Serie (Escanee o escriba):").strip()
        modelo = st.text_input("🧊 Modelo del Refrigerador:").strip()
        canal = st.selectbox("🏬 Canal:", CANALES)
        ubicacion = st.selectbox("📍 Ubicación inicial", UBICACIONES)
        estatus = st.selectbox("⚡ Estatus inicial", ESTATUS)
        fecha_entrada = st.date_input("📅 Fecha real de entrada al inventario", value=date.today())
        
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
                    "Fecha_Registro": fecha_str,
                    "Ultimo_Movimiento": fecha_str
                }])
                df_inv = pd.concat([df_inv, nueva_fila], ignore_index=True)
                guardar_datos(df_inv)
                registrar_historial(serie, modelo, "ENTRADA", f"Canal: {canal} | Ubicación: {ubicacion} | Estatus: {estatus} | Fecha: {fecha_str}")
                st.success(f"✅ ¡Equipo con serie {serie} registrado exitosamente!")

# 4. ACTUALIZAR / CAMBIAR MODELO, CANAL, UBICACIÓN Y ESTATUS (SALIDAS)
elif menu == "🔄 Actualizar / Salida":
    st.subheader("🔄 Actualizar Modelo, Canal, Ubicación o Estatus (Salidas / Movimientos)")
    
    serie_buscar = st.text_input("🔍 Escanee o escriba la serie del equipo a actualizar:").strip()
    
    if serie_buscar:
        equipo = df_inv[df_inv['Serie'] == serie_buscar]
        if equipo.empty:
            st.warning("⚠️ No se encontró ningún equipo con esa serie.")
        else:
            modelo_actual_eq = str(equipo.values[0][1])
            canal_actual_eq = str(equipo.values[0][2])
            ubicacion_actual_eq = str(equipo.values[0][3])
            estatus_actual_eq = str(equipo.values[0][4])
            
            st.info(f"📌 Equipo encontrado -> Modelo actual: **{modelo_actual_eq}** | Canal actual: **{canal_actual_eq}** | Ubicación actual: **{ubicacion_actual_eq}**")
            
            with st.form("form_actualizar"):
                nuevo_modelo = st.text_input("🧊 Modelo del Refrigerador", value=modelo_actual_eq).strip()
                
                idx_canal = CANALES.index(canal_actual_eq) if canal_actual_eq in CANALES else 0
                nuevo_canal = st.selectbox("🏬 Nuevo Canal", CANALES, index=idx_canal)
                
                idx_ub = UBICACIONES.index(ubicacion_actual_eq) if ubicacion_actual_eq in UBICACIONES else 0
                nueva_ubicacion = st.selectbox("📍 Nueva Ubicación", UBICACIONES, index=idx_ub)
                
                idx_est = ESTATUS.index(estatus_actual_eq) if estatus_actual_eq in ESTATUS else 0
                nuevo_estatus = st.selectbox("⚡ Nuevo Estatus", ESTATUS, index=idx_est)
                
                fecha_movimiento = st.date_input("📅 Fecha en que ocurrió este movimiento", value=date.today())
                
                motivo = st.text_input("📝 Motivo del movimiento / Actualización (Opcional):")
                
                btn_actualizar = st.form_submit_button("Guardar Cambios y Actualizar")
                
                if btn_actualizar:
                    if not nuevo_modelo:
                        st.error("⚠️ El campo de modelo no puede estar vacío.")
                    else:
                        idx = df_inv[df_inv['Serie'] == serie_buscar].index[0]
                        modelo_anterior = df_inv.loc[idx, 'Modelo']
                        ubicacion_anterior = df_inv.loc[idx, 'Ubicación']
                        canal_anterior = df_inv.loc[idx, 'Canal']
                        
                        fecha_str = fecha_movimiento.strftime("%Y-%m-%d")
                        
                        df_inv.loc[idx, 'Modelo'] = nuevo_modelo
                        df_inv.loc[idx, 'Canal'] = nuevo_canal
                        df_inv.loc[idx, 'Ubicación'] = nueva_ubicacion
                        df_inv.loc[idx, 'Estatus'] = nuevo_estatus
                        
                        # Actualizar Ultimo_Movimiento con la fecha proporcionada
                        df_inv.loc[idx, 'Ultimo_Movimiento'] = fecha_str
                            
                        guardar_datos(df_inv)
                        
                        registrar_historial(serie_buscar, nuevo_modelo, "ACTUALIZACIÓN/SALIDA", f"Modelo: {modelo_anterior} -> {nuevo_modelo} | Canal: {canal_anterior} -> {nuevo_canal} | Ubicación: {ubicacion_anterior} -> {nueva_ubicacion} | Fecha Mov: {fecha_str}. Motivo: {motivo}")
                        st.success("✅ ¡Información del equipo actualizada correctamente!")

# 5. EDITAR / ELIMINAR EQUIPO
elif menu == "✏️ Editar / Eliminar":
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
                
                canal_actual = str(df_inv.loc[idx, 'Canal'])
                idx_canal = CANALES.index(canal_actual) if canal_actual in CANALES else 0
                mod_canal = st.selectbox("🏬 Canal", CANALES, index=idx_canal)
                
                mod_ubicacion = st.selectbox("📍 Ubicación", UBICACIONES, index=UBICACIONES.index(df_inv.loc[idx, 'Ubicación']) if df_inv.loc[idx, 'Ubicación'] in UBICACIONES else 0)
                mod_estatus = st.selectbox("⚡ Estatus", ESTATUS, index=ESTATUS.index(df_inv.loc[idx, 'Estatus']) if df_inv.loc[idx, 'Estatus'] in ESTATUS else 0)
                
                col1, col2 = st.columns(2)
                with col1:
                    btn_guardar = st.form_submit_button("💾 Guardar Cambios")
                with col2:
                    btn_eliminar = st.form_submit_button("🗑️ Eliminar Equipo")
                
                if btn_guardar:
                    ubicacion_anterior = df_inv.loc[idx, 'Ubicación']
                    df_inv.loc[idx, 'Modelo'] = mod_modelo
                    df_inv.loc[idx, 'Canal'] = mod_canal
                    df_inv.loc[idx, 'Ubicación'] = mod_ubicacion
                    df_inv.loc[idx, 'Estatus'] = mod_estatus
                    
                    if ubicacion_anterior != mod_ubicacion:
                        df_inv.loc[idx, 'Ultimo_Movimiento'] = datetime.now().strftime("%Y-%m-%d")
                        
                    guardar_datos(df_inv)
                    registrar_historial(serie_edit, mod_modelo, "EDICIÓN", f"Datos modificados. Canal: {mod_canal}")
                    st.success("✅ ¡Datos actualizados con éxito!")
                
                if btn_eliminar:
                    modelo_eliminado = df_inv.loc[idx, 'Modelo']
                    df_inv = df_inv.drop(idx).reset_index(drop=True)
                    guardar_datos(df_inv)
                    registrar_historial(serie_edit, modelo_eliminado, "ELIMINACIÓN", "Equipo eliminado del inventario.")
                    st.success("🗑️ ¡Equipo eliminado permanentemente del sistema!")

# 6. HISTORIAL DE MOVIMIENTOS
elif menu == "📜 Historial de Movimientos":
    st.subheader("📜 Bitácora de Entradas, Salidas y Cambios de Ubicación")
    df_h = cargar_historial()
    if df_h.empty:
        st.info("ℹ️ Aún no hay movimientos registrados en la bitácora.")
    else:
        st.dataframe(df_h.sort_values(by="Fecha_Hora", ascending=False), use_container_width=True)

# 7. EXPORTAR A EXCEL
elif menu == "💾 Exportar a Excel":
    st.subheader("💾 Exportar Base de Datos a Formato Excel")
    st.markdown("Genera un archivo completo con el inventario actual (incluyendo el canal, los días sin movimiento) y la bitácora de movimientos en pestañas separadas.")
    
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