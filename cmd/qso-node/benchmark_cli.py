from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys
import time
from dataclasses import asdict, dataclass
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass
class BenchmarkResult:
    name: str
    sent_events: int
    received_events: int
    dropped_events: int
    duration_s: float
    throughput_eps: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * percentile
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    if low == high:
        return ordered[low]
    frac = rank - low
    return ordered[low] + (ordered[high] - ordered[low]) * frac


def _build_result(name: str, sent: int, received: int, duration_s: float, latencies_ms: list[float]) -> BenchmarkResult:
    dropped = max(0, sent - received)
    throughput = (received / duration_s) if duration_s > 0 else 0.0
    return BenchmarkResult(
        name=name,
        sent_events=sent,
        received_events=received,
        dropped_events=dropped,
        duration_s=round(duration_s, 6),
        throughput_eps=round(throughput, 2),
        latency_p50_ms=round(_percentile(latencies_ms, 0.50), 4),
        latency_p95_ms=round(_percentile(latencies_ms, 0.95), 4),
        latency_p99_ms=round(_percentile(latencies_ms, 0.99), 4),
    )


async def benchmark_single_uri_stream(total_events: int, queue_size: int) -> BenchmarkResult:
    from api.mcp_tools.qso_tools import QSOMCPTools

    tools = QSOMCPTools()
    uri = "qso://bench.single.uri"
    tools.qso_create(uri, {"type": "benchmark"})

    send_times_ns: dict[int, int] = {}
    latencies_ms: list[float] = []
    seen: set[int] = set()

    stream = tools.qso_subscribe(uri, backpressure="block", queue_size=queue_size)

    async def consume() -> None:
        while len(seen) < total_events:
            payload = await anext(stream)
            seq = payload.get("delta", {}).get("seq")
            if not isinstance(seq, int) or seq in seen:
                continue
            seen.add(seq)
            sent_ns = send_times_ns.get(seq)
            if sent_ns is not None:
                latencies_ms.append((time.perf_counter_ns() - sent_ns) / 1_000_000.0)

    consumer_task = asyncio.create_task(consume())
    await asyncio.sleep(0)

    start = time.perf_counter()
    for seq in range(total_events):
        send_times_ns[seq] = time.perf_counter_ns()
        tools.qso_patch(uri, {"seq": seq}, actor="bench-single")
        if seq % 64 == 0:
            await asyncio.sleep(0)

    await asyncio.wait_for(consumer_task, timeout=max(3.0, total_events / 1000.0))
    await stream.aclose()
    duration = time.perf_counter() - start
    return _build_result("single_uri_live", total_events, len(seen), duration, latencies_ms)


async def benchmark_prefix_replay(uris: int, events_per_uri: int) -> BenchmarkResult:
    from api.mcp_tools.qso_tools import QSOMCPTools

    tools = QSOMCPTools()
    prefix = "qso://bench.prefix.zone."
    total_events = uris * events_per_uri

    for idx in range(uris):
        uri = f"{prefix}{idx}"
        tools.qso_create(uri, {"type": "zone"})
        for seq in range(events_per_uri):
            tools.qso_patch(uri, {"seq": seq, "zone": idx}, actor="bench-prefix")

    stream = tools.qso_subscribe_prefix(prefix)
    received = 0
    latencies_ms: list[float] = []

    start = time.perf_counter()
    while received < total_events:
        payload = await asyncio.wait_for(anext(stream), timeout=3.0)
        if payload.get("source") != "replay":
            continue
        received += 1
        latencies_ms.append((time.perf_counter() - start) * 1000.0)

    await stream.aclose()
    duration = time.perf_counter() - start
    return _build_result("prefix_replay_scan", total_events, received, duration, latencies_ms)


async def benchmark_webxr_projection(total_events: int, queue_size: int) -> BenchmarkResult:
    from api.mcp_tools.qso_tools import QSOMCPTools
    from tools.qso_web_api import WebXRAdapter

    tools = QSOMCPTools()
    adapter = WebXRAdapter(tools)

    src = "qso://bench.xr.world"
    dst = "qso://bench.xr.viewer"
    tools.qso_create(src, {"type": "world"})
    tools.qso_create(dst, {"type": "identity"})
    tools.qso_entangle(src, dst, "feeds-view", bidirectional=False)

    send_times_ns: dict[int, int] = {}
    latencies_ms: list[float] = []
    seen: set[int] = set()
    done_sending = False

    stream = adapter.stream_projection_ws(
        uri=dst,
        viewpoint={"center": [0, 0, 0], "radius": 100000},
        backpressure="drop_oldest",
        queue_size=queue_size,
    )

    async def consume() -> None:
        nonlocal done_sending
        try:
            while True:
                timeout_s = 0.25 if done_sending else 2.0
                try:
                    message = await asyncio.wait_for(anext(stream), timeout=timeout_s)
                except asyncio.TimeoutError:
                    if done_sending:
                        return
                    continue

                projection = message.get("payload", {})
                seq = projection.get("render_delta", {}).get("global", {}).get("seq")
                if not isinstance(seq, int) or seq in seen:
                    continue
                seen.add(seq)
                sent_ns = send_times_ns.get(seq)
                if sent_ns is not None:
                    latencies_ms.append((time.perf_counter_ns() - sent_ns) / 1_000_000.0)
        finally:
            await stream.aclose()

    consumer_task = asyncio.create_task(consume())
    await asyncio.sleep(0)

    start = time.perf_counter()
    for seq in range(total_events):
        send_times_ns[seq] = time.perf_counter_ns()
        tools.qso_patch(
            src,
            {
                "seq": seq,
                "position": [float(seq % 100), 0.0, 0.0],
                "objects": {"entity": {"position": [float(seq % 100), 0.0, 0.0], "visible": True}},
            },
            actor="bench-xr",
        )
        if seq % 64 == 0:
            await asyncio.sleep(0)

    done_sending = True
    await consumer_task
    duration = time.perf_counter() - start
    return _build_result("webxr_projection_stream", total_events, len(seen), duration, latencies_ms)


async def benchmark_backpressure_drop_newest(total_events: int, queue_size: int, consume_delay_ms: float) -> BenchmarkResult:
    from api.mcp_tools.qso_tools import QSOMCPTools

    tools = QSOMCPTools()
    uri = "qso://bench.backpressure.drop_newest"
    tools.qso_create(uri, {"type": "benchmark"})

    send_times_ns: dict[int, int] = {}
    latencies_ms: list[float] = []
    seen: set[int] = set()

    stream = tools.qso_subscribe(uri, backpressure="drop_newest", queue_size=queue_size)
    done_sending = False

    async def consume() -> None:
        nonlocal done_sending
        try:
            while True:
                timeout_s = 0.25 if done_sending else 2.0
                try:
                    payload = await asyncio.wait_for(anext(stream), timeout=timeout_s)
                except asyncio.TimeoutError:
                    if done_sending:
                        return
                    continue

                seq = payload.get("delta", {}).get("seq")
                if isinstance(seq, int) and seq not in seen:
                    seen.add(seq)
                    sent_ns = send_times_ns.get(seq)
                    if sent_ns is not None:
                        latencies_ms.append((time.perf_counter_ns() - sent_ns) / 1_000_000.0)
                if consume_delay_ms > 0:
                    await asyncio.sleep(consume_delay_ms / 1000.0)
        finally:
            await stream.aclose()

    consumer_task = asyncio.create_task(consume())
    await asyncio.sleep(0)

    start = time.perf_counter()
    for seq in range(total_events):
        send_times_ns[seq] = time.perf_counter_ns()
        tools.qso_patch(uri, {"seq": seq}, actor="bench-backpressure")
        if seq % 64 == 0:
            await asyncio.sleep(0)
    done_sending = True

    await consumer_task
    duration = time.perf_counter() - start
    return _build_result("backpressure_drop_newest", total_events, len(seen), duration, latencies_ms)


async def run_suite(
    *,
    events: int,
    prefix_uris: int,
    prefix_events: int,
    queue_size: int,
    consume_delay_ms: float,
) -> list[BenchmarkResult]:
    async def _run(name: str, coro: Any, timeout_s: float) -> BenchmarkResult:
        try:
            return await asyncio.wait_for(coro, timeout=timeout_s)
        except asyncio.TimeoutError:
            return BenchmarkResult(
                name=f"{name}_timeout",
                sent_events=0,
                received_events=0,
                dropped_events=0,
                duration_s=round(timeout_s, 6),
                throughput_eps=0.0,
                latency_p50_ms=0.0,
                latency_p95_ms=0.0,
                latency_p99_ms=0.0,
            )

    results: list[BenchmarkResult] = []
    results.append(
        await _run(
            "single_uri_live",
            benchmark_single_uri_stream(total_events=events, queue_size=queue_size),
            timeout_s=45.0,
        )
    )
    results.append(
        await _run(
            "prefix_replay_scan",
            benchmark_prefix_replay(uris=prefix_uris, events_per_uri=prefix_events),
            timeout_s=45.0,
        )
    )
    results.append(
        await _run(
            "webxr_projection_stream",
            benchmark_webxr_projection(total_events=events, queue_size=queue_size),
            timeout_s=45.0,
        )
    )
    results.append(
        await _run(
            "backpressure_drop_newest",
            benchmark_backpressure_drop_newest(
                total_events=events,
                queue_size=max(1, queue_size // 8),
                consume_delay_ms=consume_delay_ms,
            ),
            timeout_s=45.0,
        )
    )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="QSO streaming benchmark suite")
    parser.add_argument("--events", type=int, default=3000, help="events for live stream benchmarks")
    parser.add_argument("--prefix-uris", type=int, default=12, help="number of URIs in prefix replay benchmark")
    parser.add_argument("--prefix-events", type=int, default=120, help="events per URI in prefix replay benchmark")
    parser.add_argument("--queue-size", type=int, default=1024, help="subscription queue size")
    parser.add_argument("--consume-delay-ms", type=float, default=0.2, help="consumer delay for backpressure benchmark")
    parser.add_argument("--json", action="store_true", help="print JSON only")
    args = parser.parse_args()

    results = asyncio.run(
        run_suite(
            events=args.events,
            prefix_uris=args.prefix_uris,
            prefix_events=args.prefix_events,
            queue_size=args.queue_size,
            consume_delay_ms=args.consume_delay_ms,
        )
    )

    rows = [asdict(result) for result in results]
    if args.json:
        print(json.dumps(rows, indent=2))
        return

    print("\n--- QSO STREAMING BENCHMARKS ---")
    for row in rows:
        print(
            f"{row['name']}: sent={row['sent_events']} recv={row['received_events']} drop={row['dropped_events']} "
            f"dur_s={row['duration_s']} throughput_eps={row['throughput_eps']} "
            f"p50_ms={row['latency_p50_ms']} p95_ms={row['latency_p95_ms']} p99_ms={row['latency_p99_ms']}"
        )

    print("\n--- JSON ---")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
