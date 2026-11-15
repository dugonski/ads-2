# Coordenadas extras da equipe

A especificação pede uma coordenada adicional por integrante, com estas regras:

- pelo menos 100 metros de distância de qualquer outra coordenada, do
  professor ou da equipe;
- menos de 1500 metros de alguma coordenada da base;
- latitude e longitude com exatamente 13 casas decimais, uma delas terminando
  nos 8 últimos dígitos da matrícula;
- CEP formado pelos 8 últimos dígitos da matrícula.

As distâncias foram calculadas com a fórmula de Haversine, com raio da Terra
de 6371 km.

## Coordenadas escolhidas

| Integrante | Matrícula | CEP | Latitude | Longitude | Ponto mais próximo | Distância (m) |
|---|---|---|---|---|---|---|
| Guilherme Dugonski | 2024101129 | 24101129 | -25.4083724101129 | -49.2577899153158 | CEP 80030430 | 748,25 |
| Tiago Machado da Rosa | 2024101751 | 24101751 | -25.4210024101751 | -49.2124839175329 | CEP 82821020 | 442,32 |

A latitude da coordenada de Guilherme termina em `24101129`.

As distâncias devem ser recalculadas sobre a base final consolidada quando a
coordenada de Tiago for incluída em `data/coordenadas.csv`.
