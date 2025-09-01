import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import warnings
import base64
warnings.filterwarnings('ignore')

def get_image_as_base64(file_path):
    """Convierte una imagen a base64 para incrustarla en HTML"""
    try:
        with open(file_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except:
        return ""

# Configuración de la página
st.set_page_config(
    page_title="Dashboard Licitaciones AENA 2024",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal
st.title("Dashboard de licitaciones - AENA")
st.markdown("---")

@st.cache_data
def cargar_datos():
    """Carga y procesa los datos de AENA"""
    try:
        df = pd.read_excel('2024_AENA.xlsx')
        
        # Limpiar y procesar datos
        # Usar el nombre exacto de la columna
        fecha_col = 'Fecha presentación licitación'
        
        if fecha_col not in df.columns:
            st.error(f"No se encontró la columna '{fecha_col}'")
            return None
        
        df[fecha_col] = pd.to_datetime(df[fecha_col])
        df['Mes'] = df[fecha_col].dt.month
        df['Año'] = df[fecha_col].dt.year
        df['Trimestre'] = df[fecha_col].dt.quarter
        df['Día_Semana'] = df[fecha_col].dt.day_name()
        df['Nombre_Mes'] = df[fecha_col].dt.month_name()
        
        # Usar la columna %baja existente si está disponible, sino calcularla
        if '%baja' in df.columns:
            # Convertir de decimal a porcentaje si es necesario
            if df['%baja'].max() <= 1:
                df['Porcentaje_Ahorro'] = df['%baja'] * 100
            else:
                df['Porcentaje_Ahorro'] = df['%baja']
        else:
            # Calcular diferencia entre presupuesto y adjudicación
            df['Diferencia_Importe'] = df['Presupuesto base sin impuestos'] - df['Importe adjudicación sin impuestos licitación/lote']
            df['Porcentaje_Ahorro'] = (df['Diferencia_Importe'] / df['Presupuesto base sin impuestos']) * 100
        
        # Guardar el nombre de la columna de fecha para uso posterior
        df.attrs['fecha_col'] = fecha_col
        
        return df
    except Exception as e:
        st.error(f"Error al cargar los datos: {e}")
        return None

def crear_filtros_sidebar(df):
    """Crea los filtros en el sidebar con dependencias"""
    # Logo de Acciona en el sidebar
    st.sidebar.markdown("""
    <div style="
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 15px;
        background: white;
        border-radius: 15px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        border: 1px solid #e0e0e0;
        margin-bottom: 20px;
        width: 200px;
        margin-left: auto;
        margin-right: auto;
    ">
        <img src="data:image/jpeg;base64,{}" style="max-width: 192px; height: auto;">
    </div>
    """.format(get_image_as_base64("acciona.JPG")), unsafe_allow_html=True)
    
    st.sidebar.header("🔍 Filtros")
    
    fecha_col = 'Fecha presentación licitación'
    
    # Inicializar session_state si no existe
    if 'aeropuerto_seleccionado' not in st.session_state:
        st.session_state.aeropuerto_seleccionado = 'Todos'
    if 'empresa_seleccionada' not in st.session_state:
        st.session_state.empresa_seleccionada = 'Todas'
    
    # Obtener datos base para filtros
    df_empresas_validas = df[df['Adjudicatario licitación/lote'].notna() & 
                             (df['Adjudicatario licitación/lote'] != '')]
    
    # Obtener todas las opciones disponibles
    todos_aeropuertos = ['Todos'] + sorted(df['Aeropuerto'].unique().tolist())
    todas_empresas = ['Todas'] + sorted(df_empresas_validas['Adjudicatario licitación/lote'].unique().tolist())
    
    # Filtro por aeropuerto
    aeropuerto_seleccionado = st.sidebar.selectbox(
        "Aeropuerto:", 
        todos_aeropuertos,
        key="aeropuerto_filter"
    )
    
    # Filtrar empresas según el aeropuerto seleccionado
    if aeropuerto_seleccionado != 'Todos':
        empresas_del_aeropuerto = df_empresas_validas[df_empresas_validas['Aeropuerto'] == aeropuerto_seleccionado]['Adjudicatario licitación/lote'].unique()
        empresas_disponibles = ['Todas'] + sorted(empresas_del_aeropuerto.tolist())
        
        # Si la empresa actual no está en las disponibles, resetear a 'Todas'
        if st.session_state.empresa_seleccionada not in empresas_disponibles:
            st.session_state.empresa_seleccionada = 'Todas'
        
        empresa_seleccionada = st.sidebar.selectbox(
            f"Empresa Adjudicataria (en {aeropuerto_seleccionado}):", 
            empresas_disponibles,
            key="empresa_filter_aeropuerto"
        )
    else:
        empresa_seleccionada = st.sidebar.selectbox(
            "Empresa Adjudicataria:", 
            todas_empresas,
            key="empresa_filter_all"
        )
    
    # Filtrar aeropuertos según la empresa seleccionada
    if empresa_seleccionada != 'Todas':
        aeropuertos_de_la_empresa = df_empresas_validas[df_empresas_validas['Adjudicatario licitación/lote'] == empresa_seleccionada]['Aeropuerto'].unique()
        aeropuertos_disponibles = ['Todos'] + sorted(aeropuertos_de_la_empresa.tolist())
        
        # Si el aeropuerto actual no está en los disponibles, resetear a 'Todos'
        if st.session_state.aeropuerto_seleccionado not in aeropuertos_disponibles:
            st.session_state.aeropuerto_seleccionado = 'Todos'
        
        aeropuerto_seleccionado = st.sidebar.selectbox(
            f"Aeropuerto (donde opera {empresa_seleccionada}):", 
            aeropuertos_disponibles,
            key="aeropuerto_filter_empresa"
        )
    
    # Actualizar session_state
    st.session_state.aeropuerto_seleccionado = aeropuerto_seleccionado
    st.session_state.empresa_seleccionada = empresa_seleccionada
    
    # Filtro por rango de fechas
    fecha_min = df[fecha_col].min()
    fecha_max = df[fecha_col].max()
    rango_fechas = st.sidebar.date_input(
        "Rango de fechas:",
        value=(fecha_min.date(), fecha_max.date()),
        min_value=fecha_min.date(),
        max_value=fecha_max.date()
    )
    
    # Filtro por rango de importes (campos de texto)
    st.sidebar.markdown("**Rango de importes (€):**")
    col1, col2 = st.sidebar.columns(2)
    
    importe_min = float(df['Importe adjudicación sin impuestos licitación/lote'].min())
    importe_max = float(df['Importe adjudicación sin impuestos licitación/lote'].max())
    
    with col1:
        importe_min_input = st.number_input(
            "Mínimo:",
            min_value=0.0,
            max_value=importe_max,
            value=importe_min,
            step=10000.0,
            format="%.0f"
        )
    
    with col2:
        importe_max_input = st.number_input(
            "Máximo:",
            min_value=importe_min_input,
            max_value=importe_max * 2,
            value=importe_max,
            step=10000.0,
            format="%.0f"
        )
    
    rango_importes = (importe_min_input, importe_max_input)
    
    return aeropuerto_seleccionado, empresa_seleccionada, rango_fechas, rango_importes

def aplicar_filtros(df, aeropuerto_seleccionado, empresa_seleccionada, rango_fechas, rango_importes):
    """Aplica los filtros al dataframe"""
    df_filtrado = df.copy()
    fecha_col = 'Fecha presentación licitación'
    
    if aeropuerto_seleccionado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Aeropuerto'] == aeropuerto_seleccionado]
    
    if empresa_seleccionada != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['Adjudicatario licitación/lote'] == empresa_seleccionada]
    
    df_filtrado = df_filtrado[
        (df_filtrado[fecha_col].dt.date >= rango_fechas[0]) &
        (df_filtrado[fecha_col].dt.date <= rango_fechas[1]) &
        (df_filtrado['Importe adjudicación sin impuestos licitación/lote'] >= rango_importes[0]) &
        (df_filtrado['Importe adjudicación sin impuestos licitación/lote'] <= rango_importes[1])
    ]
    
    return df_filtrado

def crear_metricas_principales(df_filtrado):
    """Crea las métricas principales del dashboard"""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            label="📊 Total Licitaciones",
            value=f"{len(df_filtrado):,}",
            delta=None
        )
    
    with col2:
        total_presupuesto = df_filtrado['Presupuesto base sin impuestos'].sum() / 1e6
        st.metric(
            label="💰 Presupuesto Total (M€)",
            value=f"{total_presupuesto:,.1f}",
            delta=None
        )
    
    with col3:
        total_adjudicado = df_filtrado['Importe adjudicación sin impuestos licitación/lote'].sum() / 1e6
        st.metric(
            label="🏆 Importe Adjudicado (M€)",
            value=f"{total_adjudicado:,.1f}",
            delta=None
        )
    
    with col4:
        ahorro_total = (df_filtrado['Presupuesto base sin impuestos'].sum() - df_filtrado['Importe adjudicación sin impuestos licitación/lote'].sum()) / 1e6
        porcentaje_ahorro = (ahorro_total / total_presupuesto) * 100 if total_presupuesto > 0 else 0
        st.metric(
            label="💡 Ahorro Total (M€)",
            value=f"{ahorro_total:,.1f}",
            delta=f"{porcentaje_ahorro:.1f}%"
        )
    
    with col5:
        # Calcular %baja medio usando la columna existente o calculada
        porcentaje_baja_medio = df_filtrado['Porcentaje_Ahorro'].mean()
        st.metric(
            label="📉 %Baja Medio",
            value=f"{porcentaje_baja_medio:.1f}%",
            delta=None
        )

def crear_grafico_evolucion_temporal(df_filtrado):
    """Crea gráfico de evolución temporal de licitaciones"""
    st.subheader("📅 Evolución Temporal de Licitaciones")
    
    if len(df_filtrado) == 0:
        st.warning("No hay datos para mostrar con los filtros seleccionados.")
        return
    
    fecha_col = 'Fecha presentación licitación'
    
    # Agrupar por mes
    df_mensual = df_filtrado.groupby(df_filtrado[fecha_col].dt.to_period('M')).agg({
        'Número de expediente': 'count',
        'Presupuesto base sin impuestos': 'sum',
        'Importe adjudicación sin impuestos licitación/lote': 'sum'
    }).reset_index()
    
    df_mensual['Fecha'] = df_mensual[fecha_col].dt.to_timestamp()
    
    # Crear gráfico
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Número de Licitaciones por Mes', 'Importes por Mes (M€)'),
        vertical_spacing=0.1
    )
    
    # Gráfico de número de licitaciones
    fig.add_trace(
        go.Scatter(
            x=df_mensual['Fecha'],
            y=df_mensual['Número de expediente'],
            mode='lines+markers',
            name='Número de Licitaciones',
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=8)
        ),
        row=1, col=1
    )
    
    # Gráfico de importes
    fig.add_trace(
        go.Scatter(
            x=df_mensual['Fecha'],
            y=df_mensual['Presupuesto base sin impuestos'] / 1e6,
            mode='lines+markers',
            name='Presupuesto Base',
            line=dict(color='#ff7f0e', width=3)
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_mensual['Fecha'],
            y=df_mensual['Importe adjudicación sin impuestos licitación/lote'] / 1e6,
            mode='lines+markers',
            name='Importe Adjudicado',
            line=dict(color='#2ca02c', width=3)
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        height=600,
        showlegend=True,
        title_text="Evolución Temporal de Licitaciones AENA 2024"
    )
    
    fig.update_yaxes(title_text="Número de Licitaciones", row=1, col=1)
    fig.update_yaxes(title_text="Importe (M€)", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)

def crear_analisis_aeropuertos(df_filtrado):
    """Crea análisis de aeropuertos"""
    st.subheader("🏢 Análisis por Aeropuerto")
    
    if len(df_filtrado) == 0:
        st.warning("No hay datos para mostrar con los filtros seleccionados.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Top aeropuertos por número de licitaciones
        aeropuertos_count = df_filtrado['Aeropuerto'].value_counts().head(10)
        
        fig = px.bar(
            x=aeropuertos_count.values,
            y=aeropuertos_count.index,
            orientation='h',
            title="Top 10 Aeropuertos por Número de Licitaciones",
            labels={'x': 'Número de Licitaciones', 'y': 'Aeropuerto'},
            color=aeropuertos_count.values,
            color_continuous_scale='Blues'
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Top aeropuertos por importe
        aeropuertos_importe = df_filtrado.groupby('Aeropuerto')['Importe adjudicación sin impuestos licitación/lote'].sum().sort_values(ascending=False).head(10)
        
        fig = px.bar(
            x=aeropuertos_importe.values / 1e6,
            y=aeropuertos_importe.index,
            orientation='h',
            title="Top 10 Aeropuertos por Importe Adjudicado",
            labels={'x': 'Importe Adjudicado (M€)', 'y': 'Aeropuerto'},
            color=aeropuertos_importe.values,
            color_continuous_scale='Greens'
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

def crear_analisis_empresas(df_filtrado):
    """Crea análisis de empresas adjudicatarias"""
    st.subheader("🏢 Análisis de Empresas Adjudicatarias")
    
    if len(df_filtrado) == 0:
        st.warning("No hay datos para mostrar con los filtros seleccionados.")
        return
    
    # Limpiar nombres de empresas (eliminar valores nulos o vacíos)
    df_empresas = df_filtrado[df_filtrado['Adjudicatario licitación/lote'].notna() & 
                              (df_filtrado['Adjudicatario licitación/lote'] != '')].copy()
    
    if len(df_empresas) == 0:
        st.warning("No hay datos de empresas adjudicatarias disponibles.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Top empresas por número de licitaciones
        empresas_count = df_empresas['Adjudicatario licitación/lote'].value_counts().head(15)
        
        fig = px.bar(
            x=empresas_count.values,
            y=empresas_count.index,
            orientation='h',
            title="Top 15 Empresas por Número de Licitaciones",
            labels={'x': 'Número de Licitaciones', 'y': 'Empresa'},
            color=empresas_count.values,
            color_continuous_scale='Purples'
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Top empresas por importe adjudicado
        empresas_importe = df_empresas.groupby('Adjudicatario licitación/lote')['Importe adjudicación sin impuestos licitación/lote'].sum().sort_values(ascending=False).head(15)
        
        fig = px.bar(
            x=empresas_importe.values / 1e6,
            y=empresas_importe.index,
            orientation='h',
            title="Top 15 Empresas por Importe Adjudicado",
            labels={'x': 'Importe Adjudicado (M€)', 'y': 'Empresa'},
            color=empresas_importe.values,
            color_continuous_scale='Reds'
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
    
    # Estadísticas adicionales
    st.subheader("📊 Estadísticas de Empresas")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_empresas = df_empresas['Adjudicatario licitación/lote'].nunique()
        st.metric(
            label="🏢 Total Empresas",
            value=f"{total_empresas}",
            delta=None
        )
    
    with col2:
        empresa_mas_activa = empresas_count.index[0]
        st.metric(
            label="🏆 Empresa más activa",
            value=empresa_mas_activa[:30] + "..." if len(empresa_mas_activa) > 30 else empresa_mas_activa,
            delta=f"{empresas_count.iloc[0]} licitaciones"
        )
    
    with col3:
        promedio_por_empresa = len(df_empresas) / total_empresas
        st.metric(
            label="📊 Promedio por empresa",
            value=f"{promedio_por_empresa:.1f}",
            delta="licitaciones"
        )

def crear_analisis_mensual(df_filtrado):
    """Crea análisis de licitaciones por mes"""
    st.subheader("📅 Análisis de Licitaciones por Mes")
    
    if len(df_filtrado) == 0:
        st.warning("No hay datos para mostrar con los filtros seleccionados.")
        return
    
    # Ordenar meses correctamente
    orden_meses = ['January', 'February', 'March', 'April', 'May', 'June', 
                   'July', 'August', 'September', 'October', 'November', 'December']
    
    # Contar licitaciones por mes
    licitaciones_por_mes = df_filtrado['Nombre_Mes'].value_counts()
    
    # Reordenar según el orden correcto de meses
    licitaciones_por_mes_ordenado = licitaciones_por_mes.reindex(orden_meses, fill_value=0)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de barras de licitaciones por mes
        fig = px.bar(
            x=licitaciones_por_mes_ordenado.index,
            y=licitaciones_por_mes_ordenado.values,
            title="Licitaciones por Mes",
            labels={'x': 'Mes', 'y': 'Número de Licitaciones'},
            color=licitaciones_por_mes_ordenado.values,
            color_continuous_scale='Viridis'
        )
        fig.update_layout(height=400)
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Gráfico circular de distribución mensual
        fig = px.pie(
            values=licitaciones_por_mes_ordenado.values,
            names=licitaciones_por_mes_ordenado.index,
            title="Distribución de Licitaciones por Mes",
            hole=0.4
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Estadísticas adicionales
    st.subheader("📊 Estadísticas Mensuales")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        mes_mas_activo = licitaciones_por_mes_ordenado.idxmax()
        st.metric(
            label="📈 Mes más activo",
            value=mes_mas_activo,
            delta=f"{licitaciones_por_mes_ordenado.max()} licitaciones"
        )
    
    with col2:
        mes_menos_activo = licitaciones_por_mes_ordenado.idxmin()
        st.metric(
            label="📉 Mes menos activo",
            value=mes_menos_activo,
            delta=f"{licitaciones_por_mes_ordenado.min()} licitaciones"
        )
    
    with col3:
        promedio_mensual = licitaciones_por_mes_ordenado.mean()
        st.metric(
            label="📊 Promedio mensual",
            value=f"{promedio_mensual:.1f}",
            delta="licitaciones"
        )

def crear_tabla_datos(df_filtrado):
    """Crea tabla de datos interactiva"""
    st.subheader("📋 Datos Detallados")
    
    if len(df_filtrado) == 0:
        st.warning("No hay datos para mostrar con los filtros seleccionados.")
        return
    
    # Mostrar estadísticas de filtros
    st.info(f"📊 Mostrando {len(df_filtrado)} licitaciones")
    
    # Buscador de contratos
    st.markdown("### 🔍 Buscar Contrato")
    search_term = st.text_input(
        "Buscar por número de expediente, objeto del contrato, aeropuerto o empresa adjudicataria:",
        placeholder="Ej: mantenimiento, Madrid, ACCIONA..."
    )
    
    # Filtrar datos según la búsqueda
    if search_term:
        search_term_lower = search_term.lower()
        mask = (
            df_filtrado['Número de expediente'].astype(str).str.lower().str.contains(search_term_lower, na=False) |
            df_filtrado['Objeto del Contrato'].astype(str).str.lower().str.contains(search_term_lower, na=False) |
            df_filtrado['Aeropuerto'].astype(str).str.lower().str.contains(search_term_lower, na=False) |
            df_filtrado['Adjudicatario licitación/lote'].astype(str).str.lower().str.contains(search_term_lower, na=False)
        )
        df_busqueda = df_filtrado[mask]
        st.success(f"🔍 Encontrados {len(df_busqueda)} contratos que coinciden con '{search_term}'")
    else:
        df_busqueda = df_filtrado
    
    # Tabla de datos
    fecha_col = 'Fecha presentación licitación'
    columnas_mostrar = [
        'Aeropuerto', 'Número de expediente', 'Objeto del Contrato',
        'Presupuesto base sin impuestos', 'Importe adjudicación sin impuestos licitación/lote',
        fecha_col, 'Adjudicatario licitación/lote', 'Porcentaje_Ahorro'
    ]
    
    df_mostrar = df_busqueda[columnas_mostrar].copy()
    df_mostrar['Presupuesto base sin impuestos'] = df_mostrar['Presupuesto base sin impuestos'].apply(lambda x: f"{x:,.0f} €")
    df_mostrar['Importe adjudicación sin impuestos licitación/lote'] = df_mostrar['Importe adjudicación sin impuestos licitación/lote'].apply(lambda x: f"{x:,.0f} €")
    df_mostrar[fecha_col] = df_mostrar[fecha_col].dt.strftime('%d/%m/%Y')
    df_mostrar['Porcentaje_Ahorro'] = df_mostrar['Porcentaje_Ahorro'].apply(lambda x: f"{x:.1f}%")
    
    st.dataframe(
        df_mostrar,
        use_container_width=True,
        height=400
    )
    
    # Botón de descarga
    csv = df_filtrado.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 Descargar datos filtrados (CSV)",
        data=csv,
        file_name=f"licitaciones_aena_filtradas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )





def main():
    """Función principal del dashboard"""
    
    # Cargar datos
    df = cargar_datos()
    
    if df is None:
        st.error("❌ No se pudieron cargar los datos. Verifica que el archivo existe.")
        return
    
    # Crear filtros en sidebar
    aeropuerto_seleccionado, empresa_seleccionada, rango_fechas, rango_importes = crear_filtros_sidebar(df)
    
    # Aplicar filtros
    df_filtrado = aplicar_filtros(df, aeropuerto_seleccionado, empresa_seleccionada, rango_fechas, rango_importes)
    
    # Métricas principales (ahora con datos filtrados)
    crear_metricas_principales(df_filtrado)
    
    st.markdown("---")
    
    # Pestañas para organizar el contenido
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📅 Evolución Temporal", 
        "🏢 Análisis Aeropuertos", 
        "🏢 Análisis Empresas",
        "📅 Análisis Mensual",
        "📋 Datos"
    ])
    
    with tab1:
        crear_grafico_evolucion_temporal(df_filtrado)
    
    with tab2:
        crear_analisis_aeropuertos(df_filtrado)
    
    with tab3:
        crear_analisis_empresas(df_filtrado)
    
    with tab4:
        crear_analisis_mensual(df_filtrado)
    
    with tab5:
        crear_tabla_datos(df_filtrado)
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
        <p>📊 Dashboard creado con Streamlit | Datos: AENA 2024 | ✈️ Análisis de Licitaciones</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
