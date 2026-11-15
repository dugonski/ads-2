"""Regulagens de velocidade, paradas e bateria do drone."""

import math

from src.contrato import SEGUNDOS_POR_HORA

# Inteiros múltiplos de 4, de 36 km/h (10 m/s) até o limite de 83 km/h.
VELOCIDADES_PERMITIDAS = tuple(range(36, 84, 4))

TEMPO_DE_PARADA_PARA_FOTO_S = 60
TEMPO_DE_PARADA_COM_POUSO_S = 172

AUTONOMIA_NOMINAL_S = 5000
VELOCIDADE_DE_REFERENCIA_KMH = 36
FATOR_DE_CORRECAO = 1.14  # condições reais de Curitiba


def autonomia_s(velocidade_kmh: int) -> float:
    """Duração da bateria cheia na velocidade regulada, antes do efeito do vento."""
    return (
        AUTONOMIA_NOMINAL_S
        * FATOR_DE_CORRECAO
        * (VELOCIDADE_DE_REFERENCIA_KMH / velocidade_kmh) ** 2
    )


def tempo_de_voo_s(distancia_km: float, velocidade_efetiva_kmh: float) -> int:
    """Tempo do deslocamento, arredondado para cima em segundo fracionado."""
    return math.ceil(distancia_km * SEGUNDOS_POR_HORA / velocidade_efetiva_kmh)


def tempo_de_parada_s(pousar: bool) -> int:
    return TEMPO_DE_PARADA_COM_POUSO_S if pousar else TEMPO_DE_PARADA_PARA_FOTO_S
