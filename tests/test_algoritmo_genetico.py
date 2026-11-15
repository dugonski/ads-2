import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Garante que a pasta src/ seja encontrada ao rodar pytest da raiz do projeto
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_PROJETO / "src"))

from algoritmo_genetico import (
    AUTONOMIA_NOMINAL_CURITIBA,
    CEP_BASE,
    PESO_CUSTO_FINANCEIRO,
    VELOCIDADES_VALIDAS,
    Individuo,
    aplicar_2opt,
    calcular_fitness,
    crossover_ox1,
    decodificar_individuo,
    executar_algoritmo_genetico,
    gerar_populacao_inicial,
    mutacao,
    selecao_torneio,
)
from contrato import ResultadoSimulacao, TrechoPlanejado


def criar_cenario_ficticio() -> Tuple[List[str], Dict[Tuple[str, str], float]]:
    """Cria um mini-mapa com o Unibrasil (82821020) e 4 CEPs formando um quadrado."""
    ceps = [CEP_BASE, "80000001", "80000002", "80000003", "80000004"]
    # Coordenadas planas simuladas em metros:
    # Base=(0,0), 01=(0,2000), 02=(2000,2000), 03=(2000,0), 04=(1000,1000)
    pontos = {
        CEP_BASE: (0.0, 0.0),
        "80000001": (0.0, 2000.0),
        "80000002": (2000.0, 2000.0),
        "80000003": (2000.0, 0.0),
        "80000004": (1000.0, 1000.0),
    }
    matriz: Dict[Tuple[str, str], float] = {}
    for a, (xa, ya) in pontos.items():
        for b, (xb, yb) in pontos.items():
            matriz[(a, b)] = ((xa - xb) ** 2 + (ya - yb) ** 2) ** 0.5
    return ceps, matriz


def test_gerar_populacao_inicial_integridade():
    """Garante que os indivíduos criados não repetem nem omitem CEPs e usam velocidades válidas[cite: 2, 7]."""
    ceps, matriz = criar_cenario_ficticio()
    ceps_intermediarios = set(ceps) - {CEP_BASE}

    populacao = gerar_populacao_inicial(tamanho_populacao=10, todos_ceps=ceps, matriz_distancias=matriz)

    assert len(populacao) == 10
    for ind in populacao:
        assert CEP_BASE not in ind.ordem_ceps
        assert set(ind.ordem_ceps) == ceps_intermediarios
        assert len(ind.ordem_ceps) == len(ceps_intermediarios)
        assert len(ind.velocidades) == len(ceps)
        assert all(v in VELOCIDADES_VALIDAS for v in ind.velocidades)


def test_crossover_ox1_preserva_permutacao():
    """Garante que o cruzamento OX1 gera filhos válidos sem duplicar ou perder CEPs[cite: 2, 11]."""
    pai1 = Individuo(ordem_ceps=["80000001", "80000002", "80000003", "80000004"], velocidades=[36, 40, 44, 48, 52])
    pai2 = Individuo(ordem_ceps=["80000004", "80000003", "80000002", "80000001"], velocidades=[60, 64, 68, 72, 76])

    filho = crossover_ox1(pai1, pai2)

    assert set(filho.ordem_ceps) == {"80000001", "80000002", "80000003", "80000004"}
    assert len(filho.ordem_ceps) == 4
    assert len(filho.velocidades) == 5
    assert all(v in VELOCIDADES_VALIDAS for v in filho.velocidades)


def test_aplicar_2opt_remove_cruzamento():
    """Verifica se o 2-opt descruza uma rota em formato de 'X' reduzindo a distância."""
    _, matriz = criar_cenario_ficticio()
    # Rota cruzada: Base(0,0) -> 02(2000,2000) -> 01(0,2000) -> 03(2000,0) -> Base(0,0)
    ind = Individuo(
        ordem_ceps=["80000002", "80000001", "80000003"],
        velocidades=[36, 36, 36, 36],
    )

    aplicar_2opt(ind, matriz, max_passadas=3)

    # Após descruzar, os pontos adjacentes do quadrado (01 e 03) devem ficar nas extremidades
    assert ind.ordem_ceps in (
        ["80000001", "80000002", "80000003"],
        ["80000003", "80000002", "80000001"],
    )


def test_mutacao_mantem_validade_dos_genes():
    """Verifica se a mutação (inversão, deslocamento e velocidade) mantém o cromossomo íntegro[cite: 13]."""
    _, matriz = criar_cenario_ficticio()
    ind = Individuo(
        ordem_ceps=["80000001", "80000002", "80000003", "80000004"],
        velocidades=[36, 36, 36, 36, 36],
    )

    mutacao(ind, matriz, taxa_mutacao=1.0)  # Força execução de todos os operadores de mutação

    assert set(ind.ordem_ceps) == {"80000001", "80000002", "80000003", "80000004"}
    assert len(ind.velocidades) == 5
    assert all(v in VELOCIDADES_VALIDAS for v in ind.velocidades)


def test_decodificar_individuo_inicio_fim_e_pouso_automatico():
    """Verifica saída/retorno ao Unibrasil e inserção automática de pouso quando a bateria não basta[cite: 1, 2]."""
    ceps = [CEP_BASE, "80000001", "80000002"]
    # Distâncias muito longas (45 km cada) para forçar recarga intermediária
    matriz = {
        (CEP_BASE, "80000001"): 45_000.0,
        ("80000001", "80000002"): 45_000.0,
        ("80000002", CEP_BASE): 45_000.0,
    }
    ind = Individuo(ordem_ceps=["80000001", "80000002"], velocidades=[36, 36, 36])

    plano = decodificar_individuo(ind, matriz)

    assert len(plano) == 3
    assert plano[0].cep_origem == CEP_BASE
    assert plano[-1].cep_destino == CEP_BASE
    assert plano[-1].pouso is True
    # Como cada trecho de 45 km a 36 km/h gasta > 4500s e a autonomia é 5700s, precisa pousar no 1º destino
    assert plano[0].pouso is True


def test_calcular_fitness_penaliza_rota_invalida():
    """Garante que rotas inválidas recebam penalização severa maior que qualquer rota válida[cite: 2, 13]."""
    res_valido = ResultadoSimulacao(
        valida=True,
        motivo_invalidez=None,
        tempo_total_segundos=10_000,
        custo_total_reais=240.0,
        linhas_csv=[],
    )
    res_invalido = ResultadoSimulacao(
        valida=False,
        motivo_invalidez="Bateria acabou no ar",
        tempo_total_segundos=500,
        custo_total_reais=0.0,
        linhas_csv=[],
    )

    nota_valida = calcular_fitness(res_valido)
    nota_invalida = calcular_fitness(res_invalido)

    assert nota_valida == 10_000 + (240.0 * PESO_CUSTO_FINANCEIRO)
    assert nota_invalida > nota_valida
    assert nota_invalida >= 1_000_000_000.0


def test_executar_algoritmo_genetico_fluxo_completo():
    """Testa seleção por torneio, elitismo e critério de parada do loop evolutivo[cite: 11, 13]."""
    ceps, matriz = criar_cenario_ficticio()

    def avaliador_ficticio(plano: List[TrechoPlanejado]) -> ResultadoSimulacao:
        dist_total = sum(matriz[(t.cep_origem, t.cep_destino)] for t in plano)
        tempo = int(dist_total / 10.0)
        custo = sum(80.0 for t in plano if t.pouso)
        return ResultadoSimulacao(True, None, tempo, custo, [])

    melhor_ind, melhor_res, historico = executar_algoritmo_genetico(
        todos_ceps=ceps,
        matriz_distancias=matriz,
        funcao_avaliacao=avaliador_ficticio,
        tamanho_populacao=8,
        max_geracoes=10,
        geracoes_sem_melhora_limite=5,
    )

    assert melhor_res.valida is True
    assert len(historico) >= 1
    assert historico[-1] <= historico[0]
    assert set(melhor_ind.ordem_ceps) == set(ceps) - {CEP_BASE}