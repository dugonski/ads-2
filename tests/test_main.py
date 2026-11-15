import csv

import pytest

from src import main as modulo_main
from src.coordenadas import CEP_UNIBRASIL, carregar_coordenadas
from src.saida import COLUNAS


def test_main_grava_um_plano_valido_que_visita_todos_os_ceps(tmp_path, capsys):
    saida = tmp_path / "solucao.csv"

    modulo_main.main(["--populacao", "5", "--geracoes", "1", "--semente", "1", "--saida", str(saida)])

    with open(saida, encoding="utf-8", newline="") as arquivo:
        linhas = list(csv.reader(arquivo))
    ceps = {coordenada.cep for coordenada in carregar_coordenadas()}
    assert linhas[0] == COLUNAS
    assert len(linhas) - 1 == len(ceps)
    assert {linha[6] for linha in linhas[1:]} == ceps
    assert linhas[1][0] == linhas[-1][6] == CEP_UNIBRASIL
    assert f"Plano gravado em {saida}" in capsys.readouterr().out


def test_main_recusa_gravar_quando_nao_ha_plano_valido(tmp_path, monkeypatch):
    saida = tmp_path / "solucao.csv"
    # Com um único dia de prazo, nenhum plano consegue visitar todos os CEPs a 36 km/h.
    monkeypatch.setattr("src.algoritmo_genetico.VELOCIDADES_PERMITIDAS", (36,))
    monkeypatch.setattr("src.algoritmo_genetico.PESOS_DAS_VELOCIDADES_INICIAIS", [1])
    monkeypatch.setattr("src.algoritmo_genetico.ULTIMO_DIA", 1)

    with pytest.raises(SystemExit, match="Nenhum plano válido"):
        modulo_main.main(["--populacao", "5", "--geracoes", "1", "--saida", str(saida)])

    assert not saida.exists()
