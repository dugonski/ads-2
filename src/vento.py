"""Previsão de vento dos 7 dias e seu efeito na velocidade do drone.

As rajadas da previsão são ignoradas. A coluna das 21h não é registrada porque
nenhum voo pode partir depois das 19h.
"""

import math
from dataclasses import dataclass

from src.contrato import SEGUNDOS_POR_HORA, Momento

# Ângulo de cada direção, a partir do Norte no sentido horário.
DIRECAO_EM_GRAUS = {
    "N": 0.0, "NNE": 22.5, "NE": 45.0, "ENE": 67.5,
    "E": 90.0, "ESE": 112.5, "SE": 135.0, "SSE": 157.5,
    "S": 180.0, "SSW": 202.5, "SW": 225.0, "WSW": 247.5,
    "W": 270.0, "WNW": 292.5, "NW": 315.0, "NNW": 337.5,
}  # fmt: skip


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


def vento_na_partida(partida: Momento) -> Vento:
    """Vento válido durante todo o trecho, definido pelo horário de partida."""
    hora = partida.segundo_do_dia // SEGUNDOS_POR_HORA
    if partida.dia not in PREVISAO or not 6 <= hora < 21:
        raise ValueError(f"Sem previsão de vento para o dia {partida.dia} às {partida.horario}")
    return PREVISAO[partida.dia][(hora - 6) // 3]


def velocidade_efetiva_kmh(velocidade_kmh: float, angulo_de_voo_graus: float, vento: Vento) -> float:
    """Módulo da soma vetorial da velocidade do drone com a do vento."""
    angulo_de_voo = math.radians(angulo_de_voo_graus)
    destino_do_vento = math.radians(DIRECAO_EM_GRAUS[vento.direcao_de_origem] + 180)
    leste = velocidade_kmh * math.sin(angulo_de_voo) + vento.velocidade_kmh * math.sin(
        destino_do_vento
    )
    norte = velocidade_kmh * math.cos(angulo_de_voo) + vento.velocidade_kmh * math.cos(
        destino_do_vento
    )
    return math.hypot(leste, norte)
