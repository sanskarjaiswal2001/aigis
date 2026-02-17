"""Data collectors (Strategy pattern)."""

from aigis.collectors.base import CollectorProtocol, run_collectors
from aigis.collectors.disk import DiskCollector
from aigis.collectors.docker import DockerCollector
from aigis.collectors.load import LoadCollector
from aigis.collectors.network import NetworkCollector
from aigis.collectors.restic import ResticCollector

__all__ = [
    "CollectorProtocol",
    "DiskCollector",
    "DockerCollector",
    "LoadCollector",
    "NetworkCollector",
    "ResticCollector",
    "run_collectors",
]
