import streamlit as st
import requests
import pandas as pd
import altair as alt
import datetime
import time
from streamlit_autorefresh import st_autorefresh

# 1. Configuración de página de Streamlit para Videowall (sidebar colapsada por defecto, layout ancho)
st.set_page_config(
    page_title="MONITOR NACIONAL - Cortes de Luz Chile",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Definir orden geográfico de Norte a Sur oficial
REGIONS_NORTH_TO_SOUTH = [
    "Arica y Parinacota",
    "Tarapaca",
    "Antofagasta",
    "Atacama",
    "Coquimbo",
    "Valparaiso",
    "Metropolitana",
    "O`Higgins",  # Formato con backtick proveniente del backend
    "Maule",
    "Ñuble",
    "Biobio",
    "La Araucania",
    "Los Rios",
    "Los Lagos",
    "Aysén",
    "Magallanes"
]

def get_region_order(region_name):
    """Retorna el índice geográfico para ordenar de Norte a Sur."""
    name_clean = region_name.strip()
    for idx, reg in enumerate(REGIONS_NORTH_TO_SOUTH):
        if reg.lower() in name_clean.lower() or name_clean.lower() in reg.lower():
            return idx
    return len(REGIONS_NORTH_TO_SOUTH) # Elementos desconocidos al final

# 2. Inyección de Estilos CSS Especiales para VIDEOWALL (Estilo Institucional SENAPRED, fuentes grandes, alta legibilidad)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Share+Tech+Mono&display=swap');

/* Reset de tipografía global y fondo claro institucional */
html, body, [class*="css"], .stApp {
    font-family: 'Outfit', sans-serif;
    background-color: #F8F9FA !important;
    color: #212529 !important;
}

/* Banner institucional tipo SENAPRED */
.videowall-title-container {
    background-color: #002855 !important;
    padding: 20px 25px;
    border-radius: 8px;
    border-left: 8px solid #E85D04;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.08);
}
.videowall-title {
    font-family: 'Outfit', sans-serif;
    font-weight: 800;
    font-size: 2.6rem;
    line-height: 1.1;
    color: #FFFFFF !important;
    letter-spacing: -0.5px;
}
.videowall-subtitle {
    font-family: 'Share Tech Mono', monospace;
    font-size: 1.1rem;
    color: #FFB03A !important;
    letter-spacing: 1px;
    margin-top: 5px;
    font-weight: 600;
}

/* Indicador de estado y servidor */
.status-pill {
    display: inline-flex;
    align-items: center;
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    padding: 8px 16px;
    border-radius: 6px;
    margin-bottom: 25px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
}
.pulse-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-right: 12px;
    box-shadow: 0 0 0 0 rgba(0, 230, 118, 0.7);
    animation: pulse-anim 1.8s infinite;
}
@keyframes pulse-anim {
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 230, 118, 0.7); }
    70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(0, 230, 118, 0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 230, 118, 0); }
}
.pulse-text {
    font-family: 'Share Tech Mono', monospace;
    font-size: 1rem;
    color: #475569;
}

/* Tarjetas de Métricas Gigantes para Videowall */
[data-testid="metric-container"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    padding: 20px 18px !important;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.04) !important;
    transition: all 0.25s ease-in-out;
}
[data-testid="metric-container"]:hover {
    border-color: #002855 !important;
    box-shadow: 0 8px 20px rgba(0, 40, 85, 0.1) !important;
    transform: translateY(-2px);
}
[data-testid="stMetricLabel"] {
    font-family: 'Outfit', sans-serif !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    color: #475569 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 3.2rem !important;
    font-weight: 700 !important;
    color: #E85D04 !important; /* Naranja institucional para números críticos */
    letter-spacing: -1px;
}

/* Estilo para avisos y tablas */
.stAlert {
    border-radius: 12px !important;
    border-left-width: 6px !important;
}

/* Formatear el contenedor principal de los gráficos */
.chart-title {
    font-size: 1.35rem;
    font-weight: 700;
    color: #002855;
    border-bottom: 2px solid #002855;
    padding-bottom: 8px;
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)

# 3. Configuración de API y Headers obligatorios
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Content-Type': 'application/json; charset=utf-8',
    'Accept': 'application/json, text/plain, */*'
}

URLS_SERVER_TIME = [
    "https://apps.sec.cl/INTONLINEv1/ClientesAfectados/GetHoraServer",
    "https://www.sec.cl/interrupciones-en-linea/ClientesAfectados/GetHoraServer"
]
URLS_DATA = [
    "https://apps.sec.cl/INTONLINEv1/ClientesAfectados/GetPorFecha",
    "https://www.sec.cl/interrupciones-en-linea/ClientesAfectados/GetPorFecha"
]

@st.cache_data(ttl=60)
def get_sec_data():
    """Obtiene la hora oficial y descarga datos con fallback."""
    time_data = fetch_post_with_fallback(URLS_SERVER_TIME)
    
    if not isinstance(time_data, list) or len(time_data) == 0 or "FECHA" not in time_data[0]:
        raise ValueError("El servidor de la SEC retornó un formato de fecha no válido.")
        
    fecha_str = time_data[0]["FECHA"]
    
    try:
        date_part, time_part = fecha_str.strip().split(" ")
        dia, mes, anho = map(int, date_part.split("/"))
        hora = int(time_part.split(":")[0])
    except Exception as e:
        raise ValueError(f"Error procesando la fecha oficial '{fecha_str}': {e}")
        
    payload = {
        "anho": anho,
        "mes": mes,
        "dia": dia,
        "hora": hora
    }
    
    outage_data = fetch_post_with_fallback(URLS_DATA, json_payload=payload)
    if not isinstance(outage_data, list):
        raise ValueError("Datos devueltos por la SEC no válidos.")
        
    return outage_data, fecha_str

def fetch_post_with_fallback(urls, json_payload=None, encoding='cp1252'):
    last_error = None
    for url in urls:
        try:
            r = requests.post(url, headers=HEADERS, json=json_payload or {}, timeout=10)
            if r.status_code == 200:
                r.encoding = encoding
                return r.json()
            elif r.status_code == 404:
                continue
            else:
                r.raise_for_status()
        except Exception as e:
            last_error = e
            continue
    if last_error:
        raise last_error
    raise requests.RequestException("No se pudo obtener respuesta válida de la SEC.")

# 4. Sistema de Auto-refresco (Cada 5 minutos)
st_autorefresh(interval=300000, key="sec_videowall_autorefresh")

# 5. Inicializar session_state para caché persistente ante caídas de red
if 'cached_data' not in st.session_state:
    st.session_state.cached_data = None
if 'cached_time' not in st.session_state:
    st.session_state.cached_time = None

# Extracción de Datos
try:
    with st.spinner("Actualizando datos de alerta..."):
        outages_list, server_time_str = get_sec_data()
    st.session_state.cached_data = outages_list
    st.session_state.cached_time = server_time_str
    st.session_state.last_success = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    st.session_state.is_stale = False
except Exception as e:
    st.session_state.is_stale = True
    if st.session_state.cached_data is not None:
        st.sidebar.error(f"Error de actualización: {str(e)}")
        st.warning(
            f"⚠️ **FALLO DE CONEXIÓN SEC:** Mostrando datos persistentes del **{st.session_state.last_success}**."
        )
        outages_list = st.session_state.cached_data
        server_time_str = st.session_state.cached_time
    else:
        st.error(f"❌ **Error Crítico de Conexión SEC:** Sin datos anteriores en caché. Detalles: {str(e)}")
        st.button("🔄 Reintentar conexión")
        st.stop()

# Procesamiento de Datos
if outages_list:
    df = pd.DataFrame(outages_list)
    df['CLIENTES_AFECTADOS'] = pd.to_numeric(df['CLIENTES_AFECTADOS'], errors='coerce').fillna(0).astype(int)
    df['NOMBRE_REGION'] = df['NOMBRE_REGION'].str.strip()
    df['NOMBRE_COMUNA'] = df['NOMBRE_COMUNA'].str.strip()
    df['NOMBRE_EMPRESA'] = df['NOMBRE_EMPRESA'].str.strip()
    
    # 6. Encabezado estilo Centro de Control (Videowall)
    st.markdown(
        f"""
        <div class="videowall-title-container">
            <div class="videowall-title">UNIDAD NACIONAL DE ALERTA TEMPRANA</div>
            <div class="videowall-subtitle">SITUACIÓN SUMINISTRO ELÉCTRICO CHILE</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    pulse_color = "#FFC107" if st.session_state.is_stale else "#00E676"
    status_msg = "SISTEMA OPERATIVO | DATOS HISTÓRICOS EN CACHÉ" if st.session_state.is_stale else "EN VIVO | AUTO-REFRESCO ACTIVO (5 MIN)"
    st.markdown(
        f"""
        <div class="status-pill">
            <div class="pulse-dot" style="background-color: {pulse_color};"></div>
            <div class="pulse-text">{status_msg} &nbsp;|&nbsp; HORA SERVIDOR SEC: {server_time_str}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # 7. Sidebar de Control (Contraída por defecto para maximizar el Videowall)
    st.sidebar.markdown("## ⚙️ Controles de Filtros")
    if st.sidebar.button("🔄 Refrescar Forzado", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.sidebar.markdown("---")
    
    # Regiones ordenadas de Norte a Sur para el selector
    regiones_ordenadas = sorted(df['NOMBRE_REGION'].unique(), key=get_region_order)
    # Vista permanente de todo el país es el default
    selected_region = st.sidebar.selectbox(
        "📍 Región de Consulta:",
        options=["Todo el País"] + regiones_ordenadas,
        index=0
    )
    
    # Filtrar datos según selección de Región
    if selected_region == "Todo el País":
        df_view = df.copy()
    else:
        df_view = df[df['NOMBRE_REGION'] == selected_region]
        
    # Filtros avanzados en sidebar
    comunas_disponibles = sorted(df_view['NOMBRE_COMUNA'].unique())
    selected_comunas = st.sidebar.multiselect("🏢 Filtrar Comunas:", options=comunas_disponibles)
    empresas_disponibles = sorted(df_view['NOMBRE_EMPRESA'].unique())
    selected_empresas = st.sidebar.multiselect("⚡ Filtrar Distribuidoras:", options=empresas_disponibles)
    
    if selected_comunas:
        df_view = df_view[df_view['NOMBRE_COMUNA'].isin(selected_comunas)]
    if selected_empresas:
        df_view = df_view[df_view['NOMBRE_EMPRESA'].isin(selected_empresas)]

    # 8. Cálculo de Métricas Clave
    total_afectados = df_view['CLIENTES_AFECTADOS'].sum()
    comunas_con_cortes = df_view[df_view['CLIENTES_AFECTADOS'] > 0]['NOMBRE_COMUNA'].nunique()
    
    # Región / Empresa / Comuna más afectada
    if selected_region == "Todo el País":
        # Región más afectada
        reg_stats = df_view.groupby('NOMBRE_REGION')['CLIENTES_AFECTADOS'].sum().reset_index()
        if not reg_stats.empty and reg_stats['CLIENTES_AFECTADOS'].max() > 0:
            reg_top = reg_stats.loc[reg_stats['CLIENTES_AFECTADOS'].idxmax()]
            top_label_1 = "Región más Afectada"
            top_val_1 = f"{reg_top['NOMBRE_REGION']}"
        else:
            top_label_1 = "Región más Afectada"
            top_val_1 = "Ninguna"
    else:
        # Empresa más afectada (en la región seleccionada)
        emp_stats = df_view.groupby('NOMBRE_EMPRESA')['CLIENTES_AFECTADOS'].sum().reset_index()
        if not emp_stats.empty and emp_stats['CLIENTES_AFECTADOS'].max() > 0:
            emp_top = emp_stats.loc[emp_stats['CLIENTES_AFECTADOS'].idxmax()]
            top_label_1 = "Distribuidora más Afectada"
            top_val_1 = f"{emp_top['NOMBRE_EMPRESA']}"
        else:
            top_label_1 = "Distribuidora más Afectada"
            top_val_1 = "Ninguna"
            
    # Comuna más afectada
    com_stats = df_view.groupby(['NOMBRE_COMUNA', 'NOMBRE_REGION'])['CLIENTES_AFECTADOS'].sum().reset_index()
    if not com_stats.empty and com_stats['CLIENTES_AFECTADOS'].max() > 0:
        com_top = com_stats.loc[com_stats['CLIENTES_AFECTADOS'].idxmax()]
        top_val_2 = f"{com_top['NOMBRE_COMUNA']}"
    else:
        top_val_2 = "Ninguna"

    # Mostrar métricas gigantes en una fila de 4
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Clientes Afectados", value=f"{total_afectados:,}")
    with col2:
        st.metric(label="Comunas Afectadas", value=str(comunas_con_cortes))
    with col3:
        st.metric(label=top_label_1, value=top_val_1)
    with col4:
        st.metric(label="Punto Crítico (Comuna)", value=top_val_2)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 9. Panel de Gráficos de alta visibilidad (Altair con fuentes sobredimensionadas y colores claros)
    c1, c2 = st.columns([1, 1])
    
    with c1:
        if selected_region == "Todo el País":
            st.markdown('<div class="chart-title">📊 Cortes de Luz por Región (Geográfico de Norte a Sur)</div>', unsafe_allow_html=True)
            # Agrupar por región
            df_reg_group = df_view.groupby('NOMBRE_REGION')['CLIENTES_AFECTADOS'].sum().reset_index()
            # Asegurar que todas las regiones del país se muestren ordenadas de Norte a Sur
            # Rellenar con 0 si no hay cortes en alguna región
            all_regs_df = pd.DataFrame({"NOMBRE_REGION": REGIONS_NORTH_TO_SOUTH})
            df_reg_chart = pd.merge(all_regs_df, df_reg_group, on="NOMBRE_REGION", how="left").fillna(0)
            df_reg_chart['CLIENTES_AFECTADOS'] = df_reg_chart['CLIENTES_AFECTADOS'].astype(int)
            
            # Gráfico de barras horizontal ordenado geográficamente de Norte a Sur
            reg_chart = alt.Chart(df_reg_chart).mark_bar(
                color='#002855', # Azul institucional de SENAPRED
                cornerRadiusTopRight=4, 
                cornerRadiusBottomRight=4
            ).encode(
                x=alt.X('CLIENTES_AFECTADOS:Q', title='Clientes Afectados'),
                y=alt.Y('NOMBRE_REGION:N', sort=REGIONS_NORTH_TO_SOUTH, title='Región (Norte a Sur)'),
                tooltip=['NOMBRE_REGION', 'CLIENTES_AFECTADOS']
            ).properties(
                height=480
            ).configure_axis(
                labelFontSize=13,
                titleFontSize=14,
                labelColor='#212529',
                titleColor='#475569'
            ).configure_view(
                strokeWidth=0
            )
            st.altair_chart(reg_chart, use_container_width=True)
        else:
            st.markdown(f'<div class="chart-title">📊 Afectación Comunal en Región: {selected_region}</div>', unsafe_allow_html=True)
            df_com_group = df_view[df_view['CLIENTES_AFECTADOS'] > 0].groupby('NOMBRE_COMUNA')['CLIENTES_AFECTADOS'].sum().reset_index()
            df_com_group = df_com_group.sort_values(by='CLIENTES_AFECTADOS', ascending=False).head(15)
            
            if not df_com_group.empty:
                com_chart = alt.Chart(df_com_group).mark_bar(
                    color='#002855', # Azul institucional
                    cornerRadiusTopRight=4,
                    cornerRadiusBottomRight=4
                ).encode(
                    x=alt.X('CLIENTES_AFECTADOS:Q', title='Clientes Afectados'),
                    y=alt.Y('NOMBRE_COMUNA:N', sort='-x', title='Comuna'),
                    tooltip=['NOMBRE_COMUNA', 'CLIENTES_AFECTADOS']
                ).properties(
                    height=480
                ).configure_axis(
                    labelFontSize=13,
                    titleFontSize=14,
                    labelColor='#212529',
                    titleColor='#475569'
                )
                st.altair_chart(com_chart, use_container_width=True)
            else:
                st.info("Sin registros de clientes afectados en esta región.")
                
    with c2:
        st.markdown('<div class="chart-title">🔥 Top 10 Puntos de Crisis (Comunas con más Cortes)</div>', unsafe_allow_html=True)
        df_top_comunas = df_view[df_view['CLIENTES_AFECTADOS'] > 0].groupby(['NOMBRE_COMUNA', 'NOMBRE_REGION'])['CLIENTES_AFECTADOS'].sum().reset_index()
        df_top_comunas = df_top_comunas.sort_values(by='CLIENTES_AFECTADOS', ascending=False).head(10)
        
        if not df_top_comunas.empty:
            df_top_comunas['COMUNA_LABEL'] = df_top_comunas['NOMBRE_COMUNA'] + " (" + df_top_comunas['NOMBRE_REGION'] + ")"
            
            top_chart = alt.Chart(df_top_comunas).mark_bar(
                color='#E85D04', # Naranja de alerta para enfatizar crisis
                cornerRadiusTopRight=4,
                cornerRadiusBottomRight=4
            ).encode(
                x=alt.X('CLIENTES_AFECTADOS:Q', title='Clientes Afectados'),
                y=alt.Y('COMUNA_LABEL:N', sort='-x', title='Comuna (Región)'),
                tooltip=['NOMBRE_COMUNA', 'NOMBRE_REGION', 'CLIENTES_AFECTADOS']
            ).properties(
                height=480
            ).configure_axis(
                labelFontSize=13,
                titleFontSize=14,
                labelColor='#212529',
                titleColor='#475569'
            )
            st.altair_chart(top_chart, use_container_width=True)
        else:
            st.info("No se registran comunas con clientes sin suministro eléctrico en este momento.")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 10. Tabla de Detalle legible
    st.markdown('<div class="chart-title">📋 Registro Detallado de Cortes de Suministro</div>', unsafe_allow_html=True)
    
    df_table = df_view.copy()
    # Ordenar por afectados de mayor a menor por defecto
    df_table = df_table.sort_values(by='CLIENTES_AFECTADOS', ascending=False)
    
    # Mapeo y selección de campos
    display_cols = {
        'NOMBRE_REGION': 'Región',
        'NOMBRE_COMUNA': 'Comuna',
        'NOMBRE_EMPRESA': 'Empresa Distribuidora',
        'CLIENTES_AFECTADOS': 'Clientes Afectados',
        'ACTUALIZADO_HACE': 'Última Actualización SEC',
        'FECHA_INT_STR': 'Fecha Reporte'
    }
    
    # Ordenar regiones en la tabla también geográficamente si se exporta o muestra todo el país
    if selected_region == "Todo el País":
        df_table['reg_order'] = df_table['NOMBRE_REGION'].apply(get_region_order)
        # Ordenamos primero por clientes afectados (foco de crisis), y en empates por orden geográfico
        df_table = df_table.sort_values(by=['CLIENTES_AFECTADOS', 'reg_order'], ascending=[False, True])
        df_table = df_table.drop(columns=['reg_order'])
        
    df_display = df_table[list(display_cols.keys())].rename(columns=display_cols)
    
    # Tabla interactiva legible con filas estilizadas
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Clientes Afectados": st.column_config.NumberColumn(
                format="%d",
                help="Clientes afectados sin suministro"
            )
        }
    )
    
    # Botón de Descarga para reportabilidad remota en videowall
    csv_data = df_display.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(
        label="📥 Exportar Base de Datos a CSV",
        data=csv_data,
        file_name=f"reporte_videowall_sec_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )
