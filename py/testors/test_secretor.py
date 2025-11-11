#!/usr/bin/env python3
import import_helpor  # noqa NEEDED!!!
from salaisuudet.secrets import Secretor
from executin.logge import Loggor


class SecretsTestor:
    def __init__(self):
        super().__init__()
        # Loggor.set_log_dir('/opt/projects/deluge_source_project/learning/log')
        Loggor.clean_logs()
        self.loggor = Loggor(klass=self.__class__)

    def executize(self):
        self.loggor.exclaim('executize')
        # secretor = Secretor()
        mediator = Secretor.mediator
        self.loggor.info(f'mediator: {mediator}')



def main():
    executor = SecretsTestor()
    executor.executize()


if __name__ == '__main__':
    main()
