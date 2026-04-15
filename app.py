
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
st.set_page_config(page_title="App Nutricional", layout="wide")
st.title("app nutricional:")
st.markdown("Seleccione un grupo de alimentos para ver sus detalles:")
grupos = [
    'FRUTAS ENTERAS', 'Productos salados', 'Legumbres', 'Bebidas',
    'Leche y derivados', 'Cereales', 'Salsas', 'AZUCARES Y MIEL',
    'Pescados y mariscos', 'Carnes y visceras', 'JUGOS Y NECTARES',
    'VERDURAS', 'Bebidas alcohólicas', 'Grasas y Aceites', 'Huevo'
]
# Creamos una cuadrícula de 3 columnas
cols = st.columns(3)

# Iteramos sobre la lista y asignamos cada botón a una columna
for i, grupo in enumerate(grupos):
    # Usamos el operador módulo (%) para ciclar entre las 3 columnas
    with cols[i % 3]:
        if st.button(grupo.strip(), use_container_width=True):
            st.success(f"Has seleccionado: **{grupo.strip()}**")
            # Aquí podrías agregar la lógica para mostrar una tabla o gráfico
            st.info(f"Cargando información nutricional para {grupo.strip()}...")

# Sidebar opcional para filtros adicionales
with st.sidebar:
    st.header("Configuración")
    st.write("Usuario: Invitado")
    st.date_input("Fecha de consulta")



#%%