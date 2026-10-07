"""
Detecta jugadores nuevos en los registros agregados al Excel.

Compara el Excel actual con la versión del último commit (git HEAD) o con otro
libro que se indique, y lista los jugadores que solo aparecen en las filas
nuevas. Para cada uno propone nombres ya existentes que se le parecen (posible
tipeo o variante): el programa PROPONE, el usuario DECIDE (ver CLAUDE.md).

Uso:
    python scripts/jugadores_nuevos.py                  # contra git HEAD
    python scripts/jugadores_nuevos.py otro_libro.xlsx  # contra otro Excel
"""

import subprocess
import sys
from collections import Counter
from io import BytesIO
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

from transformar import construir_mapa_canonico
from validar_nombres import (
    EXCEL_FUENTE,
    RAIZ,
    clave_normalizada,
    dividir_jugadores,
    es_par_de_riesgo,
)

UMBRAL_PARECIDO = 80  # similitud mínima (0-100) para proponer un nombre existente


def leer_excel_anterior(ruta: str | None) -> pd.DataFrame:
    if ruta:
        return pd.read_excel(ruta, sheet_name="Resultados")
    relativa = EXCEL_FUENTE.relative_to(RAIZ).as_posix()
    salida = subprocess.run(
        ["git", "show", f"HEAD:{relativa}"], cwd=RAIZ, capture_output=True, check=True
    ).stdout
    return pd.read_excel(BytesIO(salida), sheet_name="Resultados")


def filas_nuevas(df_antes: pd.DataFrame, df_ahora: pd.DataFrame) -> pd.DataFrame:
    """Filas de df_ahora que no estaban en df_antes (se comparan por contenido, no por posición)."""
    def clave(fila) -> tuple:
        return tuple("" if pd.isna(v) else str(v).strip() for v in fila)

    pendientes = Counter(clave(f) for f in df_antes.itertuples(index=False))
    nuevas = []
    for i, fila in enumerate(df_ahora.itertuples(index=False)):
        k = clave(fila)
        if pendientes[k] > 0:
            pendientes[k] -= 1
        else:
            nuevas.append(i)
    return df_ahora.iloc[nuevas]


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else None
    df_ahora = pd.read_excel(EXCEL_FUENTE, sheet_name="Resultados")
    df_antes = leer_excel_anterior(ruta)
    nuevas = filas_nuevas(df_antes, df_ahora)
    print(f"Filas: {len(df_antes)} antes, {len(df_ahora)} ahora, {len(nuevas)} nuevas.")
    if nuevas.empty:
        print("No hay filas nuevas.")
        return

    # Los alias se resuelven con TODOS los datos actuales, igual que en el pipeline.
    mapa = construir_mapa_canonico(df_ahora)

    def canonicos(df) -> Counter:
        c = Counter()
        for celda in df["jugadores"]:
            for n in dividir_jugadores(celda):
                c[mapa.get(n, n)] += 1
        return c

    existentes = set(canonicos(df_antes))
    en_nuevas = canonicos(nuevas)
    nuevos = sorted(n for n in en_nuevas if n not in existentes)

    print("\nRegistros nuevos:")
    for fila in nuevas.itertuples(index=False):
        print(f"  {fila.fecha_torneo:%Y-%m-%d} | {fila.nombre_torneo} | {fila.categoria} "
              f"| puesto {fila.puesto} | {fila.equipo}")

    print(f"\nJugadores en las filas nuevas: {len(en_nuevas)} "
          f"({len(en_nuevas) - len(nuevos)} ya existían, {len(nuevos)} son nuevos).")
    if not nuevos:
        print("No hay jugadores nuevos.")
        return

    claves = {n: clave_normalizada(n) for n in existentes}
    por_clave = {}
    for n, k in claves.items():
        por_clave.setdefault(k, []).append(n)

    print("\nJugadores NUEVOS (revisar si alguno es en realidad uno existente):")
    for nuevo in nuevos:
        equipos = sorted({
            str(f.equipo) for f in nuevas.itertuples(index=False)
            if any(mapa.get(n, n) == nuevo for n in dividir_jugadores(f.jugadores))
        })
        print(f"\n* {nuevo}  (equipo: {', '.join(equipos)})")
        parecidos = process.extract(
            clave_normalizada(nuevo), list(por_clave), scorer=fuzz.token_sort_ratio,
            score_cutoff=UMBRAL_PARECIDO, limit=5,
        )
        for k, puntaje, _ in parecidos:
            for existente in por_clave[k]:
                riesgo = "  [¡cuidado: par de riesgo, podrían ser personas distintas!]" \
                    if es_par_de_riesgo(nuevo, existente) else ""
                print(f"    ¿es {existente}?  similitud {puntaje:.0f}{riesgo}")
        if not parecidos:
            print("    (sin nombres parecidos: probablemente una persona nueva)")

    print("\nSi alguno es un existente, agregar el alias en data/alias/jugadores.csv; "
          "si son personas distintas pero parecidas, en data/alias/no_unir.csv.")


if __name__ == "__main__":
    main()
