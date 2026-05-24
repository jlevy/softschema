---
softschema:
  contract: example.movies:MoviePage/v1
  status: enforced
movie:
  title: Spirited Away
  release_year: 2001
  directors:
    - Hayao Miyazaki
  genres:
    - Animation
    - Adventure
    - Family
  runtime_minutes: 125
  description: >
    A girl enters a spirit world and has to find a way to save her parents while
    working in a bathhouse for supernatural visitors.
  ratings:
    rotten_tomatoes:
      critics:
        label: Tomatometer
        score_percent: 96
        total_reviews: 225
      audience:
        label: Popcornmeter
        score_percent: 96
        total_ratings: 250000
        total_ratings_display: 250,000+
---
# Spirited Away (2001)

*Spirited Away* is Hayao Miyazaki's 2001 animated adventure family film about a girl who
slips into a strange spirit world. Over its 125-minute runtime, she has to work in a
bathhouse for supernatural visitors while searching for a way to save her parents.

Rotten Tomatoes shows a 96% Tomatometer based on 225 critic reviews and a 96%
Popcornmeter based on 250,000+ audience ratings.

This section reads like a small movie page on a website. It presents the same title,
year, director, genres, runtime, description, and ratings as the YAML frontmatter, but
in a format that is easy for people to scan.

## Movie Details

| Field | Value |
| --- | --- |
| Title | Spirited Away |
| Release year | 2001 |
| Director | Hayao Miyazaki |
| Genres | Animation, Adventure, Family |
| Runtime | 125 minutes |
| Description | A girl enters a spirit world and has to find a way to save her parents while working in a bathhouse for supernatural visitors. |

## Ratings

| Source | Score | Count |
| --- | ---: | ---: |
| Rotten Tomatoes Critics | 96% Tomatometer | 225 reviews |
| Rotten Tomatoes Audience | 96% Popcornmeter | 250,000+ audience ratings |

The paragraph and tables intentionally mirror the YAML fields for scanning. Consumers
should read the YAML payload, not parse this body.
