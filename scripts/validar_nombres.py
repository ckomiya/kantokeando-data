"""
Valida la columna "jugadores" del Excel fuente (data/raw/).

Genera reports/validacion_nombres_<fecha>.xlsx con:
  - "Posibles duplicados": grupos de nombres que podrían ser la misma persona,
    con el nivel de confianza y el motivo de la coincidencia.
  - "Problemas de formato": celdas con separadores ambiguos, nombres vacíos,
    espacios repetidos, puntos sueltos u otros problemas de formato.
  - "Nombres únicos": listado de todos los nombres individuales detectados,
    con su frecuencia, para referencia al crear alias en data/alias/.

El programa solo PROPONE agrupaciones; la decisión final de unir nombres
se registra manualmente en data/alias/ (ver CLAUDE.md).
"""

import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import pandas as pd
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from rapidfuzz import fuzz

RAIZ = Path(__file__).resolve().parent.parent
EXCEL_FUENTE = RAIZ / "data" / "raw" / "copas_y_torneos.xlsx"
CARPETA_REPORTES = RAIZ / "reports"
CARPETA_ALIAS = RAIZ / "data" / "alias"
ARCHIVO_ALIAS_DECIDIDOS = CARPETA_ALIAS / "jugadores.csv"
ARCHIVO_NO_UNIR = CARPETA_ALIAS / "no_unir.csv"
ARCHIVO_APODOS = CARPETA_ALIAS / "apodos.csv"
ARCHIVO_VARIANTES_APELLIDO = CARPETA_ALIAS / "variantes_apellido.csv"

SEPARADORES = re.compile(r",|;|\sy\s|\se\s", flags=re.IGNORECASE)

# Pares de nombres que difieren en algo más que tipeo/orden y requieren
# revisión manual explícita (riesgo de unir personas distintas).
PARES_DE_RIESGO = [
    ("luis", "luisa"),
    ("juan", "juana"),
    ("julio", "julia"),
    ("mario", "maria"),
    ("victor", "victoria"),
]

UMBRAL_FUZZY = 85  # similitud mínima (0-100) para proponer coincidencia por tipeo


def quitar_tildes(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def clave_normalizada(nombre: str) -> str:
    """Clave para detectar coincidencias exactas salvo orden/tildes/mayúsculas."""
    sin_tildes = quitar_tildes(nombre).lower()
    sin_tildes = re.sub(r"[^\w\s]", " ", sin_tildes)
    palabras = sorted(sin_tildes.split())
    return " ".join(palabras)


def cargar_apodos() -> dict[str, str]:
    """Equivalencias de palabras confirmadas por el usuario, ya normalizadas.

    Junta dos archivos con la misma mecánica (palabra -> forma preferida):
    - data/alias/apodos.csv (apodo, nombre_formal): alejo -> alejandro.
    - data/alias/variantes_apellido.csv (variante, apellido): tzukazan -> tsukazan.
    Regla: si existen "Alejo X" y "Alejandro X" (o "Mitsu Tzukazan" y "Mitsu
    Tsukazan"), en cualquier orden de palabras, son la misma persona.
    """
    equivalencias = {}
    for ruta, col_origen, col_destino in (
        (ARCHIVO_APODOS, "apodo", "nombre_formal"),
        (ARCHIVO_VARIANTES_APELLIDO, "variante", "apellido"),
    ):
        if not ruta.exists():
            continue
        df = pd.read_csv(ruta)
        for origen, destino in zip(df[col_origen], df[col_destino]):
            equivalencias[quitar_tildes(str(origen)).strip().lower()] = quitar_tildes(str(destino)).strip().lower()
    return equivalencias


def clave_con_apodos(nombre: str, apodos: dict[str, str] | None = None) -> str:
    """Como clave_normalizada, pero tratando cada apodo como su nombre formal."""
    if apodos is None:
        apodos = cargar_apodos()
    palabras = [apodos.get(p, p) for p in clave_normalizada(nombre).split()]
    return " ".join(sorted(palabras))


def tiene_apodo(nombre: str, apodos: dict[str, str] | None = None) -> bool:
    if apodos is None:
        apodos = cargar_apodos()
    return any(p in apodos for p in clave_normalizada(nombre).split())


def dividir_jugadores(celda: str):
    """Separa la celda "jugadores" en nombres individuales, conservando crudos."""
    if not isinstance(celda, str) or not celda.strip():
        return []
    partes = SEPARADORES.split(celda)
    return [p.strip() for p in partes if p.strip()]


def detectar_problemas_formato(fila_idx: int, celda_original, nombres: list[str]):
    problemas = []
    if not isinstance(celda_original, str) or not celda_original.strip():
        problemas.append({
            "fila_excel": fila_idx,
            "celda": celda_original,
            "problema": "Celda vacía o no es texto",
        })
        return problemas

    if re.search(r"\s{2,}", celda_original):
        problemas.append({
            "fila_excel": fila_idx,
            "celda": celda_original,
            "problema": "Espacios repetidos",
        })

    if re.search(r",\s*,|;\s*;", celda_original):
        problemas.append({
            "fila_excel": fila_idx,
            "celda": celda_original,
            "problema": "Separador duplicado (coma o punto y coma consecutivos)",
        })

    if celda_original.strip().endswith((",", ";")):
        problemas.append({
            "fila_excel": fila_idx,
            "celda": celda_original,
            "problema": "Termina en separador suelto",
        })

    for nombre in nombres:
        if not nombre:
            continue
        if re.search(r"\d", nombre):
            problemas.append({
                "fila_excel": fila_idx,
                "celda": celda_original,
                "problema": f"Nombre con dígitos: '{nombre}'",
            })
        if len(nombre.split()) == 1:
            problemas.append({
                "fila_excel": fila_idx,
                "celda": celda_original,
                "problema": f"Nombre de una sola palabra (¿falta apellido o nombre?): '{nombre}'",
            })
        if nombre.count(".") > 1 or (nombre.endswith(".") and not re.match(r"^[A-Za-zÀ-ÿ]\.$", nombre.split()[-1])):
            problemas.append({
                "fila_excel": fila_idx,
                "celda": celda_original,
                "problema": f"Puntuación sospechosa en nombre: '{nombre}'",
            })

    claves_vistas = {}
    for nombre in nombres:
        if not nombre:
            continue
        clave = clave_normalizada(nombre)
        if clave in claves_vistas:
            problemas.append({
                "fila_excel": fila_idx,
                "celda": celda_original,
                "problema": (
                    f"Jugador repetido en la misma celda: '{claves_vistas[clave]}' y '{nombre}'"
                ),
            })
        else:
            claves_vistas[clave] = nombre

    return problemas


def es_par_de_riesgo(a: str, b: str) -> bool:
    a_l, b_l = quitar_tildes(a).lower(), quitar_tildes(b).lower()
    palabras_a = set(a_l.split())
    palabras_b = set(b_l.split())
    for x, y in PARES_DE_RIESGO:
        if (x in palabras_a and y in palabras_b) or (y in palabras_a and x in palabras_b):
            return True
    return False

def comparten_solo_apellido(a: str, b: str) -> bool:
    """Heurística: mismo apellido(s) pero nombres de pila distintos -> no agrupar."""
    pa, pb = a.lower().split(), b.lower().split()
    if len(pa) < 2 or len(pb) < 2:
        return False
    apellidos_a, apellidos_b = set(pa[1:]), set(pb[1:])
    nombres_a, nombres_b = pa[0], pb[0]
    if apellidos_a & apellidos_b and nombres_a != nombres_b:
        # tipeo leve en el nombre de pila (ej. mismo apellido, nombre muy parecido) sí se evalúa aparte
        return fuzz.ratio(nombres_a, nombres_b) < 80
    return False


def cargar_alias_decididos() -> dict[str, str]:
    """Lee data/alias/jugadores.csv: texto_original -> jugador_canonico (decisiones ya tomadas)."""
    if not ARCHIVO_ALIAS_DECIDIDOS.exists():
        return {}
    df = pd.read_csv(ARCHIVO_ALIAS_DECIDIDOS)
    return dict(zip(df["texto_original"], df["jugador_canonico"]))


def cargar_pares_no_unir() -> set[frozenset]:
    """Lee data/alias/no_unir.csv: pares ya revisados y confirmados como personas distintas."""
    if not ARCHIVO_NO_UNIR.exists():
        return set()
    df = pd.read_csv(ARCHIVO_NO_UNIR)
    return {frozenset((a, b)) for a, b in zip(df["nombre_1"], df["nombre_2"])}


def construir_grupos_exactos(nombres_unicos: list[str]):
    """Agrupa automáticamente solo por orden/tildes/mayúsculas (alta confianza)."""
    apodos = cargar_apodos()
    grupos = defaultdict(list)
    for nombre in nombres_unicos:
        grupos[clave_con_apodos(nombre, apodos)].append(nombre)
    return {clave: variantes for clave, variantes in grupos.items() if len(variantes) > 1}


def construir_grupos_fuzzy(
    nombres_unicos: list[str],
    ya_agrupados: set[str],
    alias_decididos: dict[str, str],
    pares_no_unir: set[frozenset],
):
    """Propone coincidencias por tipeo/abreviación entre nombres no agrupados aún."""
    pendientes = [n for n in nombres_unicos if n not in ya_agrupados]
    apodos = cargar_apodos()
    filas = []
    vistos = set()
    for i, a in enumerate(pendientes):
        for b in pendientes[i + 1:]:
            par = (a, b)
            if par in vistos:
                continue
            vistos.add(par)

            if frozenset((a, b)) in pares_no_unir:
                continue  # ya revisado manualmente: son personas distintas

            if alias_decididos.get(a, a) == alias_decididos.get(b, b) and (
                a in alias_decididos or b in alias_decididos
            ):
                continue  # ya decidido: son la misma persona (ver data/alias/jugadores.csv)

            if clave_con_apodos(a, apodos) == clave_con_apodos(b, apodos):
                continue  # ya unidos por la regla de apodos (data/alias/apodos.csv)

            if comparten_solo_apellido(a, b):
                continue  # regla CLAUDE.md: no agrupar solo por apellido compartido

            score = fuzz.token_sort_ratio(quitar_tildes(a).lower(), quitar_tildes(b).lower())
            if score < UMBRAL_FUZZY:
                continue

            riesgo = es_par_de_riesgo(a, b)
            filas.append({
                "nombre_1": a,
                "nombre_2": b,
                "similitud": round(score, 1),
                "tipo": "RIESGO: revisar con cuidado" if riesgo else "Posible tipeo/abreviación",
            })
    return filas


def construir_reporte():
    print(f"Leyendo {EXCEL_FUENTE} ...")
    df = pd.read_excel(EXCEL_FUENTE, sheet_name="Resultados")

    if "jugadores" not in df.columns:
        raise SystemExit("La hoja 'Resultados' no tiene columna 'jugadores'.")

    filas_problemas = []
    contador_nombres = Counter()
    nombre_a_filas = defaultdict(set)

    for idx, celda in enumerate(df["jugadores"], start=2):  # fila 2 = primera fila de datos
        nombres = dividir_jugadores(celda)
        filas_problemas.extend(detectar_problemas_formato(idx, celda, nombres))
        for nombre in nombres:
            contador_nombres[nombre] += 1
            nombre_a_filas[nombre].add(idx)

    nombres_unicos = sorted(contador_nombres.keys(), key=lambda n: n.lower())
    print(f"Nombres individuales distintos detectados: {len(nombres_unicos)}")

    alias_decididos = cargar_alias_decididos()
    pares_no_unir = cargar_pares_no_unir()

    grupos_exactos = construir_grupos_exactos(nombres_unicos)
    nombres_en_grupo_exacto = {n for variantes in grupos_exactos.values() for n in variantes}

    filas_duplicados = []
    for clave, variantes in sorted(grupos_exactos.items()):
        for variante in sorted(variantes):
            filas_duplicados.append({
                "grupo": clave,
                "nombre": variante,
                "frecuencia": contador_nombres[variante],
                "confianza": "Alta (orden/tildes/mayúsculas)",
                "tipo": "Automático",
            })

    filas_fuzzy = construir_grupos_fuzzy(
        nombres_unicos, nombres_en_grupo_exacto, alias_decididos, pares_no_unir
    )
    for i, fila in enumerate(filas_fuzzy, start=1):
        grupo_id = f"fuzzy-{i}"
        for nombre in (fila["nombre_1"], fila["nombre_2"]):
            filas_duplicados.append({
                "grupo": grupo_id,
                "nombre": nombre,
                "frecuencia": contador_nombres[nombre],
                "confianza": f"{fila['similitud']}% - {fila['tipo']}",
                "tipo": "Para revisión",
            })

    df_duplicados = pd.DataFrame(filas_duplicados)
    df_problemas = pd.DataFrame(filas_problemas)
    df_nombres = pd.DataFrame(
        [{"nombre": n, "frecuencia": contador_nombres[n]} for n in nombres_unicos]
    ).sort_values(["frecuencia", "nombre"], ascending=[False, True])

    CARPETA_REPORTES.mkdir(exist_ok=True)
    ruta_salida = CARPETA_REPORTES / f"validacion_nombres_{date.today().isoformat()}.xlsx"

    with pd.ExcelWriter(ruta_salida, engine="openpyxl") as writer:
        (df_duplicados if not df_duplicados.empty else pd.DataFrame(
            columns=["grupo", "nombre", "frecuencia", "confianza", "tipo"]
        )).to_excel(writer, sheet_name="Posibles duplicados", index=False)

        (df_problemas if not df_problemas.empty else pd.DataFrame(
            columns=["fila_excel", "celda", "problema"]
        )).to_excel(writer, sheet_name="Problemas de formato", index=False)

        df_nombres.to_excel(writer, sheet_name="Nombres únicos", index=False)

        _dar_formato(writer, "Posibles duplicados", resaltar_riesgo=True)
        _dar_formato(writer, "Problemas de formato")
        _dar_formato(writer, "Nombres únicos")

    print(f"Reporte generado: {ruta_salida}")
    print(f"  Grupos de posibles duplicados: {len(grupos_exactos) + len(filas_fuzzy)}")
    print(f"  Problemas de formato: {len(filas_problemas)}")
    return ruta_salida


def _dar_formato(writer, nombre_hoja, resaltar_riesgo=False):
    ws = writer.sheets[nombre_hoja]
    negrita = Font(bold=True)
    relleno_riesgo = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")

    for celda in ws[1]:
        celda.font = negrita

    for col in ws.columns:
        largo = max((len(str(c.value)) for c in col if c.value is not None), default=10)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(largo + 2, 60)

    if resaltar_riesgo:
        encabezados = [c.value for c in ws[1]]
        if "confianza" in encabezados:
            col_confianza = encabezados.index("confianza") + 1
            for fila in ws.iter_rows(min_row=2):
                valor = fila[col_confianza - 1].value
                if isinstance(valor, str) and "RIESGO" in valor:
                    for celda in fila:
                        celda.fill = relleno_riesgo

    ws.freeze_panes = "A2"


if __name__ == "__main__":
    construir_reporte()
