import logging

from infrastructure.logging_setup import _InterceptHandler, setup_logging


def test_setup_logging_returns_console_logger():
    from arclith.adapters.output.console.logger import ConsoleLogger
    result = setup_logging()
    assert isinstance(result, ConsoleLogger)


def test_setup_logging_installs_intercept_handler():
    setup_logging()
    root = logging.getLogger()
    assert any(isinstance(h, _InterceptHandler) for h in root.handlers)


def test_intercept_handler_emit_known_level():
    handler = _InterceptHandler()
    record = logging.LogRecord(
        name="test", level=logging.WARNING, pathname="", lineno=0,
        msg="hello from test", args=(), exc_info=None,
    )
    handler.emit(record)


