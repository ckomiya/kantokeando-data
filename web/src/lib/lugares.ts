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

// Datos de lugares conocidos (clave = slugLugar). Para agregar uno: una fila más. Un lugar que no esté aquí
// no tiene nombre completo ni dirección: el calendario recibe el texto del Excel tal cual.
const LUGARES: Record<string, { nombre: string; direccion: string }> = {
  aelu: { nombre: 'Asociación Estadio La Unión (AELU)', direccion: 'Jr. Paracas 565, Pueblo Libre, Lima' },
  aop: { nombre: 'Asociación Okinawense del Perú (AOP)', direccion: 'Av. Asturias Mz 6 Lt 1, Ate Vitarte, Lima' },
};

/**
 * Lugar para Google Calendar: nombre completo y dirección si se conocen (así "AOP" no se confunde con otras
 * siglas); si no, el texto del Excel; null si el evento no tiene lugar.
 */
export function ubicacionLugar(lugar: string | null): string | null {
  if (!lugar) return null;
  const conocido = LUGARES[slugLugar(lugar)];
  return conocido ? `${conocido.nombre}, ${conocido.direccion}` : lugar;
}

/** Ruta pública del logo del lugar, o null si no hay archivo. */
export function logoLugar(lugar: string | null): string | null {
  if (!lugar) return null;
  const slug = slugLugar(lugar);
  if (!slug) return null;
  const ext = EXTENSIONES.find((x) => existsSync(`${CARPETA}${slug}.${x}`));
  return ext ? `/lugares/${slug}.${ext}` : null;
}
