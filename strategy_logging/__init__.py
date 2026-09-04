"""Runtime and strategy logging helpers.

Named `strategy_logging` so `import logging` always resolves to Python's
standard library. A previous top-level `logging/` package shadowed stdlib
and broke every pip/pipx install: `from logging.logger_setup` looked for a
stdlib submodule that does not exist.
"""
