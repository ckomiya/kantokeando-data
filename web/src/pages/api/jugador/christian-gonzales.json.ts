// JSON estático generado en el build con los mismos datos de /jugador/christian-gonzales/.
import type { APIRoute } from 'astro';
import { etiquetaPuesto, jugadores, nombreCategoria, urlJugador } from '../../../lib/datos';

const SLUG = 'christian-gonzales';

export const GET: APIRoute = ({ site }) => {
  const j = jugadores.find((x) => x.slug === SLUG);
  if (!j) throw new Error(`No existe el jugador ${SLUG}`);

  // Las participaciones vienen de la más reciente a la más antigua
  const p = j.participaciones.find((x) => x.puesto !== null && x.puesto >= 1 && x.puesto <= 3);

  const cuerpo = {
    nombre: j.nombre,
    url: new URL(urlJugador(j.slug), site).href,
    ultimo_podio: p
      ? {
          fecha: p.fecha,
          torneo: p.nombre_torneo,
          categoria: p.categoria ? nombreCategoria(p.categoria) : null,
          puesto: p.puesto,
          puesto_texto: etiquetaPuesto(p.puesto),
          equipo: p.equipo?.nombre ?? null,
          url_articulo: p.url,
        }
      : null,
  };

  return new Response(JSON.stringify(cuerpo, null, 2), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
};
