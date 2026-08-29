"""MCP server exposing a usage-report tool over the Pi's Prometheus stack.

Answers "how was usage last day" by querying the same Prometheus instance
`grafana-hardware-monitoring` and `agent-monitor` already write to — hardware
metrics (`rpi_*`) and LLM/queue metrics (`llm_*`) — and folding both into one
report, either as plain text or a self-contained HTML page. Runs over stdio,
so any MCP-capable client (Claude Desktop, an agent framework) can call it as
a tool without a network port to manage.
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

    def render_html(self) -> str:
        """Render as a self-contained instrument-panel page — system fonts only,
        no network requests, so it still renders on a Pi with no internet."""
        healthy = not self.throttle_events
        badge_class = "healthy" if healthy else "warn"
        badge_text = "healthy" if healthy else ", ".join(self.throttle_events)

        plural = "" if self.total_requests == 1 else "s"
        health_phrase = "all healthy" if healthy else badge_text
        summary = (
            f"{self.total_requests} request{plural} over the last {self.hours}h "
            f'&mdash; <span class="muted">{health_phrase}</span>.'
        )

        if self.avg_temp_c is None:
            hardware_cards = """
      <div class="card span-2">
        <div class="label">Temperature</div>
        <div class="value muted">no data</div>
        <div class="hint">Prometheus unreachable, or no rpi_exporter scrapes yet</div>
      </div>"""
        else:
            hardware_cards = f"""
      <div class="card">
        <div class="label">Avg temp</div>
        <div class="value mono">{self.avg_temp_c:.1f}<span class="unit">°C</span></div>
      </div>
      <div class="card">
        <div class="label">Peak temp</div>
        <div class="value mono">{self.max_temp_c:.1f}<span class="unit">°C</span></div>
      </div>"""

        duration_value = (
            f'{self.avg_duration_s:.2f}<span class="unit">s</span>'
            if self.avg_duration_s is not None
            else "—"
        )
        wait_value = (
            f'{self.avg_queue_wait_s:.2f}<span class="unit">s</span>'
            if self.avg_queue_wait_s is not None
            else "—"
        )

        return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>kernelgarage usage report</title>
<style>
  :root {{
    --bg: #15130f;
    --surface: #211c16;
    --ink: #f3ede2;
    --muted: #8f8574;
    --accent: #f2a154;
    --good: #7ecb7e;
    --warn: #e2703f;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    background: var(--bg);
    color: var(--ink);
    margin: 0;
    padding: 3rem 2.5rem;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }}
  .mono {{
    font-family: ui-monospace, "SF Mono", SFMono-Regular, Menlo, Consolas,
      "Liberation Mono", monospace;
    font-variant-numeric: tabular-nums;
  }}
  .brand {{
    display: flex;
    align-items: center;
    gap: .5rem;
    margin: 0 0 .6rem;
  }}
  .mark {{ width: 20px; height: 20px; color: var(--accent); flex-shrink: 0; }}
  .kicker {{
    color: var(--accent);
    font-size: .78rem;
    font-weight: 600;
    letter-spacing: .16em;
    text-transform: uppercase;
  }}
  h1 {{
    font-size: 1.35rem;
    font-weight: 600;
    line-height: 1.45;
    margin: 0 0 2.25rem;
    max-width: 34rem;
    text-wrap: balance;
  }}
  h1 .muted {{ color: var(--muted); font-weight: 400; }}
  .zone {{ margin-bottom: 1.75rem; max-width: 780px; }}
  .zone-label {{
    color: var(--muted);
    font-size: .7rem;
    font-weight: 600;
    letter-spacing: .14em;
    text-transform: uppercase;
    margin-bottom: .75rem;
  }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: .85rem;
  }}
  .card {{
    background: var(--surface);
    border-radius: 12px;
    padding: 1.1rem 1.25rem;
  }}
  .card.span-2 {{ grid-column: span 2; }}
  .label {{
    color: var(--muted);
    font-size: .68rem;
    letter-spacing: .05em;
    text-transform: uppercase;
    margin-bottom: .5rem;
  }}
  .value {{ font-size: 1.7rem; font-weight: 600; line-height: 1; }}
  .value.muted {{ color: var(--muted); font-size: 1.15rem; }}
  .unit {{ font-size: .95rem; color: var(--muted); margin-left: .2rem; }}
  .hint {{ color: var(--muted); font-size: .78rem; margin-top: .55rem; }}
  .badge {{
    display: inline-block;
    padding: .3rem .7rem;
    border-radius: 999px;
    font-size: .82rem;
    font-weight: 600;
  }}
  .badge.healthy {{ background: rgba(126, 203, 126, .16); color: var(--good); }}
  .badge.warn {{ background: rgba(226, 112, 63, .16); color: var(--warn); }}
</style>
</head>
<body>
  <div class="brand">
    <svg class="mark" viewBox="0 0 320 320" aria-hidden="true"
      xmlns="http://www.w3.org/2000/svg">
      <rect x="110" y="60" width="24" height="200" rx="12" fill="currentColor"/>
      <circle cx="122" cy="60" r="14" fill="currentColor"/>
      <circle cx="122" cy="260" r="14" fill="currentColor"/>
      <path d="M122,150 L170,150 L225,95" fill="none" stroke="currentColor"
        stroke-width="22" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M122,170 L170,170 L225,225" fill="none" stroke="currentColor"
        stroke-width="22" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="170" cy="150" r="12" fill="currentColor"/>
      <circle cx="170" cy="170" r="12" fill="currentColor"/>
      <circle cx="225" cy="95" r="14" fill="currentColor"/>
      <circle cx="225" cy="225" r="14" fill="currentColor"/>
    </svg>
    <p class="kicker mono">kernelgarage</p>
  </div>
  <h1>{summary}</h1>

  <div class="zone">
    <div class="zone-label">Hardware</div>
    <div class="grid">{hardware_cards}
      <div class="card">
        <div class="label">Throttling</div>
        <span class="badge {badge_class}">{badge_text}</span>
      </div>
    </div>
  </div>

  <div class="zone">
    <div class="zone-label">Model</div>
    <div class="grid">
      <div class="card">
        <div class="label">Requests</div>
        <div class="value mono">{self.total_requests}</div>
      </div>
      <div class="card">
        <div class="label">Prompt tokens</div>
        <div class="value mono">{self.prompt_tokens}</div>
      </div>
      <div class="card">
        <div class="label">Completion tokens</div>
        <div class="value mono">{self.completion_tokens}</div>
      </div>
      <div class="card">
        <div class="label">Peak queue depth</div>
        <div class="value mono">{self.peak_queue_depth}</div>
      </div>
      <div class="card">
        <div class="label">Avg duration</div>
        <div class="value mono">{duration_value}</div>
      </div>
      <div class="card">
        <div class="label">Avg queue wait</div>
        <div class="value mono">{wait_value}</div>
      </div>
    </div>
  </div>
</body>
</html>
"""


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


@mcp.tool()
def get_usage_report_html(hours: int = 24) -> str:
    """Same as `get_usage_report`, rendered as a self-contained HTML page."""
    return build_usage_report(hours=hours).render_html()


def main() -> None:
    """Entry point for the `kernelgarage-mcp` console script — runs over stdio."""
    mcp.run()
