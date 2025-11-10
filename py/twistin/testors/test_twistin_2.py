#!/usr/bin/env python3

from pathlib import Path

import import_helpor  # noqa NEEDED!!!
from executin.logge import Loggor
from twistin import TwistResponse
from twistin.twistees.example_twistee_2 import TwisteeExample2
from twistin.twistee import Twistee
from twistin.twistor import Twistor


class TwistinTestor:
    def __init__(self):
        super().__init__()
        dev_log_dir = Path('/opt/projects/deluge_source_project/learning/log')
        if dev_log_dir.is_dir():
            Loggor.set_log_dir('/opt/projects/deluge_source_project/learning/log')
        Loggor.clean_logs()
        self.loggor = Loggor(klass=self.__class__)

    def executize(self):
        self.loggor.exclaim('executize')
        twistee: Twistee = TwisteeExample2()
        twistor = Twistor(twistee)
        response: TwistResponse = twistor.executize()
        print(f'Final Response: {response.result}')
        self.loggor.debug(f'Final Response: {response}')


def main():
    executor = TwistinTestor()
    executor.executize()


if __name__ == '__main__':
    main()
