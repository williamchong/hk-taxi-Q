"""The `Q41` reader survey (`tools/facade_grammar.py`).

The reader itself needs a credential and 40 API calls; what is testable offline
is the part whose failure is silent — the grading. A pool rule implemented one
comparison off passes readers `Q41`'s record says must fail, and the printed
table looks exactly as authoritative either way. So the tests state each pool's
rule as a case and hold the scorer to it, and pin the label file to the shape
the scorer assumes.
"""

from __future__ import annotations

import io
import json
from hashlib import blake2b
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from facade_grammar import (
    GRAMMARS,
    LABELS,
    MAX_EDGE_PX,
    PROMPT_HASH,
    SCHEMA,
    UNWRAP_HASH,
    agrees,
    batch_entry,
    cached_read,
    encode_elevation,
    entry_path,
    is_miss,
    parse_message,
    refusal_row,
    request_params,
    score,
)
from facade_unwrap import Elevation
from PIL import Image


def label(
    readable: bool,
    grammar: str | None = None,
    *,
    alt: str | None = None,
    refusal_ok: bool = False,
    glazed: bool | None = None,
) -> dict:
    return {
        "sheet": "s",
        "building": "b",
        "face": "S",
        "readable": readable,
        "grammar": grammar,
        "alt_grammar": alt,
        "refusal_ok": refusal_ok,
        "glazed": glazed,
        "tint": None,
        "signage": None,
        "notes": "",
    }


def result(
    readable: bool,
    grammar: str | None = None,
    *,
    confidence: str = "high",
    glazed: bool | None = None,
) -> dict:
    return {
        "readable": readable,
        "grammar": grammar,
        "confidence": confidence,
        "glazed": glazed,
        "tint": None,
        "signage": None,
        "notes": "",
    }


def test_strict_pool_requires_agreement_and_counts_refusal_as_miss() -> None:
    strict = label(True, "curtain", alt="mixed")
    assert not is_miss(strict, result(True, "curtain"))
    assert not is_miss(strict, result(True, "mixed"))  # alt_grammar counts
    assert is_miss(strict, result(True, "punched"))
    assert is_miss(strict, result(False))  # refusing a strict face is a miss
    assert is_miss(strict, result(True, "punched", confidence="low"))  # low hedges nothing here


def test_marginal_pool_misses_only_on_confident_disagreement() -> None:
    marginal = label(True, "punched", refusal_ok=True)
    assert not is_miss(marginal, result(False))  # refusal is fine
    assert not is_miss(marginal, result(True, "punched"))
    assert not is_miss(marginal, result(True, "blank", confidence="low"))
    assert is_miss(marginal, result(True, "blank"))


def test_refusal_pool_misses_only_on_a_confident_claim() -> None:
    unreadable = label(False)
    assert not is_miss(unreadable, result(False))
    assert not is_miss(unreadable, result(True, "curtain", confidence="low"))
    assert is_miss(unreadable, result(True, "curtain"))


def test_score_pools_and_glazed_axis() -> None:
    results = [
        (label(True, "curtain", glazed=True), result(True, "curtain", glazed=True)),
        (label(True, "punched", glazed=False), result(True, "blank", glazed=True)),
        (label(True, "blank", refusal_ok=True), result(False)),
        (label(False), result(True, "fin")),
    ]
    by_name = {name: (hits, total) for name, hits, total, _ in score(results)}
    assert by_name["strict grammar"] == (1, 2)
    assert by_name["marginal"] == (1, 1)
    assert by_name["refusal"] == (0, 1)
    # Glazed pairs need a label value AND a readable reader value: rows 1 and 2.
    assert by_name["glazed"] == (1, 2)


def test_refusal_row_matches_the_response_schema() -> None:
    # Every face row carries `image_hash` — `None` on a refusal minted without
    # an image, a fingerprint on anything `cached_read` returns.
    assert set(refusal_row("x")) == set(SCHEMA["required"]) | {"image_hash"}
    assert refusal_row("x")["image_hash"] is None
    assert not agrees(label(True, "curtain"), refusal_row("x"))


def test_label_file_holds_the_shape_and_counts_the_record_states() -> None:
    document = json.loads(LABELS.read_text())
    faces = document["faces"]
    assert len(faces) == 40
    strict = [f for f in faces if f["readable"] and not f["refusal_ok"]]
    marginal = [f for f in faces if f["readable"] and f["refusal_ok"]]
    unreadable = [f for f in faces if not f["readable"]]
    assert (len(strict), len(marginal), len(unreadable)) == (20, 6, 14)
    # A typo'd grammar value would make agrees() unconditionally false and
    # silently score a miss against the reader — so membership is pinned here.
    assert document["protocol"]["grammar_values"] == list(GRAMMARS)
    for face in faces:
        assert (face["grammar"] is None) == (not face["readable"])
        assert face["grammar"] in (*GRAMMARS, None)
        assert face["alt_grammar"] in (*GRAMMARS, None)


def test_prompt_hash_is_a_recordable_stamp() -> None:
    for stamp in (PROMPT_HASH, UNWRAP_HASH):
        assert len(stamp) == 16
        assert int(stamp, 16) >= 0


def elevation(fill: int) -> Elevation:
    return Elevation(
        canvas=np.full((8, 8, 3), fill, dtype=np.uint8),
        coverage=1.0,
        width_m=1.0,
        height_m=1.0,
    )


def fingerprint_of(sample: Elevation) -> str:
    return blake2b(encode_elevation(sample), digest_size=8).hexdigest()


def no_client() -> None:
    raise AssertionError("a cache hit must not construct a client")


def canned_client(response: dict, calls: list[int]) -> SimpleNamespace:
    def create(**_kwargs: object) -> SimpleNamespace:
        calls.append(1)
        return SimpleNamespace(
            stop_reason="end_turn",
            content=[SimpleNamespace(type="text", text=json.dumps(response))],
        )

    return SimpleNamespace(messages=SimpleNamespace(create=create))


def test_cache_hit_replays_without_a_client_and_stamps_the_image(tmp_path: Path) -> None:
    sample = elevation(7)
    canned = result(True, "curtain")
    (tmp_path / f"k.{PROMPT_HASH}.{fingerprint_of(sample)}.json").write_text(json.dumps(canned))
    got = cached_read(no_client, tmp_path, "k", sample)
    assert got == {**canned, "image_hash": fingerprint_of(sample)}


def test_changed_image_refuses_the_hit_but_keeps_the_paid_entry(tmp_path: Path) -> None:
    old, new = elevation(7), elevation(9)
    stale = tmp_path / f"k.{PROMPT_HASH}.{fingerprint_of(old)}.json"
    stale.write_text(json.dumps(result(True, "curtain")))

    calls: list[int] = []
    got = cached_read(lambda: canned_client(result(True, "punched"), calls), tmp_path, "k", new)
    assert calls == [1]  # the stale entry must not answer for a different image
    assert got["grammar"] == "punched"
    assert got["image_hash"] == fingerprint_of(new)

    # The superseded entry is a paid read: it survives, and the old image
    # still replays it without a client — a reverted unwrap costs nothing.
    assert stale.exists()
    assert cached_read(no_client, tmp_path, "k", old)["grammar"] == "curtain"


def test_batch_entry_round_trips_to_the_cache_entry_cached_read_would_write(
    tmp_path: Path,
) -> None:
    sample = elevation(7)
    png = encode_elevation(sample)
    request = batch_entry("B1_E", png)
    # Identical params to the synchronous read — the transports cannot drift.
    assert request["params"] == request_params(png)
    assert request["custom_id"] == f"B1_E-{fingerprint_of(sample)}"
    assert entry_path(tmp_path, request["custom_id"]) == (
        tmp_path / f"B1_E.{PROMPT_HASH}.{fingerprint_of(sample)}.json"
    )


def test_parse_message_reads_refuses_and_rejects_textless_responses() -> None:
    canned = result(True, "curtain")
    read = SimpleNamespace(
        stop_reason="end_turn",
        content=[SimpleNamespace(type="text", text=json.dumps(canned))],
    )
    assert parse_message(read) == canned
    assert parse_message(SimpleNamespace(stop_reason="refusal", content=[])) == refusal_row(
        "api refusal"
    )
    with pytest.raises(RuntimeError):
        parse_message(SimpleNamespace(stop_reason="end_turn", content=[]))


def test_encode_elevation_caps_the_long_edge() -> None:
    tall = Elevation(
        canvas=np.zeros((3000, 400, 3), dtype=np.uint8),
        coverage=1.0,
        width_m=50.0,
        height_m=375.0,
    )
    image = Image.open(io.BytesIO(encode_elevation(tall)))
    assert max(image.size) == MAX_EDGE_PX
    small = Elevation(
        canvas=np.zeros((80, 40, 3), dtype=np.uint8),
        coverage=1.0,
        width_m=5.0,
        height_m=10.0,
    )
    assert Image.open(io.BytesIO(encode_elevation(small))).size == (40, 80)
