# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pycairo",
# ]
# ///

# Forked from https://github.com/eriknyquist/generate_life_calendar

import argparse
import datetime
import math
from pathlib import Path

import cairo

DEFAULT_FONT: str = "EB Garamond SC"
DEFAULT_TITLE: str = "LIFE CALENDAR"
DEFAULT_FILENAME: str = "life_calendar.pdf"
DEFAULT_AGE: int = 100
DEFAULT_A_SIZE: int = 2


class LifeCalendar:
    MIN_AGE: int = 80
    MAX_AGE: int = 150
    NUM_COLUMNS: int = 52
    AZERO_HEIGHT: float = 2 ** (1 / 4)  # ≈ 1.189m
    AZERO_WIDTH: float = 1 / AZERO_HEIGHT  # ≈ 0.8409m
    MM_PER_PT: float = 0.3528

    def __init__(
        self,
        *,
        birthdate: datetime.date | str,
        darken_until_date: datetime.date | str | None = None,
        age: int | str | None = None,
        highlight_dates: list[datetime.date] | str | None = None,
        title: str | None = None,
        subtitle_text: str | None = None,
        filename: str | None = None,
        a_size: int | None = None,
    ) -> None:
        if isinstance(birthdate, str):
            birthdate = self.parse_date(birthdate)
        self.BIRTHDATE: datetime.date = birthdate
        if isinstance(darken_until_date, str):
            darken_until_date = self.parse_darken_until_date(darken_until_date)
        self.DARKEN_UNTIL_DATE: datetime.date | None = darken_until_date
        if isinstance(age, str):
            age = int(age)
        if age is not None and ((age < self.MIN_AGE) or (age > self.MAX_AGE)):
            raise ValueError(f"Invalid age, must be between {self.MIN_AGE} and {self.MAX_AGE}")
        if isinstance(highlight_dates, str):
            highlight_dates = self.parse_highlight_dates(highlight_dates)
        self.HIGHLIGHT_DATES: list[datetime.date] = highlight_dates or []
        self.NUM_ROWS: int = age or DEFAULT_AGE
        a_size = a_size or DEFAULT_A_SIZE
        # ≈ 841mm / 2383pt for A1 size
        self.DOC_HEIGHT: float = (
            self.AZERO_HEIGHT / (2 ** (1 / 2)) ** a_size * 1000 / self.MM_PER_PT
        )
        # ≈ 594mm / 1683pt for A1 size
        self.DOC_WIDTH: float = self.DOC_HEIGHT / 2 ** (1 / 2)
        self.TITLE: str = title or DEFAULT_TITLE
        self.FILENAME: str = filename or DEFAULT_FILENAME
        self.SUBTITLE_TEXT: str | None = subtitle_text

        self.SURFACE: cairo.PDFSurface = cairo.PDFSurface(
            self.FILENAME, self.DOC_WIDTH, self.DOC_HEIGHT
        )
        self.CTX: cairo.Context = cairo.Context(self.SURFACE)

        # Constants for layout (can be adjusted manually)
        self.FONT: str = DEFAULT_FONT  # from https://github.com/georgd/EB-Garamond
        self.BIGFONT_SIZE: float = self.DOC_HEIGHT / 30  # ≈ 80pt at A1 size
        self.SMALLFONT_SIZE: float = self.DOC_HEIGHT / 120  # ≈ 20pt at A1 size
        self.TINYFONT_SIZE: float = self.DOC_HEIGHT / 200  # ≈ 12pt at A1 size

        self.TOP_MARGIN: float = self.DOC_HEIGHT * 0.10
        min_bottom_margin: float = self.DOC_HEIGHT * 0.05
        min_side_margin: float = self.DOC_WIDTH * 0.10

        # Relative to BOX_BOUNDS / i.e. column width / i.e. row height
        box_margin_ratio: float = 35 / 100
        gap_size_ratio: float = 1 * box_margin_ratio
        box_line_width_ratio: float = 1 / 6 * (1 - box_margin_ratio)
        corner_radius_ratio: float = 1 / 5 * (1 - box_margin_ratio)

        self.GAP_X_INTERVAL: int = 4
        self.GAP_Y_INTERVAL: int = 10
        self.X_GAPS: int = (self.NUM_COLUMNS - 1) // self.GAP_X_INTERVAL
        self.Y_GAPS: int = (self.NUM_ROWS - 1) // self.GAP_Y_INTERVAL

        # number of box bounds in grid
        grid_bounds_x_ratio = self.NUM_COLUMNS - box_margin_ratio + self.X_GAPS * gap_size_ratio
        grid_bounds_y_ratio = self.NUM_ROWS - box_margin_ratio + self.Y_GAPS * gap_size_ratio
        max_box_bounds_x = (self.DOC_WIDTH - 2 * min_side_margin) / grid_bounds_x_ratio
        max_box_bounds_y = (
            self.DOC_HEIGHT - self.TOP_MARGIN - min_bottom_margin
        ) / grid_bounds_y_ratio
        self.BOX_BOUNDS = min(max_box_bounds_x, max_box_bounds_y)
        self.BOX_MARGIN = box_margin_ratio * self.BOX_BOUNDS
        self.BOX_SIZE = self.BOX_BOUNDS - self.BOX_MARGIN
        self.SIDE_MARGIN = (self.DOC_WIDTH - (self.BOX_BOUNDS * grid_bounds_x_ratio)) / 2

        self.CORNER_RADIUS = corner_radius_ratio * self.BOX_BOUNDS
        self.BOX_LINE_WIDTH = box_line_width_ratio * self.BOX_BOUNDS
        self.HEAVY_BOX_LINE_WIDTH = 2 * self.BOX_LINE_WIDTH
        self.GAP_SIZE = gap_size_ratio * self.BOX_BOUNDS

        self.BLACK = (0.2, 0.2, 0.2)
        self.WHITE = (1.0, 1.0, 1.0)
        self.LIGHT_GRAY = (0.7, 0.7, 0.7)
        self.DARK_GRAY = (0.5, 0.5, 0.5)

    @staticmethod
    def parse_date(datestr: str) -> datetime.date:
        formats = ["%Y/%m/%d", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]

        for form in formats:
            try:
                parsed: datetime.datetime = datetime.datetime.strptime(datestr.strip(), form)  # noqa: DTZ007
            except ValueError:
                continue
            else:
                return parsed.date()

        raise ValueError("Incorrect date format: must be DMY or YMD with / or -")

    @classmethod
    def parse_darken_until_date(cls, datestr: str) -> datetime.date:
        if datestr == "today":
            today: datetime.date = datetime.date.today()  # noqa: DTZ011
            return datetime.date(today.year, today.month, today.day)
        return cls.parse_date(datestr)

    @classmethod
    def parse_highlight_dates(cls, datestr: str) -> list[datetime.date]:
        return [cls.parse_date(date) for date in datestr.split(",")]

    @staticmethod
    def format_date(date: datetime.date) -> str:
        numerals = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
        return f"{date.strftime('%d')} {numerals[date.month - 1].lower()} {date.strftime('%Y')}"

    @staticmethod
    def is_current_week(
        now: datetime.date,
        *,
        day: int,
        month: int,
        year: int | None = None,
    ) -> bool:
        end = now + datetime.timedelta(weeks=1)
        years: list[int] = [now.year, now.year + 1] if year is None else [year]

        for year_try in years:
            try:
                date: datetime.date = datetime.date(year_try, month, day)
            except ValueError:
                if (month == 2) and (day == 29):  # noqa: PLR2004
                    # Handle edge case for birthday being on leap year day
                    date = datetime.date(year_try, month, day - 1)
                else:
                    raise
            if now <= date < end:
                return True

        return False

    @classmethod
    def is_special_week(cls, now: datetime.date, dates: list[datetime.date]) -> bool:
        return any(
            cls.is_current_week(now, day=date.day, month=date.month, year=date.year)
            for date in dates
        )

    def count_1000k_week(self, date: datetime.date) -> int:
        days_now: int = (date - self.BIRTHDATE).days
        if (days_now - 7) // 7000 < days_now // 7000:
            return days_now // 7000
        return 0

    def count_gigasec_week(self, date: datetime.date) -> int:
        seconds: float = (date - self.BIRTHDATE).total_seconds()
        if (
            seconds - datetime.timedelta(weeks=1).total_seconds()
        ) // 1_000_000_000 < seconds // 1_000_000_000:
            return int(seconds // 1_000_000_000)
        return 0

    def get_new_fill(self, fill: tuple[float, float, float]) -> tuple[float, float, float]:
        if fill == self.WHITE:
            return self.BLACK
        return fill

    def text_size(self, text: str) -> tuple[float, float]:
        _, _, width, height, _, _ = self.CTX.text_extents(text)
        return width, height

    def draw_square(
        self,
        pos_x: float,
        pos_y: float,
        fillcolor: tuple[float, float, float] | None = None,
        linewidth: float | None = None,
    ) -> None:
        """Draws rectangles with rounded (circular arc) corners."""
        if fillcolor is None:
            fillcolor = self.WHITE
        if linewidth is None:
            linewidth = self.BOX_LINE_WIDTH
        self.CTX.set_line_width(linewidth)
        self.CTX.set_source_rgb(*self.BLACK)
        self.CTX.move_to(pos_x, pos_y)

        x_1, x_2 = pos_x, pos_x + self.BOX_SIZE
        y_1, y_2 = pos_y, pos_y + self.BOX_SIZE

        # Define corner positions and corresponding arc start/end angles
        corners = [
            (x_1 + self.CORNER_RADIUS, y_1 + self.CORNER_RADIUS, 2, 3),  # Top-left
            (x_2 - self.CORNER_RADIUS, y_1 + self.CORNER_RADIUS, 3, 4),  # Top-right
            (x_2 - self.CORNER_RADIUS, y_2 - self.CORNER_RADIUS, 0, 1),  # Bottom-right
            (x_1 + self.CORNER_RADIUS, y_2 - self.CORNER_RADIUS, 1, 2),  # Bottom-left
        ]

        # Draw the square
        self.CTX.new_sub_path()
        for cx, cy, start, end in corners:
            self.CTX.arc(cx, cy, self.CORNER_RADIUS, start * (math.pi / 2), end * (math.pi / 2))
        self.CTX.close_path()
        self.CTX.stroke_preserve()

        # Fill the square
        self.CTX.set_source_rgb(*fillcolor)
        self.CTX.fill()

    def draw_row(self, pos_y: float, date: datetime.date) -> datetime.date:
        """Draws a row of 52 or 53 squares, starting at pos_y.

        Returns:
            datetime.date: The date of the next row's start
        """
        pos_x: float = self.SIDE_MARGIN
        week: int = 0
        row_tags: list[str] = []

        # Write the start date of the row
        self.CTX.set_font_size(self.TINYFONT_SIZE)
        self.CTX.select_font_face(self.FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        self.CTX.set_source_rgb(*self.DARK_GRAY)
        date_str: str = self.format_date(date)
        w, h = self.text_size(date_str)
        self.CTX.move_to(pos_x - w - self.BOX_SIZE, pos_y + self.BOX_SIZE / 2 + h / 2)
        self.CTX.show_text(date_str)

        # Loop until reaching the next birthday week
        while week == 0 or not self.is_current_week(
            date, day=self.BIRTHDATE.day, month=self.BIRTHDATE.month
        ):
            fill = self.WHITE
            width = self.BOX_LINE_WIDTH

            if self.is_special_week(date, dates=self.HIGHLIGHT_DATES):
                fill = self.LIGHT_GRAY
            if self.count_1000k_week(date):
                row_tags.append(f"{self.count_1000k_week(date)}k")
                width = self.HEAVY_BOX_LINE_WIDTH
            if self.count_gigasec_week(date):
                row_tags.append(f"{self.count_gigasec_week(date)}Gs")
                width = self.HEAVY_BOX_LINE_WIDTH
            if self.DARKEN_UNTIL_DATE and date < self.DARKEN_UNTIL_DATE:
                fill = self.get_new_fill(fill)

            self.draw_square(pos_x, pos_y, fillcolor=fill, linewidth=width)
            pos_x += self.BOX_SIZE + self.BOX_MARGIN
            if week % self.GAP_X_INTERVAL == self.GAP_X_INTERVAL - 1:
                pos_x += self.GAP_SIZE
            week += 1
            date += datetime.timedelta(weeks=1)

        # Add special tags to the row (xk weeks, xGs)
        for tag in row_tags:
            self.CTX.set_source_rgb(*self.DARK_GRAY)
            w, h = self.text_size(tag)
            self.CTX.move_to(pos_x, pos_y + ((self.BOX_SIZE + h) / 2))
            pos_x += w + self.GAP_SIZE
            self.CTX.show_text(tag)

        return date

    def draw_grid(self) -> None:
        """Draws the whole grid of 52x90 squares."""
        pos_x = self.SIDE_MARGIN
        pos_y = self.TOP_MARGIN

        # Draw week numbers above top row
        self.CTX.set_source_rgb(*self.DARK_GRAY)
        self.CTX.set_font_size(self.TINYFONT_SIZE)
        self.CTX.select_font_face(self.FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)

        for i in range(self.NUM_COLUMNS):
            if i == 0:
                text = self.BIRTHDATE.strftime("%A").lower() + "s"
                w, _ = self.text_size(text)
                self.CTX.move_to(pos_x, pos_y - self.BOX_SIZE)
                self.CTX.show_text(text)
                header_end_x = pos_x + w + self.BOX_MARGIN
            elif i % self.GAP_X_INTERVAL == (self.GAP_X_INTERVAL - 1):
                text = str(i + 1)
                w, _ = self.text_size(text)
                num_pos_x = pos_x + self.BOX_SIZE / 2 - w / 2
                if num_pos_x > header_end_x:
                    self.CTX.move_to(num_pos_x, pos_y - self.BOX_SIZE)
                    self.CTX.show_text(text)
                pos_x += self.GAP_SIZE
            pos_x += self.BOX_SIZE + self.BOX_MARGIN

        date = self.BIRTHDATE

        for i in range(self.NUM_ROWS):
            date = self.draw_row(pos_y, date)
            pos_y += self.BOX_SIZE + self.BOX_MARGIN
            if i % self.GAP_Y_INTERVAL == (self.GAP_Y_INTERVAL - 1):
                pos_y += self.GAP_SIZE

    def gen_calendar(self) -> None:
        # Fill background with white
        self.CTX.set_source_rgb(*self.WHITE)
        self.CTX.rectangle(0, 0, self.DOC_WIDTH, self.DOC_HEIGHT)
        self.CTX.fill()

        # Draw title
        self.CTX.select_font_face(self.FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        self.CTX.set_source_rgb(*self.BLACK)
        self.CTX.set_font_size(self.BIGFONT_SIZE)
        w_title, h_title = self.text_size(self.TITLE)
        self.CTX.move_to(self.DOC_WIDTH / 2 - w_title / 2, self.TOP_MARGIN / 2)
        self.CTX.show_text(self.TITLE)

        # Draw subtitle
        if self.SUBTITLE_TEXT is not None:
            self.CTX.set_source_rgb(*self.LIGHT_GRAY)
            self.CTX.set_font_size(self.SMALLFONT_SIZE)
            w, h = self.text_size(self.SUBTITLE_TEXT)
            self.CTX.move_to(self.DOC_WIDTH / 2 - w / 2, self.TOP_MARGIN / 2 + h_title - h / 2)
            self.CTX.show_text(self.SUBTITLE_TEXT)

        # Draw grid
        self.draw_grid()

        self.CTX.show_page()


def main() -> None:
    parser = argparse.ArgumentParser(
        description='\nGenerate a personalized "Life  Calendar", inspired by'
        " the calendar with the same name from the waitbutwhy.com store"
    )

    parser.add_argument(
        type=LifeCalendar.parse_date,
        dest="date",
        help="Starting date (your birthday), in either YMD or DMY format"
        " (dashes '-' may also be used in place of slashes '/')",
    )

    parser.add_argument(
        "-f",
        "--filename",
        type=str,
        dest="filename",
        help="Output filename (default is 'life_calendar.pdf')",
        default=DEFAULT_FILENAME,
    )

    parser.add_argument(
        "-s",
        "--a-size",
        type=int,
        dest="a_size",
        help=(
            "Output file size in ISO 216 A format (A0 is 0, A1 is 1, etc., default is"
            f" A{DEFAULT_A_SIZE})"
        ),
        default=DEFAULT_A_SIZE,
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
        choices=range(LifeCalendar.MIN_AGE, LifeCalendar.MAX_AGE + 1),
        metavar=f"[{LifeCalendar.MIN_AGE}-{LifeCalendar.MAX_AGE}]",
        help=(
            "Number of rows to generate, representing years of life (default is"
            f" {DEFAULT_AGE})"
        ),
        default=DEFAULT_AGE,
    )

    parser.add_argument(
        "-d",
        "--darken-until",
        type=str,
        dest="darken_until_date",
        nargs="?",
        const="today",
        help="Darken until date (defaults to today if argument is not given)",
    )

    parser.add_argument(
        "-x",
        "--highlight-dates",
        type=LifeCalendar.parse_highlight_dates,
        dest="highlight_dates",
        help="Comma-separated list of dates to highlight (defaults to none)",
        default=None,
    )

    args: argparse.Namespace = parser.parse_args()

    # Handle filename extension
    file_path = Path(args.filename)
    if file_path.suffix:
        # User specified an extension
        if file_path.suffix.lower() != ".pdf":
            print(
                f"Warning: Replacing '{file_path.suffix}' extension with '.pdf'"
                " (cairo only supports PDF output)"
            )
            filename: str = f"{file_path.stem}.pdf"
        else:
            filename: str = args.filename
    else:
        # No extension specified, add .pdf
        filename: str = f"{args.filename}.pdf"

    try:
        LifeCalendar(
            birthdate=args.date,
            darken_until_date=args.darken_until_date,
            age=args.age,
            highlight_dates=args.highlight_dates,
            title=args.title,
            subtitle_text=args.subtitle_text,
            filename=filename,
            a_size=args.a_size,
        ).gen_calendar()

    except Exception as e:
        print(f"Error: {e}")
        raise

    print(f"Created {filename}")


if __name__ == "__main__":
    main()
