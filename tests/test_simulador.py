import math

import pytest

from src import vento
from src.contrato import Coordenada, Momento, TrechoPlanejado
from src.coordenadas import CEP_UNIBRASIL, carregar_coordenadas
from src.geografia import RAIO_DA_TERRA_KM
from src.simulador import (
    BATERIA_CHEIA,
    RESERVA_DE_SEGURANCA_DA_BATERIA,
    Simulador,
    custo_do_pouso_reais,
)

KM_POR_GRAU = RAIO_DA_TERRA_KM * math.pi / 180
AUTONOMIA_A_36_KMH_S = 5700
SEIS_DA_MANHA = Momento.de_horario(1, 6)


def ao_norte_da_base(cep: str, km: float) -> Coordenada:
    return Coordenada(cep, -25.0 + km / KM_POR_GRAU, -49.0)


BASE = Coordenada(CEP_UNIBRASIL, -25.0, -49.0)
# Sem vento e a 36 km/h cada km leva 100 s: base-PERTO 501 s, PERTO-MEDIO 501 s
# e MEDIO-base 1002 s, já com o arredondamento para cima.
PERTO = ao_norte_da_base("00000001", 5.005)
MEDIO = ao_norte_da_base("00000002", 10.013)


@pytest.fixture
def sem_vento(monkeypatch):
    calmaria = tuple(vento.Vento(0, "N") for _ in range(5))
    monkeypatch.setattr(vento, "PREVISAO", {dia: calmaria for dia in range(1, 8)})


@pytest.fixture
def simulador(sem_vento):
    return Simulador([BASE, PERTO, MEDIO])


def ida_e_volta(**alteracoes_do_ultimo_trecho) -> list[TrechoPlanejado]:
    ultimo = {"cep_destino": CEP_UNIBRASIL, "velocidade_kmh": 36, "pousar": True}
    ultimo.update(alteracoes_do_ultimo_trecho)
    return [
        TrechoPlanejado(PERTO.cep, 36, pousar=False),
        TrechoPlanejado(MEDIO.cep, 36, pousar=False),
        TrechoPlanejado(**ultimo),
    ]


def unica_violacao(resultado) -> str:
    assert len(resultado.violacoes) == 1
    return resultado.violacoes[0]


def test_lista_sem_o_campus_unibrasil_e_recusada():
    with pytest.raises(ValueError, match=CEP_UNIBRASIL):
        Simulador([PERTO, MEDIO])


# Plano válido


def test_horarios_somam_voo_e_parada(simulador):
    resultado = simulador.simular_plano(ida_e_volta())

    assert resultado.valido
    assert [trecho.partida.horario for trecho in resultado.trechos] == [
        "06:00:00", "06:09:21", "06:18:42",
    ]  # fmt: skip
    assert [trecho.chegada.horario for trecho in resultado.trechos] == [
        "06:09:21", "06:18:42", "06:38:16",
    ]  # fmt: skip
    assert [trecho.duracao_s for trecho in resultado.trechos] == [501 + 60, 501 + 60, 1002 + 172]


def test_totais_do_plano(simulador):
    resultado = simulador.simular_plano(ida_e_volta())

    assert resultado.tempo_total_de_voo_s == 561 + 561 + 1174
    assert resultado.numero_de_pousos == 1
    assert resultado.custo_dos_pousos_reais == 80


def test_trecho_simulado_traz_os_dados_da_linha_do_csv(simulador):
    primeiro = simulador.simular_plano(ida_e_volta()).trechos[0]

    assert (primeiro.origem, primeiro.destino) == (BASE, PERTO)
    assert (primeiro.velocidade_kmh, primeiro.pousou) == (36, False)
    assert primeiro.partida == SEIS_DA_MANHA


def test_campus_pode_ser_usado_para_recarga_no_meio_do_plano(simulador):
    plano = [
        TrechoPlanejado(PERTO.cep, 36, pousar=False),
        TrechoPlanejado(CEP_UNIBRASIL, 36, pousar=True),
        TrechoPlanejado(MEDIO.cep, 36, pousar=False),
        TrechoPlanejado(CEP_UNIBRASIL, 36, pousar=True),
    ]

    assert simulador.simular_plano(plano).valido


# Bateria


def test_bateria_e_consumida_pelo_voo_e_pela_parada(simulador):
    resultado = simulador.simular_plano(ida_e_volta())

    assert [trecho.carga_restante for trecho in resultado.trechos] == pytest.approx(
        [
            1 - 561 / AUTONOMIA_A_36_KMH_S,
            1 - (561 + 561) / AUTONOMIA_A_36_KMH_S,
            1 - (561 + 561 + 1174) / AUTONOMIA_A_36_KMH_S,
        ]
    )


def test_velocidade_maior_consome_mais_bateria_no_mesmo_trecho(simulador):
    rapido = simulador.simular_trecho(
        CEP_UNIBRASIL, TrechoPlanejado(PERTO.cep, 72, False), SEIS_DA_MANHA, BATERIA_CHEIA
    )

    # A 72 km/h o voo leva metade do tempo, mas a autonomia cai para um quarto.
    assert rapido.duracao_s == 251 + 60
    assert rapido.carga_restante == pytest.approx(1 - 311 / (AUTONOMIA_A_36_KMH_S / 4))


def test_pouso_troca_a_bateria_e_permite_retomar_no_dia_seguinte(simulador):
    plano = [
        TrechoPlanejado(PERTO.cep, 36, pousar=True),
        TrechoPlanejado(MEDIO.cep, 36, pousar=False, partida=Momento.de_horario(2, 6)),
        TrechoPlanejado(CEP_UNIBRASIL, 36, pousar=True),
    ]

    resultado = simulador.simular_plano(plano)

    assert resultado.valido
    assert resultado.trechos[1].partida == Momento.de_horario(2, 6)
    assert resultado.trechos[1].carga_restante == pytest.approx(1 - 561 / AUTONOMIA_A_36_KMH_S)
    assert resultado.numero_de_pousos == 2
    assert resultado.custo_dos_pousos_reais == 160


def test_reserva_de_seguranca_limita_o_alcance(sem_vento):
    # Com 1% de reserva sobram 5643 s a 36 km/h: 5471 s de voo (54,71 km) mais 172 s de pouso.
    dentro = ao_norte_da_base("00000003", 54.0)
    fora = ao_norte_da_base("00000004", 55.0)
    simulador = Simulador([BASE, dentro, fora])

    resultado = simulador.simular_plano(
        [
            TrechoPlanejado(dentro.cep, 36, pousar=True),
            TrechoPlanejado(CEP_UNIBRASIL, 36, pousar=True),
            TrechoPlanejado(fora.cep, 36, pousar=True),
        ]
    )

    assert [len(resultado.trechos), resultado.violacoes[0]] == [
        3,
        "Trecho 3: bateria abaixo da reserva de segurança ao fim do trecho",
    ]
    assert resultado.trechos[0].carga_restante >= RESERVA_DE_SEGURANCA_DA_BATERIA
    assert 0 < resultado.trechos[2].carga_restante < RESERVA_DE_SEGURANCA_DA_BATERIA


def test_plano_que_esgotaria_a_bateria_para_no_trecho_do_problema(simulador):
    # A 80 km/h a autonomia é de 1154 s: não cobre os 1128 s do plano mais o pouso.
    plano = [
        TrechoPlanejado(MEDIO.cep, 80, pousar=False),
        TrechoPlanejado(PERTO.cep, 80, pousar=False),
        TrechoPlanejado(CEP_UNIBRASIL, 80, pousar=True),
    ]

    resultado = simulador.simular_plano(plano)

    assert unica_violacao(resultado) == "Trecho 3: bateria abaixo da reserva de segurança ao fim do trecho"
    assert resultado.trechos[-1].carga_restante < 0


# Custo do pouso


def test_taxa_adicional_vale_somente_depois_das_17_horas():
    assert custo_do_pouso_reais(Momento.de_horario(1, 17).segundo_do_dia) == 80
    assert custo_do_pouso_reais(Momento.de_horario(1, 17, 0, 1).segundo_do_dia) == 160


def test_pouso_apos_as_17_horas_no_plano(simulador):
    plano = [
        TrechoPlanejado(PERTO.cep, 36, pousar=True, partida=Momento.de_horario(1, 16, 50)),
        TrechoPlanejado(MEDIO.cep, 36, pousar=False),
        TrechoPlanejado(CEP_UNIBRASIL, 36, pousar=True),
    ]

    resultado = simulador.simular_plano(plano)

    assert resultado.valido
    assert resultado.trechos[0].chegada.horario == "17:01:13"
    assert [trecho.custo_do_pouso_reais for trecho in resultado.trechos] == [160, 0, 160]


# Regras de horário


def test_chegada_depois_das_19_horas(simulador):
    plano = ida_e_volta()
    plano[0] = TrechoPlanejado(PERTO.cep, 36, pousar=True, partida=Momento.de_horario(1, 18, 59))

    resultado = simulador.simular_plano(plano)

    assert "Trecho 1: chegada às 19:10:13" in resultado.violacoes[0]


def test_chegada_exatamente_as_19_horas_e_permitida(simulador):
    duracao_dos_dois_ultimos_trechos = 561 + 1174
    plano = [
        TrechoPlanejado(PERTO.cep, 36, pousar=True),
        TrechoPlanejado(
            MEDIO.cep,
            36,
            pousar=False,
            partida=Momento.de_horario(1, 19).apos(-duracao_dos_dois_ultimos_trechos),
        ),
        TrechoPlanejado(CEP_UNIBRASIL, 36, pousar=True),
    ]

    resultado = simulador.simular_plano(plano)

    assert resultado.valido
    assert resultado.trechos[-1].chegada.horario == "19:00:00"


@pytest.mark.parametrize(
    ("partida", "mensagem"),
    [
        (Momento.de_horario(2, 5, 59, 59), "partida às 05:59:59, fora do horário de voo"),
        (Momento.de_horario(1, 19), "partida às 19:00:00, fora do horário de voo"),
        (Momento.de_horario(8, 6), "partida no dia 8, fora do prazo de 7 dias"),
    ],
)
def test_partida_fora_do_horario_ou_do_prazo(simulador, partida, mensagem):
    plano = ida_e_volta()
    plano[0] = TrechoPlanejado(PERTO.cep, 36, pousar=False, partida=partida)

    resultado = simulador.simular_plano(plano)

    assert resultado.trechos == ()
    assert unica_violacao(resultado) == f"Trecho 1: {mensagem}"


def test_drone_no_ar_nao_pode_adiar_a_partida(simulador):
    resultado = simulador.simular_plano(ida_e_volta(partida=Momento.de_horario(1, 7)))

    assert unica_violacao(resultado) == "Trecho 3: partida incompatível com a chegada anterior"


def test_partida_antes_da_chegada_anterior(simulador):
    plano = [
        TrechoPlanejado(PERTO.cep, 36, pousar=True),
        TrechoPlanejado(MEDIO.cep, 36, pousar=False, partida=Momento.de_horario(1, 6, 5)),
        TrechoPlanejado(CEP_UNIBRASIL, 36, pousar=True),
    ]

    resultado = simulador.simular_plano(plano)

    assert unica_violacao(resultado) == "Trecho 2: partida incompatível com a chegada anterior"


def test_drone_em_solo_pode_esperar_para_decolar(simulador):
    plano = ida_e_volta()
    plano[0] = TrechoPlanejado(PERTO.cep, 36, pousar=False, partida=Momento.de_horario(4, 10))

    resultado = simulador.simular_plano(plano)

    assert resultado.valido
    assert resultado.trechos[-1].chegada == Momento.de_horario(4, 10, 38, 16)


# Regras de rota


def test_plano_vazio(simulador):
    resultado = simulador.simular_plano([])

    assert unica_violacao(resultado) == "Plano sem trechos"
    assert resultado.tempo_total_de_voo_s == 0


def test_destino_desconhecido(simulador):
    plano = [TrechoPlanejado("99999999", 36, pousar=False), *ida_e_volta()]

    resultado = simulador.simular_plano(plano)

    assert resultado.trechos == ()
    assert unica_violacao(resultado) == "Trecho 1: CEP 99999999 fora da lista de coordenadas"


def test_trecho_sem_deslocamento(simulador):
    plano = [TrechoPlanejado(CEP_UNIBRASIL, 36, pousar=True), *ida_e_volta()]

    assert unica_violacao(simulador.simular_plano(plano)) == "Trecho 1: origem e destino iguais"


@pytest.mark.parametrize("velocidade", [32, 38, 83, 84])
def test_velocidade_fora_das_regulagens(simulador, velocidade):
    resultado = simulador.simular_plano(ida_e_volta(velocidade_kmh=velocidade))

    assert unica_violacao(resultado) == (
        f"Trecho 3: velocidade de {velocidade} km/h fora das regulagens do drone"
    )


def test_coordenada_visitada_duas_vezes(simulador):
    plano = [
        TrechoPlanejado(PERTO.cep, 36, pousar=False),
        TrechoPlanejado(MEDIO.cep, 36, pousar=False),
        TrechoPlanejado(PERTO.cep, 36, pousar=False),
        TrechoPlanejado(CEP_UNIBRASIL, 36, pousar=True),
    ]

    resultado = simulador.simular_plano(plano)

    assert unica_violacao(resultado) == f"CEPs visitados mais de uma vez: {PERTO.cep}"


def test_coordenada_sem_visita(simulador):
    plano = [
        TrechoPlanejado(PERTO.cep, 36, pousar=False),
        TrechoPlanejado(CEP_UNIBRASIL, 36, pousar=True),
    ]

    assert unica_violacao(simulador.simular_plano(plano)) == "1 CEPs sem visita"


def test_plano_que_nao_volta_ao_campus(simulador):
    plano = ida_e_volta()[:2]
    plano[1] = TrechoPlanejado(MEDIO.cep, 36, pousar=True)

    assert unica_violacao(simulador.simular_plano(plano)) == (
        "O plano não termina no campus Unibrasil"
    )


def test_plano_que_termina_com_o_drone_no_ar(simulador):
    resultado = simulador.simular_plano(ida_e_volta(pousar=False))

    assert unica_violacao(resultado) == "O plano termina com o drone no ar"


# Efeito do vento, com a previsão real


def test_vento_lateral_altera_o_tempo_de_voo_mas_nao_o_consumo_por_segundo():
    # Dia 2 às 06h: vento de 20 km/h vindo de leste, perpendicular ao voo para o norte.
    simulador = Simulador([BASE, PERTO])

    trecho = simulador.simular_trecho(
        CEP_UNIBRASIL, TrechoPlanejado(PERTO.cep, 36, False), Momento.de_horario(2, 6), BATERIA_CHEIA
    )

    tempo_de_voo = math.ceil(5.005 * 3600 / math.hypot(36, 20))
    assert tempo_de_voo == 438
    assert trecho.duracao_s == tempo_de_voo + 60
    assert trecho.carga_restante == pytest.approx(1 - (438 + 60) / AUTONOMIA_A_36_KMH_S)


def test_vento_depende_da_coluna_do_horario_de_partida():
    # Dia 3: vento de NE a 17 km/h às 09h e a 8 km/h às 12h, contra o voo para o norte.
    simulador = Simulador([BASE, PERTO])
    trecho = TrechoPlanejado(PERTO.cep, 36, False)

    as_11h59 = simulador.simular_trecho(
        CEP_UNIBRASIL, trecho, Momento.de_horario(3, 11, 59, 59), BATERIA_CHEIA
    )
    as_12h = simulador.simular_trecho(CEP_UNIBRASIL, trecho, Momento.de_horario(3, 12), BATERIA_CHEIA)

    assert as_11h59.duracao_s > as_12h.duracao_s


def test_vento_a_favor_e_mais_rapido_que_vento_contra_nas_coordenadas_reais():
    coordenadas = carregar_coordenadas()
    simulador = Simulador(coordenadas)
    vizinho_a_oeste = coordenadas[1]
    partida = Momento.de_horario(2, 6)  # vento de 20 km/h soprando para oeste

    ida = simulador.simular_trecho(
        CEP_UNIBRASIL, TrechoPlanejado(vizinho_a_oeste.cep, 36, True), partida, BATERIA_CHEIA
    )
    volta = simulador.simular_trecho(
        vizinho_a_oeste.cep, TrechoPlanejado(CEP_UNIBRASIL, 36, True), partida, BATERIA_CHEIA
    )

    assert ida.duracao_s < volta.duracao_s
