# UNIBRASIL Surveyor - Serviços Cognitivos

Atividade discente supervisionada 2. Planejamento da rota de um drone que
fotografa uma lista de CEPs de Curitiba, usando um algoritmo genético para
minimizar o tempo total de voo e a quantidade de pousos para recarga.

## Integrantes

- Guilherme Dugonski - Matrícula: 2024101129
- Tiago (nome completo a preencher) - Matrícula: 2024101751

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `data/coordenadas_professor.csv` | Lista original fornecida pelo professor, sem alterações |
| `data/coordenadas.csv` | Lista original mais as coordenadas extras da equipe |
| `docs/coordenadas_extras.md` | Documentação das coordenadas extras e matrículas |
| `output/` | CSV com a melhor solução encontrada |
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

## Convenções do projeto

- Caminhos sempre com `pathlib`, relativos à raiz do projeto.
- Nomes de arquivos, pastas e módulos em minúsculas.
- Arquivos lidos e gravados com `encoding="utf-8"`; CSV com `newline=""`.
- Quebra de linha LF, garantida pelo `.gitattributes`.
- Commits no padrão `feat:`, `fix:`, `chore:`, `docs:`, `test:`.
