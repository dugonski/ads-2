import csv

from src.contrato import Momento, TrechoPlanejado
from src.coordenadas import ARQUIVO_DE_COORDENADAS, CEP_UNIBRASIL, carregar_coordenadas
from src.saida import COLUNAS, gravar_solucao
from src.simulador import BATERIA_CHEIA, Simulador


def test_csv_tem_as_onze_colunas_e_uma_linha_por_trecho(tmp_path):
    coordenadas = carregar_coordenadas()[:2]
    vizinho = coordenadas[1]
    resultado = Simulador(coordenadas).simular_plano(
        [TrechoPlanejado(vizinho.cep, 36, pousar=False), TrechoPlanejado(CEP_UNIBRASIL, 40, True)]
    )
    caminho = tmp_path / "pasta_nova" / "solucao.csv"

    gravar_solucao(resultado.trechos, caminho)

    with open(caminho, encoding="utf-8", newline="") as arquivo:
        linhas = list(csv.reader(arquivo))
    ida, volta = resultado.trechos
    assert linhas[0] == COLUNAS
    assert len(COLUNAS) == 11
    assert b"\r" not in caminho.read_bytes()
    assert linhas[1] == [
        CEP_UNIBRASIL, "-25.4233146347775", "-49.2160678044742", "1", "06:00:00", "36",
        vizinho.cep, "-25.4936598469491", "-49.3400481020638", "NÃO", ida.chegada.horario,
    ]  # fmt: skip
    assert linhas[2][3:6] == ["1", ida.chegada.horario, "40"]
    assert linhas[2][9:] == ["SIM", volta.chegada.horario]


def test_coordenadas_sao_gravadas_exatamente_como_no_arquivo_de_entrada(tmp_path):
    coordenadas = carregar_coordenadas()
    simulador = Simulador(coordenadas)
    voos = [
        simulador.simular_trecho(
            CEP_UNIBRASIL,
            TrechoPlanejado(coordenada.cep, 36, pousar=True),
            Momento.de_horario(1, 6),
            BATERIA_CHEIA,
        )
        for coordenada in coordenadas[1:]
    ]
    caminho = tmp_path / "solucao.csv"

    gravar_solucao(voos, caminho)

    with open(caminho, encoding="utf-8", newline="") as arquivo:
        gravadas = {(linha[6], linha[8], linha[7]) for linha in list(csv.reader(arquivo))[1:]}
    with open(ARQUIVO_DE_COORDENADAS, encoding="utf-8", newline="") as arquivo:
        originais = {tuple(linha) for linha in list(csv.reader(arquivo))[2:]}
    assert gravadas == originais
