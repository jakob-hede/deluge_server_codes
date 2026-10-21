#!/usr/bin/env python3
import import_helpor  # noqa NEEDED!!!
from executin.torrentor import move_cap_rounds


class Testor:
    def __init__(self):
        super().__init__()

    def executize(self):
        print("Testor.executize...")
        gib = 1024 * 1024 * 1024
        # (case, total_wanted, expected rounds)
        cases = [
            ('nothing wanted', 0, 300),
            ('the florist', 1943522380, 300),
            ('23 GiB', 23 * gib, 1177),
            ('200 GiB', 200 * gib, 3600),
        ]
        all_as_expected = True
        for case_name, total_wanted, expected in cases:
            rounds = move_cap_rounds(total_wanted)
            is_as_expected = rounds == expected
            all_as_expected = all_as_expected and is_as_expected
            print(f"{case_name}: move_cap_rounds({total_wanted}) = {rounds}  expected {expected}  {is_as_expected}")
        print(f"all as expected: {all_as_expected}")


def main():
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()
