# UNIBRASIL Surveyor - Serviços Cognitivos

Atividade discente supervisionada 2. Planejamento da rota de um drone que
fotografa uma lista de CEPs de Curitiba, usando um algoritmo genético para
minimizar o tempo total de voo e a quantidade de pousos para recarga.

## Integrantes

- Guilherme Dugonski - Matrícula: 2024101129
- Tiago Machado da Rosa - Matrícula: 2024101751

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `data/coordenadas_professor.csv` | Lista original fornecida pelo professor, sem alterações |
| `data/coordenadas.csv` | Lista original mais as coordenadas extras da equipe |
| `docs/coordenadas_extras.md` | Documentação das coordenadas extras e matrículas |
| `docs/regras_do_simulador.md` | Regras implementadas no simulador e interpretações adotadas |
| `docs/algoritmo_genetico.md` | Codificação, operadores, fitness e critério de parada |
| `output/solucao_final.csv` | Plano de voo completo da melhor solução encontrada |
| `output/mapa_rota.png` | Gráfico da rota otimizada gerada pelo script de visualização |
| `docs/evidencias/` | Saída da execução do algoritmo e dos testes com cobertura |
| `src/` | Código-fonte |
| `tests/` | Testes unitários |

Nos arquivos de `data/`, a ordem das colunas é `cep,longitude,latitude`.

## Como executar no Linux

Requer Python 3.10 ou superior. Todos os comandos são executados na raiz do
projeto.

1. Criar e ativar o ambiente virtual:

   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   ```

2. Instalar as dependências:

   ```bash
   pip install -r requirements.txt
   ```

3. Executar os testes unitários e verificar a cobertura:

   ```bash
   pytest
   ```

4. Executar o algoritmo genético e gerar o CSV da rota:

   ```bash
   python3 -m src.main
   ```

   O plano de voo é gravado em `output/solucao_final.csv`. A execução usa a
   semente 2024, que reproduz o arquivo entregue. Para uma execução rápida de
   conferência:

   ```bash
   python3 -m src.main --populacao 20 --geracoes 20 --saida output/teste.csv
   ```

5. Após executar o algoritmo genético, gerar o visual da rota percorrida:
   ```bash
   python3 -m src.visualizar_rota
   ```

   O gráfico do plano de voo é gravado em `output/mapa_rota.png` utilizando a
   biblioteca matplotlib, destacando os CEPs visitados, os pontos de pouso
   para recarga e a base na Unibrasil.

## Convenções do projeto

- Caminhos sempre com `pathlib`, relativos à raiz do projeto.
- Nomes de arquivos, pastas e módulos em minúsculas.
- Arquivos lidos e gravados com `encoding="utf-8"`; CSV com `newline=""`.
- Quebra de linha LF, garantida pelo `.gitattributes`.
- Commits no padrão `feat:`, `fix:`, `chore:`, `docs:`, `test:`.
