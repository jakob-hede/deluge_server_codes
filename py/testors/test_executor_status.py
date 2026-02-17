#!/usr/bin/env python3
import sys
import import_helpor  # noqa NEEDED!!!
from runs.executor import main as executor_main


class Testor:
    def __init__(self):
        super().__init__()

    def executize(self):
        print("Testor.executize...")

        sys.argv.append('exe_status')
        executor_main()


def main():
    executor = Testor()
    executor.executize()


if __name__ == '__main__':
    main()
