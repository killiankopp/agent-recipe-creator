import logging
from types import FrameType

from loguru import logger as _loguru

from arclith.adapters.output.console.logger import ConsoleLogger

_EMOJI = {"DEBUG": "🔬", "INFO": "💬", "WARNING": "⚠️", "ERROR": "❌", "CRITICAL": "🔥"}


class _InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = _loguru.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)
        frame: FrameType | None = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        _loguru.bind(
            level_emoji = _EMOJI.get(record.levelname, "💬"),
            meta = {"logger": record.name},
        ).opt(depth = depth, exception = record.exc_info).log(level, record.getMessage())


def setup_logging() -> ConsoleLogger:
    logging.basicConfig(handlers = [_InterceptHandler()], level = logging.DEBUG, force = True)
    return ConsoleLogger()
