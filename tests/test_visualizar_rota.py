import csv
import sys
from pathlib import Path
import pytest

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_PROJETO / "src"))

from visualizar_rota import carregar_dados_rota, gerar_mapa


def criar_csv_rota_exemplo(caminho: Path) -> None:
    """Cria um CSV fictício válido no formato oficial de 11 colunas."""
    cabecalho = [
        "CEP inicial", "Latitude inicial", "Longitude inicial",
        "Dia do vôo", "Hora inicial", "Velocidade",
        "CEP final", "Latitude final", "Longitude final",
        "Pouso", "Hora final"
    ]
    linhas = [
        # Trecho 1: Sai do Unibrasil (82821020) e apenas tira foto (Pouso = NAO)
        ["82821020", -25.4233, -49.2160, 1, "06:00:00", 36, "80010000", -25.4300, -49.2336, "NAO", "06:05:10"],
        # Trecho 2: Pousa para recarga em ponto intermediário (Pouso = SIM -> deve aparecer no gráfico)
        ["80010000", -25.4300, -49.2336, 1, "06:05:10", 40, "80020000", -25.4400, -49.2500, "SIM", "06:12:00"],
        # Trecho 3: Retorna e pousa no Unibrasil (82821020 -> não entra na lista de recargas intermediárias)
        ["80020000", -25.4400, -49.2500, 1, "06:12:00", 36, "82821020", -25.4233, -49.2160, "SIM", "06:20:00"],
    ]
    with open(caminho, mode="w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerow(cabecalho)
        escritor.writerows(linhas)


def test_carregar_dados_rota_extrai_pontos_e_pousos(tmp_path: Path):
    """Verifica se coordenadas, ponto base e recargas intermediárias são lidos corretamente."""
    csv_teste = tmp_path / "rota_teste.csv"
    criar_csv_rota_exemplo(csv_teste)

    lats, lons, pousos_lat, pousos_lon, base = carregar_dados_rota(csv_teste)

    # 3 trechos = 4 pontos na sequência (origem + 3 destinos)
    assert len(lats) == 4
    assert len(lons) == 4
    assert base == (-25.4233, -49.2160)

    # Apenas o pouso intermediário (80020000) deve entrar na lista de recargas laranjas
    assert len(pousos_lat) == 1
    assert len(pousos_lon) == 1
    assert pousos_lat[0] == -25.4400
    assert pousos_lon[0] == -49.2500


def test_gerar_mapa_cria_arquivo_png_valido(tmp_path: Path):
    """Garante que o arquivo PNG é criado no destino e possui cabeçalho válido."""
    csv_teste = tmp_path / "rota_teste.csv"
    img_saida = tmp_path / "subpasta" / "mapa_teste.png"
    criar_csv_rota_exemplo(csv_teste)

    gerar_mapa(csv_teste, img_saida)

    assert img_saida.exists()
    assert img_saida.stat().st_size > 0
    # Verifica assinatura mágica padrão de arquivos PNG
    assert img_saida.read_bytes().startswith(b"\x89PNG")


def test_gerar_mapa_erro_csv_inexistente(tmp_path: Path):
    """Garante que FileNotFoundError é levantado caso o CSV de entrada não exista."""
    csv_falso = tmp_path / "nao_existe.csv"
    img_saida = tmp_path / "mapa.png"

    with pytest.raises(FileNotFoundError):
        gerar_mapa(csv_falso, img_saida)