"""Distância e ângulo de voo entre coordenadas geográficas."""

import math
from collections.abc import Sequence

from src.contrato import Coordenada

RAIO_DA_TERRA_KM = 6371.0


def distancia_haversine_km(origem: Coordenada, destino: Coordenada) -> float:
    latitude_origem = math.radians(origem.latitude)
    latitude_destino = math.radians(destino.latitude)
    diferenca_latitude = latitude_destino - latitude_origem
    diferenca_longitude = math.radians(destino.longitude - origem.longitude)
    a = (
        math.sin(diferenca_latitude / 2) ** 2
        + math.cos(latitude_origem)
        * math.cos(latitude_destino)
        * math.sin(diferenca_longitude / 2) ** 2
    )
    return RAIO_DA_TERRA_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def angulo_de_voo_graus(origem: Coordenada, destino: Coordenada) -> float:
    """Rumo de partida, de 0 a 360 graus a partir do Norte no sentido horário."""
    latitude_origem = math.radians(origem.latitude)
    latitude_destino = math.radians(destino.latitude)
    diferenca_longitude = math.radians(destino.longitude - origem.longitude)
    leste = math.sin(diferenca_longitude) * math.cos(latitude_destino)
    norte = math.cos(latitude_origem) * math.sin(latitude_destino) - math.sin(
        latitude_origem
    ) * math.cos(latitude_destino) * math.cos(diferenca_longitude)
    return math.degrees(math.atan2(leste, norte)) % 360


def matriz_de_distancias_km(coordenadas: Sequence[Coordenada]) -> list[list[float]]:
    """Distância de cada coordenada (linha) até cada outra (coluna)."""
    return [
        [distancia_haversine_km(origem, destino) for destino in coordenadas]
        for origem in coordenadas
    ]


def matriz_de_angulos_graus(coordenadas: Sequence[Coordenada]) -> list[list[float]]:
    """Ângulo de voo de cada coordenada (linha) até cada outra (coluna)."""
    return [
        [angulo_de_voo_graus(origem, destino) for destino in coordenadas]
        for origem in coordenadas
    ]
