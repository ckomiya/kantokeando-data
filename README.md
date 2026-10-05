# kantokeando-data

Datos históricos de torneos de gateball en Perú (2014–2026).
Fuente: blog kantokeando.blogspot.com.

## Preparar el entorno
```
python -m venv .venv
pip install -r requirements.txt          # pipeline de datos (Python)
cp .env.example .env                     # solo si vas a cargar a Neon (opcional): completar DATABASE_URL
cd web && npm install                    # web (Node 22+)
```

## Pipeline de datos
Fuente única de verdad: `data/raw/copas_y_torneos.xlsx` (nunca se modifica por código,
salvo corrección puntual de typos pedida explícitamente). Las decisiones de qué
nombres de jugadores son la misma persona se guardan en `data/alias/` (ver CLAUDE.md).

1. Validar nombres de jugadores (genera un reporte en reports/ con posibles
   duplicados y problemas de formato para revisar manualmente):
   ```
   python scripts/validar_nombres.py
   ```
2. Revisar el reporte, y registrar las decisiones en:
   - `data/alias/jugadores.csv` (texto_original → jugador_canonico, misma persona)
   - `data/alias/no_unir.csv` (nombre_1, nombre_2, confirmados como personas distintas)
3. Exportar los datos a JSON para la web (escribe en `web/src/data/`; los archivos
   se commitean, así el build de Astro no necesita Python ni base de datos):
   ```
   python scripts/exportar_datos.py
   ```
4. (Opcional) Cargar a Neon, por ejemplo para consultas SQL; recrea el esquema en
   cada corrida, se puede correr varias veces:
   ```
   python scripts/cargar_datos.py
   ```

El esquema de tablas está en `sql/schema.sql` y hay consultas de ejemplo (por año,
por nombre común, estadísticas de jugador y de equipo) en `sql/consultas_ejemplo.sql`.

## Web
Sitio estático hecho con Astro en `web/`, que lee los JSON de `web/src/data/`
(no necesita base de datos ni credenciales). Identidad "Gate-Datos" (nombre provisional).

```
cd web
npm run dev        # servidor de desarrollo en http://localhost:4321
npm run build      # genera web/dist/ (~1.200 páginas)
npm run preview    # sirve web/dist/ para revisarlo
```

**Atajo: un solo comando** (cierra el Excel antes). Valida nombres, exporta los JSON,
muestra qué cambió y compila la web:

```
python scripts/actualizar.py              # actualizar y compilar
python scripts/actualizar.py --publicar   # además hace commit y push (publica)
python scripts/actualizar.py --sin-build  # solo validar y exportar
```

O paso a paso:

1. `python scripts/validar_nombres.py` y revisar el reporte (si hay nombres nuevos).
2. `python scripts/exportar_datos.py` (regenera `web/src/data/*.json`; revisa los AVISO).
3. `cd web && npm run build`.

Con los datos actuales el build genera **1.197 páginas** en ~20 s (714 jugadores,
225 equipos, 206 torneos, 33 por nombre común, 13 por año, 5 índices y 404) y
`web/dist/` pesa ~51 MB. Siempre se regenera todo: es rápido y evita que queden
páginas desactualizadas, porque la normalización de nombres es global.

Ritmo previsto: una actualización cada ~2 semanas con unos 4–8 registros nuevos.
Tras el push, el hosting (Cloudflare Pages, Netlify, Vercel o GitHub Pages) compila
y publica solo. Importante: re-exportar los JSON antes del commit.

Nota para Windows: si el Excel está abierto en Excel, ningún script puede guardarlo;
ciérralo primero.

El diseño de referencia (exportado de Claude Design) está en `docs/diseno/export/`.
