import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://leescoop.com',
  output: 'static',
  vite: {
    resolve: {
      alias: {
        '@': new URL('./src', import.meta.url).pathname
      }
    }
  }
});
