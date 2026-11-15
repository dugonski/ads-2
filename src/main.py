"""Ponto de entrada: executa o algoritmo genético e grava o plano de voo."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from src.algoritmo_genetico import executar_algoritmo_genetico
from src.coordenadas import RAIZ_DO_PROJETO, carregar_coordenadas
from src.saida import gravar_solucao
from src.simulador import Simulador

ARQUIVO_DA_SOLUCAO = RAIZ_DO_PROJETO / "output" / "solucao_final.csv"
SEMENTE_PADRAO = 2024


def main(argumentos: Sequence[str] | None = None) -> None:
    leitor = argparse.ArgumentParser(description=__doc__)
    leitor.add_argument("--semente", type=int, default=SEMENTE_PADRAO)
    leitor.add_argument("--populacao", type=int, default=80)
    leitor.add_argument("--geracoes", type=int, default=400)
    leitor.add_argument("--saida", type=Path, default=ARQUIVO_DA_SOLUCAO)
    opcoes = leitor.parse_args(argumentos)

    coordenadas = carregar_coordenadas()
    _, resultado, _ = executar_algoritmo_genetico(
        Simulador(coordenadas),
        coordenadas,
        tamanho_populacao=opcoes.populacao,
        max_geracoes=opcoes.geracoes,
        semente=opcoes.semente,
    )

    if not resultado.valido:
        raise SystemExit(f"Nenhum plano válido encontrado: {resultado.violacoes[0]}")
    gravar_solucao(resultado.trechos, opcoes.saida)
    ultimo = resultado.trechos[-1]
    print(
        f"Plano gravado em {opcoes.saida}\n"
        f"Trechos: {len(resultado.trechos)} | Fim: dia {ultimo.chegada.dia} às "
        f"{ultimo.chegada.horario} | Tempo de voo: {resultado.tempo_total_de_voo_s} s | "
        f"Pousos: {resultado.numero_de_pousos} | Custo: R$ {resultado.custo_dos_pousos_reais}"
    )


if __name__ == "__main__":
    main()
