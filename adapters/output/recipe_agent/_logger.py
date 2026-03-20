from loguru import logger as _loguru

_EMOJI = {"DEBUG": "🔬", "INFO": "💬", "WARNING": "⚠️", "ERROR": "❌", "CRITICAL": "🔥"}


class _AdapterLogger:
    """Thin loguru wrapper that pre-binds the extras expected by ConsoleLogger's format."""

    def debug(self, msg: str) -> None:
        _loguru.bind(level_emoji = _EMOJI["DEBUG"], meta = {}).debug(msg)

    def info(self, msg: str) -> None:
        _loguru.bind(level_emoji = _EMOJI["INFO"], meta = {}).info(msg)

    def warning(self, msg: str) -> None:
        _loguru.bind(level_emoji = _EMOJI["WARNING"], meta = {}).warning(msg)

    def error(self, msg: str) -> None:
        _loguru.bind(level_emoji = _EMOJI["ERROR"], meta = {}).error(msg)


log = _AdapterLogger()
