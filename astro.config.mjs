import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://qwedaq.github.io',
  integrations: [sitemap()],
  output: 'static',
  trailingSlash: 'never'
});
