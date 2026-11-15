import math

import pytest

from src.contrato import Coordenada
from src.geografia import (
    RAIO_DA_TERRA_KM,
    angulo_de_voo_graus,
    distancia_haversine_km,
    matriz_de_angulos_graus,
    matriz_de_distancias_km,
)

ORIGEM = Coordenada("0", 0.0, 0.0)
UNIBRASIL = Coordenada("82821020", -25.4233146347775, -49.2160678044742)
EXTRA_GUILHERME = Coordenada("24101129", -25.4083724101129, -49.2577899153158)
VIZINHO_DA_EXTRA = Coordenada("80030430", -25.4146322176159, -49.2550561883948)


def test_um_grau_de_latitude_e_um_arco_de_um_grau_do_raio_da_terra():
    um_grau_ao_norte = Coordenada("1", 1.0, 0.0)

    assert distancia_haversine_km(ORIGEM, um_grau_ao_norte) == pytest.approx(
        RAIO_DA_TERRA_KM * math.pi / 180
    )


def test_um_quarto_do_equador():
    assert distancia_haversine_km(ORIGEM, Coordenada("1", 0.0, 90.0)) == pytest.approx(
        RAIO_DA_TERRA_KM * math.pi / 2
    )


def test_distancia_documentada_da_coordenada_extra_ate_o_vizinho_mais_proximo():
    metros = distancia_haversine_km(EXTRA_GUILHERME, VIZINHO_DA_EXTRA) * 1000

    assert metros == pytest.approx(748.25, abs=0.01)


def test_distancia_e_nula_no_mesmo_ponto_e_igual_nos_dois_sentidos():
    assert distancia_haversine_km(UNIBRASIL, UNIBRASIL) == 0
    assert distancia_haversine_km(UNIBRASIL, EXTRA_GUILHERME) == distancia_haversine_km(
        EXTRA_GUILHERME, UNIBRASIL
    )


@pytest.mark.parametrize(
    ("latitude", "longitude", "angulo"),
    [(1.0, 0.0, 0.0), (0.0, 1.0, 90.0), (-1.0, 0.0, 180.0), (0.0, -1.0, 270.0)],
)
def test_angulo_de_voo_parte_do_norte_no_sentido_horario(latitude, longitude, angulo):
    destino = Coordenada("1", latitude, longitude)

    assert angulo_de_voo_graus(ORIGEM, destino) == pytest.approx(angulo)


def test_angulo_de_voo_em_direcao_intermediaria():
    # A extra fica a noroeste do campus: mais a oeste do que ao norte.
    assert 270 < angulo_de_voo_graus(UNIBRASIL, EXTRA_GUILHERME) < 315


def test_matrizes_seguem_a_ordem_das_coordenadas():
    coordenadas = [UNIBRASIL, EXTRA_GUILHERME, VIZINHO_DA_EXTRA]

    distancias = matriz_de_distancias_km(coordenadas)
    angulos = matriz_de_angulos_graus(coordenadas)

    assert [len(linha) for linha in distancias] == [3, 3, 3]
    assert distancias[1][2] == distancia_haversine_km(EXTRA_GUILHERME, VIZINHO_DA_EXTRA)
    assert distancias[2][1] == distancias[1][2]
    assert distancias[0][0] == 0
    assert angulos[0][1] == angulo_de_voo_graus(UNIBRASIL, EXTRA_GUILHERME)
    assert angulos[1][0] == angulo_de_voo_graus(EXTRA_GUILHERME, UNIBRASIL)
