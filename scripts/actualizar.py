"""
Actualiza la web con un solo comando, a partir del Excel.

    python scripts/actualizar.py              # valida nombres, exporta JSON y compila la web
    python scripts/actualizar.py --publicar   # además hace commit y push (publica)
    python scripts/actualizar.py --sin-build  # solo valida y exporta (más rápido)

Pasos (ver CLAUDE.md): comprobar Excel -> validar nombres -> exportar JSON ->
resumen de cambios -> astro build -> (opcional) commit y push.
"""

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "web"
DATOS = WEB / "src" / "data"
EXCEL = RAIZ / "data" / "raw" / "copas_y_torneos.xlsx"

sys.path.insert(0, str(Path(__file__).resolve().parent))


def titulo(texto: str):
    print(f"\n=== {texto} ===")


def comprobar_excel():
    """En Windows, un Excel abierto bloquea el archivo; mejor avisar antes de empezar."""
    if not EXCEL.exists():
        raise SystemExit(f"No existe {EXCEL}")
    try:
        with open(EXCEL, "r+b"):
            pass
    except PermissionError:
        raise SystemExit("El Excel está abierto en otro programa. Guárdalo, ciérralo y vuelve a correr el comando.")


def leer_resumen() -> dict:
    ruta = DATOS / "resumen.json"
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}


def ejecutar(comando: list[str], carpeta: Path, descripcion: str):
    print(f"$ {' '.join(comando)}")
    # shell=True en Windows para encontrar npm.cmd
    r = subprocess.run(comando, cwd=carpeta, shell=(sys.platform == "win32"))
    if r.returncode != 0:
        raise SystemExit(f"Falló: {descripcion}")


def mostrar_cambios(antes: dict, despues: dict):
    titulo("Cambios en los datos")
    for clave, etiqueta in (("torneos", "Torneos"), ("resultados", "Resultados"), ("jugadores", "Jugadores"), ("equipos", "Equipos")):
        a, d = antes.get(clave), despues.get(clave)
        if a is None:
            print(f"  {etiqueta}: {d}")
        else:
            dif = d - a
            marca = "" if dif == 0 else f"  ({'+' if dif > 0 else ''}{dif})"
            print(f"  {etiqueta}: {a} -> {d}{marca}")
    r = subprocess.run(["git", "diff", "--stat", "--", "web/src/data", "data"], cwd=RAIZ, capture_output=True, text=True)
    if r.stdout.strip():
        print("\n  Archivos que cambiaron:\n" + "\n".join("  " + l for l in r.stdout.strip().splitlines()))
    else:
        print("\n  Sin cambios respecto al último commit.")


def publicar(resumen: dict):
    titulo("Publicar (commit y push)")
    estado = subprocess.run(["git", "status", "--porcelain"], cwd=RAIZ, capture_output=True, text=True).stdout.strip()
    if not estado:
        print("  No hay nada que publicar.")
        return
    mensaje = (
        f"Actualización de datos ({date.today().isoformat()})\n\n"
        f"{resumen.get('torneos')} torneos, {resumen.get('jugadores')} jugadores, "
        f"{resumen.get('equipos')} equipos, {resumen.get('resultados')} resultados."
    )
    ejecutar(["git", "add", "data", "web/src/data", "scripts", "CLAUDE.md", "README.md"], RAIZ, "git add")
    ejecutar(["git", "commit", "-m", mensaje], RAIZ, "git commit")
    ejecutar(["git", "push"], RAIZ, "git push")


def main():
    sys.stdout.reconfigure(line_buffering=True)  # mensajes en orden junto a los subprocesos
    ap = argparse.ArgumentParser(description="Actualiza la web a partir del Excel.")
    ap.add_argument("--publicar", action="store_true", help="hace commit y push al terminar")
    ap.add_argument("--sin-build", action="store_true", help="no compila la web (solo valida y exporta)")
    args = ap.parse_args()

    comprobar_excel()
    antes = leer_resumen()

    titulo("1/4 Validar nombres de jugadores")
    ejecutar([sys.executable, "scripts/validar_nombres.py"], RAIZ, "validar_nombres.py")
    print("  Revisa el reporte en reports/ si agregaste jugadores nuevos.")

    titulo("2/4 Exportar datos a JSON")
    ejecutar([sys.executable, "scripts/exportar_datos.py"], RAIZ, "exportar_datos.py")
    print("  Revisa los AVISO de arriba (nombres repetidos, URLs distintas, equipos unidos).")

    titulo("3/4 Resumen")
    despues = leer_resumen()
    mostrar_cambios(antes, despues)

    if args.sin_build:
        print("\nSaltado el build (--sin-build).")
    else:
        titulo("4/4 Compilar la web")
        if not (WEB / "node_modules").exists():
            ejecutar(["npm", "install"], WEB, "npm install")
        ejecutar(["npm", "run", "build"], WEB, "npm run build")

    if args.publicar:
        publicar(despues)
    else:
        print("\nListo. Para ver la web: cd web && npm run dev. Para publicar: python scripts/actualizar.py --publicar")


if __name__ == "__main__":
    main()
