"""Lightweight process package.

This package provides lightweight process implementations that use mutual
exclusion algorithms to coordinate access to critical sections.
"""

from .lightweight_process import LightweightProcess
from .lightweight_a import LightweightProcessA
from .lightweight_b import LightweightProcessB

__all__ = [
    'LightweightProcess',
    'LightweightProcessA',
    'LightweightProcessB'
]