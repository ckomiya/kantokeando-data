-- Esquema de base de datos para kantokeando-data (PostgreSQL / Neon).
-- Fuente de verdad: data/raw/copas_y_torneos.xlsx (ver CLAUDE.md).
-- Pensado para recrearse en cada carga (DROP + CREATE), no para migraciones incrementales.

DROP TABLE IF EXISTS resultado_jugadores;
DROP TABLE IF EXISTS resultados;
DROP TABLE IF EXISTS jugadores;
DROP TABLE IF EXISTS equipos;
DROP TABLE IF EXISTS torneos;

CREATE TABLE torneos (
    id_torneo       TEXT PRIMARY KEY,       -- fecha + nombre, ej. 2019-06-01-copa-konomi
    nombre_torneo   TEXT NOT NULL,
    nombre_comun    TEXT,
    fecha_torneo    DATE NOT NULL,
    anio            INTEGER NOT NULL,       -- derivado de fecha_torneo, para listar/agrupar por año
    tipo            TEXT,
    pais            TEXT,
    lugar           TEXT,
    url             TEXT
);

CREATE TABLE equipos (
    id_equipo       SERIAL PRIMARY KEY,
    nombre_equipo   TEXT NOT NULL,          -- ej. "AELU 3", el mismo equipo puede repetirse entre torneos/años
    extranjero      BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (nombre_equipo, extranjero)      -- identidad = nombre + extranjero ("Sakura" extranjero != "Sakura" peruano)
);

CREATE TABLE jugadores (
    id_jugador      SERIAL PRIMARY KEY,
    nombre_canonico TEXT NOT NULL UNIQUE    -- nombre normalizado (ver data/alias/jugadores.csv)
);

-- Una fila = un equipo en una categoría de un torneo (así viene en el Excel: tipo/puesto/equipo por fila).
CREATE TABLE resultados (
    id_resultado    SERIAL PRIMARY KEY,
    id_torneo       TEXT NOT NULL REFERENCES torneos (id_torneo),
    id_equipo       INTEGER REFERENCES equipos (id_equipo),  -- NULL en premios individuales sin equipo
    categoria       TEXT,
    puesto          INTEGER,
    extranjero      BOOLEAN
);

-- Tabla puente N:M: qué jugador participó en qué resultado (equipo + categoría + torneo).
CREATE TABLE resultado_jugadores (
    id_resultado    INTEGER NOT NULL REFERENCES resultados (id_resultado),
    id_jugador      INTEGER NOT NULL REFERENCES jugadores (id_jugador),
    texto_original  TEXT NOT NULL,          -- nombre tal como aparecía en la celda "jugadores", para trazabilidad
    PRIMARY KEY (id_resultado, id_jugador)
);

CREATE INDEX idx_torneos_anio ON torneos (anio);
CREATE INDEX idx_torneos_nombre_comun ON torneos (nombre_comun);
CREATE INDEX idx_resultados_id_torneo ON resultados (id_torneo);
CREATE INDEX idx_resultados_id_equipo ON resultados (id_equipo);
CREATE INDEX idx_resultado_jugadores_id_jugador ON resultado_jugadores (id_jugador);
