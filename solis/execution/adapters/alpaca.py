from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping, Protocol, Sequence, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from solis.execution.adapters.base import ExecutionAdapter
from solis.shared.canonical_json import canonical_json
from solis.shared.hashing import sha256_hex_obj


class AlpacaAdapterError(RuntimeError):
    code = "ALPACA_ADAPTER_ERROR"

    def __init__(
        self,
        *,
        operation: str,
        method: str,
        path: str,
        status_code: int | None = None,
        response_payload: Mapping[str, Any] | None = None,
        detail: str | None = None,
    ) -> None:
        self.operation = operation
        self.method = method
        self.path = path
        self.status_code = status_code
        self.response_payload = dict(response_payload or {})
        self.detail = detail or ""
        super().__init__(self._message())

    def _message(self) -> str:
        base = f"{self.code} {self.method} {self.path}"
        if self.status_code is not None:
            base = f"{base} status={self.status_code}"
        if self.detail:
            return f"{base}: {self.detail}"
        if self.response_payload:
            return f"{base}: {_error_excerpt(self.response_payload, canonical_json(self.response_payload))}"
        return base

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "operation": self.operation,
            "method": self.method,
            "path": self.path,
            "status_code": self.status_code,
            "detail": self.detail,
            "response_payload": dict(self.response_payload),
        }


class AlpacaNetworkError(AlpacaAdapterError):
    code = "ALPACA_NETWORK_ERROR"


class AlpacaAuthError(AlpacaAdapterError):
    code = "ALPACA_AUTH_ERROR"


class AlpacaRateLimitError(AlpacaAdapterError):
    code = "ALPACA_RATE_LIMIT_ERROR"


class AlpacaValidationError(AlpacaAdapterError):
    code = "ALPACA_VALIDATION_ERROR"


class AlpacaHTTPError(AlpacaAdapterError):
    code = "ALPACA_HTTP_ERROR"


@dataclass(frozen=True)
class AlpacaCredentials:
    api_key_id: str
    api_secret_key: str

    def as_headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": self.api_key_id,
            "APCA-API-SECRET-KEY": self.api_secret_key,
            "Accept": "application/json",
        }


class GovernedTransportClient(Protocol):
    def send(
        self,
        *,
        workload_type: str,
        method: str,
        url: str,
        headers: Mapping[str, Any] | None = None,
        body: str | bytes | None = None,
        actor: str = "transport-client",
        policy_version: str = "v1",
        timeout_seconds: float = 10.0,
        metadata: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]: ...


class AlpacaExecutionAdapter(ExecutionAdapter):
    def __init__(
        self,
        *,
        credentials: AlpacaCredentials,
        base_url: str = "https://paper-api.alpaca.markets",
        timeout_seconds: float = 8.0,
        transport_client: GovernedTransportClient | None = None,
        transport_actor: str = "solis-execution",
        transport_policy_version: str = "v1",
    ) -> None:
        self.credentials = credentials
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.transport_client = transport_client
        self.transport_actor = transport_actor
        self.transport_policy_version = transport_policy_version
        self._events: list[dict[str, Any]] = []
        self._event_counter = 0

    def get_account(self) -> dict[str, Any]:
        return self._request_json("GET", "/v2/account", operation="get_account")

    def get_clock(self) -> dict[str, Any]:
        return self._request_json("GET", "/v2/clock", operation="get_clock")

    def list_positions(self) -> dict[str, Any]:
        payload = self._request_json("GET", "/v2/positions", operation="list_positions")
        return {"positions": _unwrap_list(payload)}

    def list_orders(
        self,
        *,
        status: str = "open",
        limit: int = 200,
        symbols: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        status_value = status.strip().lower() or "open"
        limit_value = max(1, min(500, int(limit)))
        query: dict[str, str] = {"status": status_value, "limit": str(limit_value)}
        if symbols:
            normalized_symbols = ",".join(sorted({str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()}))
            if normalized_symbols:
                query["symbols"] = normalized_symbols
        path = f"/v2/orders?{urlencode(query)}"
        payload = self._request_json("GET", path, operation="list_orders")
        return {
            "status": status_value,
            "limit": limit_value,
            "orders": _unwrap_list(payload),
        }

    def get_order(self, *, order_id: str) -> dict[str, Any]:
        target = str(order_id).strip()
        if not target:
            raise ValueError("order_id must be non-empty")
        return self._request_json("GET", f"/v2/orders/{target}", operation="get_order")

    def cancel_order(self, *, order_id: str) -> dict[str, Any]:
        target = str(order_id).strip()
        if not target:
            raise ValueError("order_id must be non-empty")
        return self._request_json("DELETE", f"/v2/orders/{target}", operation="cancel_order")

    def cancel_all_orders(self) -> dict[str, Any]:
        payload = self._request_json("DELETE", "/v2/orders", operation="cancel_all_orders")
        return {"cancellations": _unwrap_list(payload)}

    def get_asset(self, *, symbol: str) -> dict[str, Any]:
        normalized = str(symbol).strip().upper()
        if not normalized:
            raise ValueError("symbol must be non-empty")
        return self._request_json("GET", f"/v2/assets/{normalized}", operation="get_asset")

    def submit_market_order(
        self,
        *,
        symbol: str,
        side: str,
        notional: float | str,
        time_in_force: str = "day",
        client_order_id: str | None = None,
    ) -> dict[str, Any]:
        normalized_side = side.strip().lower()
        if normalized_side not in {"buy", "sell"}:
            raise ValueError("side must be 'buy' or 'sell'")

        notional_value = float(notional)
        if notional_value <= 0:
            raise ValueError("notional must be positive")

        payload: dict[str, Any] = {
            "symbol": symbol.strip().upper(),
            "side": normalized_side,
            "type": "market",
            "time_in_force": time_in_force.strip().lower(),
            "notional": format(notional_value, ".2f"),
        }
        if client_order_id:
            payload["client_order_id"] = client_order_id

        return self._request_json(
            "POST",
            "/v2/orders",
            payload=payload,
            operation="submit_market_order",
        )

    def drain_events(self) -> list[dict[str, Any]]:
        drained = list(self._events)
        self._events.clear()
        return drained

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        operation: str,
    ) -> dict[str, Any]:
        encoded = canonical_json(dict(payload)).encode("utf-8") if payload is not None else None
        headers = self.credentials.as_headers()
        if encoded is not None:
            headers["Content-Type"] = "application/json"

        request = Request(
            f"{self.base_url}{path}",
            data=encoded,
            headers=headers,
            method=method,
        )

        started = perf_counter()
        status_code = 0
        response_body = ""
        if self.transport_client is not None:
            routed = self.transport_client.send(
                workload_type="market_execution",
                method=method,
                url=f"{self.base_url}{path}",
                headers=headers,
                body=encoded,
                actor=self.transport_actor,
                policy_version=self.transport_policy_version,
                timeout_seconds=self.timeout_seconds,
                metadata={"adapter": "alpaca", "operation": operation},
            )
            response_obj = cast(Mapping[str, Any], routed.get("response", {}))
            status_code = int(response_obj.get("status_code", 599))
            response_body = str(response_obj.get("body_text", ""))
            latency_ms = int(float(response_obj.get("elapsed_ms", (perf_counter() - started) * 1000)))
            error_detail = str(response_obj.get("error", "")).strip()

            parsed_payload = _normalize_payload(_parse_response_json(response_body))
            self._record_event(
                operation=operation,
                method=method,
                path=path,
                payload=payload,
                response_payload=parsed_payload,
                status_code=status_code,
                latency_ms=latency_ms,
            )
            if error_detail or status_code >= 400:
                error_cls = _http_error_class(status_code) if status_code > 0 else AlpacaNetworkError
                raise error_cls(
                    operation=operation,
                    method=method,
                    path=path,
                    status_code=status_code,
                    response_payload=parsed_payload,
                    detail=error_detail or _error_excerpt(parsed_payload, response_body),
                )
            return parsed_payload

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                status_code = int(response.status)
                response_body = response.read().decode("utf-8")
        except HTTPError as exc:
            status_code = int(exc.code)
            response_body = exc.read().decode("utf-8", errors="replace")
            parsed_error = _parse_response_json(response_body)
            self._record_event(
                operation=operation,
                method=method,
                path=path,
                payload=payload,
                response_payload=parsed_error,
                status_code=status_code,
                latency_ms=int((perf_counter() - started) * 1000),
            )
            error_cls = _http_error_class(status_code)
            raise error_cls(
                operation=operation,
                method=method,
                path=path,
                status_code=status_code,
                response_payload=parsed_error,
                detail=_error_excerpt(parsed_error, response_body),
            ) from exc
        except URLError as exc:
            self._record_event(
                operation=operation,
                method=method,
                path=path,
                payload=payload,
                response_payload={"error": str(exc)},
                status_code=0,
                latency_ms=int((perf_counter() - started) * 1000),
            )
            raise AlpacaNetworkError(
                operation=operation,
                method=method,
                path=path,
                detail=str(exc),
            ) from exc

        parsed = _normalize_payload(_parse_response_json(response_body))
        latency_ms = int((perf_counter() - started) * 1000)
        self._record_event(
            operation=operation,
            method=method,
            path=path,
            payload=payload,
            response_payload=parsed,
            status_code=status_code,
            latency_ms=latency_ms,
        )
        return parsed

    def _record_event(
        self,
        *,
        operation: str,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None,
        response_payload: Mapping[str, Any],
        status_code: int,
        latency_ms: int,
    ) -> None:
        self._event_counter += 1
        request_payload = dict(payload) if payload is not None else {}
        event: dict[str, Any] = {
            "event_id": f"alpaca-event-{self._event_counter:06d}",
            "operation": operation,
            "method": method,
            "path": path,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "request": request_payload,
            "response": dict(response_payload),
            "request_hash": sha256_hex_obj(request_payload),
            "response_hash": sha256_hex_obj(response_payload),
        }
        self._events.append(event)


def build_replay_artifact(
    events: Sequence[Mapping[str, Any]],
    *,
    base_url: str,
    scenario: str,
) -> dict[str, Any]:
    chain: list[dict[str, Any]] = []
    prev_hash = "GENESIS"
    for index, event in enumerate(events):
        payload = {"index": index, "prev_hash": prev_hash, "event": dict(event)}
        node_hash = sha256_hex_obj(payload)
        chain.append(
            {
                "index": index,
                "prev_hash": prev_hash,
                "hash": node_hash,
                "event": dict(event),
            }
        )
        prev_hash = node_hash

    artifact_without_hash: dict[str, Any] = {
        "schema_version": "1.0",
        "adapter": "alpaca",
        "base_url": base_url,
        "scenario": scenario,
        "event_count": len(chain),
        "root_hash": prev_hash,
        "events": chain,
    }
    artifact_hash = sha256_hex_obj(artifact_without_hash)
    return {
        **artifact_without_hash,
        "artifact_hash": artifact_hash,
    }


def verify_replay_artifact(artifact: Mapping[str, Any]) -> bool:
    raw_events = artifact.get("events")
    if not isinstance(raw_events, list):
        return False

    prev_hash = "GENESIS"
    for index, node in enumerate(raw_events):
        if not isinstance(node, Mapping):
            return False
        event = node.get("event")
        if not isinstance(event, Mapping):
            return False
        node_prev_hash = str(node.get("prev_hash", ""))
        if node_prev_hash != prev_hash:
            return False

        expected_hash = sha256_hex_obj(
            {
                "index": index,
                "prev_hash": prev_hash,
                "event": dict(event),
            }
        )
        node_hash = str(node.get("hash", ""))
        if node_hash != expected_hash:
            return False
        prev_hash = expected_hash

    root_hash = str(artifact.get("root_hash", ""))
    if root_hash != prev_hash:
        return False

    artifact_hash = str(artifact.get("artifact_hash", ""))
    unsigned = {k: v for k, v in artifact.items() if k != "artifact_hash"}
    expected_artifact_hash = cast(str, sha256_hex_obj(unsigned))
    return artifact_hash == expected_artifact_hash


def write_replay_artifact(path: Path, artifact: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(dict(artifact)), encoding="utf-8")


def load_replay_artifact(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("replay artifact must deserialize to a JSON object")
    return cast(dict[str, Any], loaded)


def _parse_response_json(payload: str) -> dict[str, Any]:
    if payload.strip() == "":
        return {}
    parsed = json.loads(payload)
    if isinstance(parsed, Mapping):
        return dict(parsed)
    return {"value": parsed}


def _normalize_payload(value: Any) -> Any:
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key in sorted(value.keys(), key=str):
            normalized[str(key)] = _normalize_payload(value[key])
        return normalized
    if isinstance(value, list):
        normalized_list = [_normalize_payload(item) for item in value]
        sort_key = _common_sort_key(normalized_list)
        if sort_key is not None:
            normalized_list = sorted(
                normalized_list,
                key=lambda item: str(item.get(sort_key, "")) if isinstance(item, Mapping) else "",
            )
        return normalized_list
    return value


def _common_sort_key(items: list[Any]) -> str | None:
    if not items or not all(isinstance(item, Mapping) for item in items):
        return None
    candidates = ("id", "order_id", "asset_id", "symbol", "client_order_id")
    for candidate in candidates:
        if all(candidate in item for item in items):
            return candidate
    return None


def _unwrap_list(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("value", [])
    if not isinstance(raw, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, Mapping):
            rows.append({str(key): value for key, value in item.items()})
    return rows


def _error_excerpt(parsed_error: Mapping[str, Any], fallback: str) -> str:
    message = parsed_error.get("message")
    if isinstance(message, str) and message.strip():
        return message.strip()
    compact = fallback.strip().replace("\n", " ")
    if len(compact) <= 180:
        return compact
    return compact[:177] + "..."


def _http_error_class(status_code: int) -> type[AlpacaAdapterError]:
    if status_code in {401, 403}:
        return AlpacaAuthError
    if status_code == 429:
        return AlpacaRateLimitError
    if status_code in {400, 422}:
        return AlpacaValidationError
    return AlpacaHTTPError
