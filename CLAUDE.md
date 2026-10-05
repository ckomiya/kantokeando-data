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
  Todo junto: python scripts/actualizar.py (valida, exporta, resume los cambios y
  compila); con --publicar además hace commit y push; --sin-build omite el build.
  Avisa si el Excel está abierto. Ver scripts/actualizar.py.
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
  - Equipos extranjeros (Extranjero = "S"): no existen como equipo en la web: sin
    ficha, sin buscador, sin listado y sin enlace (ni en palmarés). Sus resultados
    SÍ se muestran en los podios de los torneos, como texto con la etiqueta
    "Extranjero", y cuentan en los medalleros de sus jugadores (que conservan su
    ficha). Se aplica en scripts/exportar_datos.py (slug null + extranjero true).
  - Jugadores extranjeros (los que solo jugaron con equipos Extranjero = "S"; hoy
    125): no existen como jugador en la web: sin ficha, sin buscador, sin listado y
    sin enlace. Su nombre sigue apareciendo como texto en los podios de los torneos
    donde jugaron. Quien jugó con un equipo extranjero y también con uno no
    extranjero conserva su ficha. Se aplica en scripts/exportar_datos.py (slug null).
  - Torneos internacionales (esInternacional en web/src/lib/datos.ts): los de tipo
    "Campeonato Internacional" más los que tienen equipos extranjeros (hoy 8). En
    la ficha del jugador se resaltan: etiqueta "Internacional" y resumen en la
    cabecera, panel "Torneos internacionales", filas marcadas en el historial y
    filtro "Internacionales".
  - Torneos de tipo "Confraternidad/Integración": sus equipos solo se ocultan del
    listado /equipos/ (equipoListable en web/src/lib/datos.ts: se muestra un equipo
    si tiene al menos una participación en otro tipo de torneo, incluido uno sin
    tipo). Todo lo demás los incluye: fichas, buscador, páginas de torneo y los
    puntajes/medalleros de jugadores y equipos.
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
- Tipeos y abreviaciones (Ychikawa/Ichikawa, Yoshi/Yoshiko): proponer para
  revisión, nunca unir sin confirmación.
- Apodos confirmados como regla (data/alias/apodos.csv: apodo, nombre_formal):
  hoy Alejo = Alejandro, Lucho = Luis y Lucha = Luisa. Si en los datos existen "Alejo Kamiyama" y
  "Alejandro Kamiyama" (mismo apellido, en cualquier orden) se unen solos, y el
  nombre formal gana como canónico. Un apodo sin su forma formal no se toca. Se
  agrega un apodo al CSV solo cuando el usuario lo confirma como regla general
  (ej. "Ale" NO está: puede ser Alejandra o Alejandro; "Ali Miyagusuku → Alicia"
  es un alias puntual en jugadores.csv).
- No agrupar familiares que solo comparten apellido (Hideko/Sachiko Tamashiro).
- Alertar diferencias de riesgo: Luis/Luisa, Juan/Juana, Julio/Julia, etc.
- Decisiones confirmadas por el usuario:
  - data/alias/jugadores.csv: texto_original → jugador_canonico (misma persona).
    Ej.: Shichan Guima → Juana Guima (el canónico es la variante más frecuente).
    Criterio al elegir el canónico: nombre formal/completo sobre apodo; si no hay
    diferencia, la variante más frecuente.
  - data/alias/no_unir.csv: nombre_1, nombre_2 confirmados como personas distintas.
  - data/alias/apodos.csv: reglas generales apodo → nombre formal (ver arriba).
  - data/alias/variantes_apellido.csv: grafías equivalentes de un apellido (hoy
    Tzukazan = Tzukasan = Tsukazan). Misma mecánica que los apodos: si existen
    "Mitsu Tsukazan" y "Mitsu Tzukazan" se unen solos; una variante sin su forma
    correcta no se toca (ej. un "Luis Tzukazan" sin "Luis Tsukazan" queda igual).
  - Los tres archivos de data/alias/ los lee scripts/validar_nombres.py (para no re-proponer lo ya
    decidido) y scripts/transformar.py (para resolver el nombre canónico). Si un
    nombre queda agrupado automáticamente con otro que a su vez tiene alias, se
    debe seguir la cadena hasta el destino final (bug ya corregido una vez: ver
    resolver_final en transformar.py).

## Normalización de equipos
- scripts/transformar.py une automáticamente solo diferencias de mayúsculas,
  tildes y espacios (ej. "La Capitana A" / "LA CAPITANA A" / " La Capitana A") y
  se queda con la variante más frecuente; cada unión se imprime como AVISO.
- "Lunes" y "Lunes 1", o "AELU 1" y "AELU 2", son equipos distintos: nunca se unen.
- La identidad de un equipo es NOMBRE + EXTRANJERO (columna Extranjero = "S" del
  Excel): "Sakura" extranjero y "Sakura" peruano son equipos distintos. Por eso la
  marca Extranjero debe ir en TODAS las filas de un equipo extranjero; una fila
  sin marcar crea un equipo local con el mismo nombre, que sí tendría ficha.

## Torneos
- Un torneo = nombre_torneo + fecha_torneo.
- Id de torneo legible y autogenerado: fecha + nombre (ej. 2019-06-01-copa-konomi),
  generado por scripts/transformar.py (la columna id_torneo del Excel no se usa).

## Esquema de datos (sql/schema.sql)
- torneos, equipos (único por nombre + extranjero), jugadores, resultados (una fila = un equipo/categoría de un
  torneo), resultado_jugadores (N:M, guarda también texto_original para
  trazabilidad). id_equipo es NULL en resultados sin equipo (premios individuales).

## Scripts (scripts/)
- validar_nombres.py: reporte de calidad de nombres de jugadores (revisión humana).
- transformar.py: Excel + alias → tablas normalizadas. Parte compartida.
- exportar_datos.py: tablas → JSON para la web (torneos, jugadores, equipos,
  busqueda, resumen). Valida integridad antes de escribir.
- actualizar.py: orquesta todo el flujo con un solo comando (ver Premisas).
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