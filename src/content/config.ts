import { defineCollection, z } from 'astro:content';

const articles = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    hero_title: z.string().optional(),
    date: z.coerce.date(),
    updatedDate: z.coerce.date().optional(),
    draft: z.boolean().default(false),
    featured: z.boolean().default(false),
    pinned: z.boolean().default(false),
    ticker: z.boolean().default(false),
    tickerRank: z.number().int().min(1).max(5).optional(),
    category: z.string(),
    tags: z.array(z.string()).default([]),
    excerpt: z.string(),
    coverImage: z.string().optional().nullable(),
    author: z.string().default('LeeScoop'),
    sourceType: z.enum(['local', 'notice', 'event', 'update']).default('local'),
    contentType: z.enum(['brief', 'standard', 'guide']).default('brief')
  })
});

export const collections = { articles };
