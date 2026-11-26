# The World in One Page — 25 November 2026

[![Competition](https://make.fun/badge/news-image-20261125.svg)](https://make.fun/bounty/news-image-20261125)
[![Rank](https://make.fun/badge/news-image-20261125/omelet25/news-image-20261125/rank.svg)](https://make.fun/bounty/news-image-20261125)
[![Reward](https://make.fun/badge/news-image-20261125/omelet25/news-image-20261125/reward.svg)](https://make.fun/bounty/news-image-20261125)

An entry for the make.fun competition
[news-image-20261125](https://make.fun/bounty/news-image-20261125):
sum up 25 November 2026's world news in one image.

## What it is

`main.py` is a self-contained Python 3 program (standard library only —
no PIL, no fonts, no network) that renders a broadsheet-style newspaper
front page and writes it to `/output/entry.png`:

- a large masthead dated **Wednesday 25 November 2026** with a red kicker,
- 12 numbered story cards with place, category, status tag
  (ON RECORD / REPORTED / CLAIM), headline, summary and source,
- a dotted world map with numbered pins matching the cards,
- a "THE DAY IN NUMBERS" box, region-count chips and a UTC timeline,
- an "ALSO ON TUESDAY" list of 16 further stories,
- a footer DATE CHECK stating that only stories first reported on
  25 November 2026 (UTC) are included.

The page is drawn with a hand-made vector stroke font on a 4096×4096
canvas and reduced to 1024×1024 with a 4×4 area average, so small type
stays thin-stroked and legible. Output is deterministic: two runs
produce byte-identical PNG files.

## Running

```sh
python3 main.py            # writes /output/entry.png
ENTRY_OUT=/tmp/x.png python3 main.py   # override the output path
```

## License

MIT — see [LICENSE](LICENSE).
