// Acceso a los JSON generados por scripts/exportar_datos.py.
// Todo se calcula en build; no hay consultas en tiempo de ejecución.
import torneosJson from '../data/torneos.json';
import jugadoresJson from '../data/jugadores.json';
import equiposJson from '../data/equipos.json';
import resumenJson from '../data/resumen.json';
import posicionesJson from '../data/posiciones.json';

export type Ref = { slug: string; nombre: string };
/** Jugador en un podio. Los extranjeros no tienen ficha: slug null. */
export type JugadorRef = { slug: string | null; nombre: string };
/** Referencia a un equipo. Los extranjeros no tienen ficha: slug null y extranjero true. */
export type EquipoRef = { slug: string | null; nombre: string; extranjero?: boolean };

export type Resultado = {
  categoria: string | null;
  puesto: number | null;
  equipo: EquipoRef | null;
  extranjero: boolean;
  jugadores: JugadorRef[];
};

export type Torneo = {
  id: string;
  nombre: string;
  nombre_comun: string | null;
  fecha: string;
  anio: number;
  tipo: string | null;
  pais: string | null;
  lugar: string | null;
  url: string | null;
  resultados: Resultado[];
};

export type Medallas = { '1': number; '2': number; '3': number };

type ParticipacionBase = {
  torneo: string;
  nombre_torneo: string;
  fecha: string;
  anio: number;
  categoria: string | null;
  puesto: number | null;
  url: string | null;
};
export type ParticipacionJugador = ParticipacionBase & { equipo: EquipoRef | null };
export type ParticipacionEquipo = ParticipacionBase & { jugadores: Ref[]; tipo: string | null };

export type Jugador = {
  slug: string;
  nombre: string;
  torneos: number;
  medallas: Medallas;
  participaciones: ParticipacionJugador[];
};
export type Equipo = {
  slug: string;
  nombre: string;
  torneos: number;
  medallas: Medallas;
  participaciones: ParticipacionEquipo[];
};

// --- tablas de posiciones (hoja "Posiciones" del Excel) ------------------------

/** Equipo de la tabla: slug solo si tiene ficha en la web. */
export type EquipoPosicion = { slug: string | null; nombre: string };
export type FilaPosicion = {
  pos: number;
  equipo: EquipoPosicion;
  pj: number | null; g: number | null; e: number | null; p: number | null;
  wo: number | null; gf: number | null; gc: number | null; dg: number | null; pts: number | null;
  prob_campeonar?: number | null;
  prob_descender?: number | null;
};
export type CategoriaPosiciones = { nombre: string; estado: string | null; filas: FilaPosicion[] };
export type PosicionesAnio = { anio: number; categorias: CategoriaPosiciones[] };

export const posiciones = posicionesJson as unknown as PosicionesAnio[];
export const posicionesDe = (anio: number) => posiciones.find((a) => a.anio === anio);
export const urlPosiciones = (anio: number) => `/posiciones/${anio}/`;
/** Orden de las categorías en las tablas (la misma que usa exportar_datos.py). */
export const ORDEN_CATEGORIAS = ['Primera', 'Segunda', 'Tercera', 'Master'];
export type PosicionAnual = { anio: number; categoria: string; pos: number; total: number; pts: number | null };
/**
 * Posición final de un equipo en cada año, solo de categorías CERRADAS (una categoría en curso
 * todavía no tiene posición final). `anios` son los años que tienen alguna tabla cerrada.
 */
export function historialPosiciones(slug: string): { filas: PosicionAnual[]; anios: number[] } {
  const filas: PosicionAnual[] = [];
  const anios = new Set<number>();
  for (const a of posiciones)
    for (const c of a.categorias) {
      if (c.estado !== 'Cerrado') continue;
      anios.add(a.anio);
      const f = c.filas.find((x) => x.equipo.slug === slug);
      if (f) filas.push({ anio: a.anio, categoria: c.nombre, pos: f.pos, total: c.filas.length, pts: f.pts });
    }
  return { filas, anios: [...anios].sort((x, y) => x - y) };
}
/** Categoría en la que juega un equipo en la tabla del año actual; null si no figura en ella. */
export function categoriaActualDe(slug: string): string | null {
  const tabla = posicionesDe(anioActual);
  return tabla?.categorias.find((c) => c.filas.some((f) => f.equipo.slug === slug))?.nombre ?? null;
}

export const torneos = torneosJson as unknown as Torneo[]; // ascendente por fecha
export const jugadores = jugadoresJson as unknown as Jugador[];
export const equipos = equiposJson as unknown as Equipo[];
export const resumen = resumenJson as {
  torneos: number;
  resultados: number;
  jugadores: number;
  equipos: number;
  anios: { anio: number; torneos: number }[];
};

/** Tipo de torneo (columna "tipo" del Excel) cuyos equipos no se listan en /equipos/. */
export const TIPO_CONFRATERNIDAD = 'Confraternidad/Integración';

/**
 * ¿Aparece el equipo en el listado de /equipos/? No se listan los equipos que solo
 * participaron en torneos de Confraternidad/Integración; basta una participación
 * en otro tipo de torneo (incluido uno sin tipo) para que se muestre. Solo afecta
 * al listado: la ficha, el buscador, los torneos y los puntajes de jugadores los
 * incluyen normalmente. (Los equipos extranjeros ni llegan aquí: se quitan en
 * scripts/exportar_datos.py.)
 */
export function equipoListable(e: Equipo): boolean {
  return e.participaciones.some((p) => p.tipo !== TIPO_CONFRATERNIDAD);
}
export const equiposListables = equipos.filter(equipoListable);

export const torneosPorId = new Map(torneos.map((t) => [t.id, t]));
// Banderas en public/banderas/<código>.svg (flag-icons, licencia MIT; ver LICENSE.txt allí).
// Se usan SVG y no emojis porque Windows no dibuja los emojis de banderas. Agregar el SVG y su
// nombre aquí cuando aparezca un país nuevo; sin entrada, simplemente no se muestra bandera.
const CODIGO_PAIS: Record<string, string> = {
  peru: 'pe', argentina: 'ar', paraguay: 'py', brasil: 'br', japon: 'jp', chile: 'cl', bolivia: 'bo',
  uruguay: 'uy', colombia: 'co', ecuador: 'ec', venezuela: 've', mexico: 'mx', 'estados unidos': 'us',
};
/** Código de bandera del país de un torneo (país vacío = Perú); null si no hay bandera para ese país. */
export function banderaTorneo(id: string): string | null {
  const t = torneosPorId.get(id);
  if (!t) return null;
  const pais = t.pais?.trim() || 'Perú';
  return CODIGO_PAIS[quitarTildes(pais).toLowerCase()] ?? null;
}
/** "Lugar, País" de un torneo. Un país vacío en el Excel significa que fue en el Perú. */
export function ubicacionTorneo(id: string): string {
  const t = torneosPorId.get(id);
  if (!t) return '';
  return [t.lugar?.trim(), t.pais?.trim() || 'Perú'].filter(Boolean).join(', ');
}

/** Tipo de torneo (columna "tipo" del Excel) que marca los campeonatos internacionales. */
export const TIPO_INTERNACIONAL = 'Campeonato Internacional';

/**
 * ¿Es un torneo internacional? Los de tipo "Campeonato Internacional" y también los
 * que tienen equipos extranjeros (aunque su tipo esté vacío o sea otro).
 */
export function esInternacional(t: Torneo): boolean {
  return t.tipo === TIPO_INTERNACIONAL || t.resultados.some((r) => r.equipo?.extranjero);
}
export const torneosInternacionales = new Set(torneos.filter(esInternacional).map((t) => t.id));
export const ultimoTorneo = torneos[torneos.length - 1];
export const anioActual = resumen.anios[resumen.anios.length - 1].anio;
/** Año que muestra /posiciones/ por defecto: el actual si tiene tabla; si no, el último que la tenga. */
export const anioPosicionesDefecto = posicionesDe(anioActual) ? anioActual : Math.max(...posiciones.map((a) => a.anio));
/** Categorías del año actual que siguen "En curso" (vacío si no hay ninguna): decide si la portada muestra la franja. */
export const categoriasEnCurso = (posicionesDe(anioActual)?.categorias ?? [])
  .filter((c) => c.estado === 'En curso')
  .map((c) => c.nombre);
/** Último año que tiene torneos: destino del enlace "Por año". */
export const ultimoAnioConTorneos = [...resumen.anios].reverse().find((a) => a.torneos > 0)!.anio;

// --- utilidades de texto -----------------------------------------------------

export function quitarTildes(s: string): string {
  return s.normalize('NFD').replace(/[̀-ͯ]/g, '');
}

/** Igual que generar_slug de scripts/transformar.py. */
export function slugify(s: string): string {
  return quitarTildes(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'x';
}

const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const MESES_CORTOS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
const DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];

function partes(iso: string) {
  const [y, m, d] = iso.split('-').map(Number);
  return { y, m: m - 1, d, dia: new Date(Date.UTC(y, m - 1, d)).getUTCDay() };
}
/** "Domingo 12 de mayo de 2019" */
export function fechaLarga(iso: string): string {
  const { y, m, d, dia } = partes(iso);
  const s = `${DIAS[dia]} ${d} de ${MESES[m]} de ${y}`;
  return s[0].toUpperCase() + s.slice(1);
}
/** "12 may 2019" */
export function fechaCorta(iso: string): string {
  const { y, m, d } = partes(iso);
  return `${d} ${MESES_CORTOS[m]} ${y}`;
}
export function diaMes(iso: string): { dia: string; mes: string } {
  const { m, d } = partes(iso);
  return { dia: String(d), mes: MESES_CORTOS[m] };
}

/**
 * Etiqueta de cada edición en la lista "Otras ediciones": el año; si el año se repite, "mes año"
 * ("jun 2026"); y si también se repite el mes, la fecha corta con día ("6 jul 2014").
 */
export function etiquetasEdiciones(ts: Torneo[]): Map<string, string> {
  const cuenta = (clave: (t: Torneo) => string) => {
    const c = new Map<string, number>();
    for (const t of ts) c.set(clave(t), (c.get(clave(t)) ?? 0) + 1);
    return c;
  };
  const porAnio = cuenta((t) => String(t.anio));
  const porMes = cuenta((t) => t.fecha.slice(0, 7));
  return new Map(ts.map((t) => {
    if (porAnio.get(String(t.anio)) === 1) return [t.id, String(t.anio)];
    if (porMes.get(t.fecha.slice(0, 7)) === 1) return [t.id, `${MESES_CORTOS[partes(t.fecha).m]} ${t.anio}`];
    return [t.id, fechaCorta(t.fecha)];
  }));
}

export function plural(n: number, uno: string, varios: string): string {
  return `${n.toLocaleString('es-PE')} ${n === 1 ? uno : varios}`;
}

// --- puestos -----------------------------------------------------------------

/**
 * Puesto 0 en el Excel = reconocimiento (premio individual, mención): no está en el podio.
 * No entra en podios, medalleros ni tarjetas; se muestra aparte en el torneo y en el jugador.
 */
export const PUESTO_RECONOCIMIENTO = 0;
export const esReconocimiento = (puesto: number | null): boolean => puesto === PUESTO_RECONOCIMIENTO;

/** Texto de un puesto: "Campeón", "2.º puesto", "3.er puesto", "4.º puesto". */
export function etiquetaPuesto(p: number | null): string {
  if (p === null) return 'Participó';
  if (p === 0) return 'Reconocimiento';
  if (p === 1) return 'Campeón';
  if (p === 3) return '3.er puesto';
  return `${p}.º puesto`;
}

// --- categorías de un torneo -------------------------------------------------

export const SIN_CATEGORIA = 'General';

export type Categoria = {
  nombre: string;
  id: string;
  resultados: Resultado[];
  campeones: Resultado[];
  resto: Resultado[];
};

/** Resultados de un torneo agrupados por categoría, en el orden del Excel. */
export function categoriasDe(t: Torneo): Categoria[] {
  const grupos = new Map<string, Resultado[]>();
  for (const r of t.resultados) {
    if (esReconocimiento(r.puesto)) continue; // van aparte (reconocimientosDe)
    const nombre = r.categoria ?? SIN_CATEGORIA;
    if (!grupos.has(nombre)) grupos.set(nombre, []);
    grupos.get(nombre)!.push(r);
  }
  const usados = new Set<string>();
  return [...grupos].map(([nombre, rs]) => {
    let id = 'cat-' + slugify(nombre);
    while (usados.has(id)) id += '-2';
    usados.add(id);
    const ordenados = [...rs].sort((a, b) => (a.puesto ?? 99) - (b.puesto ?? 99));
    return {
      nombre,
      id,
      resultados: ordenados,
      campeones: ordenados.filter((r) => r.puesto === 1),
      resto: ordenados.filter((r) => r.puesto !== 1),
    };
  });
}

export type GrupoReconocimiento = { nombre: string; resultados: Resultado[] };

/** Reconocimientos (puesto 0) de un torneo, agrupados por su nombre ("Mejor Kantoku"), en el orden del Excel. */
export function reconocimientosDe(t: Torneo): GrupoReconocimiento[] {
  const grupos = new Map<string, Resultado[]>();
  for (const r of t.resultados) {
    if (!esReconocimiento(r.puesto)) continue;
    const nombre = r.categoria ?? 'Reconocimiento';
    if (!grupos.has(nombre)) grupos.set(nombre, []);
    grupos.get(nombre)!.push(r);
  }
  return [...grupos].map(([nombre, resultados]) => ({ nombre, resultados }));
}

/** Nombre a mostrar de un resultado: el equipo o, en premios individuales, los jugadores. */
export function nombreResultado(r: Resultado): string {
  if (r.equipo) return r.equipo.nombre;
  const nombres = r.jugadores.map((j) => j.nombre);
  return nombres.length ? nombres.join(' · ') : 'Sin datos';
}

export type Campeon = { categoria: string; nombre: string; equipo: EquipoRef | null; jugadores: JugadorRef[] };

/** Primer puesto de cada categoría de un torneo. */
export function campeonesDe(t: Torneo): Campeon[] {
  return categoriasDe(t).flatMap((c) =>
    c.campeones.map((r) => ({ categoria: c.nombre, nombre: nombreResultado(r), equipo: r.equipo, jugadores: r.jugadores })),
  );
}

export type Destacado = Campeon & { puesto: number };

/**
 * Para las tarjetas: el primer puesto de cada categoría; si una categoría no tiene
 * campeón registrado, su mejor resultado disponible (así no queda vacía).
 */
export function destacadosDe(t: Torneo): Destacado[] {
  return categoriasDe(t).flatMap((c) => {
    const base = c.campeones.length
      ? c.campeones
      : c.resto.filter((r) => r.puesto !== null).slice(0, 1);
    return base.map((r) => ({
      categoria: c.nombre,
      nombre: nombreResultado(r),
      equipo: r.equipo,
      jugadores: r.jugadores,
      puesto: r.puesto as number,
    }));
  });
}

export function urlTorneo(t: Torneo | string): string {
  return `/torneo/${typeof t === 'string' ? t : t.id}/`;
}
export const urlAnio = (a: number) => `/anio/${a}/`;
export const urlJugador = (slug: string) => `/jugador/${slug}/`;
export const urlEquipo = (slug: string) => `/equipo/${slug}/`;
export const urlComun = (nombre: string) => `/torneos/${slugify(nombre)}/`;

// --- torneos por año ---------------------------------------------------------

export function torneosDelAnio(anio: number): Torneo[] {
  return torneos.filter((t) => t.anio === anio);
}

// --- nombre común ("Campeonato Metropolitano" y todas sus ediciones) ---------

export type Comun = {
  slug: string;
  nombre: string;
  ediciones: Torneo[]; // más reciente primero
  desde: number;
  hasta: number;
};

export const comunes: Comun[] = (() => {
  const mapa = new Map<string, Comun>();
  for (const t of torneos) {
    if (!t.nombre_comun) continue;
    const slug = slugify(t.nombre_comun);
    if (!mapa.has(slug)) mapa.set(slug, { slug, nombre: t.nombre_comun, ediciones: [], desde: t.anio, hasta: t.anio });
    const c = mapa.get(slug)!;
    c.ediciones.unshift(t);
    c.desde = Math.min(c.desde, t.anio);
    c.hasta = Math.max(c.hasta, t.anio);
  }
  return [...mapa.values()].sort((a, b) => b.ediciones.length - a.ediciones.length || a.nombre.localeCompare(b.nombre, 'es'));
})();

export const comunPorNombre = new Map(comunes.map((c) => [c.nombre, c]));

/** Equipos con más primeros puestos dentro de un conjunto de torneos. */
export type FilaPalmares = { equipo: Ref; titulos: number; categorias: { nombre: string; n: number }[] };

export function palmares(ediciones: Torneo[], max = 5): FilaPalmares[] {
  const cuenta = new Map<string, { equipo: Ref; titulos: number; cats: Map<string, number> }>();
  for (const t of ediciones) {
    for (const r of t.resultados) {
      if (r.puesto !== 1 || !r.equipo?.slug) continue; // los extranjeros no tienen ficha ni entran al palmarés
      const e = cuenta.get(r.equipo.slug) ?? { equipo: r.equipo as Ref, titulos: 0, cats: new Map<string, number>() };
      e.titulos++;
      const cat = r.categoria ?? SIN_CATEGORIA;
      e.cats.set(cat, (e.cats.get(cat) ?? 0) + 1);
      cuenta.set(r.equipo.slug, e);
    }
  }
  return [...cuenta.values()]
    .sort((a, b) => b.titulos - a.titulos || a.equipo.nombre.localeCompare(b.equipo.nombre, 'es'))
    .slice(0, max)
    .map(({ equipo, titulos, cats }) => ({
      equipo,
      titulos,
      // categorías donde ganó, de la que más veces a la que menos
      categorias: [...cats].map(([nombre, n]) => ({ nombre, n })).sort((a, b) => b.n - a.n || a.nombre.localeCompare(b.nombre, 'es')),
    }));
}

// --- medallero por año (jugador / equipo) -----------------------------------

export type AnioMedallas = { anio: number; puestos: (1 | 2 | 3)[] };

/**
 * Una bola por podio y año, desde el primer año en que aparece (aunque no haya ganado
 * nada ese año) hasta el último año del archivo. No muestra años anteriores a su primera
 * participación, porque ahí no jugaba.
 */
export function medalleroPorAnio(parts: { anio: number; puesto: number | null }[]): AnioMedallas[] {
  const primero = parts.length ? Math.min(...parts.map((p) => p.anio)) : Infinity;
  return resumen.anios.filter(({ anio }) => anio >= primero).map(({ anio }) => ({
    anio,
    puestos: parts
      .filter((p) => p.anio === anio && p.puesto !== null && p.puesto >= 1 && p.puesto <= 3)
      .map((p) => p.puesto as 1 | 2 | 3)
      .sort(),
  }));
}

/** Agrupa participaciones (ya ordenadas) por año, más reciente primero. */
export function agruparPorAnio<T extends { anio: number }>(parts: T[]): { anio: number; filas: T[] }[] {
  const grupos: { anio: number; filas: T[] }[] = [];
  for (const p of parts) {
    const ultimo = grupos[grupos.length - 1];
    if (ultimo && ultimo.anio === p.anio) ultimo.filas.push(p);
    else grupos.push({ anio: p.anio, filas: [p] });
  }
  return grupos;
}
