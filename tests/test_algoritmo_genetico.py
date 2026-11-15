import math
import random

import pytest

from src import vento
from src.algoritmo_genetico import (
    PENALIDADE_DE_PLANO_INVALIDO,
    PESO_DO_CUSTO_EM_SEGUNDOS_POR_REAL,
    Individuo,
    aplicar_2opt,
    avaliar,
    calcular_fitness,
    criar_individuo_aleatorio,
    crossover_ox1,
    executar_algoritmo_genetico,
    gerar_populacao_inicial,
    montar_plano,
    mutacao,
    selecao_torneio,
    tabela_de_distancias,
)
from src.contrato import Coordenada, Momento, TrechoPlanejado
from src.coordenadas import CEP_UNIBRASIL
from src.drone import VELOCIDADES_PERMITIDAS
from src.geografia import RAIO_DA_TERRA_KM
from src.simulador import RESERVA_DE_SEGURANCA_DA_BATERIA, Simulador

KM_POR_GRAU = RAIO_DA_TERRA_KM * math.pi / 180
LATITUDE_DA_BASE = -25.0
LONGITUDE_DA_BASE = -49.0


def ponto(cep: str, km_ao_norte: float, km_a_leste: float = 0.0) -> Coordenada:
    km_por_grau_de_longitude = KM_POR_GRAU * math.cos(math.radians(LATITUDE_DA_BASE))
    return Coordenada(
        cep,
        LATITUDE_DA_BASE + km_ao_norte / KM_POR_GRAU,
        LONGITUDE_DA_BASE + km_a_leste / km_por_grau_de_longitude,
    )


BASE = ponto(CEP_UNIBRASIL, 0)
# Quadrado de 2 km de lado com a base em um canto e um ponto no centro.
QUADRADO = [BASE, ponto("A", 2), ponto("B", 2, 2), ponto("C", 0, 2), ponto("D", 1, 1)]
CEPS_DO_QUADRADO = {"A", "B", "C", "D"}


@pytest.fixture(autouse=True)
def sem_vento_e_com_semente(monkeypatch):
    calmaria = tuple(vento.Vento(0, "N") for _ in range(5))
    monkeypatch.setattr(vento, "PREVISAO", {dia: calmaria for dia in range(1, 8)})
    random.seed(7)


def individuo(ordem: list[str], velocidade: int = 36) -> Individuo:
    return Individuo(ordem, dict.fromkeys([*ordem, CEP_UNIBRASIL], velocidade))


def cromossomo_integro(candidato: Individuo, ceps: set[str]) -> bool:
    return (
        sorted(candidato.ordem_ceps) == sorted(ceps)
        and set(candidato.velocidades) == ceps | {CEP_UNIBRASIL}
        and all(v in VELOCIDADES_PERMITIDAS for v in candidato.velocidades.values())
    )


# Operadores genéticos


def test_populacao_inicial_tem_cromossomos_integros():
    distancias = tabela_de_distancias(QUADRADO)
    ceps = [coordenada.cep for coordenada in QUADRADO]

    populacao = gerar_populacao_inicial(10, ceps, distancias)

    assert len(populacao) == 10
    assert all(cromossomo_integro(candidato, CEPS_DO_QUADRADO) for candidato in populacao)


def test_crossover_ox1_preserva_a_permutacao_e_herda_velocidade_junto_com_o_cep():
    pai1 = individuo(["A", "B", "C", "D"], velocidade=36)
    pai2 = individuo(["D", "C", "B", "A"], velocidade=80)

    for _ in range(20):
        filho = crossover_ox1(pai1, pai2)

        assert cromossomo_integro(filho, CEPS_DO_QUADRADO)
        # Os CEPs herdados do pai 1 ficam juntos, na ordem dele e com a velocidade dele.
        do_pai1 = [cep for cep in filho.ordem_ceps if filho.velocidades[cep] == 36]
        assert "".join(do_pai1) in "ABCD"


def test_2opt_desfaz_o_cruzamento_da_rota():
    distancias = tabela_de_distancias(QUADRADO[:4])
    cruzada = individuo(["B", "A", "C"])

    aplicar_2opt(cruzada, distancias)

    assert cruzada.ordem_ceps in (["A", "B", "C"], ["C", "B", "A"])


def test_mutacao_mantem_o_cromossomo_integro():
    distancias = tabela_de_distancias(QUADRADO)

    for _ in range(20):
        mutante = individuo(["A", "B", "C", "D"])
        mutacao(mutante, distancias, taxa_mutacao=1.0)

        assert cromossomo_integro(mutante, CEPS_DO_QUADRADO)


def test_mutacao_com_taxa_zero_nao_altera_o_individuo():
    original = individuo(["A", "B", "C", "D"])
    mutante = original.copia()

    mutacao(mutante, tabela_de_distancias(QUADRADO), taxa_mutacao=0.0)

    assert mutante == original


def test_individuo_aleatorio_prefere_velocidades_economicas():
    ceps = [str(numero) for numero in range(500)]

    velocidades = list(criar_individuo_aleatorio(ceps).velocidades.values())

    assert velocidades.count(36) > velocidades.count(80)


def test_torneio_escolhe_o_menor_fitness_entre_os_sorteados():
    populacao = [Individuo([], {}, fitness=nota) for nota in (30.0, 10.0, 20.0)]

    assert selecao_torneio(populacao, tamanho_torneio=3).fitness == 10.0


# Montagem do plano


def test_plano_curto_e_voado_sem_pousos_intermediarios():
    simulador = Simulador(QUADRADO)

    plano = montar_plano(individuo(["A", "B", "C", "D"]), simulador)

    assert [trecho.cep_destino for trecho in plano] == ["A", "B", "C", "D", CEP_UNIBRASIL]
    assert [trecho.pousar for trecho in plano] == [False, False, False, False, True]
    assert simulador.simular_plano(plano).valido


def test_plano_pousa_antes_de_faltar_bateria():
    # A 80 km/h a autonomia é de 1154 s: depois de M e P, a volta com pouso não cabe.
    coordenadas = [BASE, ponto("P", 5.005), ponto("M", 10.013)]
    simulador = Simulador(coordenadas)

    plano = montar_plano(individuo(["M", "P"], velocidade=80), simulador)

    resultado = simulador.simular_plano(plano)
    assert [trecho.pousar for trecho in plano] == [False, True, True]
    assert resultado.valido
    assert all(
        trecho.carga_restante >= RESERVA_DE_SEGURANCA_DA_BATERIA for trecho in resultado.trechos
    )


def test_plano_que_nao_cabe_em_um_dia_continua_no_dia_seguinte():
    # 11 pontos no contorno de um quadrado de 120 km: 12 trechos de 40 km levam mais de 13 h.
    contorno = [(40, 0), (80, 0), (120, 0), (120, 40), (120, 80), (120, 120)]
    contorno += [(80, 120), (40, 120), (0, 120), (0, 80), (0, 40)]
    coordenadas = [BASE] + [
        ponto(f"{numero:02d}", norte, leste) for numero, (norte, leste) in enumerate(contorno)
    ]
    simulador = Simulador(coordenadas)
    ordem = [coordenada.cep for coordenada in coordenadas[1:]]

    plano = montar_plano(individuo(ordem), simulador)
    resultado = simulador.simular_plano(plano)

    assert resultado.valido
    assert all(trecho.pousar for trecho in plano)
    assert [trecho.partida for trecho in plano if trecho.partida] == [Momento.de_horario(2, 6)]
    assert resultado.trechos[-1].chegada.dia == 2


def test_trecho_alem_da_autonomia_gera_plano_invalido_e_penalizado():
    # 60 km a 36 km/h passam dos 5700 s de autonomia.
    simulador = Simulador([BASE, ponto("LONGE", 60)])
    candidato = individuo(["LONGE"])

    resultado = avaliar(candidato, simulador)

    assert "reserva de segurança" in resultado.violacoes[0]
    assert candidato.fitness >= PENALIDADE_DE_PLANO_INVALIDO


def test_plano_fica_incompleto_quando_o_prazo_nao_basta(monkeypatch):
    monkeypatch.setattr("src.algoritmo_genetico.ULTIMO_DIA", 1)
    contorno = [(40, 0), (80, 0), (120, 0), (120, 40), (120, 80), (120, 120)]
    contorno += [(80, 120), (40, 120), (0, 120), (0, 80), (0, 40)]
    coordenadas = [BASE] + [
        ponto(f"{numero:02d}", norte, leste) for numero, (norte, leste) in enumerate(contorno)
    ]
    ordem = [coordenada.cep for coordenada in coordenadas[1:]]

    plano = montar_plano(individuo(ordem), Simulador(coordenadas))

    assert len(plano) == 11
    assert plano[-1].cep_destino != CEP_UNIBRASIL


# Fitness


def test_fitness_soma_tempo_de_voo_e_custo_dos_pousos():
    simulador = Simulador(QUADRADO)
    candidato = individuo(["A", "B", "C", "D"])

    resultado = avaliar(candidato, simulador)

    assert resultado.custo_dos_pousos_reais == 80
    assert candidato.fitness == (
        resultado.tempo_total_de_voo_s + 80 * PESO_DO_CUSTO_EM_SEGUNDOS_POR_REAL
    )


def test_plano_invalido_e_pior_que_qualquer_valido_e_melhora_quanto_mais_voa():
    simulador = Simulador(QUADRADO)
    valido = simulador.simular_plano(montar_plano(individuo(["A", "B", "C", "D"]), simulador))
    parou_no_primeiro = simulador.simular_plano([TrechoPlanejado("A", 38, pousar=True)])
    parou_no_segundo = simulador.simular_plano(
        [TrechoPlanejado("A", 36, pousar=False), TrechoPlanejado("B", 38, pousar=True)]
    )

    nota_valida = calcular_fitness(valido, total_de_trechos=5)
    nota_do_primeiro = calcular_fitness(parou_no_primeiro, total_de_trechos=5)
    nota_do_segundo = calcular_fitness(parou_no_segundo, total_de_trechos=5)

    assert nota_valida < PENALIDADE_DE_PLANO_INVALIDO <= nota_do_segundo < nota_do_primeiro


# Laço evolutivo


def test_execucao_encontra_a_volta_pelo_contorno_do_quadrado(capsys):
    simulador = Simulador(QUADRADO[:4])

    melhor, resultado, historico = executar_algoritmo_genetico(
        simulador, QUADRADO[:4], tamanho_populacao=8, max_geracoes=12, semente=1
    )

    assert resultado.valido
    assert melhor.ordem_ceps in (["A", "B", "C"], ["C", "B", "A"])
    assert historico == sorted(historico, reverse=True)
    assert "Geração 001" in capsys.readouterr().out


def test_execucao_para_apos_o_limite_de_geracoes_sem_melhora(capsys):
    simulador = Simulador(QUADRADO)

    _, _, historico = executar_algoritmo_genetico(
        simulador,
        QUADRADO,
        tamanho_populacao=8,
        max_geracoes=200,
        geracoes_sem_melhora_limite=5,
        semente=1,
    )

    assert len(historico) < 200
    assert historico[-6:] == [historico[-1]] * 6
    assert "5 gerações sem melhora" in capsys.readouterr().out


def test_mesma_semente_reproduz_a_mesma_execucao():
    simulador = Simulador(QUADRADO)
    parametros = {"tamanho_populacao": 8, "max_geracoes": 5, "taxa_crossover": 0.5, "semente": 3}

    primeira = executar_algoritmo_genetico(simulador, QUADRADO, **parametros)
    segunda = executar_algoritmo_genetico(simulador, QUADRADO, **parametros)

    assert primeira[0] == segunda[0]
    assert primeira[2] == segunda[2]
