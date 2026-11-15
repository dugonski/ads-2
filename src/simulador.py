"""Simulação do plano de voo: horários, bateria, custos e regras do problema."""

from collections import Counter
from collections.abc import Sequence

from src.contrato import (
    SEGUNDOS_POR_HORA,
    Coordenada,
    Momento,
    ResultadoSimulacao,
    TrechoPlanejado,
    TrechoSimulado,
)
from src.coordenadas import CEP_UNIBRASIL
from src.drone import VELOCIDADES_PERMITIDAS, autonomia_s, tempo_de_parada_s, tempo_de_voo_s
from src.geografia import matriz_de_angulos_graus, matriz_de_distancias_km
from src.vento import velocidade_efetiva_kmh, vento_na_partida

ULTIMO_DIA = 7
INICIO_DOS_VOOS_S = 6 * SEGUNDOS_POR_HORA
LIMITE_DE_POUSO_S = 19 * SEGUNDOS_POR_HORA
INICIO_DA_TAXA_ADICIONAL_S = 17 * SEGUNDOS_POR_HORA

CUSTO_DO_POUSO_REAIS = 80
TAXA_ADICIONAL_DE_POUSO_REAIS = 80

BATERIA_CHEIA = 1.0


def custo_do_pouso_reais(segundo_do_dia: int) -> int:
    """Custo de um pouso, com a taxa adicional para pousos após as 17:00:00."""
    if segundo_do_dia > INICIO_DA_TAXA_ADICIONAL_S:
        return CUSTO_DO_POUSO_REAIS + TAXA_ADICIONAL_DE_POUSO_REAIS
    return CUSTO_DO_POUSO_REAIS


class Simulador:
    """Calcula o voo do drone sobre um conjunto fixo de coordenadas."""

    def __init__(self, coordenadas: Sequence[Coordenada]) -> None:
        self._coordenadas = tuple(coordenadas)
        self._indices = {coordenada.cep: indice for indice, coordenada in enumerate(coordenadas)}
        if CEP_UNIBRASIL not in self._indices:
            raise ValueError(f"A lista de coordenadas não contém o CEP {CEP_UNIBRASIL}")
        self._distancias_km = matriz_de_distancias_km(self._coordenadas)
        self._angulos_graus = matriz_de_angulos_graus(self._coordenadas)

    def simular_trecho(
        self, cep_origem: str, trecho: TrechoPlanejado, partida: Momento, carga: float
    ) -> TrechoSimulado:
        """Voa um trecho, sem verificar as regras do problema.

        O tempo de parada no destino conta no horário de chegada e consome
        bateria na velocidade regulada para o trecho.
        """
        origem = self._indices[cep_origem]
        destino = self._indices[trecho.cep_destino]
        velocidade_efetiva = velocidade_efetiva_kmh(
            trecho.velocidade_kmh, self._angulos_graus[origem][destino], vento_na_partida(partida)
        )
        duracao = tempo_de_voo_s(
            self._distancias_km[origem][destino], velocidade_efetiva
        ) + tempo_de_parada_s(trecho.pousar)
        chegada = partida.apos(duracao)
        return TrechoSimulado(
            origem=self._coordenadas[origem],
            destino=self._coordenadas[destino],
            partida=partida,
            chegada=chegada,
            velocidade_kmh=trecho.velocidade_kmh,
            pousou=trecho.pousar,
            carga_restante=carga - duracao / autonomia_s(trecho.velocidade_kmh),
            custo_do_pouso_reais=(
                custo_do_pouso_reais(chegada.segundo_do_dia) if trecho.pousar else 0
            ),
        )

    def simular_plano(self, trechos: Sequence[TrechoPlanejado]) -> ResultadoSimulacao:
        """Simula o plano a partir do campus Unibrasil e aponta as regras descumpridas.

        A simulação para no primeiro trecho que descumpre uma regra.
        """
        simulados: list[TrechoSimulado] = []
        violacoes: list[str] = []
        cep_atual = CEP_UNIBRASIL
        carga = BATERIA_CHEIA
        em_solo = True
        disponivel_em = Momento(1, INICIO_DOS_VOOS_S)

        for numero, trecho in enumerate(trechos, start=1):
            partida = trecho.partida or disponivel_em
            adiou_no_ar = partida > disponivel_em and not em_solo
            if partida < disponivel_em or adiou_no_ar:
                problema = "partida incompatível com a chegada anterior"
            else:
                problema = self._problema_antes_do_voo(cep_atual, trecho, partida)
            if problema is None:
                simulado = self.simular_trecho(cep_atual, trecho, partida, carga)
                simulados.append(simulado)
                problema = _problema_na_chegada(simulado)
            if problema is not None:
                violacoes.append(f"Trecho {numero}: {problema}")
                break
            cep_atual = trecho.cep_destino
            em_solo = trecho.pousar
            carga = BATERIA_CHEIA if trecho.pousar else simulado.carga_restante
            disponivel_em = simulado.chegada

        violacoes.extend(self._problemas_da_rota(trechos))
        return ResultadoSimulacao(tuple(simulados), tuple(violacoes))

    def _problema_antes_do_voo(
        self, cep_origem: str, trecho: TrechoPlanejado, partida: Momento
    ) -> str | None:
        if trecho.cep_destino not in self._indices:
            return f"CEP {trecho.cep_destino} fora da lista de coordenadas"
        if trecho.cep_destino == cep_origem:
            return "origem e destino iguais"
        if trecho.velocidade_kmh not in VELOCIDADES_PERMITIDAS:
            return f"velocidade de {trecho.velocidade_kmh} km/h fora das regulagens do drone"
        if not 1 <= partida.dia <= ULTIMO_DIA:
            return f"partida no dia {partida.dia}, fora do prazo de {ULTIMO_DIA} dias"
        if not INICIO_DOS_VOOS_S <= partida.segundo_do_dia < LIMITE_DE_POUSO_S:
            return f"partida às {partida.horario}, fora do horário de voo"
        return None

    def _problemas_da_rota(self, trechos: Sequence[TrechoPlanejado]) -> list[str]:
        if not trechos:
            return ["Plano sem trechos"]
        problemas = []
        if trechos[-1].cep_destino != CEP_UNIBRASIL:
            problemas.append("O plano não termina no campus Unibrasil")
        if not trechos[-1].pousar:
            problemas.append("O plano termina com o drone no ar")
        visitas = Counter(trecho.cep_destino for trecho in trechos)
        del visitas[CEP_UNIBRASIL]
        repetidos = sorted(cep for cep, vezes in visitas.items() if vezes > 1)
        if repetidos:
            problemas.append(f"CEPs visitados mais de uma vez: {', '.join(repetidos)}")
        sem_visita = len(set(self._indices) - set(visitas) - {CEP_UNIBRASIL})
        if sem_visita:
            problemas.append(f"{sem_visita} CEPs sem visita")
        return problemas


def _problema_na_chegada(trecho: TrechoSimulado) -> str | None:
    if trecho.carga_restante < 0:
        return "bateria esgotada antes do fim do trecho"
    if trecho.chegada.segundo_do_dia > LIMITE_DE_POUSO_S:
        return f"chegada às {trecho.chegada.horario}, depois do limite de pouso"
    return None
