#!/usr/bin/env python3
import import_helpor  # noqa NEEDED!!!
from executin.torrenthandlor import media_dir_name


class Testor:
    cases: list[tuple[str, int | str | None, str]] = [
        ('The Florist', 2026, 'the.florist.2026'),
        ('Amélie', 2001, 'amelie.2001'),
        ('WALL·E', 2008, 'wall.e.2008'),
        ('M3GAN 2.0', 2025, 'm3gan.2.0.2025'),
        ('Se7en', 1995, 'se7en.1995'),
        ('Nope', None, 'nope'),
        ('The Florist', None, 'the.florist'),
        ('...', 2024, ''),
        ('東京物語', 1953, ''),
        (' The Florist ', 2026, 'the.florist.2026'),
        ('The Florist', '2024', 'the.florist'),
        ('Ørkenens Sønner', 1959, 'oerkenens.soenner.1959'),
        ('Blåbærgrød', 2020, 'blaabaergroed.2020'),
        ('Åge', 1951, 'aage.1951'),
        ('Straße', 1999, 'strasse.1999'),
    ]

    def __init__(self):
        super().__init__()

    def executize(self):
        print("Testor.executize...")
        all_as_expected = True
        for media_title, media_year, expected in self.cases:
            dir_name = media_dir_name(media_title, media_year)  # noqa
            is_as_expected = dir_name == expected
            all_as_expected = all_as_expected and is_as_expected
            print(f"{media_title!r:<18} {media_year!r:<7} -> {dir_name!r:<20} expected {expected!r:<20} {is_as_expected}")
        print(f"all as expected: {all_as_expected}")


def main():
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()
