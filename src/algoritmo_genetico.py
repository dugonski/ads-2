import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from contrato import ResultadoSimulacao, TrechoPlanejado


#CONSTANTES DO PROBLEMA
VELOCIDADES_VALIDAS = [36, 40, 44, 48, 52, 56, 60, 64, 68, 72, 76, 80]
CEP_BASE = "82821020"
AUTONOMIA_NOMINAL_CURITIBA = 5000.0 * 1.14 
PESO_CUSTO_FINANCEIRO = 15.0


#REPRESENTAÇÃO DO INDIVÍDUO (CROMOSSOMO)
@dataclass
class Individuo:
    ordem_ceps: List[str]          # Permutação dos 375 CEPs intermediários[cite: 10]
    velocidades: List[int]         # Lista com 376 velocidades (uma por trecho)[cite: 7, 8]
    fitness: float = float("inf")  # Nota da rota (quanto menor, melhor)

#OPERADORES DE REFINAMENTO E MUTAÇÃO
def aplicar_2opt(
    individuo: Individuo,
    matriz_distancias: Dict[Tuple[str, str], float],
    max_passadas: int = 3
) -> None:
    """
    Descruza linhas ('X') invertendo sub-trechos da rota sempre que
    a troca diminuir a distância total percorrida.
    """
    rota = [CEP_BASE] + individuo.ordem_ceps + [CEP_BASE]
    n = len(rota)
    melhorou = True
    passadas = 0

    while melhorou and passadas < max_passadas:
        melhorou = False
        passadas += 1
        for i in range(1, n - 2):
            for j in range(i + 1, n - 1):
                a, b = rota[i - 1], rota[i]
                c, d = rota[j], rota[j + 1]

                dist_atual = matriz_distancias[(a, b)] + matriz_distancias[(c, d)]
                dist_nova = matriz_distancias[(a, c)] + matriz_distancias[(b, d)]

                if dist_nova + 1e-6 < dist_atual:
                    rota[i:j + 1] = reversed(rota[i:j + 1])
                    melhorou = True

    individuo.ordem_ceps = rota[1:-1]


def mutacao_deslocamento(
    individuo: Individuo,
    matriz_distancias: Dict[Tuple[str, str], float]
) -> None:
    """
    Remove um CEP fora de lugar e o reinsere entre dois vizinhos
    onde o desvio de distância seja mínimo (elimina 'pontas')[cite: 13].
    """
    tamanho = len(individuo.ordem_ceps)
    idx_origem = random.randrange(tamanho)

    cep_movido = individuo.ordem_ceps.pop(idx_origem)
    vel_movida = individuo.velocidades.pop(idx_origem)

    rota_temp = [CEP_BASE] + individuo.ordem_ceps + [CEP_BASE]
    melhor_pos = 0
    menor_custo_extra = float("inf")

    for pos in range(len(rota_temp) - 1):
        anterior = rota_temp[pos]
        proximo = rota_temp[pos + 1]
        custo_extra = (
            matriz_distancias[(anterior, cep_movido)]
            + matriz_distancias[(cep_movido, proximo)]
            - matriz_distancias[(anterior, proximo)]
        )
        if custo_extra < menor_custo_extra:
            menor_custo_extra = custo_extra
            melhor_pos = pos

    individuo.ordem_ceps.insert(melhor_pos, cep_movido)
    individuo.velocidades.insert(melhor_pos, vel_movida)


def mutacao(
    individuo: Individuo,
    matriz_distancias: Dict[Tuple[str, str], float],
    taxa_mutacao: float = 0.20
) -> None:
    """Aplica mutação por inversão, deslocamento e ajuste de velocidades[cite: 13]."""
    if random.random() < taxa_mutacao:
        i, j = sorted(random.sample(range(len(individuo.ordem_ceps)), 2))
        individuo.ordem_ceps[i:j + 1] = reversed(individuo.ordem_ceps[i:j + 1])

    if random.random() < taxa_mutacao:
        mutacao_deslocamento(individuo, matriz_distancias)

    if random.random() < taxa_mutacao:
        qtd_alteracoes = random.randint(1, 3)
        for _ in range(qtd_alteracoes):
            idx = random.randrange(len(individuo.velocidades))
            individuo.velocidades[idx] = random.choice(VELOCIDADES_VALIDAS)


#POPULAÇÃO INICIAL
def criar_individuo_aleatorio(ceps_intermediarios: List[str]) -> Individuo:
    """Cria uma rota aleatória com velocidades iniciais econômicas[cite: 2, 7]."""
    ordem = ceps_intermediarios.copy()
    random.shuffle(ordem)
    num_trechos = len(ordem) + 1
    pesos_velocidade = [30, 25, 15, 10, 5, 4, 3, 2, 2, 2, 1, 1]
    velocidades = random.choices(VELOCIDADES_VALIDAS, weights=pesos_velocidade, k=num_trechos)
    return Individuo(ordem_ceps=ordem, velocidades=velocidades)


def criar_individuo_vizinho_proximo(
    ceps_intermediarios: List[str],
    matriz_distancias: Dict[Tuple[str, str], float],
    k_vizinhos: int = 2
) -> Individuo:
    """Cria uma rota geograficamente organizada e já remove cruzamentos iniciais."""
    nao_visitados = set(ceps_intermediarios)
    ordem = []
    atual = CEP_BASE

    while nao_visitados:
        candidatos = sorted(
            nao_visitados,
            key=lambda destino: matriz_distancias[(atual, destino)]
        )
        escolhido = random.choice(candidatos[:k_vizinhos])
        ordem.append(escolhido)
        nao_visitados.remove(escolhido)
        atual = escolhido

    num_trechos = len(ordem) + 1
    velocidades = random.choices(VELOCIDADES_VALIDAS[:4], k=num_trechos)
    ind = Individuo(ordem_ceps=ordem, velocidades=velocidades)
    aplicar_2opt(ind, matriz_distancias, max_passadas=4)
    return ind


def gerar_populacao_inicial(
    tamanho_populacao: int,
    todos_ceps: List[str],
    matriz_distancias: Dict[Tuple[str, str], float],
    percentual_guiado: float = 0.20
) -> List[Individuo]:
    """Gera a população inicial misturando rotas guiadas (20%) e aleatórias (80%)."""
    ceps_intermediarios = [cep for cep in todos_ceps if cep != CEP_BASE]
    qtd_guiados = int(tamanho_populacao * percentual_guiado)
    qtd_aleatorios = tamanho_populacao - qtd_guiados

    populacao = []
    for _ in range(qtd_guiados):
        populacao.append(criar_individuo_vizinho_proximo(ceps_intermediarios, matriz_distancias))

    for _ in range(qtd_aleatorios):
        populacao.append(criar_individuo_aleatorio(ceps_intermediarios))

    return populacao


#DECODIFICADOR E FUNÇÃO FITNESS
def estimar_consumo_bateria(distancia_metros: float, velocidade_kmh: int) -> float:
    """Estima o gasto de bateria com margem de segurança de 35% para o vento[cite: 2, 3]."""
    velocidade_ms = velocidade_kmh / 3.6
    tempo_estimado_s = (distancia_metros / velocidade_ms) * 1.35
    fator_consumo = (velocidade_kmh / 36.0) ** 2
    return tempo_estimado_s * fator_consumo


def decodificar_individuo(
    individuo: Individuo,
    matriz_distancias: Dict[Tuple[str, str], float]
) -> List[TrechoPlanejado]:
    """Traduz o cromossomo em trechos de voo inserindo pousos seguros[cite: 2, 13]."""
    rota_completa = [CEP_BASE] + individuo.ordem_ceps + [CEP_BASE]
    plano: List[TrechoPlanejado] = []
    bateria_restante = AUTONOMIA_NOMINAL_CURITIBA
    num_trechos = len(rota_completa) - 1

    for i in range(num_trechos):
        origem = rota_completa[i]
        destino = rota_completa[i + 1]
        vel_atual = individuo.velocidades[i]

        dist_atual = matriz_distancias[(origem, destino)]
        consumo_atual = estimar_consumo_bateria(dist_atual, vel_atual)

        if i == num_trechos - 1:
            precisa_pousar = True
        else:
            proximo_destino = rota_completa[i + 2]
            vel_proxima = individuo.velocidades[i + 1]
            dist_proxima = matriz_distancias[(destino, proximo_destino)]
            consumo_proximo = estimar_consumo_bateria(dist_proxima, vel_proxima)

            energia_necessaria_sem_pouso = consumo_atual + 60.0 + consumo_proximo + 172.0
            precisa_pousar = bateria_restante < energia_necessaria_sem_pouso

        if precisa_pousar:
            bateria_restante = AUTONOMIA_NOMINAL_CURITIBA
        else:
            bateria_restante -= (consumo_atual + 60.0)

        plano.append(TrechoPlanejado(
            cep_origem=origem,
            cep_destino=destino,
            velocidade=vel_atual,
            pouso=precisa_pousar
        ))

    return plano


def calcular_fitness(resultado: ResultadoSimulacao) -> float:
    """Calcula a nota da rota (menor = melhor)[cite: 1, 11]."""
    if not resultado.valida:
        return 1_000_000_000.0 + resultado.tempo_total_segundos

    return resultado.tempo_total_segundos + (resultado.custo_total_reais * PESO_CUSTO_FINANCEIRO)


#SELEÇÃO, CROSSOVER E LOOP PRINCIPAL DO ALGORITMO GENÉTICO
def selecao_torneio(populacao: List[Individuo], tamanho_torneio: int = 3) -> Individuo:
    """Seleciona o melhor indivíduo entre 'k' competidores aleatórios[cite: 13]."""
    competidores = random.sample(populacao, tamanho_torneio)
    return min(competidores, key=lambda ind: ind.fitness)


def crossover_ox1(pai1: Individuo, pai2: Individuo) -> Individuo:
    """Order Crossover (OX1) nos CEPs + Crossover de 1 ponto nas velocidades[cite: 11, 13]."""
    tamanho = len(pai1.ordem_ceps)
    inicio, fim = sorted(random.sample(range(tamanho), 2))

    filho_ceps: List[Optional[str]] = [None] * tamanho
    filho_ceps[inicio:fim] = pai1.ordem_ceps[inicio:fim]
    ja_inseridos = set(filho_ceps[inicio:fim])

    restantes_pai2 = [cep for cep in pai2.ordem_ceps if cep not in ja_inseridos]
    idx_restante = 0
    for i in range(tamanho):
        if filho_ceps[i] is None:
            filho_ceps[i] = restantes_pai2[idx_restante]
            idx_restante += 1

    corte_vel = random.randint(1, len(pai1.velocidades) - 1)
    filho_velocidades = pai1.velocidades[:corte_vel] + pai2.velocidades[corte_vel:]

    return Individuo(ordem_ceps=filho_ceps, velocidades=filho_velocidades)  


def executar_algoritmo_genetico(
    todos_ceps: List[str],
    matriz_distancias: Dict[Tuple[str, str], float],
    funcao_avaliacao: Callable[[List[TrechoPlanejado]], ResultadoSimulacao],
    tamanho_populacao: int = 80,
    max_geracoes: int = 400,
    geracoes_sem_melhora_limite: int = 80,
    taxa_crossover: float = 0.85,
    taxa_mutacao: float = 0.25,
    elitismo: int = 2
) -> Tuple[Individuo, ResultadoSimulacao, List[float]]:
    """Executa a evolução completa e retorna a melhor rota encontrada[cite: 11, 13]."""
    populacao = gerar_populacao_inicial(tamanho_populacao, todos_ceps, matriz_distancias)

    melhor_global: Optional[Individuo] = None
    melhor_resultado: Optional[ResultadoSimulacao] = None
    historico_fitness: List[float] = []
    geracoes_sem_melhora = 0

    for geracao in range(1, max_geracoes + 1):
        for ind in populacao:
            plano = decodificar_individuo(ind, matriz_distancias)
            resultado = funcao_avaliacao(plano)
            ind.fitness = calcular_fitness(resultado)

            if melhor_global is None or ind.fitness < melhor_global.fitness:
                melhor_global = Individuo(
                    ordem_ceps=ind.ordem_ceps.copy(),
                    velocidades=ind.velocidades.copy(),
                    fitness=ind.fitness
                )
                melhor_resultado = resultado
                geracoes_sem_melhora = 0

        populacao.sort(key=lambda ind: ind.fitness)

        # Aplica refinamento 2-opt apenas no melhor indivíduo da geração para limpar cruzamentos
        aplicar_2opt(populacao[0], matriz_distancias, max_passadas=2)
        plano_elite = decodificar_individuo(populacao[0], matriz_distancias)
        res_elite = funcao_avaliacao(plano_elite)
        populacao[0].fitness = calcular_fitness(res_elite)

        if populacao[0].fitness < melhor_global.fitness:  
            melhor_global = Individuo(
                ordem_ceps=populacao[0].ordem_ceps.copy(),
                velocidades=populacao[0].velocidades.copy(),
                fitness=populacao[0].fitness
            )
            melhor_resultado = res_elite
            geracoes_sem_melhora = 0

        historico_fitness.append(melhor_global.fitness)  

        if geracao == 1 or geracao % 10 == 0:
            print(
                f"Geração {geracao:03d} | Fitness: {melhor_global.fitness:.2f} | "  
                f"Válida: {melhor_resultado.valida} | "  
                f"Tempo: {melhor_resultado.tempo_total_segundos}s | "  
                f"Custo: R$ {melhor_resultado.custo_total_reais:.2f}"  
            )

        geracoes_sem_melhora += 1
        if geracoes_sem_melhora >= geracoes_sem_melhora_limite:
            print(f"Parada antecipada na geração {geracao}: {geracoes_sem_melhora_limite} gerações sem melhora.")
            break

        nova_populacao: List[Individuo] = [
            Individuo(ind.ordem_ceps.copy(), ind.velocidades.copy(), ind.fitness)
            for ind in populacao[:elitismo]
        ]

        while len(nova_populacao) < tamanho_populacao:
            pai1 = selecao_torneio(populacao)
            pai2 = selecao_torneio(populacao)

            if random.random() < taxa_crossover:
                filho = crossover_ox1(pai1, pai2)
            else:
                filho = Individuo(pai1.ordem_ceps.copy(), pai1.velocidades.copy())

            mutacao(filho, matriz_distancias, taxa_mutacao)
            nova_populacao.append(filho)

        populacao = nova_populacao

    return melhor_global, melhor_resultado, historico_fitness