import csv
from pathlib import Path
from typing import List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def carregar_dados_rota(
    caminho_csv: Path,
) -> Tuple[List[float], List[float], List[float], List[float], Tuple[float, float]]:
    """Lê o CSV da rota e extrai coordenadas do trajeto, pousos de recarga e ponto base."""
    lats: List[float] = []
    lons: List[float] = []
    pousos_lat: List[float] = []
    pousos_lon: List[float] = []
    base_lat, base_lon = 0.0, 0.0

    with open(caminho_csv, mode="r", encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        for i, linha in enumerate(leitor):
            lat_ini = float(linha["Latitude inicial"])
            lon_ini = float(linha["Longitude inicial"])
            lat_fim = float(linha["Latitude final"])
            lon_fim = float(linha["Longitude final"])

            if i == 0:
                base_lat, base_lon = lat_ini, lon_ini
                lats.append(lat_ini)
                lons.append(lon_ini)

            lats.append(lat_fim)
            lons.append(lon_fim)

            if linha["Pouso"] == "SIM" and linha["CEP final"] != "82821020":
                pousos_lat.append(lat_fim)
                pousos_lon.append(lon_fim)

    return lats, lons, pousos_lat, pousos_lon, (base_lat, base_lon)


def gerar_mapa(caminho_csv: Path, caminho_imagem: Path) -> None:
    """Gera e salva o gráfico PNG da rota otimizada a partir do CSV final."""
    lats, lons, pousos_lat, pousos_lon, (base_lat, base_lon) = carregar_dados_rota(caminho_csv)

    plt.figure(figsize=(10, 8))
    plt.plot(lons, lats, color="royalblue", linewidth=0.8, alpha=0.7, zorder=1)
    plt.scatter(lons, lats, color="royalblue", s=18, label="CEPs Visitados", zorder=2)
    plt.scatter(pousos_lon, pousos_lat, color="orange", s=55, marker="^", label="Recarga (Pouso = SIM)", zorder=3)
    plt.scatter([base_lon], [base_lat], color="red", s=90, label="Unibrasil (82821020)", zorder=4)

    plt.title("Rota Otimizada - UNIBRASIL Surveyor")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()

    caminho_imagem.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(caminho_imagem, dpi=150)
    plt.close()


if __name__ == "__main__":
    RAIZ = Path(__file__).resolve().parent.parent
    CSV_PATH = RAIZ / "output" / "solucao_final.csv"
    IMAGEM_PATH = RAIZ / "output" / "mapa_rota.png"
    gerar_mapa(CSV_PATH, IMAGEM_PATH)
    print(f"Gráfico salvo com sucesso em: {IMAGEM_PATH}")