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

## Publicación (Cloudflare Workers con archivos estáticos)
El sitio es estático y se publica en Cloudflare (plan gratuito) como Worker de "static assets":
no ejecuta código propio, Cloudflare sirve directamente los archivos de `web/dist`. Las
peticiones a archivos estáticos son gratis e ilimitadas en el plan gratuito. Cada `git push`
a `main` compila y publica solo (Workers Builds, conectado a GitHub).

Estado actual:
- Proyecto/Worker: `gate-datos`. Dirección: https://gate-datos.christian-komiya.workers.dev/
- Dominio propio: `gatedatos.org.pe` (comprado en un registrador peruano). Ver "Dominio propio".
- El repositorio es público y no contiene secretos.

Configuración en el panel de Cloudflare (Compute → Workers & Pages):
- Root directory: `web`
- Build command: `npm run build`
- Deploy command: `npx wrangler deploy` (usa `web/wrangler.jsonc`)
- Preview command: `npx wrangler preview`
- Variable de entorno `NODE_VERSION` = `22` (Astro 7 exige Node 22.12 o superior; `web/.node-version` también lo indica).
- Importante: el `name` de `web/wrangler.jsonc` (`gate-datos`) debe coincidir con el nombre del proyecto en el panel.

Archivos del repo que intervienen:
- `web/wrangler.jsonc`: publica `web/dist` y muestra `404.html` en rutas inexistentes.
- `web/public/_headers`: caché larga para `/_astro/` y cabeceras de seguridad básicas.
- `web/.node-version`: Node 22.

Para actualizar el sitio tras editar el Excel: `python scripts/actualizar.py --publicar`.

### Dominio propio (gatedatos.org.pe)
Un dominio propio solo se puede asociar a un Worker si está como zona ACTIVA en Cloudflare.
1. Hecho: en Cloudflare, Domains → Overview → Add a domain → `gatedatos.org.pe`, plan Free
   (no se agregaron registros DNS: el registro lo crea Cloudflare al asociar el dominio; no crear
   a mano registros A, AAAA ni CNAME en la raíz porque impedirían el Custom Domain).
2. Hecho: en el registrador se pusieron los nameservers de Cloudflare
   `nolan.ns.cloudflare.com` y `teagan.ns.cloudflare.com` (el registrador avisó de hasta 60
   minutos y hasta 24 horas de propagación). Se desactiva DNSSEC si estuviera activo.
3. Pendiente: esperar a que el dominio diga Active (Domains → Overview; también llega un correo).
   Si tras unas 6 horas sigue en Pending: revisar que los nameservers estén bien escritos y,
   si hiciera falta, agregar un registro TXT de relleno (DNS → Records: tipo TXT, nombre @,
   contenido gate-datos).
4. Pendiente: asociar el dominio al proyecto: Workers & Pages → `gate-datos` → Settings →
   Domains & Routes → Add → Custom Domain → `gatedatos.org.pe`. Cloudflare crea el DNS y el
   certificado HTTPS solo. Un Custom Domain responde solo a la dirección exacta: para que
   `www.gatedatos.org.pe` también funcione hay que agregarlo aparte o crear una redirección.
5. Pendiente: fijar `site: 'https://gatedatos.org.pe'` en `web/astro.config.mjs` y subirlo.
6. Opcional: desactivar la dirección `workers.dev` cuando el dominio propio funcione, y
   cambiar el subdominio de cuenta (Workers & Pages → Your subdomain → Change) si no gusta
   `christian-komiya` (afecta a todos los proyectos de la cuenta).

### Analítica (pendiente de decidir/activar)
Se pensó usar Cloudflare Web Analytics. El script y su token quedan visibles en el HTML
publicado y no se pueden ocultar (el repo público o privado no cambia eso). Cloudflare valida
el nombre del sitio de origen de los datos, así que no sirve copiar el snippet en otro dominio.
No guardar contraseñas ni URLs del panel en el repo. Si el hosting es Workers, el snippet se
agrega con la variable de entorno `PUBLIC_ANALYTICS_ID` o desde el panel de Cloudflare.
