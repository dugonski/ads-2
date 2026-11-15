import pytest

from src.drone import VELOCIDADES_PERMITIDAS, autonomia_s, tempo_de_parada_s, tempo_de_voo_s


def test_regulagens_sao_multiplos_de_4_entre_10_metros_por_segundo_e_83_kmh():
    assert VELOCIDADES_PERMITIDAS == (36, 40, 44, 48, 52, 56, 60, 64, 68, 72, 76, 80)


@pytest.mark.parametrize(
    ("velocidade", "autonomia_nominal_s"), [(36, 5000), (48, 2812.5), (60, 1800), (72, 1250)]
)
def test_autonomia_da_tabela_da_especificacao_com_fator_de_correcao(
    velocidade, autonomia_nominal_s
):
    assert autonomia_s(velocidade) == pytest.approx(autonomia_nominal_s * 1.14)


def test_tempo_de_voo_exato_nao_e_arredondado():
    assert tempo_de_voo_s(1.0, 36.0) == 100


def test_tempo_de_voo_com_segundo_fracionado_arredonda_para_cima():
    assert tempo_de_voo_s(1.001, 36.0) == 101
    assert tempo_de_voo_s(10.0, 41.0026532396) == 878


def test_tempo_de_parada_com_e_sem_pouso():
    assert tempo_de_parada_s(pousar=False) == 60
    assert tempo_de_parada_s(pousar=True) == 172
