import sys
from enum import Enum
from logging import Logger, NOTSET, DEBUG, _levelToName, _nameToLevel
from logging import FileHandler, StreamHandler, Formatter
from pathlib import Path

from .commons import Commons


class ColorNameEnum(Enum):
    RESET = '0'
    BLACK = '30'
    RED = '31'
    GREEN = '32'
    YELLOW = '33'
    BLUE = '34'
    MAGENTA = '35'
    CYAN = '36'
    WHITE = '37'
    GRAY = '90'

    HEAVY_RED = '1;4;31'
    BOLD_GRAY = '1;90'
    BOLD_CYAN = '1;36'

    @classmethod
    def coded(cls, name: str) -> str:
        color = cls.__members__.get(name.upper(), cls.RESET)
        return f'\033[{color.value}m'


class CustomFormatter(Formatter):
    # base_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    base_format = '%(asctime)s - %(name)s - %(levelname)s | %(message)s'

    def __init__(self, fmt=None, datefmt=None, style="%", validate=True, *, defaults=None):
        super().__init__(fmt=fmt or self.base_format, datefmt=datefmt, style=style, validate=validate,
                         defaults=defaults)

    @staticmethod
    def fixed_levelname(record):
        txt = record.levelname
        # fixed_txt = f'{txt:<6.6}'
        # fixed_txt = txt
        fixed_txt = f'{txt:<9}'

        return fixed_txt

    def format(self, record):
        formatted = super().format(record)
        fixed_levelname = self.fixed_levelname(record)
        formatted = formatted.replace(record.levelname, fixed_levelname, 1)
        formatted = self.further_format(formatted, fixed_levelname, record)
        return formatted

    def further_format(self, formatted, fixed_levelname, record):
        return formatted


class ColorFormatter(CustomFormatter):
    REMARK = 25
    _levelToName[REMARK] = 'REMARK'
    _nameToLevel['REMARK'] = REMARK
    EXCLAIM = 26
    _levelToName[EXCLAIM] = 'EXCLAIM'
    _nameToLevel['EXCLAIM'] = EXCLAIM

    COLORS = {
        'DEBUG': ColorNameEnum.coded('GRAY'),
        'INFO': ColorNameEnum.coded('GREEN'),
        'WARNING': ColorNameEnum.coded('YELLOW'),
        'ERROR': ColorNameEnum.coded('RED'),
        'CRITICAL': ColorNameEnum.coded('HEAVY_RED'),
        'REMARK': ColorNameEnum.coded('MAGENTA'),
        'EXCLAIM': ColorNameEnum.coded('BOLD_CYAN'),
    }

    RESET = ColorNameEnum.coded('RESET')

    def __init__(self):
        # super().__init__('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        gray_code = ColorNameEnum.coded('BOLD_GRAY')
        # fmt = f'{gray_code}%(asctime)s - %(name)s - %(levelname)s - %(message)s{self.RESET}'
        fmt = f'{gray_code}{self.base_format}{self.RESET}'
        # super().__init__(f'{gray_code}%(asctime)s - %(name)s - %(levelname)s - %(message)s{self.RESET}')
        super().__init__(fmt=fmt)

    def further_format(self, formatted, fixed_levelname, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        further_txt = formatted.replace(
            fixed_levelname, f'{log_color}{fixed_levelname}', 1
        )
        return further_txt


class Loggor(Logger):
    moniker = 'loggor'
    do_colorfile: bool = True
    log_dir = Commons.singleton.deluge_root_dir / 'log'
    color_log_dir = log_dir / 'colorlog'

    @classmethod
    def set_log_dir(cls, log_dir: str | Path):
        cls.log_dir = Path(log_dir)
        cls.log_dir.mkdir(parents=True, exist_ok=True)
        cls.color_log_dir = cls.log_dir / 'colorlog'

    def __init__(self, name: str = '', level: int = DEBUG, klass: type = None):
        if klass and not name:
            name = klass.__name__
        name = name or self.moniker
        super().__init__(name, level=level)
        # log to both file and console
        # formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        normal_formatter = CustomFormatter()
        color_formatter = ColorFormatter()

        file_handler = None
        color_file_handler = None
        if self.log_dir.is_dir():
            self.log_file = self.log_dir / f'{self.name}.log'
            file_handler = FileHandler(self.log_file)
            file_handler.setLevel(level)
            file_handler.setFormatter(normal_formatter)

            if self.do_colorfile:
                self.color_log_dir.mkdir(parents=True, exist_ok=True)
                color_log_file = self.color_log_dir / f'{self.name}.color.log'
                color_file_handler = FileHandler(color_log_file)
                color_file_handler.setLevel(level)
                color_file_handler.setFormatter(color_formatter)
        else:
            self.warning(f"Log directory '{self.log_dir}' does not exist. File logging disabled.")

        # color_formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler = StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(color_formatter)

        if not self.hasHandlers():
            self.addHandler(console_handler)
            if file_handler:
                self.addHandler(file_handler)
            if color_file_handler:
                self.addHandler(color_file_handler)

        # self.info(f"Loggor '{self.moniker}' initialized with level {DEBUG} and log file '{self.log_file}'")

    def remark(self, msg, *args, **kwargs):
        self.log(ColorFormatter.REMARK, msg, *args, **kwargs)

    def exclaim(self, msg, *args, **kwargs):
        self.log(ColorFormatter.EXCLAIM, msg, *args, **kwargs)

    @classmethod
    def clean_logs(cls):
        log_files = cls.log_dir.rglob('*.log')
        for log_file in log_files:
            # print(f' - {log_file}')
            log_file.write_text('CLEANSED\n')


class TorrentHandlorLoggor(Loggor):
    def __init__(self):
        self.moniker = 'torrenthandlor'
        super().__init__(self.moniker, level=DEBUG)


class DelugapiClientLoggor(Loggor):
    def __init__(self):
        self.moniker = 'delugapiclient'
        super().__init__(self.moniker, level=DEBUG)


class DelugapiTorrentorLoggor(Loggor):
    def __init__(self):
        self.moniker = 'torrentor'
        super().__init__(self.moniker, level=DEBUG)


class ExecutorLoggor(Loggor):
    def __init__(self):
        self.moniker = 'executor'
        super().__init__(self.moniker, level=DEBUG)


class StatusorLoggor(Loggor):
    moniker = 'statusor'

    # def __init__(self):
    #     self.moniker = 'statusor'
    #     super().__init__(self.moniker, level=DEBUG)


class TestLoggor(Loggor):
    moniker = 'testloggor'
