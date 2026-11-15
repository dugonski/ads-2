"""Simulação do plano de voo: horários, bateria, custos e regras do problema."""

from collections.abc import Sequence

from src.contrato import (
    SEGUNDOS_POR_HORA,
    Coordenada,
    Momento,
    ResultadoSimulacao,
    TipoViolacao,
    TrechoPlanejado,
    TrechoSimulado,
    Violacao,
)
from src.coordenadas import CEP_UNIBRASIL
from src.drone import (
    CARGA_CHEIA,
    consumo_de_carga,
    tempo_de_parada_s,
    tempo_de_voo_s,
    velocidade_permitida,
)
from src.geografia import matriz_de_angulos_graus, matriz_de_distancias_km
from src.vento import velocidade_efetiva_kmh, vento_na_partida

PRIMEIRO_DIA = 1
ULTIMO_DIA = 7
INICIO_DOS_VOOS_S = 6 * SEGUNDOS_POR_HORA
LIMITE_DE_POUSO_S = 19 * SEGUNDOS_POR_HORA
INICIO_DA_TAXA_ADICIONAL_S = 17 * SEGUNDOS_POR_HORA

CUSTO_DO_POUSO_REAIS = 80
TAXA_ADICIONAL_DE_POUSO_REAIS = 80


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
        self, cep_origem: str, trecho: TrechoPlanejado, partida: Momento, carga_disponivel: int
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
        tempo_de_voo = tempo_de_voo_s(self._distancias_km[origem][destino], velocidade_efetiva)
        tempo_de_parada = tempo_de_parada_s(trecho.pousar)
        chegada = partida.apos(tempo_de_voo + tempo_de_parada)
        consumo = consumo_de_carga(tempo_de_voo + tempo_de_parada, trecho.velocidade_kmh)
        return TrechoSimulado(
            origem=self._coordenadas[origem],
            destino=self._coordenadas[destino],
            partida=partida,
            chegada=chegada,
            velocidade_kmh=trecho.velocidade_kmh,
            pousou=trecho.pousar,
            tempo_de_voo_s=tempo_de_voo,
            tempo_de_parada_s=tempo_de_parada,
            carga_restante=carga_disponivel - consumo,
            custo_do_pouso_reais=(
                custo_do_pouso_reais(chegada.segundo_do_dia) if trecho.pousar else 0
            ),
        )

    def simular_plano(self, trechos: Sequence[TrechoPlanejado]) -> ResultadoSimulacao:
        """Simula o plano a partir do campus Unibrasil e aponta as regras descumpridas.

        A simulação para no primeiro trecho que não pode ser calculado: destino
        desconhecido ou partida em dia ou horário sem previsão de vento.
        """
        violacoes: list[Violacao] = []
        simulados: list[TrechoSimulado] = []
        visitas: dict[str, int] = {}
        cep_atual = CEP_UNIBRASIL
        carga = CARGA_CHEIA
        em_solo = True
        disponivel_em = Momento(PRIMEIRO_DIA, INICIO_DOS_VOOS_S)

        def violar(tipo: TipoViolacao, indice: int | None, detalhe: str) -> None:
            violacoes.append(Violacao(tipo, indice, f"{tipo.value}: {detalhe}"))

        for indice, trecho in enumerate(trechos):
            partida = trecho.partida or disponivel_em
            if trecho.cep_destino not in self._indices:
                violar(TipoViolacao.CEP_DESCONHECIDO, indice, trecho.cep_destino)
                break
            if not PRIMEIRO_DIA <= partida.dia <= ULTIMO_DIA:
                violar(TipoViolacao.FORA_DO_PRAZO, indice, f"dia {partida.dia}")
                break
            if not INICIO_DOS_VOOS_S <= partida.segundo_do_dia < LIMITE_DE_POUSO_S:
                violar(TipoViolacao.FORA_DO_HORARIO_DE_VOO, indice, partida.horario)
                break
            if partida < disponivel_em or (not em_solo and partida != disponivel_em):
                violar(
                    TipoViolacao.PARTIDA_INCOMPATIVEL,
                    indice,
                    f"dia {partida.dia} às {partida.horario}",
                )
            if trecho.cep_destino == cep_atual:
                violar(TipoViolacao.TRECHO_SEM_DESLOCAMENTO, indice, cep_atual)
            if not velocidade_permitida(trecho.velocidade_kmh):
                violar(TipoViolacao.VELOCIDADE_INVALIDA, indice, f"{trecho.velocidade_kmh} km/h")

            simulado = self.simular_trecho(cep_atual, trecho, partida, carga)
            simulados.append(simulado)
            if simulado.chegada.segundo_do_dia > LIMITE_DE_POUSO_S:
                violar(TipoViolacao.CHEGADA_APOS_O_LIMITE, indice, simulado.chegada.horario)
            if simulado.carga_restante < 0:
                violar(TipoViolacao.BATERIA_ESGOTADA, indice, f"destino {trecho.cep_destino}")

            visitas[trecho.cep_destino] = visitas.get(trecho.cep_destino, 0) + 1
            if trecho.cep_destino != CEP_UNIBRASIL and visitas[trecho.cep_destino] > 1:
                violar(TipoViolacao.CEP_REPETIDO, indice, trecho.cep_destino)

            cep_atual = trecho.cep_destino
            em_solo = trecho.pousar
            carga = CARGA_CHEIA if trecho.pousar else simulado.carga_restante
            disponivel_em = simulado.chegada

        if not trechos:
            violar(TipoViolacao.PLANO_VAZIO, None, "nenhum voo planejado")
        else:
            if trechos[-1].cep_destino != CEP_UNIBRASIL:
                violar(TipoViolacao.FIM_FORA_DA_BASE, None, trechos[-1].cep_destino)
            if not trechos[-1].pousar:
                violar(TipoViolacao.FIM_SEM_POUSO, None, "último trecho sem pouso")
        nao_visitados = [
            cep for cep in self._indices if cep != CEP_UNIBRASIL and cep not in visitas
        ]
        if nao_visitados:
            violar(TipoViolacao.CEPS_NAO_VISITADOS, None, f"{len(nao_visitados)} coordenadas")

        return ResultadoSimulacao(tuple(simulados), tuple(violacoes))
