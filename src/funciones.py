import polars as pl
import numpy as np
import math
import streamlit as st

# general!!!
def puntaje(puntuaje_max,consumo_observado,consumo_minimo,consumo_maximo):

    puntuacion=puntuaje_max*((consumo_observado-consumo_minimo)*((consumo_maximo-consumo_minimo)**-1))
    return puntuacion


# Estos es para el grup taza
def consumo_observado_tazas(suma_tazas,kcalorias_sumadas):
    tot=(suma_tazas/kcalorias_sumadas)*1000
    return tot



# nota de MUFA,PUFA Y SAT:
# pufas y mufas es solamente para ácidos grasos, grasas saturadas es con % de energía
def consumo_obserevado_acidos_grasos(MUFA,PUFA,SAT):
    indice=(MUFA+PUFA)/SAT
    return indice
def gramos_a_tazas(gramos):# una taza es igual a 200 gramos
    n_tazas=gramos/200
    return n_tazas
def consumo_observado_sodio(sodio_g,kcal):
    consumo_obs_sodio=(sodio_g/kcal)*1000
    return consumo_obs_sodio

def densidad_calorica(consumo_observado_sodio,kcal_total_de_la_dieta):
    dense_cal=consumo_observado_sodio*kcal_total_de_la_dieta

def porcentaje_energia(cantidad_grasas_sat,cantidad_kcal):
    kcal_grasas_sat=cantidad_grasas_sat*4
    porcentaje_de_energia=(kcal_grasas_sat/cantidad_kcal)*100 # multiplicado por 100 para porcentaje
    return porcentaje_de_energia

#### Funciones con dataframes

## Para  mufa pufa sat:
# primero tengo la cantidad de lo que se consumio y multiplico cada cosa por su respectivo MUFA
# su respectivo pufa y su SAT (multiplicacion por columnas del dataframe)
def analisis_grasas(cantidad_dict:dict,df:pl.DataFrame,puntaje_max:float,consumo_minimo:float,consumo_maximo:float):
    # tengo pensado que cantida sea un dicionario el cual se puede convertir en una columna de dataframe
    # con el fin de operar con otras columnas del dataframe del cual vienen los valores
    # cantidad -> dado por el usuario
    # df -> base de datos (dataframe) ya provisto en el backend
    # Ejemplo: alimento: gramos->leche entera:200 gramos, pollo cocido: 100 gramos osea lo que puso el usuario
    # MUFA para leche entera y pollo en funcion de su cantidad y valor en el dataframe (una regla de 3)
    # PUFA igual para leche y pollo
    # SAT lo mismo ya teniendo esos 3 valores (MUFA,PUFA,SAT) para cada aelemento del diccionario cantidad
    # los sumo compacatando todo en un vector de tres entredas, tipo un sum por columna
    # quiero tener esos tres valores
    # de ahi yo uso esta funcion
    # Los argumentos seran los el vector venido de la suma ya mencionada
    cantidades_df = pl.DataFrame({
        'Alimento': list(cantidad_dict.keys()),
        'gramos_consumidos': list(cantidad_dict.values())
    })
    df_nutricional = df.select([
        'Alimento',
        'Gramaje',
        pl.col('MUFA').cast(pl.Float64),
        pl.col('PUFA').cast(pl.Float64),
        pl.col('SAT').cast(pl.Float64)
    ])
    df_completo = cantidades_df.join(
        df_nutricional,
        on='Alimento',
        how='left'
    )
    df_calculado = df_completo.with_columns([
        ((pl.col('MUFA') * pl.col('gramos_consumidos')) / pl.col('Gramaje')).alias('MUFA_total'),
        ((pl.col('PUFA') * pl.col('gramos_consumidos')) / pl.col('Gramaje')).alias('PUFA_total'),
        ((pl.col('SAT') * pl.col('gramos_consumidos')) / pl.col('Gramaje')).alias('SAT_total')
    ])
    totales = df_calculado.select([
        pl.col('MUFA_total').sum().alias('MUFA_sum'),
        pl.col('PUFA_total').sum().alias('PUFA_sum'),
        pl.col('SAT_total').sum().alias('SAT_sum')
    ])
    # definiendo los argumentos
    MUFA=totales['MUFA_sum'][0]
    PUFA=totales['TUFA_sum'][0]
    SAT=totales['SAT_sum'][0]
    consumo_registrado= consumo_obserevado_acidos_grasos(MUFA,PUFA,SAT)
    puntuacion=puntaje(puntaje_max,consumo_registrado,consumo_minimo,consumo_maximo)
    return puntuacion

def analisis_grasas_v2(cantidad_dict: dict, df: pl.DataFrame, puntaje_max: float,
                       consumo_minimo: float, consumo_maximo: float) -> float:
    """
    Versión optimizada - todo en una sola expresión Polars
    """

    # Crear DataFrame de cantidades
    resultado = (pl.DataFrame({
        'Alimento': list(cantidad_dict.keys()),
        'gramos_consumidos': list(cantidad_dict.values())
    })
                 # Join con datos nutricionales (convirtiendo strings a float)
                 .join(
        df.select([
            'Alimento',
            'Gramaje',
            pl.col('MUFA').cast(pl.Float64),
            pl.col('PUFA').cast(pl.Float64),
            pl.col('SAT').cast(pl.Float64)
        ]),
        on='Alimento',
        how='left'
    )
                 # Calcular valores ajustados por cantidad consumida
                 .with_columns([
        (pl.col('MUFA') * pl.col('gramos_consumidos') / pl.col('Gramaje')).alias('MUFA_total'),
        (pl.col('PUFA') * pl.col('gramos_consumidos') / pl.col('Gramaje')).alias('PUFA_total'),
        (pl.col('SAT') * pl.col('gramos_consumidos') / pl.col('Gramaje')).alias('SAT_total')
    ])
                 # Sumar totales y calcular resultado final
                 .select([
        ((pl.col('MUFA_total').sum() + pl.col('PUFA_total').sum()) /
         pl.col('SAT_total').sum()).alias('indice')
    ])
                 .with_columns([
        (puntaje_max * ((pl.col('indice') - consumo_minimo) /
                        (consumo_maximo - consumo_minimo))).alias('puntuacion')
    ])
                 .select('puntuacion')
                 .item()
                 )

    return resultado

def analisis_grasas_robusto(cantidad_dict: dict, df: pl.DataFrame, puntaje_max: float,
                            consumo_minimo: float, consumo_maximo: float) -> float:
    """
    Versión robusta con validación de datos
    """

    # Validar que el diccionario no esté vacío
    if not cantidad_dict:
        raise ValueError("El diccionario de cantidades no puede estar vacío")

    # Validar que los alimentos existan en el DataFrame
    alimentos_no_encontrados = set(cantidad_dict.keys()) - set(df['Alimento'].to_list())
    if alimentos_no_encontrados:
        raise ValueError(f"Alimentos no encontrados en la base de datos: {alimentos_no_encontrados}")

    # Crear DataFrame de cantidades
    cantidades_df = pl.DataFrame({
        'Alimento': list(cantidad_dict.keys()),
        'gramos_consumidos': list(cantidad_dict.values())
    })

    # Join con datos nutricionales
    df_completo = cantidades_df.join(
        df.select([
            'Alimento',
            'Gramaje',
            pl.col('MUFA').cast(pl.Float64, strict=False).fill_null(0),
            pl.col('PUFA').cast(pl.Float64, strict=False).fill_null(0),
            pl.col('SAT').cast(pl.Float64, strict=False).fill_null(0)
        ]),
        on='Alimento',
        how='left'
    )

    # Calcular valores ajustados
    df_calculado = df_completo.with_columns([
        ((pl.col('MUFA') * pl.col('gramos_consumidos')) / pl.col('Gramaje')).alias('MUFA_total'),
        ((pl.col('PUFA') * pl.col('gramos_consumidos')) / pl.col('Gramaje')).alias('PUFA_total'),
        ((pl.col('SAT') * pl.col('gramos_consumidos')) / pl.col('Gramaje')).alias('SAT_total')
    ])

    # Obtener sumas
    MUFA = df_calculado['MUFA_total'].sum()
    PUFA = df_calculado['PUFA_total'].sum()
    SAT = df_calculado['SAT_total'].sum()

    # Validar que SAT no sea cero para evitar división por cero
    if SAT == 0:
        raise ValueError("La suma de grasas saturadas es cero, no se puede calcular el índice")

    # Calcular puntuación
    consumo_registrado = consumo_obserevado_acidos_grasos(MUFA, PUFA, SAT)
    puntuacion = puntaje(puntaje_max, consumo_registrado, consumo_minimo, consumo_maximo)

    return puntuacion



def analisis_sodio(cantidad_dict: dict, df: pl.DataFrame, puntaje_max: float,
                   consumo_minimo: float, consumo_maximo: float) -> float:
    """
    Calcula el puntaje para el análisis de sodio por 1000 kcal

    Parameters:
    -----------
    cantidad_dict : dict
        Diccionario con formato: {'Alimento': gramos_consumidos}
        Ejemplo: {'Pan Manaque': 120, 'Leche entera': 200}
    df : pl.DataFrame
        DataFrame con columnas: 'Alimento', 'Gramaje', 'KCAL', 'SODIO'
        Los valores de SODIO vienen como string y representan
        la cantidad en gramos por el gramaje indicado
    puntaje_max : float
        Puntaje máximo posible (ejemplo: 10)
    consumo_minimo : float
        Valor mínimo para el consumo de sodio (ejemplo: 0)
    consumo_maximo : float
        Valor máximo para el consumo de sodio (ejemplo: algo como 10 o según referencia)

    Returns:
    --------
    float
        Puntuación calculada para sodio

    Example manual:
    --------------
    Para 120g de Pan Manaque (KCAL=272/100g, SODIO=0.60g/100g):
    - KCAL total = (272 * 120) / 100 = 326.4 kcal
    - SODIO total = (0.60 * 120) / 100 = 0.72 g
    - Consumo observado = (0.72 / 326.4) * 1000 = 2.21 g/1000kcal
    """

    # 1. Convertir el diccionario de cantidades a DataFrame
    cantidades_df = pl.DataFrame({
        'Alimento': list(cantidad_dict.keys()),
        'gramos_consumidos': list(cantidad_dict.values())
    })

    # 2. Preparar DataFrame nutricional convirtiendo SODIO de string a float
    df_nutricional = df.select([
        'Alimento',
        'Gramaje',
        'KCAL',
        pl.col('SODIO').cast(pl.Float64, strict=False).fill_null(0)
    ])

    # 3. Join de las cantidades con los valores nutricionales
    df_completo = cantidades_df.join(
        df_nutricional,
        on='Alimento',
        how='left'
    )

    # 4. Calcular KCAL y SODIO ajustados por la cantidad consumida
    df_calculado = df_completo.with_columns([
        ((pl.col('KCAL') * pl.col('gramos_consumidos')) / pl.col('Gramaje')).alias('KCAL_total'),
        ((pl.col('SODIO') * pl.col('gramos_consumidos')) / pl.col('Gramaje')).alias('SODIO_total')
    ])

    # 5. Sumar todos los valores para obtener totales
    totales = df_calculado.select([
        pl.col('KCAL_total').sum().alias('KCAL_sum'),
        pl.col('SODIO_total').sum().alias('SODIO_sum')
    ])

    # 6. Extraer los valores para el cálculo
    kcal_total = totales['KCAL_sum'][0]
    sodio_total = totales['SODIO_sum'][0]

    # 7. Calcular el consumo observado de sodio por 1000 kcal
    consumo_registrado = consumo_observado_sodio(sodio_total, kcal_total)

    # 8. Calcular la puntuación final usando la función puntaje
    puntuacion = puntaje(puntaje_max, consumo_registrado, consumo_minimo, consumo_maximo)

    return puntuacion


def consumo_observado_sodio(sodio_g: float, kcal: float) -> float:
    """
    Calcula el consumo de sodio en gramos por 1000 kcal

    Parameters:
    -----------
    sodio_g : float
        Gramos totales de sodio consumidos
    kcal : float
        Kilocalorías totales consumidas

    Returns:
    --------
    float
        Gramos de sodio por 1000 kcal
    """
    if kcal == 0:
        return 0.0
    consumo_obs_sodio = (sodio_g / kcal) * 1000
    return consumo_obs_sodio


def porcentaje_energia_macronutriente(gramos_macronutriente: float, kcal_total: float,
                                      tipo_macronutriente: str) -> float:
    """
    Calcula el porcentaje de energía para grasas (9 kcal/g) o azúcares (4 kcal/g)

    Parameters:
    -----------
    gramos_macronutriente : float
        Gramos del macronutriente
    kcal_total : float
        Kilocalorías totales
    tipo_macronutriente : str
        'grasa', 'grasa_saturada' -> factor 9
        'azucar', 'azucar_añadida' -> factor 4

    Returns:
    --------
    float
        Porcentaje de energía del macronutriente
    """
    factores = {
        'grasa': 9,
        'grasa_saturada': 9,
        'sat': 9,
        'azucar': 4,
        'azucar_añadida': 4,
        'azucares': 4
    }

    tipo_normalizado = tipo_macronutriente.lower().strip()

    if tipo_normalizado not in factores:
        raise ValueError(f"Tipo '{tipo_macronutriente}' no válido. Usa 'grasa' (factor 9) o 'azucar' (factor 4)")

    if kcal_total == 0:
        return 0.0

    factor = factores[tipo_normalizado]
    kcal_macronutriente = gramos_macronutriente * factor
    porcentaje = (kcal_macronutriente / kcal_total) * 100

    return porcentaje
# ejemplo de uso
#porcentaje_azucar = porcentaje_energia_macronutriente(50, 2000, 'azucar') # 4
#porcentaje_grasa_sat = porcentaje_energia_macronutriente(20, 2000, 'grasa_saturada')  # 9

import polars as pl

def analisis_tazas(cantidad_dict: dict, df: pl.DataFrame, puntaje_max: float,
                   consumo_minimo: float, consumo_maximo: float) -> float:
    """
    Calcula el puntaje para el análisis de tazas por 1000 kcal

    Parameters:
    -----------
    cantidad_dict : dict
        Diccionario con formato: {'Alimento': gramos_consumidos}
        Ejemplo: {'Manzana': 200, 'Plátano': 120}
    df : pl.DataFrame
        DataFrame con columnas: 'Alimento', 'Gramaje', 'KCAL'
    puntaje_max : float
        Puntaje máximo posible (ejemplo: 5)
    consumo_minimo : float
        Valor mínimo para tazas/1000 kcal
    consumo_maximo : float
        Valor máximo para tazas/1000 kcal

    Returns:
    --------
    float
        Puntuación calculada para tazas

    Example manual (basado en tu imagen):
    -------------------------------------
    - Manzana: 200g -> tazas = 200/200 = 1 taza
    - Plátano: 120g -> tazas = 120/200 = 0.6 tazas
    - Total tazas = 1.6 tazas
    - Consumo observado = (1.6 / kcal_total) * 1000
    """

    # 1. Convertir el diccionario de cantidades a DataFrame
    cantidades_df = pl.DataFrame({
        'Alimento': list(cantidad_dict.keys()),
        'gramos_consumidos': list(cantidad_dict.values())
    })

    # 2. Preparar DataFrame nutricional
    df_nutricional = df.select([
        'Alimento',
        'Gramaje',
        'KCAL'
    ])

    # 3. Join de las cantidades con los valores nutricionales
    df_completo = cantidades_df.join(
        df_nutricional,
        on='Alimento',
        how='left'
    )

    # 4. Calcular KCAL totales y convertir gramos a tazas
    df_calculado = df_completo.with_columns([
        ((pl.col('KCAL') * pl.col('gramos_consumidos')) / pl.col('Gramaje')).alias('KCAL_total'),
        (pl.col('gramos_consumidos') / 200).alias('tazas')  # Conversión directa a tazas
    ])

    # 5. Sumar todos los valores para obtener totales
    totales = df_calculado.select([
        pl.col('KCAL_total').sum().alias('KCAL_sum'),
        pl.col('tazas').sum().alias('tazas_sum')
    ])

    # 6. Extraer los valores para el cálculo
    kcal_total = totales['KCAL_sum'][0]
    tazas_total = totales['tazas_sum'][0]

    # 7. Calcular el consumo observado (tazas/1000 kcal)
    consumo_registrado = consumo_observado_tazas(tazas_total, kcal_total)

    # 8. Calcular la puntuación final
    puntuacion = puntaje(puntaje_max, consumo_registrado, consumo_minimo, consumo_maximo)

    return puntuacion


def consumo_observado_tazas(tazas: float, kcal: float) -> float:
    """
    Calcula el consumo observado en tazas por 1000 kcal

    Parameters:
    -----------
    tazas : float
        Total de tazas consumidas
    kcal : float
        Kilocalorías totales consumidas

    Returns:
    --------
    float
        Tazas por 1000 kcal

    Formula: (tazas / kcal) * 1000
    """
    if kcal == 0:
        return 0.0

    return (tazas / kcal) * 1000


def gramos_a_tazas(gramos: float) -> float:
    """
    Convierte gramos a tazas (1 taza = 200 gramos)

    Parameters:
    -----------
    gramos : float
        Cantidad en gramos

    Returns:
    --------
    float
        Cantidad en tazas
    """
    n_tazas = gramos / 200
    return n_tazas


#%%
