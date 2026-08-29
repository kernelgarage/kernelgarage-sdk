from unittest.mock import MagicMock, patch

import pytest

from kernelgarage import mcp_server


def _fake_query_factory(values):
    def _fake_query(client, promql):
        for key, value in values.items():
            if key in promql:
                return value
        raise AssertionError(f"unexpected promql: {promql}")

    return _fake_query


def test_prometheus_url_raises_when_unset(monkeypatch):
    monkeypatch.delenv("PROMETHEUS_URL", raising=False)
    with pytest.raises(RuntimeError, match="PROMETHEUS_URL"):
        mcp_server._prometheus_url()


def test_decode_throttled_healthy():
    assert mcp_server._decode_throttled(0) == ()


def test_decode_throttled_combo():
    # bit 0 (under-voltage now) + bit 18 (throttling has occurred)
    assert mcp_server._decode_throttled(0x40001) == (
        "under-voltage detected",
        "throttling has occurred",
    )


def test_query_returns_none_on_empty_result():
    client = MagicMock()
    client.get.return_value.json.return_value = {"data": {"result": []}}
    assert mcp_server._query(client, "up") is None


def test_query_returns_value():
    client = MagicMock()
    client.get.return_value.json.return_value = {
        "data": {"result": [{"value": [0, "42.5"]}]}
    }
    assert mcp_server._query(client, "up") == 42.5


def test_build_usage_report_full_data():
    values = {
        "avg_over_time(rpi_cpu_temperature_celsius": 45.0,
        "max_over_time(rpi_cpu_temperature_celsius": 60.0,
        "rpi_throttled_state": float(0x40001),
        "llm_requests_total": 12.0,
        "llm_tokens_prompt_total": 500.0,
        "llm_tokens_completion_total": 800.0,
        "llm_requests_waiting": 3.0,
        "llm_request_duration_seconds_sum": 24.0,
        "llm_request_duration_seconds_count": 12.0,
        "llm_queue_wait_seconds_sum": 6.0,
        "llm_queue_wait_seconds_count": 12.0,
    }
    with (
        patch(
            "kernelgarage.mcp_server._query",
            side_effect=_fake_query_factory(values),
        ),
        patch("httpx.Client"),
    ):
        report = mcp_server.build_usage_report(hours=24)

    assert report.hours == 24
    assert report.avg_temp_c == 45.0
    assert report.max_temp_c == 60.0
    assert report.throttle_events == (
        "under-voltage detected",
        "throttling has occurred",
    )
    assert report.total_requests == 12
    assert report.prompt_tokens == 500
    assert report.completion_tokens == 800
    assert report.peak_queue_depth == 3
    assert report.avg_duration_s == 2.0
    assert report.avg_queue_wait_s == 0.5


def test_build_usage_report_no_data():
    with (
        patch("kernelgarage.mcp_server._query", return_value=None),
        patch("httpx.Client"),
    ):
        report = mcp_server.build_usage_report(hours=1)

    assert report.avg_temp_c is None
    assert report.max_temp_c is None
    assert report.throttle_events == ()
    assert report.total_requests == 0
    assert report.prompt_tokens == 0
    assert report.completion_tokens == 0
    assert report.peak_queue_depth == 0
    assert report.avg_duration_s is None
    assert report.avg_queue_wait_s is None


def test_render_with_data():
    report = mcp_server.UsageReport(
        hours=24,
        avg_temp_c=45.0,
        max_temp_c=60.0,
        throttle_events=("under-voltage detected",),
        total_requests=10,
        prompt_tokens=100,
        completion_tokens=200,
        peak_queue_depth=2,
        avg_duration_s=1.5,
        avg_queue_wait_s=0.3,
    )

    text = report.render()

    assert "last 24h" in text
    assert "avg 45.0°C, peak 60.0°C" in text
    assert "under-voltage detected" in text
    assert "10" in text
    assert "1.50s" in text
    assert "0.30s" in text


def test_render_no_hardware_or_llm_data():
    report = mcp_server.UsageReport(
        hours=1,
        avg_temp_c=None,
        max_temp_c=None,
        throttle_events=(),
        total_requests=0,
        prompt_tokens=0,
        completion_tokens=0,
        peak_queue_depth=0,
        avg_duration_s=None,
        avg_queue_wait_s=None,
    )

    text = report.render()

    assert "no data" in text
    assert "Throttling: none" in text
    assert "Avg request duration" not in text
    assert "Avg queue wait" not in text


def test_render_html_with_data_and_throttle_warning():
    report = mcp_server.UsageReport(
        hours=24,
        avg_temp_c=45.0,
        max_temp_c=60.0,
        throttle_events=("under-voltage detected",),
        total_requests=10,
        prompt_tokens=100,
        completion_tokens=200,
        peak_queue_depth=2,
        avg_duration_s=1.5,
        avg_queue_wait_s=0.3,
    )

    html = report.render_html()

    assert html.startswith("<!doctype html>")
    assert 'class="mark"' in html
    assert "10 requests over the last 24h" in html
    assert "45.0" in html and "60.0" in html
    assert "under-voltage detected" in html
    assert 'badge warn"' in html
    assert "1.50" in html
    assert "0.30" in html


def test_render_html_no_data_is_healthy_and_singular_request():
    report = mcp_server.UsageReport(
        hours=1,
        avg_temp_c=None,
        max_temp_c=None,
        throttle_events=(),
        total_requests=1,
        prompt_tokens=0,
        completion_tokens=0,
        peak_queue_depth=0,
        avg_duration_s=None,
        avg_queue_wait_s=None,
    )

    html = report.render_html()

    assert "1 request over the last 1h" in html
    assert "no data" in html
    assert 'badge healthy"' in html
    assert "all healthy" in html


def test_get_usage_report_tool(monkeypatch):
    fake_report = MagicMock()
    fake_report.render.return_value = "rendered report"
    monkeypatch.setattr(mcp_server, "build_usage_report", lambda hours=24: fake_report)

    assert mcp_server.get_usage_report(hours=5) == "rendered report"


def test_get_usage_report_html_tool(monkeypatch):
    fake_report = MagicMock()
    fake_report.render_html.return_value = "<html>rendered</html>"
    monkeypatch.setattr(mcp_server, "build_usage_report", lambda hours=24: fake_report)

    assert mcp_server.get_usage_report_html(hours=5) == "<html>rendered</html>"


def test_main_runs_over_stdio(monkeypatch):
    calls = []
    monkeypatch.setattr(mcp_server.mcp, "run", lambda: calls.append(True))

    mcp_server.main()

    assert calls == [True]


def test_print_report_html_writes_file_and_prints_link(monkeypatch, tmp_path, capsys):
    fake_report = MagicMock()
    fake_report.render_html.return_value = "<html>hi</html>"
    monkeypatch.setattr(mcp_server, "build_usage_report", lambda hours=24: fake_report)
    out_path = tmp_path / "custom.html"

    mcp_server.print_report(hours=5, html=True, out=out_path)

    assert out_path.read_text() == "<html>hi</html>"
    output = capsys.readouterr().out.replace("\n", "")
    assert "report saved" in output
    assert str(out_path) in output


def test_print_report_html_default_out_path(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    fake_report = MagicMock()
    fake_report.render_html.return_value = "<html>hi</html>"
    monkeypatch.setattr(mcp_server, "build_usage_report", lambda hours=24: fake_report)

    mcp_server.print_report(html=True)

    assert (tmp_path / "report.html").read_text() == "<html>hi</html>"


def test_print_report_table_with_data_and_warning(monkeypatch, capsys):
    report = mcp_server.UsageReport(
        hours=24,
        avg_temp_c=45.0,
        max_temp_c=60.0,
        throttle_events=("under-voltage detected",),
        total_requests=10,
        prompt_tokens=100,
        completion_tokens=200,
        peak_queue_depth=2,
        avg_duration_s=1.5,
        avg_queue_wait_s=0.3,
    )
    monkeypatch.setattr(mcp_server, "build_usage_report", lambda hours=24: report)

    mcp_server.print_report(hours=24)

    output = capsys.readouterr().out
    assert "kernelgarage" in output
    assert "under-voltage detected" in output
    assert "45.0" in output and "60.0" in output
    assert "10" in output
    assert "1.50s" in output
    assert "0.30s" in output


def test_print_report_table_no_data_is_healthy(monkeypatch, capsys):
    report = mcp_server.UsageReport(
        hours=1,
        avg_temp_c=None,
        max_temp_c=None,
        throttle_events=(),
        total_requests=0,
        prompt_tokens=0,
        completion_tokens=0,
        peak_queue_depth=0,
        avg_duration_s=None,
        avg_queue_wait_s=None,
    )
    monkeypatch.setattr(mcp_server, "build_usage_report", lambda hours=24: report)

    mcp_server.print_report(hours=1)

    output = capsys.readouterr().out
    assert "no data" in output
    assert "healthy" in output
