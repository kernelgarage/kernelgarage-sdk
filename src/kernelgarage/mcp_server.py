"""MCP server exposing a usage-report tool over the Pi's Prometheus stack.

Answers "how was usage last day" by querying the same Prometheus instance
`grafana-hardware-monitoring` and `agent-monitor` already write to — hardware
metrics (`rpi_*`) and LLM/queue metrics (`llm_*`) — and folding both into one
plain-text report. Runs over stdio, so any MCP-capable client (Claude Desktop,
an agent framework) can call it as a tool without a network port to manage.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import httpx
from mcp.server.mcpserver import MCPServer

__all__ = ["UsageReport", "build_usage_report", "mcp"]


def _prometheus_url() -> str:
    try:
        return os.environ["PROMETHEUS_URL"]
    except KeyError as exc:
        raise RuntimeError("PROMETHEUS_URL is not set — see .env.example") from exc


# A stalled mDNS lookup for an unreachable .local host can hang far longer than
# any bare numeric httpx timeout suggests — an explicit Timeout object bounds it
# reliably (see get_pi_stats in the voice-interface episode for the same fix).
_TIMEOUT = httpx.Timeout(connect=1.5, read=5.0, write=5.0, pool=5.0)

# Bit meanings per Raspberry Pi's documented `vcgencmd get_throttled` bitmask,
# as exposed (already decimal, not hex) by rpi_exporter.sh's `rpi_throttled_state`.
_THROTTLE_LABELS = {
    0: "under-voltage detected",
    1: "arm frequency capped",
    2: "currently throttled",
    3: "soft temperature limit active",
    16: "under-voltage has occurred",
    17: "arm frequency capping has occurred",
    18: "throttling has occurred",
    19: "soft temperature limit has occurred",
}


def _decode_throttled(value: int) -> tuple[str, ...]:
    return tuple(label for bit, label in _THROTTLE_LABELS.items() if value & (1 << bit))


def _query(client: httpx.Client, promql: str) -> float | None:
    response = client.get(f"{_prometheus_url()}/api/v1/query", params={"query": promql})
    response.raise_for_status()
    result = response.json()["data"]["result"]
    if not result:
        return None
    return float(result[0]["value"][1])


@dataclass(frozen=True)
class UsageReport:
    """A usage summary for the trailing window ending now."""

    hours: int
    avg_temp_c: float | None
    max_temp_c: float | None
    throttle_events: tuple[str, ...]
    total_requests: int
    prompt_tokens: int
    completion_tokens: int
    peak_queue_depth: int
    avg_duration_s: float | None
    avg_queue_wait_s: float | None

    def render(self) -> str:
        lines = [f"Usage report — last {self.hours}h"]

        if self.avg_temp_c is None:
            lines.append("Hardware: no data (Prometheus unreachable or no scrapes yet)")
        else:
            lines.append(
                f"Hardware: avg {self.avg_temp_c:.1f}°C, peak {self.max_temp_c:.1f}°C"
            )
        lines.append("Throttling: " + (", ".join(self.throttle_events) or "none"))

        lines.append(
            f"LLM requests: {self.total_requests} "
            f"({self.prompt_tokens} prompt tokens, "
            f"{self.completion_tokens} completion tokens)"
        )
        lines.append(f"Peak queue depth: {self.peak_queue_depth}")
        if self.avg_duration_s is not None:
            lines.append(f"Avg request duration: {self.avg_duration_s:.2f}s")
        if self.avg_queue_wait_s is not None:
            lines.append(f"Avg queue wait: {self.avg_queue_wait_s:.2f}s")

        return "\n".join(lines)


def build_usage_report(hours: int = 24) -> UsageReport:
    """Query Prometheus for the trailing `hours` and summarize hardware + LLM usage."""
    window = f"{hours}h"
    queries = {
        "avg_temp_c": f"avg_over_time(rpi_cpu_temperature_celsius[{window}])",
        "max_temp_c": f"max_over_time(rpi_cpu_temperature_celsius[{window}])",
        "throttled_raw": "rpi_throttled_state",
        "total_requests": f"sum(increase(llm_requests_total[{window}]))",
        "prompt_tokens": f"sum(increase(llm_tokens_prompt_total[{window}]))",
        "completion_tokens": f"sum(increase(llm_tokens_completion_total[{window}]))",
        "peak_queue_depth": f"max_over_time(llm_requests_waiting[{window}])",
        "duration_sum": f"sum(increase(llm_request_duration_seconds_sum[{window}]))",
        "duration_count": (
            f"sum(increase(llm_request_duration_seconds_count[{window}]))"
        ),
        "wait_sum": f"sum(increase(llm_queue_wait_seconds_sum[{window}]))",
        "wait_count": f"sum(increase(llm_queue_wait_seconds_count[{window}]))",
    }

    with (
        httpx.Client(timeout=_TIMEOUT) as client,
        ThreadPoolExecutor(max_workers=len(queries)) as pool,
    ):
        results = dict(
            zip(
                queries,
                pool.map(lambda promql: _query(client, promql), queries.values()),
                strict=True,
            )
        )

    throttled_raw = results["throttled_raw"]
    throttle_events = (
        _decode_throttled(int(throttled_raw)) if throttled_raw is not None else ()
    )

    duration_sum, duration_count = results["duration_sum"], results["duration_count"]
    avg_duration_s = (
        duration_sum / duration_count
        if duration_sum is not None and duration_count
        else None
    )

    wait_sum, wait_count = results["wait_sum"], results["wait_count"]
    avg_queue_wait_s = (
        wait_sum / wait_count if wait_sum is not None and wait_count else None
    )

    return UsageReport(
        hours=hours,
        avg_temp_c=results["avg_temp_c"],
        max_temp_c=results["max_temp_c"],
        throttle_events=throttle_events,
        total_requests=int(results["total_requests"] or 0),
        prompt_tokens=int(results["prompt_tokens"] or 0),
        completion_tokens=int(results["completion_tokens"] or 0),
        peak_queue_depth=int(results["peak_queue_depth"] or 0),
        avg_duration_s=avg_duration_s,
        avg_queue_wait_s=avg_queue_wait_s,
    )


mcp = MCPServer("kernelgarage")


@mcp.tool()
def get_usage_report(hours: int = 24) -> str:
    """Report hardware and LLM usage for the trailing `hours` (default 24)."""
    return build_usage_report(hours=hours).render()


def main() -> None:
    """Entry point for the `kernelgarage-mcp` console script — runs over stdio."""
    mcp.run()
