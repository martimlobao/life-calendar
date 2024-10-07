# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pycairo",
# ]
# ///

# https://github.com/eriknyquist/generate_life_calendar

import datetime
import argparse
import os
import math

import cairo

# global constants (do not change)
MIN_AGE = 90
MAX_AGE = 150
NUM_ROWS = 100
NUM_COLUMNS = 52  # always 52 columns

# independent variables (can be changed)
AZERO_HEIGHT = 2 ** (1/4)  # ≈ 1.189m
AZERO_WIDTH = 1 / AZERO_HEIGHT  # ≈ 0.8409m
MM_PER_PT = 0.3528
# A1 standard international paper size
A_SIZE = 4
DOC_HEIGHT = AZERO_HEIGHT / (2 ** (1/2)) ** A_SIZE * 1000 / MM_PER_PT  # ≈ 841mm / 2383pt
DOC_WIDTH = DOC_HEIGHT / 2 ** (1/2)  # ≈ 594mm / 1683pt

DOC_NAME = "life_calendar2.pdf"

KEY_NEWYEAR_DESC = "First week of the new year"
KEY_BIRTHDAY_DESC = "Week of your birthday"
DEFAULT_TITLE = "LIFE CALENDAR"

FONT = "Baskerville"
BIGFONT_SIZE = 40
BIGFONT_SIZE = DOC_HEIGHT / 60  # ≈ 14pt at A1 size
SMALLFONT_SIZE = 16
SMALLFONT_SIZE = DOC_HEIGHT / 150  # ≈ 16pt at A1 size
TINYFONT_SIZE = 12
TINYFONT_SIZE = DOC_HEIGHT / 200  # ≈ 12pt at A1 size
# MAX_TITLE_SIZE = 50

TOP_MARGIN = DOC_HEIGHT * 0.10
MIN_BOTTOM_MARGIN = DOC_HEIGHT * 0.05
MIN_SIDE_MARGIN = DOC_WIDTH * 0.15

GAP_X_INTERVAL = 4
GAP_Y_INTERVAL = 10

# dependent on BOX_SIZE
CORNER_RADIUS_RATIO = 1 / 5
BOX_LINE_WIDTH_RATIO = 1 / 6
BOX_MARGIN_RATIO = 3 / 10
# GAP_SIZE_RATIO = 1 / 2
GAP_SIZE_RATIO = 2 * BOX_MARGIN_RATIO

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
# BOX_BOUNDS = MAX_BOX_BOUNDS_X
BOX_MARGIN = BOX_MARGIN_RATIO * BOX_BOUNDS
BOX_SIZE = BOX_BOUNDS - BOX_MARGIN
SIDE_MARGIN = (DOC_WIDTH - (BOX_BOUNDS * GRID_BOUNDS_X_RATIO)) / 2

CORNER_RADIUS = CORNER_RADIUS_RATIO * BOX_BOUNDS
BOX_LINE_WIDTH = BOX_LINE_WIDTH_RATIO * BOX_BOUNDS
GAP_SIZE = GAP_SIZE_RATIO * BOX_BOUNDS

BIRTHDAY_COLOR = (0.5, 0.5, 0.5)
NEWYEAR_COLOR = (0.8, 0.8, 0.8)
DARKENED_COLOR_DELTA = (-0.4, -0.4, -0.4)
DARKENED_COLOR_DELTA = (-0.7, -0.7, -0.7)

# TOP_MARGIN = 144

# BOX_BOUNDS = (DOC_HEIGHT - (TOP_MARGIN + 36)) / NUM_ROWS
# BOX_MARGIN = 0.3 * BOX_BOUNDS
# BOX_SIZE = BOX_BOUNDS - BOX_MARGIN
# BOX_LINE_WIDTH = 3
# CORNER_RADIUS = BOX_SIZE / 5
# GAP_SIZE = BOX_SIZE / 2
# box size dependent



def parse_date(date):
    formats = ["%Y/%m/%d", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]

    for f in formats:
        try:
            ret = datetime.datetime.strptime(date.strip(), f)
        except ValueError:
            continue
        else:
            return ret

    raise ValueError("Incorrect date format: must be dd-mm-yyyy or dd/mm/yyyy")


def format_date(date):
    numerals = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
    return f"{date.day} {numerals[date.month - 1]} {date.year}"


def text_size(ctx, text):
    _, _, width, height, _, _ = ctx.text_extents(text)
    return width, height


def back_up_to_monday(date):
    return date - datetime.timedelta(days=date.weekday())


def is_future(now, date):
    return now < date


def is_current_week(now, month, day):
    end = now + datetime.timedelta(weeks=1)
    ret = []

    for year in [now.year, now.year + 1]:
        try:
            date = datetime.datetime(year, month, day)
        except ValueError as e:
            if (month == 2) and (day == 29):
                # Handle edge case for birthday being on leap year day
                date = datetime.datetime(year, month, day - 1)
            else:
                raise e

        ret.append(now <= date < end)

    return True in ret


def count_1000k_week(date, *, birthdate) -> int:
    days_now = (date - birthdate).days
    days_last_week = (date - datetime.timedelta(weeks=1) - birthdate).days
    if days_last_week // 7000 < days_now // 7000:
        return days_now // 7000
    return 0

def count_Gs_week(date, *, birthdate) -> int:
    total_seconds_now = (date - birthdate).total_seconds()
    total_seconds_last_week = (date - datetime.timedelta(weeks=1) - birthdate).total_seconds()

    if total_seconds_last_week // 1_000_000_000 < total_seconds_now // 1_000_000_000:
        return int(total_seconds_now // 1_000_000_000)
    return 0



def parse_darken_until_date(date):
    if date == "today":
        today = datetime.date.today()
        until_date = datetime.datetime(today.year, today.month, today.day)
    else:
        until_date = parse_date(date)

    return back_up_to_monday(until_date)


def get_darkened_fill(fill):
    return tuple(map(sum, zip(fill, DARKENED_COLOR_DELTA)))


def draw_square(ctx, pos_x, pos_y, box_size, fillcolor=(1, 1, 1), width=BOX_LINE_WIDTH):
    """Draws rectangles with rounded (circular arc) corners."""

    ctx.set_line_width(width)
    ctx.set_source_rgb(0, 0, 0)
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

    ctx.new_sub_path()

    for (cx, cy, start, end) in corners:
        ctx.arc(cx, cy, CORNER_RADIUS, start * (math.pi / 2), end * (math.pi / 2))

    ctx.close_path()
    ctx.stroke_preserve()

    # Fill the square
    ctx.set_source_rgb(*fillcolor)
    ctx.fill()


def draw_row(ctx, pos_y, birthdate, date, box_size, x_margin, darken_until_date):
    """
    Draws a row of 52 or 53 squares, starting at pos_y
    """

    pos_x = x_margin
    birthday_count = 0

    for week in range(NUM_COLUMNS + 1):
        fill = (1, 1, 1)

        if is_current_week(date, birthdate.month, birthdate.day):
            fill = BIRTHDAY_COLOR
            birthday_count += 1
            if birthday_count > 1:
                break
        elif is_current_week(date, 1, 1):
            fill = NEWYEAR_COLOR

        if darken_until_date and is_future(date, darken_until_date):
            fill = get_darkened_fill(fill)

        draw_square(ctx, pos_x, pos_y, box_size, fillcolor=fill)
        pos_x += box_size + BOX_MARGIN
        if week % 4 == 3:
            pos_x += GAP_SIZE
        date += datetime.timedelta(weeks=1)
    return date

def draw_row(ctx, pos_y, birthdate, date, box_size, x_margin, darken_until_date):
    """
    Draws a row of 52 or 53 squares, starting at pos_y
    """

    pos_x = SIDE_MARGIN
    week = 0
    row_tags = []

    ctx.set_font_size(TINYFONT_SIZE)
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    # write the date
    ctx.set_source_rgb(0.5, 0.5, 0.5)
    date_str = format_date(date)
    w, h = text_size(ctx, date_str)
    # Draw it in front of the current row
    ctx.move_to(pos_x - w - BOX_SIZE, pos_y + ((BOX_SIZE / 2) + (h / 2)))
    ctx.show_text(date_str)

    # loop until reaching the next birthday week
    while week == 0 or not is_current_week(date, birthdate.month, birthdate.day):
        fill = (1, 1, 1)
        width = BOX_LINE_WIDTH

        if count_1000k_week(date, birthdate=birthdate):
            row_tags.append(f"{count_1000k_week(date, birthdate=birthdate)}k")
            # fill = BIRTHDAY_COLOR
            width = 1.5 * BOX_LINE_WIDTH

        if count_Gs_week(date, birthdate=birthdate):
            row_tags.append(f"{count_Gs_week(date, birthdate=birthdate)}Gs")
            # fill = NEWYEAR_COLOR
            width = 1.5 * BOX_LINE_WIDTH
        if darken_until_date and is_future(date, darken_until_date):
            fill = get_darkened_fill(fill)

        draw_square(ctx, pos_x, pos_y, box_size, fillcolor=fill, width=width)
        pos_x += box_size + BOX_MARGIN
        if week % GAP_X_INTERVAL == (GAP_X_INTERVAL - 1):
            pos_x += GAP_SIZE
        week += 1
        date += datetime.timedelta(weeks=1)

    for tag in row_tags:
        ctx.set_source_rgb(0.5, 0.5, 0.5)
        w, h = text_size(ctx, tag)
        ctx.move_to(pos_x, pos_y + ((BOX_SIZE + h )/ 2))
        pos_x += w + GAP_SIZE
        ctx.show_text(tag)

    return date


def draw_key_item(ctx, pos_x, pos_y, desc, box_size, color):
    draw_square(ctx, pos_x, pos_y, box_size, fillcolor=color)
    pos_x += box_size + (box_size / 2)

    ctx.set_source_rgb(0, 0, 0)
    w, h = text_size(ctx, desc)
    ctx.move_to(pos_x, pos_y + (box_size / 2) + (h / 2))
    ctx.show_text(desc)

    return pos_x + w + (box_size * 2)


def draw_grid(ctx, birthdate, age, darken_until_date):
    """
    Draws the whole grid of 52x90 squares
    """
    num_rows = age

    # pos_x = SIDE_MARGIN / 4
    # pos_y = pos_x

    ctx.set_line_width(2)
    ctx.set_source_rgba(0, 0, 0, 1)  # Black color
    ctx.move_to(0, TOP_MARGIN)
    ctx.line_to(DOC_WIDTH, TOP_MARGIN)
    ctx.stroke()

    ctx.move_to(0, DOC_HEIGHT - MIN_BOTTOM_MARGIN)
    ctx.line_to(DOC_WIDTH, DOC_HEIGHT - MIN_BOTTOM_MARGIN)
    ctx.stroke()

    ctx.move_to(DOC_WIDTH - MIN_SIDE_MARGIN, 0)
    ctx.line_to(DOC_WIDTH - MIN_SIDE_MARGIN, DOC_HEIGHT)
    ctx.stroke()

    ctx.move_to(MIN_SIDE_MARGIN, 0)
    ctx.line_to(MIN_SIDE_MARGIN, DOC_HEIGHT)
    ctx.stroke()

    ctx.set_source_rgba(0, 0, 255, 1)  # Black color
    ctx.move_to(SIDE_MARGIN, 0)
    ctx.line_to(SIDE_MARGIN, DOC_HEIGHT)
    ctx.stroke()

    ctx.set_source_rgba(0, 0, 255, 1)  # Black color
    ctx.move_to(DOC_WIDTH - SIDE_MARGIN, 0)
    ctx.line_to(DOC_WIDTH - SIDE_MARGIN, DOC_HEIGHT)
    ctx.stroke()

    # width = BOX_BOUNDS * NUM_COLUMNS + X_GAPS * GAP_SIZE_RATIO * BOX_BOUNDS
    # ctx.set_source_rgba(255, 0, 255, 1)  # Black color
    # ctx.move_to(SIDE_MARGIN + BOX_BOUNDS * GRID_BOUNDS_X_RATIO, 0)
    # ctx.line_to(SIDE_MARGIN + BOX_BOUNDS * GRID_BOUNDS_X_RATIO, DOC_HEIGHT)
    # ctx.stroke()

    # # Draw the key for box colors
    # ctx.set_font_size(TINYFONT_SIZE)
    # ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)

    # pos_x = draw_key_item(ctx, pos_x, pos_y, KEY_BIRTHDAY_DESC, BOX_SIZE, BIRTHDAY_COLOR)
    # draw_key_item(ctx, pos_x, pos_y, KEY_NEWYEAR_DESC, BOX_SIZE, NEWYEAR_COLOR)

    # draw week numbers above top row
    ctx.set_source_rgb(0, 0, 0)
    ctx.set_font_size(TINYFONT_SIZE)
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)

    pos_x = SIDE_MARGIN
    pos_y = TOP_MARGIN

    # # Draw it above the current row
    # ctx.move_to(pos_x - w, pos_y + (h / 2))
    #     # X_MARGIN - w - BOX_SIZE,
    #     # pos_y - BOX_SIZE + ((BOX_SIZE / 2) + (h / 2)))

    for i in range(NUM_COLUMNS):
        if i == 0:
            text = birthdate.strftime("%A").lower() + "s"
        else:
            text = str(i + 1)
        w, h = text_size(ctx, text)
        if i == 0:
            ctx.move_to(pos_x, pos_y - BOX_SIZE)
            ctx.show_text(text)
            # pos_x += GAP_SIZE
        if i % 4 == 3:
            ctx.move_to(pos_x + (BOX_SIZE / 2) - (w / 2), pos_y - BOX_SIZE)
            ctx.show_text(text)
            pos_x += GAP_SIZE
        pos_x += BOX_SIZE + BOX_MARGIN

    ctx.set_font_size(TINYFONT_SIZE)
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)

    date = birthdate

    for i in range(num_rows):
        date = draw_row(ctx, pos_y, birthdate, date, BOX_SIZE, SIDE_MARGIN, darken_until_date)
        pos_y += BOX_SIZE + BOX_MARGIN
        if i % GAP_Y_INTERVAL == (GAP_Y_INTERVAL - 1):
            pos_y += GAP_SIZE


    # for i in range(num_rows):
    #     # Generate string for current date
    #     # ctx.set_source_rgb(0, 0, 0)
    #     # # date_str = date.strftime('%d %b, %Y')
    #     # date_str = format_date(date)
    #     # w, h = text_size(ctx, date_str)

    #     # # Draw it in front of the current row
    #     # ctx.move_to(SIDE_MARGIN - w - BOX_SIZE, pos_y + ((BOX_SIZE / 2) + (h / 2)))
    #     # ctx.show_text(date_str)

    #     # Draw the current row
    #     new_date = draw_row(ctx, pos_y, birthdate, date, BOX_SIZE, SIDE_MARGIN, darken_until_date)
    #     # calculate week diff between current date and new_date
    #     # if (date - birthdate).days // 7000 < (new_date - birthdate).days // 7000:
    #     #     # print(f"{(new_date - birthdate).days // 7000}k")

    #     #     ctx.set_source_rgb(0, 0, 0)
    #     #     date_str = f"{(new_date - birthdate).days // 7000}k"
    #     #     w1, h1 = text_size(ctx, date_str + "m")

    #     #     # Draw it in after of the current row
    #     #     ctx.move_to(pos_x, pos_y + ((BOX_SIZE / 2) + (h1 / 2)))
    #     #     ctx.show_text(date_str)

    #     # total_seconds = int((new_date - birthdate).total_seconds() // 1_000_000_000)
    #     # if (date - birthdate).total_seconds() // 1_000_000_000 < total_seconds:
    #     #     # print(f"{total_seconds}Gs")

    #     #     ctx.set_source_rgb(0, 0, 0)
    #     #     date_str = f"{total_seconds}Gs"
    #     #     _, h2 = text_size(ctx, date_str)

    #     #     # Draw it in after of the current row
    #     #     ctx.move_to(pos_x + w1, pos_y + ((BOX_SIZE / 2) + (h2 / 2)))
    #     #     ctx.show_text(date_str)
    #     # # Increment y position and current date by 1 row/year
    #     pos_y += BOX_SIZE + BOX_MARGIN
    #     if i % GAP_Y_INTERVAL == (GAP_Y_INTERVAL - 1):
    #         pos_y += GAP_SIZE
    #     date = new_date


def gen_calendar(
    birthdate, title, age, filename, darken_until_date, sidebar_text=None, subtitle_text=None
):
    # if len(title) > MAX_TITLE_SIZE:
    #     raise ValueError("Title can't be longer than %d characters" % MAX_TITLE_SIZE)

    age = int(age)
    if (age < MIN_AGE) or (age > MAX_AGE):
        raise ValueError("Invalid age, must be between %d and %d" % (MIN_AGE, MAX_AGE))

    # Fill background with white
    surface = cairo.PDFSurface(filename, DOC_WIDTH, DOC_HEIGHT)
    ctx = cairo.Context(surface)

    ctx.set_source_rgb(1, 1, 1)
    ctx.rectangle(0, 0, DOC_WIDTH, DOC_HEIGHT)
    ctx.fill()

    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_source_rgb(0, 0, 0)
    ctx.set_font_size(BIGFONT_SIZE)
    w, h = text_size(ctx, title)
    ctx.move_to((DOC_WIDTH / 2) - (w / 2), (TOP_MARGIN / 2) - (h / 2))
    ctx.show_text(title)

    if subtitle_text is not None:
        ctx.set_source_rgb(0.7, 0.7, 0.7)
        ctx.set_font_size(SMALLFONT_SIZE)
        w, h = text_size(ctx, subtitle_text)
        ctx.move_to((DOC_WIDTH / 2) - (w / 2), (TOP_MARGIN / 2) - (h / 2) + 15)
        ctx.show_text(subtitle_text)

    # date = back_up_to_monday(birthdate)

    # Draw 52x90 grid of squares
    draw_grid(ctx, birthdate, age, darken_until_date)

    if sidebar_text is not None:
        # Draw text on sidebar
        w, h = text_size(ctx, sidebar_text)
        ctx.move_to((DOC_WIDTH - SIDE_MARGIN) + 20, TOP_MARGIN + w + 100)
        ctx.set_font_size(SMALLFONT_SIZE)
        ctx.set_source_rgb(0.7, 0.7, 0.7)
        ctx.rotate(-90 * math.pi / 180)
        ctx.show_text(sidebar_text)

    ctx.show_page()


def main():
    parser = argparse.ArgumentParser(
        description='\nGenerate a personalized "Life '
        ' Calendar", inspired by the calendar with the same name from the '
        "waitbutwhy.com store"
    )

    parser.add_argument(
        type=parse_date,
        dest="date",
        help="starting date; your birthday,"
        "in either yyyy/mm/dd or dd/mm/yyyy format (dashes '-' may also be used in "
        "place of slashes '/')",
    )

    parser.add_argument(
        "-f", "--filename", type=str, dest="filename", help="output filename", default=DOC_NAME
    )

    parser.add_argument(
        "-t",
        "--title",
        type=str,
        dest="title",
        help='Calendar title text (default is "%s")' % DEFAULT_TITLE,
        default=DEFAULT_TITLE,
    )

    parser.add_argument(
        "-s",
        "--sidebar-text",
        type=str,
        dest="sidebar_text",
        help="Text to show along the right side of grid (default is no sidebar text)",
        default=None,
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
        metavar="[%s-%s]" % (MIN_AGE, MAX_AGE),
        help=("Number of rows to generate, representing years of life"),
        default=100,
    )

    parser.add_argument(
        "-d",
        "--darken-until",
        type=parse_darken_until_date,
        dest="darken_until_date",
        nargs="?",
        const="today",
        help="Darken until date. " "(defaults to today if argument is not given)",
    )

    args = parser.parse_args()
    doc_name = "%s.pdf" % (os.path.splitext(args.filename)[0])

    try:
        gen_calendar(
            args.date,
            args.title,
            args.age,
            doc_name,
            args.darken_until_date,
            sidebar_text=args.sidebar_text,
            subtitle_text=args.subtitle_text,
        )
    except Exception as e:
        print("Error: %s" % e)
        raise

    print("Created %s" % doc_name)


if __name__ == "__main__":
    main()
