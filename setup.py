"""Compatibility shim for tools that still invoke ``setup.py``.

Project metadata lives in ``pyproject.toml``. Modern installers use the PEP 517
build backend directly; this file exists so older tooling and editable installs
continue to work.
"""

from setuptools import setup


setup()
