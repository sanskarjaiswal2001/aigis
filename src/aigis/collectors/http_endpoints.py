"""HTTP endpoint health check collector."""

import time
import urllib.request
import urllib.error

from aigis.config import AppConfig
from aigis.schemas.signals import CollectorRun, HttpEndpointSignal


class HttpEndpointsCollector:
    """Check HTTP endpoint availability and latency."""

    collector_id = "http_endpoints"

    def collect(self, config: AppConfig, runner) -> CollectorRun:
        endpoints = config.collectors.http_endpoints.endpoints
        if not endpoints:
            return CollectorRun(
                collector_id=self.collector_id,
                success=True,
                signals=[],
            )

        timeout = config.collectors.http_endpoints.timeout_sec
        signals: list[HttpEndpointSignal] = []

        for url in endpoints:
            signals.append(self._check_endpoint(url, timeout))

        return CollectorRun(
            collector_id=self.collector_id,
            success=True,
            signals=signals,
        )

    def _check_endpoint(self, url: str, timeout: int) -> HttpEndpointSignal:
        try:
            start = time.perf_counter()
            req = urllib.request.Request(url, method="GET")
            req.add_header("User-Agent", "aigis-monitor/0.1")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                latency = (time.perf_counter() - start) * 1000
                return HttpEndpointSignal(
                    url=url,
                    status_code=resp.status,
                    latency_ms=round(latency, 1),
                    up=200 <= resp.status < 400,
                )
        except urllib.error.HTTPError as exc:
            latency = (time.perf_counter() - start) * 1000
            return HttpEndpointSignal(
                url=url,
                status_code=exc.code,
                latency_ms=round(latency, 1),
                up=False,
                error=str(exc.reason),
            )
        except Exception as exc:
            return HttpEndpointSignal(
                url=url,
                up=False,
                error=str(exc),
            )
