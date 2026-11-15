"""Regulagens de velocidade, paradas e bateria do drone."""

import math

from src.contrato import SEGUNDOS_POR_HORA

VELOCIDADE_MINIMA_KMH = 36  # 10 metros por segundo
VELOCIDADE_MAXIMA_KMH = 83
MULTIPLO_DE_VELOCIDADE_KMH = 4
VELOCIDADES_PERMITIDAS = tuple(
    range(VELOCIDADE_MINIMA_KMH, VELOCIDADE_MAXIMA_KMH + 1, MULTIPLO_DE_VELOCIDADE_KMH)
)

TEMPO_DE_PARADA_PARA_FOTO_S = 60
TEMPO_DE_PARADA_COM_POUSO_S = 172

VELOCIDADE_DE_REFERENCIA_KMH = 36
AUTONOMIA_NOMINAL_S = 5000
FATOR_DE_CORRECAO_PERCENTUAL = 114  # fator 1,14 das condições reais de Curitiba

# Um segundo de voo a v km/h gasta v² unidades de carga. Com isso a autonomia
# CARGA_CHEIA / v² é igual a 5000 x 1,14 x (36 / v)², em aritmética inteira.
CARGA_CHEIA = (
    AUTONOMIA_NOMINAL_S * FATOR_DE_CORRECAO_PERCENTUAL * VELOCIDADE_DE_REFERENCIA_KMH**2 // 100
)


def velocidade_permitida(velocidade_kmh: int) -> bool:
    return velocidade_kmh in VELOCIDADES_PERMITIDAS


def tempo_de_voo_s(distancia_km: float, velocidade_efetiva_kmh: float) -> int:
    """Tempo do deslocamento, arredondado para cima em segundo fracionado."""
    return math.ceil(distancia_km * SEGUNDOS_POR_HORA / velocidade_efetiva_kmh)


def tempo_de_parada_s(pousar: bool) -> int:
    return TEMPO_DE_PARADA_COM_POUSO_S if pousar else TEMPO_DE_PARADA_PARA_FOTO_S


def consumo_de_carga(segundos: int, velocidade_kmh: int) -> int:
    """Carga gasta em `segundos` na velocidade regulada, antes do efeito do vento."""
    return segundos * velocidade_kmh**2
