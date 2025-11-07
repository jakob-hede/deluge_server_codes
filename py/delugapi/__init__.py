"""
DelugAPI - A clean Python API for Deluge BitTorrent daemon.

This module provides object-oriented access to Deluge daemon functionality
through the native RPC protocol.
"""

from .delugapi import DelugApi  # type: ignore
from .delugapi_client import DelugapiClient  # type: ignore

# from delugapi.delugapi import DelugApi
# x = DelugApi

__all__ = ['DelugApi', 'DelugapiClient']
__version__ = '0.1.0'
