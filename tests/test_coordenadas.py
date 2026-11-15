import pytest

from src.contrato import Coordenada
from src.coordenadas import CEP_UNIBRASIL, RAIZ_DO_PROJETO, carregar_coordenadas


def test_le_colunas_na_ordem_cep_longitude_latitude(tmp_path):
    arquivo = tmp_path / "coordenadas.csv"
    arquivo.write_text(
        "cep,longitude,latitude\n"
        "82821020,-49.2160678044742,-25.4233146347775\n"
        "81350686,-49.3400481020638,-25.4936598469491\n",
        encoding="utf-8",
    )

    assert carregar_coordenadas(arquivo) == [
        Coordenada("82821020", -25.4233146347775, -49.2160678044742),
        Coordenada("81350686", -25.4936598469491, -49.3400481020638),
    ]


def test_cep_repetido_e_recusado(tmp_path):
    arquivo = tmp_path / "coordenadas.csv"
    arquivo.write_text(
        "cep,longitude,latitude\n82821020,-49.2,-25.4\n82821020,-49.3,-25.5\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="CEP repetido"):
        carregar_coordenadas(arquivo)


def test_base_consolidada_contem_a_lista_do_professor_e_as_extras():
    professor = carregar_coordenadas(RAIZ_DO_PROJETO / "data" / "coordenadas_professor.csv")
    consolidada = carregar_coordenadas()

    assert consolidada[0].cep == CEP_UNIBRASIL
    assert set(professor) < set(consolidada)
    assert Coordenada("24101129", -25.4083724101129, -49.2577899153158) in consolidada
