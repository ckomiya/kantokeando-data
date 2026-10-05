// Índice de búsqueda generado por scripts/exportar_datos.py, servido como archivo estático.
import type { APIRoute } from 'astro';
import indice from '../data/busqueda.json';

export const GET: APIRoute = () =>
  new Response(JSON.stringify(indice), { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
