import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// Sitio estático (sin SSR). `site` es necesario para el sitemap.
export default defineConfig({
  site: 'https://gatedatos.org.pe',
  output: 'static',
  build: { format: 'directory' },
  integrations: [
    // /buscar/ no aporta nada en los resultados de Google (es un buscador sin contenido propio)
    sitemap({ filter: (pagina) => !pagina.endsWith('/buscar/') }),
  ],
});
