#!/usr/bin/env python3
import sys
import import_helpor  # noqa NEEDED!!!
from executin.logge import TestLoggor, Loggor
from twistin.twistor import Twistor, Twistor2


class TwistinTestor:
    def __init__(self):
        super().__init__()
        Loggor.set_log_dir('/opt/projects/deluge_source_project/learning/log')
        Loggor.clean_logs()
        self.loggor = Loggor(klass=self.__class__)

    def executize(self):
        self.loggor.exclaim('executize')
        twistor = Twistor2()
        twistor.executize()


def main():
    executor = TwistinTestor()
    executor.executize()


if __name__ == '__main__':
    main()
