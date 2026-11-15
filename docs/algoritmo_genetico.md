# Algoritmo genético

## Codificação

Cada indivíduo (`Individuo`, em `src/algoritmo_genetico.py`) tem dois grupos de
genes:

- **Ordem de visita:** permutação dos CEPs, sem o campus (codificação por
  permutação).
- **Velocidades:** a velocidade do voo que chega a cada CEP, incluindo o campus
  como destino do último trecho.

A velocidade fica ligada ao CEP de destino, e não à posição na rota. Assim, no
crossover, um pedaço de rota herdado de um pai leva junto as velocidades que
funcionavam nele.

Pousos e horários não são genes. `montar_plano` deriva essas decisões do
cromossomo consultando o simulador:

- o drone só segue sem pousar quando, do destino, ainda alcança o ponto
  seguinte com bateria e antes das 19:00:00;
- em solo, se o próximo trecho não cabe no dia, a partida fica para as 06:00:00
  do dia seguinte.

## Operadores

| Etapa | Implementação |
|---|---|
| População inicial | 20% de rotas do vizinho mais próximo refinadas com 2-opt; 80% aleatórias |
| Seleção | Torneio de 3 |
| Crossover | Order Crossover (OX1), com as velocidades acompanhando os CEPs |
| Mutação | Inversão de um trecho da rota, deslocamento de um CEP para a melhor posição e troca de 1 a 3 velocidades |
| Elitismo | Os 2 melhores passam direto para a geração seguinte |
| Refinamento | 2-opt no melhor de cada geração, aceito somente se a nota melhorar |

## Fitness

Quanto menor, melhor.

- **Plano válido:** tempo total de voo em segundos, mais o custo dos pousos em
  reais multiplicado por `PESO_DO_CUSTO_EM_SEGUNDOS_POR_REAL` (15).
- **Plano inválido:** penalidade de 1.000.000.000, mais 10.000 por trecho que o
  plano não chegou a voar. A parcela por trecho faz planos que avançam mais
  serem preferidos entre os inválidos.

O peso de 15 segundos por real é um parâmetro a calibrar e depende da resposta
do professor sobre como combinar tempo e custo.

## Monitoramento e parada

A cada 10 gerações o programa imprime fitness, validade, tempo de voo, pousos e
custo do melhor plano. A execução termina ao atingir o máximo de gerações ou
após 80 gerações seguidas sem melhora.

## Reprodução

A semente aleatória é um parâmetro. Com a mesma semente, população e número de
gerações, a execução produz o mesmo resultado:

```bash
python3 -m src.main --semente 2024 --populacao 80 --geracoes 400
```
