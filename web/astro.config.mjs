import { defineConfig } from 'astro/config';

// Sitio estático (sin SSR). `site` se define cuando se conozca el dominio final.
export default defineConfig({
  output: 'static',
  build: { format: 'directory' },
});
