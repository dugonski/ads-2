"""Algoritmo genético que escolhe a ordem de visita e a velocidade de cada trecho.

O cromossomo guarda a ordem dos CEPs e a velocidade do voo que chega a cada um.
Pousos e horários de partida são derivados dele por `montar_plano`.
"""

import random
from collections.abc import Sequence
from dataclasses import dataclass

from src.contrato import Coordenada, Momento, ResultadoSimulacao, TrechoPlanejado
from src.coordenadas import CEP_UNIBRASIL
from src.drone import VELOCIDADES_PERMITIDAS
from src.geografia import distancia_haversine_km
from src.simulador import (
    BATERIA_CHEIA,
    INICIO_DOS_VOOS_S,
    ULTIMO_DIA,
    Simulador,
    problema_na_chegada,
)

# Quantos segundos de voo equivalem a um real gasto com pousos.
PESO_DO_CUSTO_EM_SEGUNDOS_POR_REAL = 15.0
PENALIDADE_DE_PLANO_INVALIDO = 1_000_000_000.0
PENALIDADE_POR_TRECHO_NAO_VOADO = 10_000.0

# Chance de cada velocidade na população aleatória: as econômicas são mais prováveis.
PESOS_DAS_VELOCIDADES_INICIAIS = [30, 25, 15, 10, 5, 4, 3, 2, 2, 2, 1, 1]

Distancias = dict[tuple[str, str], float]


@dataclass
class Individuo:
    """Cromossomo: ordem de visita e velocidade do voo que chega a cada CEP."""

    ordem_ceps: list[str]  # permutação dos CEPs, sem o campus
    velocidades: dict[str, int]  # inclui o campus, destino do último trecho
    fitness: float = float("inf")  # quanto menor, melhor

    def copia(self) -> "Individuo":
        return Individuo(self.ordem_ceps.copy(), self.velocidades.copy(), self.fitness)


def tabela_de_distancias(coordenadas: Sequence[Coordenada]) -> Distancias:
    """Distância em km entre cada par de CEPs, usada pelos operadores de rota."""
    return {
        (origem.cep, destino.cep): distancia_haversine_km(origem, destino)
        for origem in coordenadas
        for destino in coordenadas
    }


# Operadores de refinamento e mutação


def aplicar_2opt(individuo: Individuo, distancias: Distancias, max_passadas: int = 3) -> None:
    """Desfaz cruzamentos da rota invertendo sub-trechos sempre que isso a encurta."""
    rota = [CEP_UNIBRASIL] + individuo.ordem_ceps + [CEP_UNIBRASIL]
    melhorou = True
    passadas = 0

    while melhorou and passadas < max_passadas:
        melhorou = False
        passadas += 1
        for i in range(1, len(rota) - 2):
            for j in range(i + 1, len(rota) - 1):
                a, b = rota[i - 1], rota[i]
                c, d = rota[j], rota[j + 1]
                distancia_atual = distancias[(a, b)] + distancias[(c, d)]
                distancia_nova = distancias[(a, c)] + distancias[(b, d)]
                if distancia_nova + 1e-9 < distancia_atual:
                    rota[i : j + 1] = reversed(rota[i : j + 1])
                    melhorou = True

    individuo.ordem_ceps = rota[1:-1]


def mutacao_deslocamento(individuo: Individuo, distancias: Distancias) -> None:
    """Retira um CEP da rota e o reinsere onde o desvio de distância é mínimo."""
    cep_movido = individuo.ordem_ceps.pop(random.randrange(len(individuo.ordem_ceps)))
    rota = [CEP_UNIBRASIL] + individuo.ordem_ceps + [CEP_UNIBRASIL]

    def desvio(posicao: int) -> float:
        anterior, proximo = rota[posicao], rota[posicao + 1]
        return (
            distancias[(anterior, cep_movido)]
            + distancias[(cep_movido, proximo)]
            - distancias[(anterior, proximo)]
        )

    melhor_posicao = min(range(len(rota) - 1), key=desvio)
    individuo.ordem_ceps.insert(melhor_posicao, cep_movido)


def mutacao(individuo: Individuo, distancias: Distancias, taxa_mutacao: float = 0.20) -> None:
    """Aplica mutação por inversão, por deslocamento e de velocidades."""
    if random.random() < taxa_mutacao:
        i, j = sorted(random.sample(range(len(individuo.ordem_ceps)), 2))
        individuo.ordem_ceps[i : j + 1] = reversed(individuo.ordem_ceps[i : j + 1])

    if random.random() < taxa_mutacao:
        mutacao_deslocamento(individuo, distancias)

    if random.random() < taxa_mutacao:
        for cep in random.sample(sorted(individuo.velocidades), random.randint(1, 3)):
            individuo.velocidades[cep] = random.choice(VELOCIDADES_PERMITIDAS)


# População inicial


def criar_individuo_aleatorio(ceps_intermediarios: list[str]) -> Individuo:
    """Cria uma rota aleatória com velocidades iniciais econômicas."""
    ordem = ceps_intermediarios.copy()
    random.shuffle(ordem)
    destinos = ordem + [CEP_UNIBRASIL]
    sorteadas = random.choices(
        VELOCIDADES_PERMITIDAS, weights=PESOS_DAS_VELOCIDADES_INICIAIS, k=len(destinos)
    )
    return Individuo(ordem, dict(zip(destinos, sorteadas)))


def criar_individuo_vizinho_proximo(
    ceps_intermediarios: list[str], distancias: Distancias, k_vizinhos: int = 2
) -> Individuo:
    """Cria uma rota que segue para um dos vizinhos mais próximos e já sai sem cruzamentos."""
    nao_visitados = set(ceps_intermediarios)
    ordem = []
    atual = CEP_UNIBRASIL

    while nao_visitados:
        candidatos = sorted(nao_visitados, key=lambda destino: distancias[(atual, destino)])
        atual = random.choice(candidatos[:k_vizinhos])
        ordem.append(atual)
        nao_visitados.remove(atual)

    destinos = ordem + [CEP_UNIBRASIL]
    sorteadas = random.choices(VELOCIDADES_PERMITIDAS[:4], k=len(destinos))
    individuo = Individuo(ordem, dict(zip(destinos, sorteadas)))
    aplicar_2opt(individuo, distancias, max_passadas=4)
    return individuo


def gerar_populacao_inicial(
    tamanho_populacao: int,
    todos_ceps: list[str],
    distancias: Distancias,
    percentual_guiado: float = 0.20,
) -> list[Individuo]:
    """Mistura rotas guiadas pelo vizinho mais próximo com rotas aleatórias."""
    ceps_intermediarios = [cep for cep in todos_ceps if cep != CEP_UNIBRASIL]
    quantidade_guiados = int(tamanho_populacao * percentual_guiado)
    guiados = [
        criar_individuo_vizinho_proximo(ceps_intermediarios, distancias)
        for _ in range(quantidade_guiados)
    ]
    aleatorios = [
        criar_individuo_aleatorio(ceps_intermediarios)
        for _ in range(tamanho_populacao - quantidade_guiados)
    ]
    return guiados + aleatorios


# Do cromossomo ao plano de voo e à nota


def montar_plano(individuo: Individuo, simulador: Simulador) -> list[TrechoPlanejado]:
    """Traduz o cromossomo em trechos, decidindo pousos e viradas de dia.

    O drone só segue sem pousar quando, do destino, ainda alcança o ponto
    seguinte com bateria e dentro do horário. Em solo, se o próximo trecho não
    cabe no dia, a partida fica para o início do dia seguinte. O plano sai
    incompleto quando os 7 dias não bastam.
    """
    destinos = individuo.ordem_ceps + [CEP_UNIBRASIL]
    plano: list[TrechoPlanejado] = []
    origem = CEP_UNIBRASIL
    carga = BATERIA_CHEIA
    em_solo = True
    agora = Momento(1, INICIO_DOS_VOOS_S)

    for posicao, destino in enumerate(destinos):
        velocidade = individuo.velocidades[destino]
        com_pouso = TrechoPlanejado(destino, velocidade, pousar=True)
        partida_escolhida = None
        if em_solo and problema_na_chegada(
            simulador.simular_trecho(origem, com_pouso, agora, carga)
        ):
            agora = partida_escolhida = Momento(agora.dia + 1, INICIO_DOS_VOOS_S)
            if agora.dia > ULTIMO_DIA:
                break

        pousar = True
        if posicao + 1 < len(destinos):
            seguinte = destinos[posicao + 1]
            sem_pouso = simulador.simular_trecho(
                origem, TrechoPlanejado(destino, velocidade, pousar=False), agora, carga
            )
            pousar = problema_na_chegada(sem_pouso) is not None or (
                problema_na_chegada(
                    simulador.simular_trecho(
                        destino,
                        TrechoPlanejado(seguinte, individuo.velocidades[seguinte], pousar=True),
                        sem_pouso.chegada,
                        sem_pouso.carga_restante,
                    )
                )
                is not None
            )

        trecho = TrechoPlanejado(destino, velocidade, pousar, partida_escolhida)
        voo = simulador.simular_trecho(origem, trecho, agora, carga)
        plano.append(trecho)
        origem = destino
        em_solo = pousar
        carga = BATERIA_CHEIA if pousar else voo.carga_restante
        agora = voo.chegada

    return plano


def calcular_fitness(resultado: ResultadoSimulacao, total_de_trechos: int) -> float:
    """Nota do plano: tempo de voo mais o custo dos pousos convertido em segundos.

    Plano inválido recebe uma penalidade que diminui quanto mais trechos ele
    consegue voar, para a evolução caminhar em direção aos planos válidos.
    """
    if not resultado.valido:
        trechos_nao_voados = total_de_trechos - len(resultado.trechos)
        return (
            PENALIDADE_DE_PLANO_INVALIDO + PENALIDADE_POR_TRECHO_NAO_VOADO * trechos_nao_voados
        )
    return (
        resultado.tempo_total_de_voo_s
        + resultado.custo_dos_pousos_reais * PESO_DO_CUSTO_EM_SEGUNDOS_POR_REAL
    )


def avaliar(individuo: Individuo, simulador: Simulador) -> ResultadoSimulacao:
    """Simula o plano do indivíduo e grava a nota nele."""
    resultado = simulador.simular_plano(montar_plano(individuo, simulador))
    individuo.fitness = calcular_fitness(resultado, len(individuo.ordem_ceps) + 1)
    return resultado


# Seleção, crossover e laço principal


def selecao_torneio(populacao: list[Individuo], tamanho_torneio: int = 3) -> Individuo:
    """Seleciona o melhor entre competidores sorteados."""
    return min(random.sample(populacao, tamanho_torneio), key=lambda ind: ind.fitness)


def crossover_ox1(pai1: Individuo, pai2: Individuo) -> Individuo:
    """Order Crossover (OX1): cada CEP leva junto a velocidade do pai de onde veio."""
    tamanho = len(pai1.ordem_ceps)
    inicio, fim = sorted(random.sample(range(tamanho), 2))

    do_pai1 = pai1.ordem_ceps[inicio:fim]
    herdados_do_pai1 = set(do_pai1)
    do_pai2 = [cep for cep in pai2.ordem_ceps if cep not in herdados_do_pai1]
    ordem = do_pai2[:inicio] + do_pai1 + do_pai2[inicio:]

    velocidades = {
        cep: (pai1 if cep in herdados_do_pai1 else pai2).velocidades[cep] for cep in ordem
    }
    velocidades[CEP_UNIBRASIL] = random.choice((pai1, pai2)).velocidades[CEP_UNIBRASIL]
    return Individuo(ordem, velocidades)


def executar_algoritmo_genetico(
    simulador: Simulador,
    coordenadas: Sequence[Coordenada],
    tamanho_populacao: int = 80,
    max_geracoes: int = 400,
    geracoes_sem_melhora_limite: int = 80,
    taxa_crossover: float = 0.85,
    taxa_mutacao: float = 0.25,
    elitismo: int = 2,
    semente: int | None = None,
) -> tuple[Individuo, ResultadoSimulacao, list[float]]:
    """Evolui a população e devolve o melhor indivíduo, seu plano simulado e o histórico.

    Para quando atinge `max_geracoes` ou fica `geracoes_sem_melhora_limite`
    gerações sem melhorar. A mesma `semente` reproduz a mesma execução.
    """
    random.seed(semente)
    distancias = tabela_de_distancias(coordenadas)
    todos_ceps = [coordenada.cep for coordenada in coordenadas]
    populacao = gerar_populacao_inicial(tamanho_populacao, todos_ceps, distancias)

    melhor = Individuo([], {})
    melhor_resultado = ResultadoSimulacao((), ())
    historico_fitness: list[float] = []
    geracoes_sem_melhora = 0

    for geracao in range(1, max_geracoes + 1):
        for individuo in populacao:
            avaliar(individuo, simulador)
        populacao.sort(key=lambda ind: ind.fitness)

        # O 2-opt só substitui o melhor da geração se a nota realmente melhorar.
        refinado = populacao[0].copia()
        aplicar_2opt(refinado, distancias, max_passadas=2)
        avaliar(refinado, simulador)
        if refinado.fitness < populacao[0].fitness:
            populacao[0] = refinado

        if populacao[0].fitness < melhor.fitness:
            melhor = populacao[0].copia()
            melhor_resultado = avaliar(melhor, simulador)
            geracoes_sem_melhora = 0
        else:
            geracoes_sem_melhora += 1
        historico_fitness.append(melhor.fitness)

        if geracao == 1 or geracao % 10 == 0:
            print(
                f"Geração {geracao:03d} | Fitness: {melhor.fitness:.2f} | "
                f"Válido: {melhor_resultado.valido} | "
                f"Tempo de voo: {melhor_resultado.tempo_total_de_voo_s} s | "
                f"Pousos: {melhor_resultado.numero_de_pousos} | "
                f"Custo: R$ {melhor_resultado.custo_dos_pousos_reais}"
            )

        if geracoes_sem_melhora >= geracoes_sem_melhora_limite:
            print(f"Parada na geração {geracao}: {geracoes_sem_melhora} gerações sem melhora.")
            break

        nova_populacao = [individuo.copia() for individuo in populacao[:elitismo]]
        while len(nova_populacao) < tamanho_populacao:
            pai1 = selecao_torneio(populacao)
            pai2 = selecao_torneio(populacao)
            if random.random() < taxa_crossover:
                filho = crossover_ox1(pai1, pai2)
            else:
                filho = Individuo(pai1.ordem_ceps.copy(), pai1.velocidades.copy())
            mutacao(filho, distancias, taxa_mutacao)
            nova_populacao.append(filho)
        populacao = nova_populacao

    return melhor, melhor_resultado, historico_fitness
