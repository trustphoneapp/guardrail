"""One key-value store behind tokens, baselines, and trend rows.

Two backends, same four calls. With GUARDRAIL_TABLE unset it is a process-local
dict, which is what every test uses and needs no credentials. With it set, it
is one DynamoDB table (pk, sk) shared by the AgentCore runtime container and
the dashboard, which is the fix for the bug where a token minted in the runtime
returned 403 from the dashboard because they were two processes with two dicts.

Keys are strings. Values are JSON-able dicts; pydantic models go through
model_dump(mode="json") at the call site, and datetimes come back as ISO
strings the models re-parse.
"""

from __future__ import annotations

import os
import threading
from typing import Any

_LOCK = threading.Lock()
_MEM: dict[tuple[str, str], dict[str, Any]] = {}
_LIST: dict[str, list[dict[str, Any]]] = {}


def _table():
    name = os.environ.get("GUARDRAIL_TABLE")
    if not name:
        return None
    import boto3

    return boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1")).Table(name)


def get(pk: str, sk: str) -> dict[str, Any] | None:
    t = _table()
    if t is None:
        with _LOCK:
            return _MEM.get((pk, sk))
    item = t.get_item(Key={"pk": pk, "sk": sk}, ConsistentRead=True).get("Item")
    return _strip(item) if item else None


def put(pk: str, sk: str, value: dict[str, Any]) -> None:
    t = _table()
    if t is None:
        with _LOCK:
            _MEM[(pk, sk)] = dict(value)
        return
    t.put_item(Item={"pk": pk, "sk": sk, **_numbers(value)})


def put_if_absent(pk: str, sk: str, value: dict[str, Any]) -> bool:
    """Atomic create. Returns False if the key already exists. This is what
    makes single-use redemption safe across two processes: the first writer of
    REDEEMED#token wins, every other writer gets False."""
    t = _table()
    if t is None:
        with _LOCK:
            if (pk, sk) in _MEM:
                return False
            _MEM[(pk, sk)] = dict(value)
            return True
    from botocore.exceptions import ClientError

    try:
        t.put_item(
            Item={"pk": pk, "sk": sk, **_numbers(value)},
            ConditionExpression="attribute_not_exists(pk)",
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


def append(pk: str, value: dict[str, Any]) -> None:
    """Append to an ordered list under pk. Trend rows use this; sk is the ISO
    timestamp so a Query on pk returns them in time order."""
    t = _table()
    if t is None:
        with _LOCK:
            _LIST.setdefault(pk, []).append(dict(value))
        return
    t.put_item(Item={"pk": pk, "sk": str(value["ts"]), **_numbers(value)})


def list_(pk: str, limit: int = 30) -> list[dict[str, Any]]:
    t = _table()
    if t is None:
        with _LOCK:
            return list(_LIST.get(pk, []))[-limit:]
    from boto3.dynamodb.conditions import Key

    resp = t.query(KeyConditionExpression=Key("pk").eq(pk), ScanIndexForward=False, Limit=limit)
    items = [_strip(i) for i in resp.get("Items", [])]
    return list(reversed(items))


def _numbers(v: dict[str, Any]) -> dict[str, Any]:
    """DynamoDB refuses float; store numbers as Decimal. Strings, bools, ints,
    lists and dicts pass through, recursively."""
    from decimal import Decimal

    def conv(x):
        if isinstance(x, bool):
            return x
        if isinstance(x, float):
            return Decimal(str(x))
        if isinstance(x, dict):
            return {k: conv(y) for k, y in x.items()}
        if isinstance(x, list):
            return [conv(y) for y in x]
        return x

    return conv(v)


def _strip(item: dict[str, Any]) -> dict[str, Any]:
    """Inverse of _numbers: drop the key columns and turn Decimal back into
    float/int so pydantic is happy."""
    from decimal import Decimal

    def conv(x):
        if isinstance(x, Decimal):
            return int(x) if x == x.to_integral_value() else float(x)
        if isinstance(x, dict):
            return {k: conv(y) for k, y in x.items()}
        if isinstance(x, list):
            return [conv(y) for y in x]
        return x

    return {k: conv(v) for k, v in item.items() if k not in ("pk", "sk")}


def reset_for_tests() -> None:
    with _LOCK:
        _MEM.clear()
        _LIST.clear()
