---
softschema:
  contract: example.movies:MoviePage/v1
  status: enforced
movie:
  title: Spirited Away
  release_year: 2001
  runtime_minutes: 125
  mpaa_rating: PG
  directors:
    - Hayao Miyazaki
  genres:
    - Animation
    - Adventure
    - Family
  synopsis: >
    Ten-year-old Chihiro and her parents stumble into a mysterious abandoned town
    that turns out to be a spirit world. After her parents are transformed into pigs,
    Chihiro must take a job in a magical bathhouse run by the witch Yubaba and find a
    way to break the spell so the family can return home.
  cast:
    - actor: Rumi Hiiragi
      character: Chihiro / Sen
    - actor: Miyu Irino
      character: Haku
    - actor: Mari Natsuki
      character: Yubaba
  ratings:
    rotten_tomatoes:
      critics_percent: 96
      audience_percent: 96
      critic_review_count: 225
    imdb:
      score: 8.6
      total_votes: 850000
---
# Spirited Away (2001)

*Spirited Away* is Hayao Miyazaki's 2001 animated adventure film about a young girl
who slips into a strange spirit world. Over its 125-minute runtime, she takes a job
in a bathhouse for supernatural visitors while searching for a way to save her parents
and return home.

Rotten Tomatoes shows a 96% Tomatometer based on 225 critic reviews and a 96%
Popcornmeter from the audience. IMDb users give it 8.6 out of 10 across more than
850,000 votes.

This section reads like a small movie page on a website. It presents the same title,
year, runtime, directors, genres, synopsis, lead cast, and rating summary as the YAML
frontmatter, but in a format that is easy for people to scan.

## Movie Details

| Field | Value |
| --- | --- |
| Title | Spirited Away |
| Release year | 2001 |
| Runtime | 125 minutes |
| MPAA rating | PG |
| Director | Hayao Miyazaki |
| Genres | Animation, Adventure, Family |

## Lead Cast

| Actor | Character |
| --- | --- |
| Rumi Hiiragi | Chihiro / Sen |
| Miyu Irino | Haku |
| Mari Natsuki | Yubaba |

## Ratings

| Source | Score | Count |
| --- | ---: | ---: |
| Rotten Tomatoes Critics | 96% Tomatometer | 225 reviews |
| Rotten Tomatoes Audience | 96% Popcornmeter | — |
| IMDb | 8.6 / 10 | 850,000+ votes |

The paragraphs and tables intentionally mirror the YAML fields for scanning.
Consumers should read the YAML payload, not parse this body.
