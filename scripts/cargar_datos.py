"""
Carga las tablas normalizadas a Neon (PostgreSQL). Paso OPCIONAL: la web se
genera desde JSON (scripts/exportar_datos.py) y no necesita la base.

Pipeline (ver CLAUDE.md): Excel + alias -> validación -> [carga a Neon].
Recrea el esquema (sql/schema.sql) en cada corrida, así que se puede correr
varias veces sin duplicar datos.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from transformar import leer_tablas

RAIZ = Path(__file__).resolve().parent.parent
SCHEMA_SQL = RAIZ / "sql" / "schema.sql"


def obtener_engine():
    load_dotenv()
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL no está definida en .env")
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(db_url)


def recrear_esquema(engine):
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    with engine.begin() as conn:
        for sentencia in sql.split(";"):
            sentencia = sentencia.strip()
            if sentencia:
                conn.execute(text(sentencia))


def cargar():
    df_torneos, df_equipos, df_jugadores, df_resultados, df_resultado_jugadores = leer_tablas()

    engine = obtener_engine()

    print("Recreando esquema en Neon ...")
    recrear_esquema(engine)

    print("Insertando datos ...")
    df_torneos.to_sql("torneos", engine, if_exists="append", index=False)
    df_equipos.to_sql("equipos", engine, if_exists="append", index=False)
    df_jugadores.to_sql("jugadores", engine, if_exists="append", index=False)
    df_resultados.to_sql("resultados", engine, if_exists="append", index=False)
    df_resultado_jugadores.to_sql("resultado_jugadores", engine, if_exists="append", index=False)

    print("Carga completada.")


if __name__ == "__main__":
    cargar()
