import { defineCollection, z } from 'astro:content';

const articles = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    slug: z.string().optional(),
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

    // LeeScoop keeps one collection for now. `contentKind` controls display.
    contentKind: z.enum(['event', 'news']).default('event'),
    sourceType: z.enum(['official', 'community', 'news', 'local']).default('official'),
    contentType: z.enum(['brief', 'standard', 'guide']).default('brief'),

    // Event fields.
    eventDate: z.coerce.date().optional(),
    eventEndDate: z.coerce.date().optional(),
    eventTime: z.string().optional(),
    city: z.string().optional(),
    location: z.string().optional(),
    venue: z.string().optional(),
    address: z.string().optional(),
    audience: z.string().optional(),
    cost: z.string().optional(),

    // Source fields.
    sourceName: z.string().optional(),
    sourceUrl: z.string().url().optional()
  })
});

export const collections = { articles };
