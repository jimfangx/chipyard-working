import starlight from '@astrojs/starlight';
import { defineConfig } from 'astro/config';

import { sidebar } from './src/sidebar.mjs';

function getBasePath() {
  if (process.env.DOCS_BASE) return process.env.DOCS_BASE;
  if (process.env.READTHEDOCS !== 'True') return undefined;

  const language = process.env.READTHEDOCS_LANGUAGE || 'en';
  const version = process.env.READTHEDOCS_VERSION || 'latest';
  return `/${language}/${version}`;
}

const base = getBasePath();
const basePrefix = base ? base.replace(/\/$/, '') : '';

export default defineConfig({
  site: process.env.DOCS_SITE_URL || 'https://chipyard.readthedocs.io',
  base,
  integrations: [
    starlight({
      title: 'Chipyard',
      description: 'Chipyard documentation',
      logo: {
        src: './_static/images/chipyard-logo.svg',
        replacesTitle: true,
      },
      customCss: ['./src/styles/sphinx.css'],
      sidebar,
      tableOfContents: {
        minHeadingLevel: 2,
        maxHeadingLevel: 4,
      },
      head: [
        {
          tag: 'meta',
          attrs: {
            name: 'readthedocs-addons-api-version',
            content: '1',
          },
        },
        {
          tag: 'script',
          attrs: {
            src: `${basePrefix}/readthedocs-version-switcher.js`,
            defer: true,
          },
        },
      ],
    }),
  ],
});
