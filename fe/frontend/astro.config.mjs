// @ts-check
import { defineConfig, envField } from 'astro/config';

// https://astro.build/config
export default defineConfig({
    output: 'static',
    env: {
        schema: {
            API_URL: envField.string({ context: "client", access: "public", default: "http://localhost:8000" })
        }
    }
});
