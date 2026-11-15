import pytest

from src.contrato import Momento
from src.vento import PREVISAO, Vento, velocidade_efetiva_kmh, vento_na_partida


def test_exemplo_da_especificacao_com_vento_vindo_de_sse():
    efetiva = velocidade_efetiva_kmh(36, 39.5, Vento(9, "SSE"))

    assert efetiva == pytest.approx(41.0026532396, abs=1e-9)


def test_sem_vento_a_velocidade_nao_muda():
    assert velocidade_efetiva_kmh(48, 123.0, Vento(0, "E")) == pytest.approx(48)


def test_vento_de_cauda_soma_e_vento_de_proa_subtrai():
    rumo_norte = 0.0

    assert velocidade_efetiva_kmh(36, rumo_norte, Vento(10, "S")) == pytest.approx(46)
    assert velocidade_efetiva_kmh(36, rumo_norte, Vento(10, "N")) == pytest.approx(26)


def test_exemplo_da_especificacao_para_a_coluna_do_horario_de_partida():
    # Partida 08:59:00 usa a coluna 06h; partida 09:21:00 usa a coluna 09h.
    assert vento_na_partida(Momento.de_horario(3, 8, 59, 0)) == Vento(15, "ENE")
    assert vento_na_partida(Momento.de_horario(3, 9, 21, 0)) == Vento(17, "NE")


@pytest.mark.parametrize(
    ("partida", "vento"),
    [
        (Momento.de_horario(1, 6), Vento(3, "WSW")),
        (Momento.de_horario(1, 14, 59, 59), Vento(7, "WSW")),
        (Momento.de_horario(1, 15), Vento(7, "SSW")),
        (Momento.de_horario(2, 12), Vento(16, "E")),
        (Momento.de_horario(6, 17, 59, 59), Vento(8, "E")),
        (Momento.de_horario(7, 18, 59, 59), Vento(13, "ENE")),
    ],
)
def test_vento_da_tabela_de_previsao(partida, vento):
    assert vento_na_partida(partida) == vento


@pytest.mark.parametrize(
    "partida",
    [Momento.de_horario(0, 12), Momento.de_horario(8, 12), Momento.de_horario(1, 5, 59, 59),
     Momento.de_horario(1, 21)],
)  # fmt: skip
def test_partida_sem_previsao_e_recusada(partida):
    with pytest.raises(ValueError, match="Sem previsão"):
        vento_na_partida(partida)


def test_previsao_cobre_cinco_colunas_em_cada_um_dos_sete_dias():
    assert sorted(PREVISAO) == [1, 2, 3, 4, 5, 6, 7]
    assert all(len(ventos) == 5 for ventos in PREVISAO.values())
