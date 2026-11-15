"""Previsão de vento dos 7 dias e seu efeito na velocidade do drone.

As rajadas da previsão são ignoradas. A coluna das 21h não é registrada porque
nenhum voo pode partir depois das 19h.
"""

import math
from dataclasses import dataclass

from src.contrato import SEGUNDOS_POR_HORA, Momento

ROSA_DOS_VENTOS = (
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
)  # fmt: skip
GRAUS_POR_PONTO_DA_ROSA = 360 / len(ROSA_DOS_VENTOS)

PRIMEIRA_HORA_DA_PREVISAO = 6
HORAS_POR_COLUNA_DA_PREVISAO = 3


@dataclass(frozen=True)
class Vento:
    """Vento da previsão. `direcao_de_origem` é o ponto de onde ele vem."""

    velocidade_kmh: int
    direcao_de_origem: str


# Para cada dia, o vento das colunas 06h, 09h, 12h, 15h e 18h.
PREVISAO = {
    1: (Vento(3, "WSW"), Vento(3, "WSW"), Vento(7, "WSW"), Vento(7, "SSW"), Vento(10, "E")),
    2: (Vento(20, "E"), Vento(19, "E"), Vento(16, "E"), Vento(19, "E"), Vento(21, "E")),
    3: (Vento(15, "ENE"), Vento(17, "NE"), Vento(8, "NE"), Vento(20, "E"), Vento(16, "E")),
    4: (Vento(8, "ENE"), Vento(11, "ENE"), Vento(7, "NE"), Vento(6, "NE"), Vento(11, "E")),
    5: (Vento(17, "ENE"), Vento(18, "E"), Vento(19, "E"), Vento(19, "E"), Vento(20, "E")),
    6: (Vento(4, "NE"), Vento(5, "ENE"), Vento(4, "NE"), Vento(8, "E"), Vento(15, "E")),
    7: (Vento(6, "NE"), Vento(8, "NE"), Vento(14, "NE"), Vento(16, "NE"), Vento(13, "ENE")),
}


def graus_da_direcao(direcao: str) -> float:
    """Ângulo do ponto da rosa dos ventos, a partir do Norte no sentido horário."""
    return ROSA_DOS_VENTOS.index(direcao) * GRAUS_POR_PONTO_DA_ROSA


def vento_na_partida(partida: Momento) -> Vento:
    """Vento válido durante todo o trecho, definido pelo horário de partida."""
    hora = partida.segundo_do_dia // SEGUNDOS_POR_HORA
    coluna = (hora - PRIMEIRA_HORA_DA_PREVISAO) // HORAS_POR_COLUNA_DA_PREVISAO
    ventos_do_dia = PREVISAO.get(partida.dia, ())
    if not 0 <= coluna < len(ventos_do_dia):
        raise ValueError(f"Sem previsão de vento para o dia {partida.dia} às {partida.horario}")
    return ventos_do_dia[coluna]


def velocidade_efetiva_kmh(velocidade_kmh: float, angulo_de_voo_graus: float, vento: Vento) -> float:
    """Módulo da soma vetorial da velocidade do drone com a do vento."""
    angulo_de_voo = math.radians(angulo_de_voo_graus)
    destino_do_vento = math.radians(graus_da_direcao(vento.direcao_de_origem) + 180)
    leste = velocidade_kmh * math.sin(angulo_de_voo) + vento.velocidade_kmh * math.sin(
        destino_do_vento
    )
    norte = velocidade_kmh * math.cos(angulo_de_voo) + vento.velocidade_kmh * math.cos(
        destino_do_vento
    )
    return math.hypot(leste, norte)
