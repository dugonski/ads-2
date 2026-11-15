# Regras implementadas no simulador

Este documento registra como cada regra da especificação foi implementada e
quais pontos dependem de confirmação do professor.

## Como usar

```python
from src.contrato import Momento, TrechoPlanejado
from src.coordenadas import carregar_coordenadas
from src.simulador import Simulador

simulador = Simulador(carregar_coordenadas())
resultado = simulador.simular_plano([
    TrechoPlanejado(cep_destino="82530380", velocidade_kmh=36, pousar=False),
    TrechoPlanejado(cep_destino="82821020", velocidade_kmh=40, pousar=True),
])
resultado.valido                  # False: faltam coordenadas a visitar
resultado.violacoes               # mensagens das regras descumpridas
resultado.tempo_total_de_voo_s    # soma de voo e paradas
resultado.numero_de_pousos
resultado.custo_dos_pousos_reais
```

Cada `TrechoPlanejado` é uma decisão do algoritmo genético: destino, velocidade,
se pousa no destino e, opcionalmente, quando decola. Sem `partida`, o drone
decola assim que fica disponível. Para retomar no dia seguinte, o trecho deve
informar `partida=Momento.de_horario(dia, 6)`.

A simulação para no primeiro trecho que descumpre uma regra, e a mensagem
informa o número desse trecho. A bateria é uma fração: 1 é cheia e 0 é vazia.

`Simulador.simular_trecho` calcula um único voo sem verificar regras. Serve para
montar um plano passo a passo, consultando horário de chegada e carga restante
antes de decidir o próximo trecho.

Cada `TrechoSimulado` contém os dados de uma linha do CSV de saída.

## Regras

| Regra | Implementação |
|---|---|
| Distância | Haversine, raio de 6371 km |
| Velocidade regulada | Inteiros múltiplos de 4, de 36 km/h (10 m/s) a 80 km/h |
| Vento | Coluna da previsão definida pelo horário de partida, fixa durante o trecho; rajadas ignoradas |
| Velocidade efetiva | Módulo da soma vetorial da velocidade regulada, no rumo do voo, com o vento |
| Tempo de voo | Distância dividida pela velocidade efetiva, em segundos, arredondado para cima |
| Parada | 60 s para foto sem pouso; 172 s quando há pouso |
| Autonomia | 5000 x 1,14 x (36 / v)² segundos, com v igual à velocidade regulada |
| Recarga | Todo pouso troca a bateria |
| Reserva de segurança | Cada trecho precisa terminar com pelo menos 10% da bateria |
| Horário | Partidas das 06:00:00 às 18:59:59; chegada até 19:00:00 |
| Prazo | Dias 1 a 7 |
| Custo | R$ 80 por pouso, mais R$ 80 se o pouso termina depois das 17:00:00 |
| Rota | Começa e termina pousado no campus (CEP 82821020); cada outro CEP é visitado uma única vez |

O simulador devolve tempo, número de pousos e custo em reais separados. A
combinação desses valores na função fitness pertence ao algoritmo genético.

## Interpretações a confirmar com o professor

1. **Fator de correção 1,14.** Foi aplicado multiplicando a autonomia: 5700 s a
   36 km/h. A constante é `FATOR_DE_CORRECAO_PERCENTUAL` em `src/drone.py`.
2. **Consumo durante a parada.** Os 60 s ou 172 s consomem bateria na
   velocidade regulada do trecho que chega à coordenada.
3. **Velocidade máxima.** A especificação cita 83 km/h, mas o maior múltiplo de
   4 permitido é 80 km/h.
4. **Direção do vento.** A direção da tabela é de onde o vento vem, como no
   exemplo do vento "vindo de SSE".
5. **Velocidade efetiva.** Segue o exemplo da especificação: usa o módulo da
   soma vetorial, sem corrigir o desvio lateral que o vento causaria na rota.
6. **Pouso final.** O pouso de chegada ao campus custa R$ 80, como qualquer
   outro, e R$ 160 se terminar depois das 17:00:00.
7. **Pouso às 17:00:00 em ponto.** Não paga a taxa adicional; ela vale a partir
   de 17:00:01.
8. **Campus no meio da rota.** O drone pode voltar ao campus para recarregar
   quantas vezes quiser.
9. **Espera no ar.** Sem pouso, o drone parte para o próximo trecho assim que
   termina a parada de 60 s; só é possível esperar em solo.
10. **Reserva de bateria.** A especificação exige apenas que o drone não fique
    sem carga. Por segurança, o simulador recusa qualquer trecho que termine
    com menos de 10% da bateria (`RESERVA_DE_SEGURANCA_DA_BATERIA` em
    `src/simulador.py`). Isso aumenta o número de pousos em troca de folga.
