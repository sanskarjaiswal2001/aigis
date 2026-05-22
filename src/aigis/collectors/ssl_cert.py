"""SSL certificate expiry collector."""

import socket
import ssl
from datetime import datetime, timezone

from aigis.config import AppConfig
from aigis.schemas.signals import CollectorRun, SslCertSignal


class SslCertCollector:
    """Check SSL certificate expiry for configured domains."""

    collector_id = "ssl_cert"

    def collect(self, config: AppConfig, runner) -> CollectorRun:
        domains = config.collectors.ssl_cert.domains
        if not domains:
            return CollectorRun(
                collector_id=self.collector_id,
                success=True,
                signals=[],
            )

        timeout = config.collectors.ssl_cert.timeout_sec
        signals: list[SslCertSignal] = []

        for domain in domains:
            signals.append(self._check_domain(domain, timeout))

        return CollectorRun(
            collector_id=self.collector_id,
            success=True,
            signals=signals,
        )

    def _check_domain(self, domain: str, timeout: int) -> SslCertSignal:
        port = 443
        # Support domain:port syntax
        if ":" in domain:
            parts = domain.rsplit(":", 1)
            domain = parts[0]
            try:
                port = int(parts[1])
            except ValueError:
                pass

        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((domain, port), timeout=timeout) as sock:
                with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()

            if not cert:
                return SslCertSignal(
                    domain=domain,
                    port=port,
                    valid=False,
                    error="No certificate returned",
                )

            not_after_str = cert.get("notAfter", "")
            not_after = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z").replace(
                tzinfo=timezone.utc
            )
            now = datetime.now(tz=timezone.utc)
            days_remaining = (not_after - now).total_seconds() / 86400

            # Extract issuer and subject
            issuer = _extract_cn(cert.get("issuer", ()))
            subject = _extract_cn(cert.get("subject", ()))

            return SslCertSignal(
                domain=domain,
                port=port,
                issuer=issuer,
                subject=subject,
                not_after=not_after,
                days_remaining=round(days_remaining, 1),
                valid=days_remaining > 0,
            )
        except ssl.SSLCertVerificationError as exc:
            return SslCertSignal(
                domain=domain,
                port=port,
                valid=False,
                error=f"Certificate verification failed: {exc.verify_message}",
            )
        except Exception as exc:
            return SslCertSignal(
                domain=domain,
                port=port,
                valid=False,
                error=str(exc),
            )


def _extract_cn(rdns: tuple) -> str:
    """Extract Common Name from certificate RDN sequence."""
    for rdn in rdns:
        for attr_type, attr_value in rdn:
            if attr_type == "commonName":
                return attr_value
    return ""
