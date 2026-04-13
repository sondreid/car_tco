"""
car_reliability — modular TCO and reliability analysis for used cars.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("car_reliability")
except PackageNotFoundError:
    __version__ = "0.0.0"
