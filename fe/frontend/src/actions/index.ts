import { defineAction } from 'astro:actions';
import { API_URL } from "astro:env/client"
import { z } from 'astro/zod';

export const server = {
    userquery: defineAction({
        accept: 'form',
        input: z.object({
            budget_min: z.coerce.number().int().optional(),
            budget_max: z.coerce.number().int().optional(),
            score_type: z.enum(['ACT', 'SAT']).optional(),
            score: z.coerce.number().int().optional(),
            region: z.string().optional(),
            qualities: z.string().optional()
        }),

        handler: async (input) => {
            const { budget_min, budget_max, score_type, score, region, qualities } = input;

            const response = await fetch(`${API_URL}/prompt`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_prompt: qualities ?? "",
                    budget_min: budget_min ?? 0,
                    budget_max: budget_max ?? 100_000_000,
                    score_type: score_type ?? null,
                    score: score ?? null,
                    region: region ?? null,
                }),
            });

            if (!response.ok) throw new Error("Backend request failed");

            const data = await response.json();
            return data.recommendations;
        }

    })
}
