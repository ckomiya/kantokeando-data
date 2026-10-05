"""
Transforma data/raw/copas_y_torneos.xlsx en tablas normalizadas (torneos,
equipos, jugadores, resultados, resultado_jugadores), aplicando los alias de
jugadores ya decididos en data/alias/.

Es la parte compartida del pipeline (ver CLAUDE.md): la usan tanto
exportar_datos.py (JSON para la web) como cargar_datos.py (Neon, opcional).
"""

import re
from collections import Counter, defaultdict

import pandas as pd

from validar_nombres import (
    EXCEL_FUENTE,
    cargar_alias_decididos,
    clave_normalizada,
    dividir_jugadores,
    quitar_tildes,
)


def generar_slug(texto: str) -> str:
    sin_tildes = quitar_tildes(texto).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", sin_tildes).strip("-")
    return slug or "torneo"


def generar_id_torneo(nombre_torneo: str, fecha_torneo, usados: set[str]) -> str:
    base = f"{fecha_torneo.date().isoformat()}-{generar_slug(nombre_torneo)}"
    id_torneo = base
    sufijo = 2
    while id_torneo in usados:
        id_torneo = f"{base}-{sufijo}"
        sufijo += 1
    usados.add(id_torneo)
    return id_torneo


def construir_mapa_canonico(df: pd.DataFrame) -> dict[str, str]:
    """Resuelve cada nombre crudo a su forma canónica.

    Primero agrupa automáticamente por orden/tildes/mayúsculas (se queda con
    la variante más frecuente); luego aplica las decisiones manuales de
    data/alias/jugadores.csv, que tienen prioridad.
    """
    contador = Counter()
    for celda in df["jugadores"]:
        for nombre in dividir_jugadores(celda):
            contador[nombre] += 1

    grupos = defaultdict(list)
    for nombre in contador:
        grupos[clave_normalizada(nombre)].append(nombre)

    mapa = {}
    for variantes in grupos.values():
        canonico = sorted(variantes, key=lambda n: (-contador[n], n))[0]
        for variante in variantes:
            mapa[variante] = canonico

    for original, canonico in cargar_alias_decididos().items():
        mapa[original] = canonico

    # Resolver la cadena completa: un nombre agrupado automáticamente con una
    # variante que a su vez tiene alias manual debe terminar en el destino final
    # (ej. "Sakugawa Lucho" -> "Lucho Sakugawa" -> "Luis Sakugawa").
    def resolver_final(nombre: str) -> str:
        actual = nombre
        visitados = set()
        while actual in mapa and mapa[actual] != actual and actual not in visitados:
            visitados.add(actual)
            actual = mapa[actual]
        return actual

    return {original: resolver_final(original) for original in mapa}


def clave_equipo(nombre: str) -> str:
    """Clave para unir variantes de un equipo: ignora mayúsculas, tildes y espacios."""
    return quitar_tildes(re.sub(r"\s+", " ", nombre.strip())).lower()


def construir_mapa_equipos(df: pd.DataFrame) -> dict[str, str]:
    """Mapea cada nombre crudo de equipo a su forma canónica.

    Une solo diferencias de mayúsculas, tildes y espacios (misma regla que los
    jugadores). "Lunes" y "Lunes 1" siguen siendo equipos distintos. Se queda
    con la variante más frecuente.
    """
    contador = Counter(
        re.sub(r"\s+", " ", n.strip()) for n in df["equipo"].dropna()
    )
    grupos = defaultdict(list)
    for nombre in contador:
        grupos[clave_equipo(nombre)].append(nombre)

    mapa = {}
    for variantes in grupos.values():
        # en empates, preferir la variante que no está toda en mayúsculas
        canonico = sorted(variantes, key=lambda n: (-contador[n], n.isupper(), n))[0]
        for variante in variantes:
            mapa[variante] = canonico
        if len(variantes) > 1:
            print(f"AVISO: equipos unidos automáticamente -> '{canonico}': {sorted(variantes)}")
    return mapa


def construir_tablas(df: pd.DataFrame):
    mapa_jugadores = construir_mapa_canonico(df)

    # --- torneos: una fila por (nombre_torneo, fecha_torneo) ---
    filas_torneos = []
    ids_usados: set[str] = set()
    mapa_id_torneo = {}

    for (nombre_torneo, fecha_torneo), grupo in df.groupby(
        ["nombre_torneo", "fecha_torneo"], sort=False
    ):
        id_torneo = generar_id_torneo(nombre_torneo, fecha_torneo, ids_usados)
        mapa_id_torneo[(nombre_torneo, fecha_torneo)] = id_torneo

        if grupo["URL"].nunique() > 1:
            print(
                f"AVISO: '{nombre_torneo}' ({fecha_torneo.date()}) tiene URLs "
                f"distintas en el Excel; se usa la más frecuente."
            )

        def moda_o_none(serie: pd.Series):
            serie = serie.dropna()
            if serie.empty:
                return None
            return serie.mode().iloc[0]

        filas_torneos.append({
            "id_torneo": id_torneo,
            "nombre_torneo": nombre_torneo,
            "nombre_comun": moda_o_none(grupo["nombre_comun"]),
            "fecha_torneo": fecha_torneo.date(),
            "anio": fecha_torneo.year,
            "tipo": moda_o_none(grupo["tipo"]),
            "pais": moda_o_none(grupo["País"]),
            "lugar": moda_o_none(grupo["lugar"]),
            "url": moda_o_none(grupo["URL"]),
        })

    df_torneos = pd.DataFrame(filas_torneos)

    # --- equipos ---
    mapa_equipos = construir_mapa_equipos(df)
    nombres_equipo = sorted(set(mapa_equipos.values()))
    df_equipos = pd.DataFrame({"nombre_equipo": nombres_equipo})
    df_equipos.insert(0, "id_equipo", range(1, len(df_equipos) + 1))
    mapa_id_equipo = dict(zip(df_equipos["nombre_equipo"], df_equipos["id_equipo"]))

    # --- jugadores ---
    nombres_canonicos = sorted(set(mapa_jugadores.values()))
    df_jugadores = pd.DataFrame({"nombre_canonico": nombres_canonicos})
    df_jugadores.insert(0, "id_jugador", range(1, len(df_jugadores) + 1))
    mapa_id_jugador = dict(zip(df_jugadores["nombre_canonico"], df_jugadores["id_jugador"]))

    # --- resultados + resultado_jugadores ---
    filas_resultados = []
    filas_resultado_jugadores = []
    filas_sin_jugadores = 0

    for id_resultado, fila in enumerate(df.itertuples(index=False), start=1):
        id_torneo = mapa_id_torneo[(fila.nombre_torneo, fila.fecha_torneo)]
        equipo = mapa_equipos[re.sub(r"\s+", " ", fila.equipo.strip())] if pd.notna(fila.equipo) else None
        id_equipo = mapa_id_equipo[equipo] if equipo else None
        puesto = int(fila.puesto) if pd.notna(fila.puesto) else None
        extranjero = fila.Extranjero == "S" if pd.notna(fila.Extranjero) else False
        categoria = fila.categoria if pd.notna(fila.categoria) else None

        nombres = dividir_jugadores(fila.jugadores)
        if not nombres:
            filas_sin_jugadores += 1

        filas_resultados.append({
            "id_resultado": id_resultado,
            "id_torneo": id_torneo,
            "id_equipo": id_equipo,
            "categoria": categoria,
            "puesto": puesto,
            "extranjero": extranjero,
        })

        ids_jugador_vistos = set()
        for nombre_original in nombres:
            canonico = mapa_jugadores.get(nombre_original, nombre_original)
            id_jugador = mapa_id_jugador[canonico]
            if id_jugador in ids_jugador_vistos:
                print(
                    f"AVISO: jugador '{nombre_original}' repetido en la misma "
                    f"celda (torneo '{fila.nombre_torneo}', {fila.fecha_torneo.date()}, "
                    f"equipo '{fila.equipo}'); se ignora la repetición."
                )
                continue
            ids_jugador_vistos.add(id_jugador)
            filas_resultado_jugadores.append({
                "id_resultado": id_resultado,
                "id_jugador": id_jugador,
                "texto_original": nombre_original,
            })

    df_resultados = pd.DataFrame(filas_resultados)
    df_resultado_jugadores = pd.DataFrame(filas_resultado_jugadores)

    print(f"Torneos: {len(df_torneos)}")
    print(f"Equipos: {len(df_equipos)}")
    print(f"Jugadores: {len(df_jugadores)}")
    print(f"Resultados: {len(df_resultados)}")
    print(f"Relaciones resultado-jugador: {len(df_resultado_jugadores)}")
    print(f"Resultados sin jugadores registrados: {filas_sin_jugadores}")

    return df_torneos, df_equipos, df_jugadores, df_resultados, df_resultado_jugadores


def leer_tablas():
    """Lee el Excel fuente y devuelve las cinco tablas normalizadas."""
    print(f"Leyendo {EXCEL_FUENTE} ...")
    df = pd.read_excel(EXCEL_FUENTE, sheet_name="Resultados")
    return construir_tablas(df)
