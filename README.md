# Life Calendar

![Life Calendar](./static/banner.png)

Life Calendar is a lightweight script that creates printable PDFs visualizing every week of a lifetime. Inspired by Tim Urban's ["Your Life in Weeks" post](https://waitbutwhy.com/2014/05/life-weeks.html), it helps you reflect on the past and plan for the future at a glance.

## PDF examples

* [Standard printable version](./static/life_calendar.pdf) — includes no pre-filled squares so you can mark them manually after printing.
* [Filled progress example](./static/life_calendar-darkened.pdf) — shows the calendar with weeks darkened up to a specific date.

## Usage

If you don't already have [`uv`](https://docs.astral.sh/uv/getting-started/installation/) installed, follow the official installation instructions first.

Run the script directly with `uv` by pointing to the raw GitHub URL:

```bash
uv run https://raw.githubusercontent.com/martimlobao/life-calendar/main/life_calendar.py 1990-08-06 -d -a 100 -b "Martim Lobao" -x 2010-05-15,2015-09-10,2020-12-31,2024-07-04
```

This command will generate a PDF highlighting the provided milestone dates for the named person and duration.

### Arguments

* `date` (positional): Starting date (typically your birthday) in `YYYY-MM-DD` or `DD/MM/YYYY` format.
* `-f/--filename`: Output filename (defaults to `life_calendar.pdf`).
* `-s/--a-size`: Paper size using ISO 216 A-series numbering (`A2` by default).
* `-t/--title`: Title text displayed at the top of the PDF.
* `-b/--subtitle-text`: Subtitle text shown beneath the title.
* `-a/--age`: Number of rows to generate, representing years of life (defaults to `100`).
* `-d/--darken-until`: Darken all weeks up to the supplied date (or up to today if no date is provided).
* `-x/--highlight-dates`: Comma-separated list of additional dates (`YYYY-MM-DD`) to highlight.

To produce a blank printable calendar, omit the highlight dates and darkening flag:

```bash
uv run https://raw.githubusercontent.com/martimlobao/life-calendar/main/life_calendar.py 1990-08-06 -a 100 -b "Martim Lobao"
```
