# kantokeando-data

Proyecto para mostrar resultados de gateball en Perú (torneos, equipos, jugadores),
con datos recopilados manualmente del blog kantokeando.blogspot.com (2014–2026).

## Stack
- Preparación de datos: Python + pandas + openpyxl + rapidfuzz.
- Base de datos: PostgreSQL en Neon. Conexión vía SQLAlchemy + psycopg.
- La cadena de conexión se lee de la variable DATABASE_URL en .env (python-dotenv).
  Nunca escribir credenciales en el código.
- Tecnología web: por definir. No asumir ningún framework web.

## Premisas
- Fuente única de verdad: el Excel en data/raw/. Nunca se modifica por código.
- La web será solo de lectura: sin CRUD, sin login, sin ingreso de datos.
- Pipeline repetible: Excel + alias → validación → carga a Neon.
- La carga debe poder correrse varias veces sin duplicar datos (recrear o upsert).
- El esquema de tablas se define en sql/schema.sql.

## Normalización de jugadores
- El programa PROPONE qué nombres son la misma persona; el usuario DECIDE.
- Las decisiones se guardan en data/alias/ (texto_original → jugador canónico).
- Separadores válidos en la celda "jugadores": coma, punto y coma, " y ", " e ".
- Unir automáticamente solo diferencias de orden, tildes y mayúsculas.
- Tipeos y abreviaciones (Ychikawa/Ichikawa, Yoshi/Yoshiko): proponer para revisión.
- No agrupar familiares que solo comparten apellido (Hideko/Sachiko Tamashiro).
- Alertar diferencias de riesgo: Luis/Luisa, Juan/Juana.

## Torneos
- Un torneo = nombre_torneo + fecha_torneo.
- Id de torneo legible y autogenerado: fecha + nombre (ej. 2019-06-01-copa-konomi).

## Convenciones
- Código y comentarios en español.
- Scripts en scripts/, reportes generados en reports/, SQL en sql/.