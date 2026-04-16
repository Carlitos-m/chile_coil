import polars as pl
import streamlit as st
from typing import Dict, List, Optional, Tuple
import numpy as np

# ============================================
# FUNCIONES AUXILIARES DE LIMPIEZA Y VALIDACIÓN
# ============================================

def limpiar_dataframe(df: pl.DataFrame) -> pl.DataFrame:
    """
    Limpia el DataFrame reemplazando 's/i', nulls y strings no numéricos
    """
    # Columnas numéricas que deben ser limpiadas
    columnas_numericas = ['KCAL', 'PROT', 'MUFA', 'PUFA', 'SAT', 'SODIO', 'AZUCAR AÑADIDA']

    for col in columnas_numericas:
        if col in df.columns:
            # Reemplazar 's/i', 'null', strings vacíos con None y luego con 0
            df = df.with_columns(
                pl.when(
                    pl.col(col).cast(pl.Utf8).str.to_lowercase().is_in(['s/i', 'null', '', 'nan'])
                )
                .then(pl.lit(None))
                .otherwise(pl.col(col))
                .cast(pl.Float64, strict=False)
                .fill_null(0)
                .alias(col)
            )
        else:
            # Si la columna no existe, crearla con 0
            df = df.with_columns(pl.lit(0).alias(col))

    return df


def obtener_alimento_completo(df: pl.DataFrame, alimento: str) -> pl.DataFrame:
    """
    Obtiene la fila más completa para un alimento dado.
    Si hay múltiples filas, elige la que tenga más valores no nulos.
    """
    df_filtrado = df.filter(pl.col('Alimento') == alimento)

    if df_filtrado.height == 0:
        return df_filtrado

    if df_filtrado.height == 1:
        return df_filtrado

    # Si hay múltiples filas, elegir la más completa
    columnas_a_verificar = ['KCAL', 'PROT', 'MUFA', 'PUFA', 'SAT', 'SODIO', 'AZUCAR AÑADIDA']

    df_filtrado = df_filtrado.with_columns(
        pl.sum_horizontal([
            pl.col(c).is_not_null().cast(pl.Int32)
            for c in columnas_a_verificar if c in df_filtrado.columns
        ]).alias('_completitud')
    )

    # Ordenar por completitud y tomar la primera
    return df_filtrado.sort('_completitud', descending=True).head(1)


def extraer_alimentos_por_grupo(df: pl.DataFrame, grupo: str) -> List[str]:
    """
    Extrae la lista de alimentos únicos de un grupo,
    eliminando duplicados y ordenando alfabéticamente
    """
    alimentos = (df
                 .filter(pl.col('Grupo de alimento').str.strip() == grupo)
                 .select('Alimento')
                 .unique()
                 .sort('Alimento')
                 .to_series()
                 .to_list())
    return alimentos


# ============================================
# FUNCIONES DE CÁLCULO NUTRICIONAL
# ============================================

def puntaje(puntaje_max: float, consumo_observado: float,
            consumo_minimo: float, consumo_maximo: float) -> float:
    """Calcula el puntaje normalizado"""
    if consumo_maximo == consumo_minimo:
        return 0.0
    puntuacion = puntaje_max * ((consumo_observado - consumo_minimo) /
                                (consumo_maximo - consumo_minimo))
    return puntuacion


def consumo_observado_sodio(sodio_g: float, kcal: float) -> float:
    """g de sodio por 1000 kcal"""
    if kcal == 0:
        return 0.0
    return (sodio_g / kcal) * 1000


def consumo_observado_tazas(tazas: float, kcal: float) -> float:
    """tazas por 1000 kcal"""
    if kcal == 0:
        return 0.0
    return (tazas / kcal) * 1000


def consumo_observado_acidos_grasos(MUFA: float, PUFA: float, SAT: float) -> float:
    """Índice (MUFA+PUFA)/SAT"""
    if SAT == 0:
        return 0.0
    return (MUFA + PUFA) / SAT


def porcentaje_energia_macronutriente(gramos: float, kcal_total: float,
                                      tipo: str) -> float:
    """
    Calcula % de energía para grasas (factor 9) o azúcares (factor 4)
    """
    if kcal_total == 0:
        return 0.0

    factor = 9 if tipo == 'grasa' else 4
    kcal_nutriente = gramos * factor
    return (kcal_nutriente / kcal_total) * 100


def gramos_a_tazas(gramos: float) -> float:
    """1 taza = 200 gramos"""
    return gramos / 200


# ============================================
# FUNCIÓN PRINCIPAL DE ANÁLISIS
# ============================================

def realizar_analisis_nutricional(df_registros: pl.DataFrame,
                                  df_nutricional: pl.DataFrame) -> Dict:
    """
    Realiza el análisis nutricional completo basado en los registros acumulados

    Parameters:
    -----------
    df_registros : pl.DataFrame
        DataFrame con columnas: 'Grupo', 'Alimento', 'Cantidad'
    df_nutricional : pl.DataFrame
        DataFrame limpio con información nutricional

    Returns:
    --------
    Dict con resultados por categoría
    """

    # Preparar DataFrame nutricional limpio
    df_nut = limpiar_dataframe(df_nutricional)

    # Hacer join con información nutricional
    df_analisis = df_registros.join(
        df_nut.select(['Alimento', 'Gramaje', 'KCAL', 'PROT', 'MUFA', 'PUFA',
                       'SAT', 'SODIO', 'AZUCAR AÑADIDA']),
        on='Alimento',
        how='left'
    )

    # Calcular valores ajustados por cantidad consumida
    df_analisis = df_analisis.with_columns([
        ((pl.col('KCAL') * pl.col('Cantidad')) / pl.col('Gramaje')).alias('KCAL_total'),
        ((pl.col('PROT') * pl.col('Cantidad') / pl.col('Gramaje')).fill_null(0)).alias('PROT_total'),
        ((pl.col('MUFA') * pl.col('Cantidad') / pl.col('Gramaje')).fill_null(0)).alias('MUFA_total'),
        ((pl.col('PUFA') * pl.col('Cantidad') / pl.col('Gramaje')).fill_null(0)).alias('PUFA_total'),
        ((pl.col('SAT') * pl.col('Cantidad') / pl.col('Gramaje')).fill_null(0)).alias('SAT_total'),
        ((pl.col('SODIO') * pl.col('Cantidad') / pl.col('Gramaje')).fill_null(0)).alias('SODIO_total'),
        ((pl.col('AZUCAR AÑADIDA') * pl.col('Cantidad') / pl.col('Gramaje')).fill_null(0)).alias('AZUCAR_total'),
    ])

    # Totales generales
    totales = df_analisis.select([
        pl.col('KCAL_total').sum().alias('KCAL_TOTAL'),
        pl.col('PROT_total').sum().alias('PROT_TOTAL'),
        pl.col('MUFA_total').sum().alias('MUFA_TOTAL'),
        pl.col('PUFA_total').sum().alias('PUFA_TOTAL'),
        pl.col('SAT_total').sum().alias('SAT_TOTAL'),
        pl.col('SODIO_total').sum().alias('SODIO_TOTAL'),
        pl.col('AZUCAR_total').sum().alias('AZUCAR_TOTAL'),
    ])

    kcal_total = totales['KCAL_TOTAL'][0]
    prot_total = totales['PROT_TOTAL'][0]
    mufa_total = totales['MUFA_TOTAL'][0]
    pufa_total = totales['PUFA_TOTAL'][0]
    sat_total = totales['SAT_TOTAL'][0]
    sodio_total = totales['SODIO_TOTAL'][0]
    azucar_total = totales['AZUCAR_TOTAL'][0]

    # Cálculo de tazas totales (solo para grupos específicos)
    tazas_total = 0.0
    if 'Tazas_Equivalentes' in df_registros.columns:
        tazas_total = df_registros['Tazas_Equivalentes'].sum()

    # Resultados base (siempre disponibles)
    resultados = {
        'KCAL_TOTAL': kcal_total,
        'PROTEINA_TOTAL': prot_total,
        'CONSUMO_OBSERVADO_SODIO': consumo_observado_sodio(sodio_total, kcal_total),
        'CONSUMO_OBSERVADO_TAZAS': consumo_observado_tazas(tazas_total, kcal_total),
        'INDICE_ACIDOS_GRASOS': consumo_observado_acidos_grasos(mufa_total, pufa_total, sat_total),
        'PORCENTAJE_GRASA_SAT': porcentaje_energia_macronutriente(sat_total, kcal_total, 'grasa'),
        'PORCENTAJE_AZUCAR': porcentaje_energia_macronutriente(azucar_total, kcal_total, 'azucar'),
    }

    return resultados


# ============================================
# CONFIGURACIÓN DE STREAMLIT
# ============================================

st.set_page_config(page_title="App Nutricional", layout="wide")

# Cargar datos
@st.cache_data
def cargar_datos():
    """Carga y limpia el DataFrame nutricional"""
    try:
        # Intentar cargar desde parquet
        df = pl.read_parquet('notebooks/datos_correctos')
    except:
        try:
            # Si falla, intentar cargar desde CSV
            df = pl.read_csv('datos_correctos.csv', ignore_errors=True)
        except Exception as e:
            st.error(f"Error al cargar datos: {e}")
            return None

    # Limpiar el DataFrame
    df = limpiar_dataframe(df)
    return df

df_nutricional = cargar_datos()

if df_nutricional is None:
    st.error("No se pudieron cargar los datos nutricionales")
    st.stop()

# ============================================
# INTERFAZ PRINCIPAL
# ============================================

st.title("🍎 App Nutricional - Análisis de Dieta")

# Inicializar session state
if 'records' not in st.session_state:
    st.session_state.records = []
if 'grupo_seleccionado' not in st.session_state:
    st.session_state.grupo_seleccionado = None
if 'alimento_seleccionado' not in st.session_state:
    st.session_state.alimento_seleccionado = None

# Definición de grupos y sus categorías
grupos = [
    'FRUTAS ENTERAS', 'Productos salados', 'Legumbres', 'Bebidas',
    'Leche y derivados', 'Cereales', 'Salsas', 'AZUCARES Y MIEL',
    'Pescados y mariscos', 'Carnes y visceras', 'JUGOS Y NECTARES',
    'VERDURAS', 'Bebidas alcohólicas', 'Grasas y Aceites', 'Huevo'
]

grup_taza = ['FRUTAS ENTERAS', 'Legumbres', 'VERDURAS', 'Leche y derivados']
acidos_grasos = ['Pescados y mariscos']
grasas_azucares = ['AZUCARES Y MIEL', 'Grasas y Aceites']

# Mostrar botones de grupos en grid de 3 columnas
st.markdown("### Seleccione un grupo de alimentos:")
cols = st.columns(3)

for i, grupo in enumerate(grupos):
    nombre_limpio = grupo.strip()
    with cols[i % 3]:
        if st.button(nombre_limpio, use_container_width=True,
                     key=f"btn_grupo_{i}"):
            st.session_state.grupo_seleccionado = nombre_limpio
            st.session_state.alimento_seleccionado = None
            st.rerun()

st.divider()

# ============================================
# FORMULARIO SEGÚN GRUPO SELECCIONADO
# ============================================

if st.session_state.grupo_seleccionado:
    grupo = st.session_state.grupo_seleccionado
    st.subheader(f"📋 Registro para: {grupo}")

    # Obtener alimentos de este grupo (versión más completa disponible)
    alimentos_disponibles = extraer_alimentos_por_grupo(df_nutricional, grupo)

    if not alimentos_disponibles:
        st.warning(f"No se encontraron alimentos en el grupo '{grupo}'")
    else:
        # Selector de alimento
        alimento = st.selectbox(
            "Seleccione el alimento:",
            options=alimentos_disponibles,
            key=f"select_{grupo}"
        )

        # Campo de cantidad (siempre en gramos)
        cantidad = st.number_input(
            "Cantidad consumida (gramos):",
            min_value=0.0,
            step=5.0,
            value=0.0,
            help="Ingrese la cantidad en gramos"
        )

        # Información adicional según el tipo de grupo
        if grupo in grup_taza:
            tazas_equiv = gramos_a_tazas(cantidad) if cantidad > 0 else 0
            st.caption(f"Equivalente en tazas: {tazas_equiv:.2f} tazas")

        # Botón de registro
        if st.button("✅ Confirmar Registro", use_container_width=True):
            if cantidad > 0:
                # Obtener información nutricional completa del alimento
                df_alimento = obtener_alimento_completo(df_nutricional, alimento)

                if df_alimento.height > 0:
                    nuevo_registro = {
                        "Grupo": grupo,
                        "Alimento": alimento,
                        "Cantidad": cantidad,
                        "Tazas_Equivalentes": gramos_a_tazas(cantidad) if grupo in grup_taza else 0.0,
                        "KCAL_base": df_alimento['KCAL'][0],
                        "PROT_base": df_alimento['PROT'][0] if 'PROT' in df_alimento.columns else 0,
                    }

                    st.session_state.records.append(nuevo_registro)

                    st.success(f"✅ Registrado: {cantidad}g de {alimento}")

                    # Mostrar resumen de lo registrado
                    with st.expander("Ver detalle nutricional del alimento"):
                        st.dataframe(df_alimento.to_pandas())
                else:
                    st.error(f"No se encontró información para '{alimento}'")
            else:
                st.warning("Por favor, ingrese una cantidad mayor a cero")

        # Botón para cerrar
        if st.button("❌ Cerrar"):
            st.session_state.grupo_seleccionado = None
            st.rerun()

# ============================================
# VISUALIZACIÓN DE REGISTROS Y ANÁLISIS
# ============================================

if st.session_state.records:
    st.divider()
    st.subheader("📊 Registros acumulados")

    df_registros = pl.DataFrame(st.session_state.records)
    st.dataframe(df_registros.to_pandas(), use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 Ejecutar Análisis Completo", use_container_width=True):
            with st.spinner("Analizando dieta..."):
                resultados = realizar_analisis_nutricional(df_registros, df_nutricional)

                st.success("✅ Análisis completado")

                # Mostrar resultados
                st.subheader("📈 Resultados del Análisis")

                col_r1, col_r2 = st.columns(2)

                with col_r1:
                    st.metric("Calorías Totales", f"{resultados['KCAL_TOTAL']:.1f} kcal")
                    st.metric("Proteína Total", f"{resultados['PROTEINA_TOTAL']:.1f} g")
                    st.metric("Sodio (obs)", f"{resultados['CONSUMO_OBSERVADO_SODIO']:.3f} g/1000kcal")
                    st.metric("Tazas (obs)", f"{resultados['CONSUMO_OBSERVADO_TAZAS']:.3f} tazas/1000kcal")

                with col_r2:
                    st.metric("Índice Ácidos Grasos", f"{resultados['INDICE_ACIDOS_GRASOS']:.3f}")
                    st.metric("% Grasa Saturada", f"{resultados['PORCENTAJE_GRASA_SAT']:.2f}%")
                    st.metric("% Azúcares", f"{resultados['PORCENTAJE_AZUCAR']:.2f}%")

                # Guardar resultados en session state para uso posterior
                st.session_state.resultados = resultados

    with col2:
        if st.button("🗑️ Limpiar Historial", use_container_width=True):
            st.session_state.records = []
            st.session_state.resultados = {}
            st.rerun()

# ============================================
# SIDEBAR
# ============================================

with st.sidebar:
    st.header("⚙️ Utilidades")

    st.subheader("Conversor gramos → tazas")
    gram_conv = st.number_input("Gramos:", min_value=0.0, value=0.0)
    if gram_conv > 0:
        st.info(f"**{gramos_a_tazas(gram_conv):.2f} tazas**")

    st.divider()

    st.subheader("📌 Información")
    st.caption("""
    **Grupos con cálculo de tazas:**
    - FRUTAS ENTERAS
    - Legumbres
    - VERDURAS
    - Leche y derivados
    
    **Grupo ácidos grasos:**
    - Pescados y mariscos
    
    **Grupos % energía:**
    - AZUCARES Y MIEL
    - Grasas y Aceites
    """)

#%%