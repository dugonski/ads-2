"""Estruturas de dados trocadas entre o simulador e o algoritmo genético."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

SEGUNDOS_POR_HORA = 3600
SEGUNDOS_POR_MINUTO = 60


@dataclass(frozen=True)
class Coordenada:
    """Ponto que o drone pode fotografar e onde pode pousar."""

    cep: str
    latitude: float
    longitude: float


@dataclass(frozen=True, order=True)
class Momento:
    """Instante do plano: dia da previsão (1 a 7) e segundo dentro do dia."""

    dia: int
    segundo_do_dia: int

    @classmethod
    def de_horario(cls, dia: int, hora: int, minuto: int = 0, segundo: int = 0) -> Momento:
        return cls(dia, hora * SEGUNDOS_POR_HORA + minuto * SEGUNDOS_POR_MINUTO + segundo)

    def apos(self, segundos: int) -> Momento:
        """Momento do mesmo dia, `segundos` depois deste."""
        return Momento(self.dia, self.segundo_do_dia + segundos)

    @property
    def horario(self) -> str:
        """Horário no formato HH:MM:SS usado no CSV de saída."""
        horas, resto = divmod(self.segundo_do_dia, SEGUNDOS_POR_HORA)
        minutos, segundos = divmod(resto, SEGUNDOS_POR_MINUTO)
        return f"{horas:02d}:{minutos:02d}:{segundos:02d}"


@dataclass(frozen=True)
class TrechoPlanejado:
    """Decisões do algoritmo genético para um voo entre duas coordenadas.

    `partida` vazia significa decolar no instante em que o drone fica
    disponível: a chegada do trecho anterior ou, no primeiro trecho, o início
    do dia 1. Só é possível escolher outra partida com o drone em solo.
    """

    cep_destino: str
    velocidade_kmh: int
    pousar: bool
    partida: Momento | None = None


@dataclass(frozen=True)
class TrechoSimulado:
    """Resultado do voo de um trecho, com os dados de uma linha do CSV de saída."""

    origem: Coordenada
    destino: Coordenada
    partida: Momento
    chegada: Momento
    velocidade_kmh: int
    pousou: bool
    tempo_de_voo_s: int
    tempo_de_parada_s: int
    carga_restante: int
    custo_do_pouso_reais: int

    @property
    def duracao_s(self) -> int:
        return self.tempo_de_voo_s + self.tempo_de_parada_s


class TipoViolacao(Enum):
    PLANO_VAZIO = "plano sem trechos"
    CEP_DESCONHECIDO = "destino fora da lista de coordenadas"
    TRECHO_SEM_DESLOCAMENTO = "origem e destino iguais"
    VELOCIDADE_INVALIDA = "velocidade fora das regulagens do drone"
    PARTIDA_INCOMPATIVEL = "partida incompatível com a chegada anterior"
    FORA_DO_PRAZO = "partida fora dos dias da previsão"
    FORA_DO_HORARIO_DE_VOO = "partida fora do horário permitido"
    CHEGADA_APOS_O_LIMITE = "chegada depois do horário limite de pouso"
    BATERIA_ESGOTADA = "carga insuficiente para completar o trecho"
    CEP_REPETIDO = "coordenada visitada mais de uma vez"
    CEPS_NAO_VISITADOS = "coordenadas sem visita"
    FIM_FORA_DA_BASE = "plano não termina no campus Unibrasil"
    FIM_SEM_POUSO = "plano termina com o drone no ar"


@dataclass(frozen=True)
class Violacao:
    """Regra descumprida. `indice_do_trecho` é vazio quando vale para o plano todo."""

    tipo: TipoViolacao
    indice_do_trecho: int | None
    descricao: str


@dataclass(frozen=True)
class ResultadoSimulacao:
    """Plano de voo simulado e as regras que ele descumpre."""

    trechos: tuple[TrechoSimulado, ...]
    violacoes: tuple[Violacao, ...]

    @property
    def valido(self) -> bool:
        return not self.violacoes

    @property
    def tempo_total_de_voo_s(self) -> int:
        return sum(trecho.duracao_s for trecho in self.trechos)

    @property
    def numero_de_pousos(self) -> int:
        return sum(trecho.pousou for trecho in self.trechos)

    @property
    def custo_dos_pousos_reais(self) -> int:
        return sum(trecho.custo_do_pouso_reais for trecho in self.trechos)
