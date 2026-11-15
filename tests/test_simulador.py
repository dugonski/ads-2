import math

import pytest

from src import vento
from src.contrato import Coordenada, Momento, TipoViolacao, TrechoPlanejado
from src.coordenadas import CEP_UNIBRASIL, carregar_coordenadas
from src.drone import CARGA_CHEIA
from src.geografia import RAIO_DA_TERRA_KM
from src.simulador import Simulador, custo_do_pouso_reais

LATITUDE_DA_BASE = -25.0
LONGITUDE_DA_BASE = -49.0
KM_POR_GRAU = RAIO_DA_TERRA_KM * math.pi / 180


def ao_norte_da_base(cep: str, km: float) -> Coordenada:
    return Coordenada(cep, LATITUDE_DA_BASE + km / KM_POR_GRAU, LONGITUDE_DA_BASE)


BASE = Coordenada(CEP_UNIBRASIL, LATITUDE_DA_BASE, LONGITUDE_DA_BASE)
# Sem vento e a 36 km/h cada km leva 100 s: base-PERTO 501 s, PERTO-MEDIO 501 s
# e MEDIO-base 1002 s, já com o arredondamento para cima.
PERTO = ao_norte_da_base("00000001", 5.005)
MEDIO = ao_norte_da_base("00000002", 10.013)


@pytest.fixture
def sem_vento(monkeypatch):
    calmaria = tuple(vento.Vento(0, "N") for _ in range(5))
    monkeypatch.setattr(vento, "PREVISAO", {dia: calmaria for dia in range(1, 8)})


@pytest.fixture
def simulador():
    return Simulador([BASE, PERTO, MEDIO])


def ida_e_volta(**alteracoes_do_ultimo_trecho) -> list[TrechoPlanejado]:
    ultimo = {"cep_destino": CEP_UNIBRASIL, "velocidade_kmh": 36, "pousar": True}
    ultimo.update(alteracoes_do_ultimo_trecho)
    return [
        TrechoPlanejado(PERTO.cep, 36, pousar=False),
        TrechoPlanejado(MEDIO.cep, 36, pousar=False),
        TrechoPlanejado(**ultimo),
    ]


def tipos(resultado) -> list[TipoViolacao]:
    return [violacao.tipo for violacao in resultado.violacoes]


def test_lista_sem_o_campus_unibrasil_e_recusada():
    with pytest.raises(ValueError, match=CEP_UNIBRASIL):
        Simulador([PERTO, MEDIO])


@pytest.mark.usefixtures("sem_vento")
class TestPlanoValido:
    def test_horarios_somam_voo_e_parada(self, simulador):
        resultado = simulador.simular_plano(ida_e_volta())

        assert resultado.valido
        assert [trecho.partida.horario for trecho in resultado.trechos] == [
            "06:00:00", "06:09:21", "06:18:42",
        ]  # fmt: skip
        assert [trecho.chegada.horario for trecho in resultado.trechos] == [
            "06:09:21", "06:18:42", "06:38:16",
        ]  # fmt: skip
        assert [trecho.tempo_de_voo_s for trecho in resultado.trechos] == [501, 501, 1002]
        assert [trecho.tempo_de_parada_s for trecho in resultado.trechos] == [60, 60, 172]

    def test_totais_do_plano(self, simulador):
        resultado = simulador.simular_plano(ida_e_volta())

        assert resultado.tempo_total_de_voo_s == 561 + 561 + 1174
        assert resultado.numero_de_pousos == 1
        assert resultado.custo_dos_pousos_reais == 80

    def test_bateria_e_consumida_pelo_voo_e_pela_parada(self, simulador):
        resultado = simulador.simular_plano(ida_e_volta())

        assert [trecho.carga_restante for trecho in resultado.trechos] == [
            CARGA_CHEIA - 561 * 36**2,
            CARGA_CHEIA - (561 + 561) * 36**2,
            CARGA_CHEIA - (561 + 561 + 1174) * 36**2,
        ]

    def test_trecho_simulado_traz_origem_e_destino_para_o_csv(self, simulador):
        primeiro = simulador.simular_plano(ida_e_volta()).trechos[0]

        assert (primeiro.origem, primeiro.destino) == (BASE, PERTO)
        assert (primeiro.velocidade_kmh, primeiro.pousou) == (36, False)
        assert primeiro.partida.dia == 1

    def test_velocidade_maior_consome_mais_bateria_no_mesmo_trecho(self, simulador):
        lento = simulador.simular_trecho(
            CEP_UNIBRASIL, TrechoPlanejado(PERTO.cep, 36, False), Momento.de_horario(1, 6), CARGA_CHEIA
        )
        rapido = simulador.simular_trecho(
            CEP_UNIBRASIL, TrechoPlanejado(PERTO.cep, 72, False), Momento.de_horario(1, 6), CARGA_CHEIA
        )

        assert rapido.tempo_de_voo_s == 251
        assert rapido.carga_restante == CARGA_CHEIA - (251 + 60) * 72**2
        assert rapido.carga_restante < lento.carga_restante

    def test_pouso_troca_a_bateria_e_permite_retomar_no_dia_seguinte(self, simulador):
        plano = [
            TrechoPlanejado(PERTO.cep, 36, pousar=True),
            TrechoPlanejado(MEDIO.cep, 36, pousar=False, partida=Momento.de_horario(2, 6)),
            TrechoPlanejado(CEP_UNIBRASIL, 36, pousar=True),
        ]

        resultado = simulador.simular_plano(plano)

        assert resultado.valido
        assert resultado.trechos[1].partida == Momento.de_horario(2, 6)
        assert resultado.trechos[1].carga_restante == CARGA_CHEIA - 561 * 36**2
        assert resultado.numero_de_pousos == 2
        assert resultado.custo_dos_pousos_reais == 160

    def test_campus_pode_ser_usado_para_recarga_no_meio_do_plano(self, simulador):
        plano = [
            TrechoPlanejado(PERTO.cep, 36, pousar=False),
            TrechoPlanejado(CEP_UNIBRASIL, 36, pousar=True),
            TrechoPlanejado(MEDIO.cep, 36, pousar=False),
            TrechoPlanejado(CEP_UNIBRASIL, 36, pousar=True),
        ]

        assert simulador.simular_plano(plano).valido


@pytest.mark.usefixtures("sem_vento")
class TestCustoDoPouso:
    def test_taxa_adicional_vale_somente_depois_das_17_horas(self):
        assert custo_do_pouso_reais(Momento.de_horario(1, 17).segundo_do_dia) == 80
        assert custo_do_pouso_reais(Momento.de_horario(1, 17, 0, 1).segundo_do_dia) == 160

    def test_pouso_apos_as_17_horas_no_plano(self, simulador):
        plano = [
            TrechoPlanejado(PERTO.cep, 36, pousar=True, partida=Momento.de_horario(1, 16, 50)),
            TrechoPlanejado(MEDIO.cep, 36, pousar=False),
            TrechoPlanejado(CEP_UNIBRASIL, 36, pousar=True),
        ]

        resultado = simulador.simular_plano(plano)

        assert resultado.valido
        assert resultado.trechos[0].chegada.horario == "17:01:13"
        assert [trecho.custo_do_pouso_reais for trecho in resultado.trechos] == [160, 0, 160]

    def test_parada_para_foto_nao_tem_custo(self, simulador):
        assert simulador.simular_plano(ida_e_volta()).trechos[0].custo_do_pouso_reais == 0


@pytest.mark.usefixtures("sem_vento")
class TestBateria:
    def test_chegar_com_a_carga_exata_e_permitido(self):
        # 5528 s de voo mais 172 s de pouso esgotam os 5700 s de autonomia a 36 km/h.
        limite = ao_norte_da_base("00000003", 55.275)
        simulador = Simulador([BASE, limite])

        chegada = simulador.simular_trecho(
            CEP_UNIBRASIL, TrechoPlanejado(limite.cep, 36, True), Momento.de_horario(1, 6), CARGA_CHEIA
        )

        assert chegada.carga_restante == 0

    def test_trecho_alem_da_autonomia_esgota_a_bateria(self):
        alem_do_limite = ao_norte_da_base("00000003", 55.285)
        simulador = Simulador([BASE, alem_do_limite])
        plano = [
            TrechoPlanejado(alem_do_limite.cep, 36, pousar=True),
            TrechoPlanejado(CEP_UNIBRASIL, 36, pousar=True),
        ]

        resultado = simulador.simular_plano(plano)

        assert tipos(resultado) == [TipoViolacao.BATERIA_ESGOTADA, TipoViolacao.BATERIA_ESGOTADA]
        assert resultado.violacoes[0].indice_do_trecho == 0

    def test_velocidade_alta_reduz_o_alcance(self, simulador):
        # A 80 km/h a autonomia é de 1154 s: não cobre os 1128 s do plano mais o pouso.
        plano = [
            TrechoPlanejado(MEDIO.cep, 80, pousar=False),
            TrechoPlanejado(PERTO.cep, 80, pousar=False),
            TrechoPlanejado(CEP_UNIBRASIL, 80, pousar=True),
        ]

        resultado = simulador.simular_plano(plano)

        assert tipos(resultado) == [TipoViolacao.BATERIA_ESGOTADA]
        assert resultado.violacoes[0].indice_do_trecho == 2

    def test_sem_pouso_a_carga_nao_e_reposta(self, simulador):
        resultado = simulador.simular_plano(ida_e_volta())

        cargas = [trecho.carga_restante for trecho in resultado.trechos]
        assert cargas == sorted(cargas, reverse=True)


@pytest.mark.usefixtures("sem_vento")
class TestRegrasDeHorario:
    def test_chegada_depois_das_19_horas(self, simulador):
        plano = ida_e_volta()
        plano[0] = TrechoPlanejado(PERTO.cep, 36, pousar=True, partida=Momento.de_horario(1, 18, 59))

        resultado = simulador.simular_plano(plano)

        assert TipoViolacao.CHEGADA_APOS_O_LIMITE in tipos(resultado)
        assert resultado.violacoes[0].indice_do_trecho == 0

    def test_chegada_exatamente_as_19_horas_e_permitida(self, simulador):
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
        "partida", [Momento.de_horario(1, 5, 59, 59), Momento.de_horario(1, 19)]
    )
    def test_partida_fora_do_horario_interrompe_a_simulacao(self, simulador, partida):
        plano = ida_e_volta()
        plano[0] = TrechoPlanejado(PERTO.cep, 36, pousar=False, partida=partida)

        resultado = simulador.simular_plano(plano)

        assert resultado.trechos == ()
        assert tipos(resultado) == [
            TipoViolacao.FORA_DO_HORARIO_DE_VOO,
            TipoViolacao.CEPS_NAO_VISITADOS,
        ]

    @pytest.mark.parametrize("dia", [0, 8])
    def test_partida_fora_dos_sete_dias_interrompe_a_simulacao(self, simulador, dia):
        plano = ida_e_volta()
        plano[0] = TrechoPlanejado(PERTO.cep, 36, pousar=False, partida=Momento.de_horario(dia, 6))

        resultado = simulador.simular_plano(plano)

        assert resultado.trechos == ()
        assert tipos(resultado)[0] == TipoViolacao.FORA_DO_PRAZO

    def test_drone_no_ar_nao_pode_adiar_a_partida(self, simulador):
        resultado = simulador.simular_plano(ida_e_volta(partida=Momento.de_horario(1, 7)))

        assert tipos(resultado) == [TipoViolacao.PARTIDA_INCOMPATIVEL]
        assert resultado.violacoes[0].indice_do_trecho == 2

    def test_partida_antes_da_chegada_anterior(self, simulador):
        plano = [
            TrechoPlanejado(PERTO.cep, 36, pousar=True),
            TrechoPlanejado(MEDIO.cep, 36, pousar=False, partida=Momento.de_horario(1, 6, 5)),
            TrechoPlanejado(CEP_UNIBRASIL, 36, pousar=True),
        ]

        assert tipos(simulador.simular_plano(plano)) == [TipoViolacao.PARTIDA_INCOMPATIVEL]

    def test_drone_em_solo_pode_esperar_para_decolar(self, simulador):
        plano = ida_e_volta()
        plano[0] = TrechoPlanejado(PERTO.cep, 36, pousar=False, partida=Momento.de_horario(4, 10))

        resultado = simulador.simular_plano(plano)

        assert resultado.valido
        assert resultado.trechos[-1].chegada == Momento.de_horario(4, 10, 38, 16)


@pytest.mark.usefixtures("sem_vento")
class TestRegrasDeRota:
    def test_plano_vazio(self, simulador):
        resultado = simulador.simular_plano([])

        assert not resultado.valido
        assert tipos(resultado) == [TipoViolacao.PLANO_VAZIO, TipoViolacao.CEPS_NAO_VISITADOS]
        assert resultado.tempo_total_de_voo_s == 0

    def test_destino_desconhecido_interrompe_a_simulacao(self, simulador):
        plano = [TrechoPlanejado("99999999", 36, pousar=False), *ida_e_volta()]

        resultado = simulador.simular_plano(plano)

        assert resultado.trechos == ()
        assert tipos(resultado)[0] == TipoViolacao.CEP_DESCONHECIDO

    def test_trecho_sem_deslocamento(self, simulador):
        plano = [TrechoPlanejado(CEP_UNIBRASIL, 36, pousar=True), *ida_e_volta()]

        assert tipos(simulador.simular_plano(plano)) == [TipoViolacao.TRECHO_SEM_DESLOCAMENTO]

    @pytest.mark.parametrize("velocidade", [32, 38, 84])
    def test_velocidade_fora_das_regulagens(self, simulador, velocidade):
        resultado = simulador.simular_plano(ida_e_volta(velocidade_kmh=velocidade))

        assert TipoViolacao.VELOCIDADE_INVALIDA in tipos(resultado)

    def test_coordenada_visitada_duas_vezes(self, simulador):
        plano = [
            TrechoPlanejado(PERTO.cep, 36, pousar=False),
            TrechoPlanejado(MEDIO.cep, 36, pousar=False),
            TrechoPlanejado(PERTO.cep, 36, pousar=False),
            TrechoPlanejado(CEP_UNIBRASIL, 36, pousar=True),
        ]

        resultado = simulador.simular_plano(plano)

        assert tipos(resultado) == [TipoViolacao.CEP_REPETIDO]
        assert resultado.violacoes[0].indice_do_trecho == 2

    def test_coordenada_sem_visita(self, simulador):
        plano = [
            TrechoPlanejado(PERTO.cep, 36, pousar=False),
            TrechoPlanejado(CEP_UNIBRASIL, 36, pousar=True),
        ]

        resultado = simulador.simular_plano(plano)

        assert tipos(resultado) == [TipoViolacao.CEPS_NAO_VISITADOS]
        assert "1 coordenadas" in resultado.violacoes[0].descricao

    def test_plano_que_nao_volta_ao_campus(self, simulador):
        plano = ida_e_volta()[:2]
        plano[1] = TrechoPlanejado(MEDIO.cep, 36, pousar=True)

        assert tipos(simulador.simular_plano(plano)) == [TipoViolacao.FIM_FORA_DA_BASE]

    def test_plano_que_termina_com_o_drone_no_ar(self, simulador):
        resultado = simulador.simular_plano(ida_e_volta(pousar=False))

        assert tipos(resultado) == [TipoViolacao.FIM_SEM_POUSO]


class TestEfeitoDoVento:
    def test_vento_lateral_do_dia_2_altera_o_tempo_de_voo(self, simulador):
        # Dia 2 às 06h: vento de 20 km/h vindo de leste, perpendicular ao voo para o norte.
        trecho = simulador.simular_trecho(
            CEP_UNIBRASIL, TrechoPlanejado(PERTO.cep, 36, False), Momento.de_horario(2, 6), CARGA_CHEIA
        )

        velocidade_efetiva = math.hypot(36, 20)
        assert trecho.tempo_de_voo_s == math.ceil(5.005 * 3600 / velocidade_efetiva) == 438

    def test_bateria_usa_a_velocidade_regulada_e_nao_a_efetiva(self, simulador):
        trecho = simulador.simular_trecho(
            CEP_UNIBRASIL, TrechoPlanejado(PERTO.cep, 36, False), Momento.de_horario(2, 6), CARGA_CHEIA
        )

        assert trecho.carga_restante == CARGA_CHEIA - (438 + 60) * 36**2

    def test_vento_depende_da_coluna_do_horario_de_partida(self, simulador):
        # Dia 3: vento de NE a 17 km/h às 09h e a 8 km/h às 12h, contra o voo para o norte.
        trecho = TrechoPlanejado(PERTO.cep, 36, False)

        as_11h59 = simulador.simular_trecho(
            CEP_UNIBRASIL, trecho, Momento.de_horario(3, 11, 59, 59), CARGA_CHEIA
        )
        as_12h = simulador.simular_trecho(
            CEP_UNIBRASIL, trecho, Momento.de_horario(3, 12), CARGA_CHEIA
        )

        assert as_11h59.tempo_de_voo_s > as_12h.tempo_de_voo_s

    def test_vento_a_favor_e_mais_rapido_que_vento_contra_nas_coordenadas_reais(self):
        coordenadas = carregar_coordenadas()
        simulador_real = Simulador(coordenadas)
        vizinho_a_oeste = coordenadas[1]
        partida = Momento.de_horario(2, 6)  # vento de 20 km/h soprando para oeste

        ida = simulador_real.simular_trecho(
            CEP_UNIBRASIL, TrechoPlanejado(vizinho_a_oeste.cep, 36, True), partida, CARGA_CHEIA
        )
        volta = simulador_real.simular_trecho(
            vizinho_a_oeste.cep, TrechoPlanejado(CEP_UNIBRASIL, 36, True), partida, CARGA_CHEIA
        )

        assert ida.tempo_de_voo_s < volta.tempo_de_voo_s
