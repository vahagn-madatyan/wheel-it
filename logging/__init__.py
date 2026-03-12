# This package shadows Python's stdlib logging module.
# Re-export stdlib logging so third-party libraries (pytest, etc.) work correctly.
import importlib.util as _ilu
import sys as _sys
import os as _os

# Find the stdlib logging module by looking in the standard library path
_stdlib_path = _os.path.join(
    _os.path.dirname(_os.__file__), "logging", "__init__.py"
)
_spec = _ilu.spec_from_file_location(
    "stdlib_logging", _stdlib_path,
    submodule_search_locations=[_os.path.dirname(_stdlib_path)]
)
_stdlib = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_stdlib)

# Re-export everything from stdlib logging into this namespace
for _name in dir(_stdlib):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_stdlib, _name)

# Also ensure key items are available
_stdlib_logging = _stdlib
