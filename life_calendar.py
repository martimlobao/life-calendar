# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pycairo",
# ]
# ///

# https://github.com/eriknyquist/generate_life_calendar

import argparse
import datetime
import math
from pathlib import Path

import cairo

# global constants (do not change)
MIN_AGE = 80
MAX_AGE = 150
NUM_ROWS = 100  # need to modify to match the provided age
NUM_COLUMNS = 52  # always 52 columns

# independent variables (can be changed)
AZERO_HEIGHT = 2 ** (1 / 4)  # ≈ 1.189m
AZERO_WIDTH = 1 / AZERO_HEIGHT  # ≈ 0.8409m
MM_PER_PT = 0.3528
# A4 standard international paper size
A_SIZE = 4
DOC_HEIGHT = AZERO_HEIGHT / (2 ** (1 / 2)) ** A_SIZE * 1000 / MM_PER_PT  # ≈ 841mm / 2383pt
DOC_WIDTH = DOC_HEIGHT / 2 ** (1 / 2)  # ≈ 594mm / 1683pt

DOC_NAME = "life_calendar.pdf"

DEFAULT_TITLE = "LIFE CALENDAR"

FONT = "EB Garamond SC"
BIGFONT_SIZE = DOC_HEIGHT / 30  # ≈ 80pt at A1 size
SMALLFONT_SIZE = DOC_HEIGHT / 120  # ≈ 20pt at A1 size
TINYFONT_SIZE = DOC_HEIGHT / 200  # ≈ 12pt at A1 size

TOP_MARGIN = DOC_HEIGHT * 0.10
MIN_BOTTOM_MARGIN = DOC_HEIGHT * 0.05
MIN_SIDE_MARGIN = DOC_WIDTH * 0.10

GAP_X_INTERVAL = 4
GAP_Y_INTERVAL = 10

# relative to BOX_BOUNDS / i.e. column width / i.e. row height
BOX_MARGIN_RATIO = 35 / 100
GAP_SIZE_RATIO = BOX_MARGIN_RATIO
BOX_LINE_WIDTH_RATIO = 1 / 6 * (1 - BOX_MARGIN_RATIO)
CORNER_RADIUS_RATIO = 1 / 5 * (1 - BOX_MARGIN_RATIO)

# dependent variables (cannot be changed)
X_GAPS = (NUM_COLUMNS - 1) // GAP_X_INTERVAL
Y_GAPS = (NUM_ROWS - 1) // GAP_Y_INTERVAL
# number of box bounds in grid
GRID_BOUNDS_X_RATIO = NUM_COLUMNS - BOX_MARGIN_RATIO + X_GAPS * GAP_SIZE_RATIO
GRID_BOUNDS_Y_RATIO = NUM_ROWS - BOX_MARGIN_RATIO + Y_GAPS * GAP_SIZE_RATIO
MAX_BOX_BOUNDS_X = (DOC_WIDTH - 2 * MIN_SIDE_MARGIN) / GRID_BOUNDS_X_RATIO
MAX_BOX_BOUNDS_Y = (DOC_HEIGHT - TOP_MARGIN - MIN_BOTTOM_MARGIN) / GRID_BOUNDS_Y_RATIO
BOX_BOUNDS = min(MAX_BOX_BOUNDS_X, MAX_BOX_BOUNDS_Y)
BOX_MARGIN = BOX_MARGIN_RATIO * BOX_BOUNDS
BOX_SIZE = BOX_BOUNDS - BOX_MARGIN
SIDE_MARGIN = (DOC_WIDTH - (BOX_BOUNDS * GRID_BOUNDS_X_RATIO)) / 2

CORNER_RADIUS = CORNER_RADIUS_RATIO * BOX_BOUNDS
BOX_LINE_WIDTH = BOX_LINE_WIDTH_RATIO * BOX_BOUNDS
HEAVY_BOX_LINE_WIDTH = 2 * BOX_LINE_WIDTH
GAP_SIZE = GAP_SIZE_RATIO * BOX_BOUNDS

BLACK = (0.2, 0.2, 0.2)
WHITE = (1.0, 1.0, 1.0)
LIGHT_GRAY = (0.7, 0.7, 0.7)
DARK_GRAY = (0.5, 0.5, 0.5)
DARKENED_COLOR_DELTA = (-0.8, -0.8, -0.8)
LIGHTEN = (1.6, 1.6, 1.6)

SPECIAL_DATES = ["2017-06-24", "2019-06-19", "2022-03-01", "2023-11-10", "2025-08-06"]


def parse_date(datestr: str) -> datetime.date:
    formats = ["%Y/%m/%d", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]

    for f in formats:
        try:
            parsed: datetime.datetime = datetime.datetime.strptime(datestr.strip(), f)
        except ValueError:
            continue
        else:
            return parsed.date()

    raise ValueError("Incorrect date format: must be DMY or YMD with / or -")


def format_date(date: datetime.date) -> str:
    numerals = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
    return f"{date.strftime("%d")} {numerals[date.month - 1].lower()} {date.strftime("%Y")}"


def is_current_week(now: datetime.date, *, day: int, month: int, year: int | None = None) -> bool:
    end = now + datetime.timedelta(weeks=1)
    years: list[int] = [now.year, now.year + 1] if year is None else [year]

    for year in years:
        try:
            date: datetime.date = datetime.date(year, month, day)
        except ValueError:
            if (month == 2) and (day == 29):  # noqa: PLR2004
                # Handle edge case for birthday being on leap year day
                date = datetime.date(year, month, day - 1)
            else:
                raise
        if now <= date < end:
            return True

    return False


def is_special_week(now, dates: list[str]):
    dates = [parse_date(date) for date in dates]
    return any(
        is_current_week(now, day=date.day, month=date.month, year=date.year) for date in dates
    )


def count_1000k_week(date: datetime.date, *, birthdate: datetime.date) -> int:
    days_now: int = (date - birthdate).days
    days_last_week: int = (date - datetime.timedelta(weeks=1) - birthdate).days
    if days_last_week // 7000 < days_now // 7000:
        return days_now // 7000
    return 0


def count_gigasec_week(date: datetime.date, *, birthdate: datetime.date) -> int:
    total_seconds_now: float = (date - birthdate).total_seconds()
    total_seconds_last_week: float = (
        date - datetime.timedelta(weeks=1) - birthdate
    ).total_seconds()

    if total_seconds_last_week // 1_000_000_000 < total_seconds_now // 1_000_000_000:
        return int(total_seconds_now // 1_000_000_000)
    return 0


def parse_darken_until_date(datestr: str) -> datetime.date:
    if datestr == "today":
        today = datetime.date.today()
        return datetime.date(today.year, today.month, today.day)
    return parse_date(datestr)


def get_darkened_fill(fill: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(map(sum, zip(fill, DARKENED_COLOR_DELTA, strict=False)))


def text_size(ctx: cairo.Context, text: str) -> tuple[float, float]:
    _, _, width, height, _, _ = ctx.text_extents(text)
    return width, height


def draw_square(
    ctx: cairo.Context,
    pos_x: float,
    pos_y: float,
    box_size: float,
    fillcolor: tuple[float, float, float] = WHITE,
    linewidth: float = BOX_LINE_WIDTH,
) -> None:
    """Draws rectangles with rounded (circular arc) corners."""
    ctx.set_line_width(linewidth)
    ctx.set_source_rgb(*BLACK)
    ctx.move_to(pos_x, pos_y)

    x_1, x_2 = pos_x, pos_x + box_size
    y_1, y_2 = pos_y, pos_y + box_size

    # Define corner positions and corresponding arc start/end angles
    corners = [
        (x_1 + CORNER_RADIUS, y_1 + CORNER_RADIUS, 2, 3),  # Top-left
        (x_2 - CORNER_RADIUS, y_1 + CORNER_RADIUS, 3, 4),  # Top-right
        (x_2 - CORNER_RADIUS, y_2 - CORNER_RADIUS, 0, 1),  # Bottom-right
        (x_1 + CORNER_RADIUS, y_2 - CORNER_RADIUS, 1, 2),  # Bottom-left
    ]

    # Draw the square
    ctx.new_sub_path()
    for cx, cy, start, end in corners:
        ctx.arc(cx, cy, CORNER_RADIUS, start * (math.pi / 2), end * (math.pi / 2))
    ctx.close_path()
    ctx.stroke_preserve()

    # Fill the square
    ctx.set_source_rgb(*fillcolor)
    ctx.fill()


def draw_row(ctx: cairo.Context, pos_y, birthdate, date, box_size, darken_until_date):
    """Draws a row of 52 or 53 squares, starting at pos_y."""
    pos_x = SIDE_MARGIN
    week = 0
    row_tags = []

    # Write the start date of the row
    ctx.set_font_size(TINYFONT_SIZE)
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_source_rgb(*DARK_GRAY)
    date_str = format_date(date)
    w, h = text_size(ctx, date_str)
    ctx.move_to(pos_x - w - BOX_SIZE, pos_y + ((BOX_SIZE / 2) + (h / 2)))
    ctx.show_text(date_str)

    # Loop until reaching the next birthday week
    while week == 0 or not is_current_week(date, day=birthdate.day, month=birthdate.month):
        fill = WHITE
        width = BOX_LINE_WIDTH

        if is_special_week(date, dates=SPECIAL_DATES):
            fill = LIGHTEN
        if count_1000k_week(date, birthdate=birthdate):
            row_tags.append(f"{count_1000k_week(date, birthdate=birthdate)}k")
            width = HEAVY_BOX_LINE_WIDTH
        if count_gigasec_week(date, birthdate=birthdate):
            row_tags.append(f"{count_gigasec_week(date, birthdate=birthdate)}Gs")
            width = HEAVY_BOX_LINE_WIDTH
        if darken_until_date and date < darken_until_date:
            fill = get_darkened_fill(fill)

        draw_square(ctx, pos_x, pos_y, BOX_SIZE, fillcolor=fill, linewidth=width)
        pos_x += BOX_SIZE + BOX_MARGIN
        if week % GAP_X_INTERVAL == GAP_X_INTERVAL - 1:
            pos_x += GAP_SIZE
        week += 1
        date += datetime.timedelta(weeks=1)

    # Add special tags to the row (xk weeks, xGs)
    for tag in row_tags:
        ctx.set_source_rgb(*DARK_GRAY)
        w, h = text_size(ctx, tag)
        ctx.move_to(pos_x, pos_y + ((BOX_SIZE + h) / 2))
        pos_x += w + GAP_SIZE
        ctx.show_text(tag)

    return date


def draw_grid(ctx: cairo.Context, birthdate, age, darken_until_date) -> None:
    """Draws the whole grid of 52x90 squares."""
    num_rows = age
    pos_x = SIDE_MARGIN
    pos_y = TOP_MARGIN

    # Draw week numbers above top row
    ctx.set_source_rgb(*DARK_GRAY)
    ctx.set_font_size(TINYFONT_SIZE)
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)

    for i in range(NUM_COLUMNS):
        if i == 0:
            text = birthdate.strftime("%A").lower() + "s"
            ctx.move_to(pos_x, pos_y - BOX_SIZE)
            ctx.show_text(text)
        elif i % GAP_X_INTERVAL == (GAP_X_INTERVAL - 1):
            text = str(i + 1)
            w, _ = text_size(ctx, text)
            ctx.move_to(pos_x + BOX_SIZE / 2 - w / 2, pos_y - BOX_SIZE)
            ctx.show_text(text)
            pos_x += GAP_SIZE
        pos_x += BOX_SIZE + BOX_MARGIN

    date = birthdate

    for i in range(num_rows):
        date = draw_row(ctx, pos_y, birthdate, date, BOX_SIZE, darken_until_date)
        pos_y += BOX_SIZE + BOX_MARGIN
        if i % GAP_Y_INTERVAL == (GAP_Y_INTERVAL - 1):
            pos_y += GAP_SIZE


def gen_calendar(birthdate, title, age, filename, darken_until_date, subtitle_text=None) -> None:
    age = int(age)
    if (age < MIN_AGE) or (age > MAX_AGE):
        raise ValueError(f"Invalid age, must be between {MIN_AGE} and {MAX_AGE}")

    # Fill background with white
    surface: cairo.PDFSurface = cairo.PDFSurface(filename, DOC_WIDTH, DOC_HEIGHT)
    ctx: cairo.Context = cairo.Context(surface)
    ctx.set_source_rgb(*WHITE)
    ctx.rectangle(0, 0, DOC_WIDTH, DOC_HEIGHT)
    ctx.fill()

    # Draw title
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_source_rgb(*BLACK)
    ctx.set_font_size(BIGFONT_SIZE)
    w_title, h_title = text_size(ctx, title)
    ctx.move_to((DOC_WIDTH / 2) - (w_title / 2), TOP_MARGIN / 2)
    ctx.show_text(title)

    # Draw subtitle
    if subtitle_text is not None:
        ctx.set_source_rgb(*LIGHT_GRAY)
        ctx.set_font_size(SMALLFONT_SIZE)
        w, h = text_size(ctx, subtitle_text)
        ctx.move_to((DOC_WIDTH / 2) - (w / 2), (TOP_MARGIN / 2) + h_title - (h / 2))
        ctx.show_text(subtitle_text)

    # Draw grid
    draw_grid(ctx, birthdate, age, darken_until_date)

    ctx.show_page()


def main() -> None:
    parser = argparse.ArgumentParser(
        description='\nGenerate a personalized "Life  Calendar", inspired by'
        " the calendar with the same name from the waitbutwhy.com store"
    )

    parser.add_argument(
        type=parse_date,
        dest="date",
        help="starting date; your birthday, in either yyyy/mm/dd or dd/mm/yyyy"
        " format (dashes '-' may also be used in place of slashes '/')",
    )

    parser.add_argument(
        "-f", "--filename", type=str, dest="filename", help="output filename", default=DOC_NAME
    )

    parser.add_argument(
        "-t",
        "--title",
        type=str,
        dest="title",
        help=f'Calendar title text (default is "{DEFAULT_TITLE}")',
        default=DEFAULT_TITLE,
    )

    parser.add_argument(
        "-b",
        "--subtitle-text",
        type=str,
        dest="subtitle_text",
        help="Text to show under the calendar title (default is no subtitle text)",
        default=None,
    )

    parser.add_argument(
        "-a",
        "--age",
        type=int,
        dest="age",
        choices=range(MIN_AGE, MAX_AGE + 1),
        metavar=f"[{MIN_AGE}-{MAX_AGE}]",
        help="Number of rows to generate, representing years of life",
        default=100,
    )

    parser.add_argument(
        "-d",
        "--darken-until",
        type=parse_darken_until_date,
        dest="darken_until_date",
        nargs="?",
        const="today",
        help="Darken until date. (defaults to today if argument is not given)",
    )

    args = parser.parse_args()
    doc_name = f"{Path(args.filename).stem}.pdf"

    try:
        gen_calendar(
            args.date,
            args.title,
            args.age,
            doc_name,
            args.darken_until_date,
            subtitle_text=args.subtitle_text,
        )
    except Exception as e:
        print(f"Error: {e}")
        raise

    print(f"Created {doc_name}")


if __name__ == "__main__":
    main()
