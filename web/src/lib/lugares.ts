// Logos de lugares/asociaciones del cronograma. Solo se usa en el build (lee web/public/lugares/).
// Para agregar un logo: guardar web/public/lugares/<slug>.svg|png|webp|jpg, con el slug del lugar
// ("AELU" -> aelu, "AOP" -> aop). Un lugar sin archivo se muestra sin logo.
import { existsSync } from 'node:fs';
import { join } from 'node:path';

// El build corre siempre desde web/ (npm run build/dev); import.meta.url no sirve: apunta a dist/chunks.
const CARPETA = join(process.cwd(), 'public', 'lugares') + '/';
const EXTENSIONES = ['svg', 'png', 'webp', 'jpg'];

/** "AELU (Estadio)" -> "aelu": se toma lo anterior al paréntesis. */
export function slugLugar(lugar: string): string {
  return lugar.split('(')[0].normalize('NFD').replace(/[̀-ͯ]/g, '')
    .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}

/** Ruta pública del logo del lugar, o null si no hay archivo. */
export function logoLugar(lugar: string | null): string | null {
  if (!lugar) return null;
  const slug = slugLugar(lugar);
  if (!slug) return null;
  const ext = EXTENSIONES.find((x) => existsSync(`${CARPETA}${slug}.${x}`));
  return ext ? `/lugares/${slug}.${ext}` : null;
}
