import { defineConfig } from 'astro/config';

// Sitio estático (sin SSR).
export default defineConfig({
  site: 'https://gatedatos.org.pe',
  output: 'static',
  build: { format: 'directory' },
});
