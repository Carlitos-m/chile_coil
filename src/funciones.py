import polars as pl
import numpy as np
import math
import streamlit as st
treshold=2500

# general!!!
def puntaje(puntuaje_max,consumo_observado,consumo_minimo,consumo_maximo):

    puntuacion=puntuaje_max*((consumo_observado-consumo_minimo)*((consumo_maximo-consumo_minimo)**-1))
    return puntuacion


def consumo_observado(suma_tazas,kcalorias_sumadas):
    tot=(suma_tazas/kcalorias_sumadas)*1000
    return tot

def consumo_obserevado_acidos_grasos(MUFA,PUFA,SAT):
    indice=(MUFA+PUFA)/SAT
    return indice
def gramos_a_tazas(gramos):# una taza es igual a 200 gramos
    n_tazas=gramos/200
    return n_tazas
def consumo_observado_sodio(sodio_g):
    consumo_obs_sodio=sodio_g/1000
    return consumo_obs_sodio

def densidad_calorica(consumo_observado_sodio,kcal_total_de_la_dieta):
    dense_cal=consumo_observado_sodio*kcal_total_de_la_dieta

