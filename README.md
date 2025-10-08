# Life Calendar

![Life Calendar](./static/banner.png)

## Usage

```bash
uv run life_calendar.py 1990-08-06 -d -a 100 -b "Martim Lobao" -x 2017-06-24,2019-06-19,2022-03-01,2023-11-10
```

Fonts bundled with the project are used automatically when you run the script locally
with `uv run` or when you execute it directly from GitHub:

```bash
uv run https://raw.githubusercontent.com/martimlobao/life-calendar/main/life_calendar.py 1990-08-06
```

You can override the font choice with `--font-family` when you prefer a specific
family among the bundled fonts:

```bash
uv run life_calendar.py 1990-08-06 --font-family "EB Garamond SC"
```

Blank printable version:

```bash
uv run life_calendar.py 1990-08-06 -a 100 -b "Martim Lobao" -f print
```
