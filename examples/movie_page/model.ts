/** Zod model for the movie page example. */

import { z } from "zod";
import { softField } from "softschema/node";

export const CastMember = z
  .strictObject({
    actor: z.string(),
    character: z.string(),
  })
  .meta({ id: "CastMember", description: "One billed cast member." });

export const RottenTomatoesRating = z
  .strictObject({
    critics_percent: z
      .int()
      .min(0)
      .max(100)
      .describe("Tomatometer score, 0-100."),
    audience_percent: z
      .int()
      .min(0)
      .max(100)
      .describe("Popcornmeter score, 0-100."),
    critic_review_count: z.int().min(0),
  })
  .meta({
    id: "RottenTomatoesRating",
    description: "Rotten Tomatoes critic and audience scores.",
  });

export const ImdbRating = z
  .strictObject({
    score: z.number().min(0).max(10).describe("IMDb rating on a 0-10 scale."),
    total_votes: z.int().min(0),
  })
  .meta({ id: "ImdbRating", description: "IMDb aggregate rating." });

export const MovieRatings = z
  .strictObject({
    rotten_tomatoes: RottenTomatoesRating.nullable().optional(),
    imdb: ImdbRating.nullable().optional(),
  })
  .meta({ id: "MovieRatings", description: "Aggregate ratings from external sources." });

export const MoviePage = z
  .strictObject({
    title: z.string(),
    release_year: z.int().min(1888),
    runtime_minutes: z.int().gt(0),
    mpaa_rating: z.enum(["G", "PG", "PG-13", "R", "NC-17", "NR"]).nullable().optional(),
    directors: z.array(z.string()).min(1),
    genres: softField(z.array(z.string()).min(1), {
      description: "Genre labels for the film.",
      group: "taxonomy",
      owner: "agent",
      tier: "constrained",
      instruction: "Pick from the standard IMDb genre vocabulary; at least one.",
    }),
    tagline: z.string().nullable().optional(),
    synopsis: z.string(),
    cast: z.array(CastMember).default([]),
    ratings: MovieRatings,
  })
  .meta({
    description:
      "A small movie info page, similar to a public IMDB-style listing.\n\n" +
      "The fields illustrate the structural variety a softschema artifact can carry:\n" +
      "constrained scalars, enums, lists of strings, lists of structured records, and\n" +
      "optional nested objects.",
  });
