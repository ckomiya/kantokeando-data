# kantokeando-data

Proyecto para mostrar resultados de gateball en Perú (torneos, equipos, jugadores),
con datos recopilados manualmente del blog kantokeando.blogspot.com (2014–2026).

## Stack
- Preparación de datos: Python + pandas + openpyxl + rapidfuzz.
- Web: Astro 7, sitio estático generado en build (no SSR), en web/, sin framework
  de UI (CSS propio con variables, scripts pequeños en el navegador). Identidad
  visual "Gate-Datos" (nombre provisional, sin dominio aún); el diseño de
  referencia exportado de Claude Design está en docs/diseno/export/ (archivos
  .dc.html, solo referencia: se reescribe en Astro, no se usa tal cual).
- La web lee JSON en web/src/data/ (generado por scripts/exportar_datos.py y
  commiteado al repo). No consulta ninguna base de datos ni necesita secretos.
- Base de datos: PostgreSQL en Neon, OPCIONAL (no está en el camino de la web).
  Conexión vía SQLAlchemy + psycopg; la cadena se lee de DATABASE_URL en .env
  (python-dotenv). Nunca escribir credenciales en el código.

## Premisas
- Fuente única de verdad: el Excel en data/raw/. Nunca se modifica por código
  salvo pedido explícito del usuario para corregir un error puntual de tipeo
  (typos, puntuación, espacios repetidos); eso sigue siendo una excepción, no
  la norma, y cada corrección debe mostrarse al usuario antes o al confirmarla.
- La web será solo de lectura: sin CRUD, sin login, sin ingreso de datos.
- Pipeline repetible: Excel + alias → validación → JSON (web/src/data/) → astro build.
  Comandos: python scripts/exportar_datos.py (genera los JSON).
- Los JSON generados se commitean: el build de Astro no necesita Python. Son
  deterministas (sin fechas de generación), así que git diff muestra solo lo que
  cambió en los datos. Tras tocar el Excel o los alias, re-exportar.
- Neon es opcional: scripts/cargar_datos.py carga las mismas tablas a PostgreSQL
  para consultas SQL ad hoc o un posible uso futuro (API/SSR). Recrea el esquema
  en cada corrida (DROP + CREATE vía sql/schema.sql), así que correrlo varias
  veces no duplica datos.
- Ritmo de actualización: cada ~2 semanas, unos 4–8 registros nuevos. Se regenera
  TODO en cada build, a propósito: no hacer build incremental. La normalización es
  global (el nombre canónico es la variante más frecuente, y los sufijos de slug
  dependen del orden), así que un registro nuevo puede cambiar datos ya existentes,
  y un build completo siempre es coherente. Medido: ~1.200 páginas en ~20 s,
  dist/ ≈ 51 MB. Revisar esta decisión solo si el build pasa de unos minutos.
- Rutina de actualización: añadir filas al Excel → validar_nombres.py (decidir
  alias si hay nombres nuevos) → exportar_datos.py (revisar los AVISO) → commit y
  push (el hosting compila y publica). Olvidar re-exportar publica JSON viejos.
- El esquema de tablas se define en sql/schema.sql; consultas de ejemplo para
  validar el esquema están en sql/consultas_ejemplo.sql.

## Web (web/)
- Comandos (desde web/): npm run dev (desarrollo), npm run build (genera dist/),
  npm run preview. Los datos se regeneran con python scripts/exportar_datos.py.
- Rutas: / · /anio/<año>/ · /torneos/ · /torneos/<nombre-comun>/ · /torneo/<id>/
  · /jugadores/ · /jugador/<slug>/ · /equipos/ · /equipo/<slug>/ · /buscar/ ·
  /busqueda.json (índice del buscador, sale de web/src/data/busqueda.json).
- Estructura: src/lib/datos.ts (tipos y funciones sobre los JSON: categorías,
  campeones, palmarés, medallero), src/components/ (Bola, Logo, Header, TabBar,
  Buscador, TarjetaTorneo, PodioCategoria, MedalleroAnual, ListaAlfabetica,
  ThemeToggle), src/layouts/Base.astro, src/styles/global.css (tokens claro/oscuro).
- Decisiones de presentación acordadas con el usuario:
  - Se muestra el primer puesto de CADA categoría (no solo "Libre": casi ningún
    torneo la tiene). Si una categoría no tiene campeón registrado, la tarjeta
    muestra su mejor resultado disponible.
  - Varios primeros puestos en una categoría (premios individuales, empates) se
    listan como filas, no un arco por cada uno.
  - El nombre del jugador se muestra tal como figura en los datos: el orden
    Nombre Apellido / Apellido Nombre es mixto, así que no se separa en dos partes.
  - Resultados sin categoría se agrupan como "General". Los torneos sin
    nombre_comun no aparecen en "Torneos de siempre" (sí en Por año y el buscador).
  - Los años sin torneos (según los datos) se muestran vacíos, no se ocultan.
  - Un solo punto de verdad para puestos: componente Bola (número dentro, texto
    escrito y orden fijo; el color no es la única señal).
- Páginas generadas (con los datos actuales: 1.197): 714 jugadores, 225 equipos,
  206 torneos, 33 por nombre común, 13 por año, 5 índices (/, /torneos/,
  /jugadores/, /equipos/, /buscar/) y 404. Cada registro nuevo puede sumar páginas.
- Solo el índice de búsqueda (busqueda.json, ~90 KB) viaja al navegador; los JSON
  grandes (jugadores.json ≈ 2 MB) los usa únicamente el build.
- Pendiente: visor de fotos de la premiación (hoy solo hay enlace al artículo;
  no existen URLs de las fotos), dominio/`site`/sitemap y despliegue.

## Normalización de jugadores
- El programa PROPONE qué nombres son la misma persona; el usuario DECIDE.
- Separadores válidos en la celda "jugadores": coma, punto y coma, " y ", " e ".
- scripts/validar_nombres.py genera reports/validacion_nombres_<fecha>.xlsx con:
  posibles duplicados (automáticos y para revisión), problemas de formato
  (celdas vacías, espacios repetidos, separador suelto, nombre repetido en la
  misma celda, nombre de una sola palabra) y el listado de nombres únicos.
- Unir automáticamente solo diferencias de orden, tildes y mayúsculas.
- Tipeos y abreviaciones (Ychikawa/Ichikawa, Yoshi/Yoshiko, Lucho=Luis):
  proponer para revisión, nunca unir sin confirmación.
- No agrupar familiares que solo comparten apellido (Hideko/Sachiko Tamashiro).
- Alertar diferencias de riesgo: Luis/Luisa, Juan/Juana, Julio/Julia, etc.
- Decisiones confirmadas por el usuario:
  - data/alias/jugadores.csv: texto_original → jugador_canonico (misma persona).
    Ej.: Shichan Guima → Juana Guima (el canónico es la variante más frecuente).
  - data/alias/no_unir.csv: nombre_1, nombre_2 confirmados como personas distintas.
  - Ambos archivos los lee scripts/validar_nombres.py (para no re-proponer lo ya
    decidido) y scripts/transformar.py (para resolver el nombre canónico). Si un
    nombre queda agrupado automáticamente con otro que a su vez tiene alias, se
    debe seguir la cadena hasta el destino final (bug ya corregido una vez: ver
    resolver_final en transformar.py).

## Normalización de equipos
- scripts/transformar.py une automáticamente solo diferencias de mayúsculas,
  tildes y espacios (ej. "La Capitana A" / "LA CAPITANA A" / " La Capitana A") y
  se queda con la variante más frecuente; cada unión se imprime como AVISO.
- "Lunes" y "Lunes 1", o "AELU 1" y "AELU 2", son equipos distintos: nunca se unen.

## Torneos
- Un torneo = nombre_torneo + fecha_torneo.
- Id de torneo legible y autogenerado: fecha + nombre (ej. 2019-06-01-copa-konomi),
  generado por scripts/transformar.py (la columna id_torneo del Excel no se usa).

## Esquema de datos (sql/schema.sql)
- torneos, equipos, jugadores, resultados (una fila = un equipo/categoría de un
  torneo), resultado_jugadores (N:M, guarda también texto_original para
  trazabilidad). id_equipo es NULL en resultados sin equipo (premios individuales).

## Scripts (scripts/)
- validar_nombres.py: reporte de calidad de nombres de jugadores (revisión humana).
- transformar.py: Excel + alias → tablas normalizadas. Parte compartida.
- exportar_datos.py: tablas → JSON para la web (torneos, jugadores, equipos,
  busqueda, resumen). Valida integridad antes de escribir.
- cargar_datos.py: tablas → Neon (opcional).

## Calidad de datos (estado al 2026-10-05)
- Corregidos por el usuario en el Excel: jugador "a" (era "Juana Gui,a" → Juana
  Guima, fila 772), equipo "Segundo Puesto", resultados sin puesto, repetidos en
  celda, punto en vez de coma (fila 741), URLs distintas en un mismo torneo.
- Pendiente de decidir: equipo "Kisey / Christian" (fila 1017, ¿nombre válido?) y
  nombres de una palabra sin apellido: Emilio (fila 45), Jorge (96), Francisco
  (713 y 743). Se dejan así mientras no se conozca el apellido.
- Informativo (no son errores): 37 resultados con equipo pero sin jugadores,
  38 torneos sin nombre_comun, 21 sin lugar.
- Para modificar el Excel por código: cerrarlo antes (Excel abierto bloquea el
  guardado en Windows), hacer copia de seguridad, mostrar el cambio al usuario y
  comparar celda por celda después. Los typos puntuales los corrige el usuario o,
  si lo pide, se hacen con esas garantías.

## Convenciones
- Código y comentarios en español.
- Scripts en scripts/, reportes generados en reports/, SQL en sql/, web en web/,
  material de diseño en docs/diseno/.