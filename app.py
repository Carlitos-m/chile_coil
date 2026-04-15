
import polars as pl
import numpy as np
import streamlit as st
# Notas del flujo
# 1. Entrada de datos: funcion que recolecte datos del usuario mediante inputs
# 2. Mapeo nutricional:(Consultar)
# 3. Estandarizacion por energia: consultar una base de datos
# 4. Calculo de componenetes: Aplicar las formulas de puntuacion (funciones) a los 13 componentes
# 5. # Suma Total: La puntuación final es la suma de los 13 resultados individuales ($0 - 100$ puntos).
# Mostrar info básica
st.title("Vista previa:")


#%%