import { defineAction } from 'astro:actions';
import { z } from 'astro/zod';

export const server = {
    userquery: defineAction({
        accept: 'form',
        input: z.object({
            budget_min: z.number().int(),
            budget_max: z.number().int(),
            score_type: z.enum(['ACT', 'SAT']),
            score: z.coerce.number().int(),
            region: z.string(),
            qualities: z.string().optional()
        }),

        handler: async ({ data }) => {
        const { budget_min, budget_max, score_type, score, region, qualities } = data;
        console.log(data)
        }

    })
}
