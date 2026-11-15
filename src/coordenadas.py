"""Leitura da lista de CEPs e coordenadas."""

import csv
from pathlib import Path

from src.contrato import Coordenada

RAIZ_DO_PROJETO = Path(__file__).resolve().parent.parent
ARQUIVO_DE_COORDENADAS = RAIZ_DO_PROJETO / "data" / "coordenadas.csv"
CEP_UNIBRASIL = "82821020"


def carregar_coordenadas(caminho: Path = ARQUIVO_DE_COORDENADAS) -> list[Coordenada]:
    """Lê o CSV de colunas `cep,longitude,latitude`, na ordem do arquivo."""
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        coordenadas = [
            Coordenada(linha["cep"], float(linha["latitude"]), float(linha["longitude"]))
            for linha in csv.DictReader(arquivo)
        ]
    ceps_lidos = set()
    for coordenada in coordenadas:
        if coordenada.cep in ceps_lidos:
            raise ValueError(f"CEP {coordenada.cep} repetido em {caminho}")
        ceps_lidos.add(coordenada.cep)
    return coordenadas
