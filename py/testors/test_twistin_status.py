#!/usr/bin/env python3

from pathlib import Path

import import_helpor  # noqa NEEDED!!!
from executin.logge import Loggor
from testors.twistees.status_twistee import StatusTwistee
from twistin.twistee import Twistee
from twistin.twistor import Twistor


class TwistinStatusTestor:
    def __init__(self):
        super().__init__()
        dev_log_dir = Path('/opt/projects/deluge_source_project/log')
        if dev_log_dir.is_dir():
            Loggor.set_log_dir(dev_log_dir)
        Loggor.clean_logs()
        self.loggor = Loggor(klass=self.__class__)

    def executize(self):
        self.loggor.exclaim('executize')
        twistee: Twistee = StatusTwistee()
        twistor = Twistor(twistee)
        twistor.executize()


def main():
    executor = TwistinStatusTestor()
    executor.executize()


if __name__ == '__main__':
    main()
