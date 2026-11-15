"""Gravação do plano de voo no CSV de entrega."""

import csv
from collections.abc import Sequence
from pathlib import Path

from src.contrato import TrechoSimulado

COLUNAS = [
    "CEP inicial",
    "Latitude inicial",
    "Longitude inicial",
    "Dia do vôo",
    "Hora inicial",
    "Velocidade",
    "CEP final",
    "Latitude final",
    "Longitude final",
    "Pouso",
    "Hora final",
]
CASAS_DECIMAIS_DAS_COORDENADAS = 13


def _graus(valor: float) -> str:
    return f"{valor:.{CASAS_DECIMAIS_DAS_COORDENADAS}f}"


def gravar_solucao(trechos: Sequence[TrechoSimulado], caminho: Path) -> None:
    """Grava uma linha por trecho, com as 11 colunas pedidas na especificação."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, mode="w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo, lineterminator="\n")
        escritor.writerow(COLUNAS)
        for trecho in trechos:
            escritor.writerow(
                [
                    trecho.origem.cep,
                    _graus(trecho.origem.latitude),
                    _graus(trecho.origem.longitude),
                    trecho.partida.dia,
                    trecho.partida.horario,
                    trecho.velocidade_kmh,
                    trecho.destino.cep,
                    _graus(trecho.destino.latitude),
                    _graus(trecho.destino.longitude),
                    "SIM" if trecho.pousou else "NÃO",
                    trecho.chegada.horario,
                ]
            )
