#!/usr/bin/env python3
import sys
import import_helpor  # noqa NEEDED!!!
from executin.logge import TestLoggor, Loggor


class LoggeTestor:
    def __init__(self):
        super().__init__()
        # self.loggor = TestLoggor()
        self.loggor = Loggor(name='LoggeTestor')
        self.loggor.clean_logs()

    def executize(self):
        print("Testor.executize...")
        self.loggor.info('info')
        self.loggor.debug('debug')
        self.loggor.warning('warning')
        self.loggor.error('error')
        self.loggor.critical('critical')
        self.loggor.fatal('fatal')
        self.loggor.remark('remark')
        self.loggor.exclaim('exclaim')


def main():
    executor = LoggeTestor()
    executor.executize()


if __name__ == '__main__':
    main()
