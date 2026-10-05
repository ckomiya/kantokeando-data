"""
Exporta los datos normalizados a JSON para la web (web/src/data/).

Pipeline (ver CLAUDE.md): Excel + alias -> validación -> JSON -> astro build.
No usa la base de datos ni credenciales. La salida es determinista (sin fechas
de generación) para que `git diff` muestre solo lo que cambió en los datos.

Archivos generados:
  torneos.json   torneos con sus resultados (podios por categoría)
  jugadores.json fichas de jugador: participaciones y medallero
  equipos.json   fichas de equipo: participaciones y medallero
  busqueda.json  índice compacto para el buscador
  resumen.json   totales y torneos por año
  posiciones.json tablas de posiciones por año y categoría (hoja "Posiciones")
"""

import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

from transformar import ORDEN_CATEGORIAS_POSICIONES, generar_slug, leer_posiciones, leer_tablas

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "web" / "src" / "data"


def nulo(valor):
    return None if pd.isna(valor) else valor


def asignar_slugs(nombres_por_id: dict[int, str], vacio: str) -> dict[int, str]:
    """Slug legible y único por id; si dos nombres colisionan, agrega sufijo."""
    usados: set[str] = set()
    slugs = {}
    for id_, nombre in sorted(nombres_por_id.items()):
        base = generar_slug(nombre) if nombre else vacio
        slug, sufijo = base, 2
        while slug in usados:
            slug = f"{base}-{sufijo}"
            sufijo += 1
        usados.add(slug)
        slugs[id_] = slug
    return slugs


def medallero(puestos: list) -> dict[str, int]:
    return {str(p): sum(1 for x in puestos if x == p) for p in (1, 2, 3)}


def construir_exportacion(df_torneos, df_equipos, df_jugadores, df_resultados, df_rj):
    nombre_jugador = dict(zip(df_jugadores["id_jugador"], df_jugadores["nombre_canonico"]))
    nombre_equipo = dict(zip(df_equipos["id_equipo"], df_equipos["nombre_equipo"]))
    es_extranjero = dict(zip(df_equipos["id_equipo"], df_equipos["extranjero"].astype(bool)))

    # Decisión del usuario: los equipos marcados Extranjero = "S" no existen como equipo
    # en la web (sin ficha, sin buscador, sin listado, sin enlace). Sus resultados SÍ
    # siguen en los podios de los torneos, como texto con la etiqueta "Extranjero".
    # Igual con los jugadores extranjeros: quien solo jugó con equipos extranjeros no tiene
    # ficha ni sale en el buscador; su nombre queda como texto en los podios.
    resultados_locales = set(df_resultados.loc[~df_resultados["extranjero"], "id_resultado"])
    jugadores_con_ficha = {int(r.id_jugador) for r in df_rj.itertuples(index=False) if r.id_resultado in resultados_locales}
    slug_jugador = asignar_slugs({i: n for i, n in nombre_jugador.items() if i in jugadores_con_ficha}, "jugador")
    slug_equipo = asignar_slugs({i: n for i, n in nombre_equipo.items() if not es_extranjero[i]}, "equipo")
    torneo_por_id = {fila["id_torneo"]: fila for fila in df_torneos.to_dict("records")}

    jugadores_de = defaultdict(list)
    for fila in df_rj.itertuples(index=False):
        jugadores_de[fila.id_resultado].append(int(fila.id_jugador))

    def ref_jugador(id_jugador):
        return {"slug": slug_jugador.get(id_jugador), "nombre": nombre_jugador[id_jugador]}

    def ref_equipo(id_equipo):
        if pd.isna(id_equipo):
            return None
        id_equipo = int(id_equipo)
        if es_extranjero[id_equipo]:
            return {"slug": None, "nombre": nombre_equipo[id_equipo], "extranjero": True}
        return {"slug": slug_equipo[id_equipo], "nombre": nombre_equipo[id_equipo]}

    # --- torneos con sus resultados, en el orden del Excel ---
    resultados_de = defaultdict(list)
    for fila in df_resultados.to_dict("records"):
        resultados_de[fila["id_torneo"]].append({
            "id_resultado": fila["id_resultado"],
            "categoria": nulo(fila["categoria"]),
            "puesto": None if pd.isna(fila["puesto"]) else int(fila["puesto"]),
            "equipo": ref_equipo(fila["id_equipo"]),
            "extranjero": bool(fila["extranjero"]),
            "jugadores": [ref_jugador(j) for j in jugadores_de[fila["id_resultado"]]],
        })

    torneos = []
    for t in sorted(torneo_por_id.values(), key=lambda t: (t["fecha_torneo"], t["id_torneo"])):
        torneos.append({
            "id": t["id_torneo"],
            "nombre": t["nombre_torneo"],
            "nombre_comun": nulo(t["nombre_comun"]),
            "fecha": t["fecha_torneo"].isoformat(),
            "anio": int(t["anio"]),
            "tipo": nulo(t["tipo"]),
            "pais": nulo(t["pais"]),
            "lugar": nulo(t["lugar"]),
            "url": nulo(t["url"]),
            "resultados": [
                {k: v for k, v in r.items() if k != "id_resultado"}
                for r in resultados_de[t["id_torneo"]]
            ],
        })

    # --- participaciones por jugador y por equipo ---
    part_jugador = defaultdict(list)
    part_equipo = defaultdict(list)
    for fila in df_resultados.to_dict("records"):
        t = torneo_por_id[fila["id_torneo"]]
        base = {
            "torneo": t["id_torneo"],
            "nombre_torneo": t["nombre_torneo"],
            "fecha": t["fecha_torneo"].isoformat(),
            "anio": int(t["anio"]),
            "categoria": nulo(fila["categoria"]),
            "puesto": None if pd.isna(fila["puesto"]) else int(fila["puesto"]),
            "url": nulo(t["url"]),
        }
        equipo = ref_equipo(fila["id_equipo"])
        ids_jug = jugadores_de[fila["id_resultado"]]
        for j in ids_jug:
            part_jugador[j].append({**base, "equipo": equipo})
        if equipo and equipo["slug"]:  # los extranjeros no tienen ficha
            part_equipo[int(fila["id_equipo"])].append({
                **base,
                "jugadores": [ref_jugador(j) for j in ids_jug],
                # para decidir qué equipos se listan en la web (ver equipoListable en datos.ts)
                "tipo": nulo(t["tipo"]),
            })

    def orden_reciente(p):
        return (p["fecha"], p["torneo"], p["categoria"] or "")

    jugadores = []
    for id_j in sorted(slug_jugador, key=lambda i: slug_jugador[i]):
        partes = sorted(part_jugador[id_j], key=orden_reciente, reverse=True)
        jugadores.append({
            "slug": slug_jugador[id_j],
            "nombre": nombre_jugador[id_j],
            "torneos": len({p["torneo"] for p in partes}),
            "medallas": medallero([p["puesto"] for p in partes]),
            "participaciones": partes,
        })

    equipos = []
    for id_e in sorted(slug_equipo, key=lambda i: slug_equipo[i]):
        partes = sorted(part_equipo[id_e], key=orden_reciente, reverse=True)
        equipos.append({
            "slug": slug_equipo[id_e],
            "nombre": nombre_equipo[id_e],
            "torneos": len({p["torneo"] for p in partes}),
            "medallas": medallero([p["puesto"] for p in partes]),
            "participaciones": partes,
        })

    # --- índice de búsqueda (j = jugador, e = equipo, t = torneo) ---
    def campeones(t):
        """[[categoría, equipo], ...] de los primeros puestos, para la respuesta rápida."""
        return [
            [r["categoria"], r["equipo"]["nombre"] if r["equipo"]
             else ", ".join(j["nombre"] for j in r["jugadores"])]
            for r in t["resultados"]
            if r["puesto"] == 1 and (r["equipo"] or r["jugadores"])
        ]

    busqueda = (
        [{"t": "j", "n": j["nombre"], "s": j["slug"], "m": j["torneos"]} for j in jugadores]
        + [{"t": "e", "n": e["nombre"], "s": e["slug"], "m": e["medallas"]["1"]} for e in equipos]
        + [{"t": "t", "n": t["nombre"], "s": t["id"], "y": t["anio"],
            "c": t["nombre_comun"], "w": campeones(t)} for t in torneos]
    )

    por_anio = defaultdict(int)
    for t in torneos:
        por_anio[t["anio"]] += 1
    anios = sorted(por_anio)
    resumen = {
        "torneos": len(torneos),
        "resultados": len(df_resultados),
        "jugadores": len(jugadores),
        "equipos": len(equipos),
        # incluye años sin torneos (ej. 2020) para que la web los muestre vacíos
        "anios": [{"anio": a, "torneos": por_anio.get(a, 0)} for a in range(anios[0], anios[-1] + 1)],
    }

    return {
        "torneos": torneos,
        "jugadores": jugadores,
        "equipos": equipos,
        "busqueda": busqueda,
        "resumen": resumen,
    }


def entero(valor):
    return None if pd.isna(valor) else int(valor)


def construir_posiciones(df_pos: pd.DataFrame, df_equipos) -> list[dict]:
    """Tablas de posiciones: [{anio, categorias: [{nombre, estado, filas: [...]}]}].

    Un equipo se enlaza a su ficha solo si existe como equipo local (no extranjero);
    si no, queda como texto. Las columnas de probabilidades se exportan solo si la
    categoría tiene algún valor.
    """
    slug_equipo = asignar_slugs(
        {i: n for i, n, e in zip(df_equipos["id_equipo"], df_equipos["nombre_equipo"], df_equipos["extranjero"]) if not e},
        "equipo",
    )
    nombres = {n: slug_equipo[i] for i, n in zip(df_equipos["id_equipo"], df_equipos["nombre_equipo"]) if i in slug_equipo}

    def orden_categoria(nombre):
        orden = ORDEN_CATEGORIAS_POSICIONES
        return (orden.index(nombre) if nombre in orden else len(orden), nombre)

    anios = []
    for anio, df_a in df_pos.groupby("Año"):
        categorias = []
        for nombre in sorted(df_a["Categoría"].unique(), key=orden_categoria):
            df_c = df_a[df_a["Categoría"] == nombre].sort_values("Pos.")
            estados = sorted(df_c["Estado"].dropna().unique())
            con_prob = df_c[["% Prob. campeonar", "% Prob. descender"]].notna().any().any()
            filas = []
            for f in df_c.to_dict("records"):
                fila = {
                    "pos": int(f["Pos."]),
                    "equipo": {"slug": nombres.get(f["Equipo"]), "nombre": f["Equipo"]},
                    "pj": entero(f["PJ"]), "g": entero(f["G"]), "e": entero(f["E"]), "p": entero(f["P"]),
                    "wo": entero(f["WO"]), "gf": entero(f["GF"]), "gc": entero(f["GC"]),
                    "dg": entero(f["DG"]), "pts": entero(f["Pts."]),
                }
                if con_prob:
                    fila["prob_campeonar"] = None if pd.isna(f["% Prob. campeonar"]) else float(f["% Prob. campeonar"])
                    fila["prob_descender"] = None if pd.isna(f["% Prob. descender"]) else float(f["% Prob. descender"])
                filas.append(fila)
            categorias.append({
                "nombre": nombre,
                "estado": estados[0] if len(estados) == 1 else None,
                "filas": filas,
            })
        anios.append({"anio": int(anio), "categorias": categorias})
    return anios


def validar(datos: dict):
    """Chequeos mínimos de integridad antes de escribir."""
    ids = [t["id"] for t in datos["torneos"]]
    assert len(ids) == len(set(ids)), "ids de torneo duplicados"
    for clave in ("jugadores", "equipos"):
        slugs = [x["slug"] for x in datos[clave]]
        assert len(slugs) == len(set(slugs)), f"slugs duplicados en {clave}"
    for a in datos["posiciones"]:
        for c in a["categorias"]:
            pos = [f["pos"] for f in c["filas"]]
            assert len(pos) == len(set(pos)), f"posiciones repetidas en {a['anio']} {c['nombre']}"
            nombres = [f["equipo"]["nombre"] for f in c["filas"]]
            assert len(nombres) == len(set(nombres)), f"equipo repetido en {a['anio']} {c['nombre']}"
            if c["estado"] is None:
                print(f"AVISO: estado mezclado o vacío en posiciones {a['anio']} {c['nombre']}")
            for f in c["filas"]:
                if f["equipo"]["slug"] is None:
                    print(f"AVISO: posiciones {a['anio']} {c['nombre']}: '{f['equipo']['nombre']}' no tiene ficha (no figura en Resultados)")
    conocidos = {j["slug"] for j in datos["jugadores"]}  # los extranjeros llevan slug None
    for t in datos["torneos"]:
        for r in t["resultados"]:
            for j in r["jugadores"]:
                assert j["slug"] is None or j["slug"] in conocidos, f"jugador desconocido: {j['slug']}"


def exportar():
    tablas = leer_tablas()
    datos = construir_exportacion(*tablas)
    df_pos = leer_posiciones()
    datos["posiciones"] = construir_posiciones(df_pos, tablas[1])
    validar(datos)

    DESTINO.mkdir(parents=True, exist_ok=True)
    for nombre, contenido in datos.items():
        ruta = DESTINO / f"{nombre}.json"
        # el índice de búsqueda va compacto (se descarga en el navegador)
        if nombre == "busqueda":
            texto = json.dumps(contenido, ensure_ascii=False, separators=(",", ":"))
        else:
            texto = json.dumps(contenido, ensure_ascii=False, indent=1)
        ruta.write_text(texto + "\n", encoding="utf-8")
        print(f"Escrito {ruta.relative_to(RAIZ)} ({ruta.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    exportar()
