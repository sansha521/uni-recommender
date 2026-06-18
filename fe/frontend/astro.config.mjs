// @ts-check
import { defineConfig, envField } from 'astro/config';
import node from '@astrojs/node';

// https://astro.build/config
export default defineConfig({
    adapter: node({
        mode: 'standalone',
    }),
    output: 'server',
    env: {
        schema: {
            API_URL: envField.string({ context: "client", access: "public", default: "http://localhost:8000/" })
        }
    }
});
