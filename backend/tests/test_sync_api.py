"""POST /api/v1/sync/batch — replaying the queue a phone built while offline.

The client that calls this is already written and it is strict. From
`frontend/src/lib/queue.ts`: every `scan_id` sent must come back in exactly one
of `results` or `failed`, no id may appear twice, no id may come back that was
not sent, every entry in `results` must have `analysis_mode === "full"`, and
every entry in `failed` needs an integer status between 400 and 599 plus a Thai
message. Anything else and the client throws and the queue stays unsent.

The contract is docs/DESIGN.md section 8.2. The part worth reading twice is
that items and files are matched **by scan_id, not by position**: an off-by-one
would attach a diagnosis to the wrong photograph, and a worker would treat the
wrong plot.
"""

import io
import json
import uuid

import cv2
import numpy as np
import pytest
from PIL import Image

from app.api.v1.scan import get_runner
from app.core.config import get_settings

LEAF_GREEN = (54, 122, 58)
SOIL = (92, 74, 62)


def _leaf_png(seed: int = 3, size: int = 320) -> bytes:
    frame = np.full((size, size, 3), SOIL, dtype=np.uint8)
    cv2.ellipse(frame, (size // 2, size // 2), (120, 80), 0, 0, 360, LEAF_GREEN, -1)
    rng = np.random.default_rng(seed)
    grain = rng.integers(-16, 17, frame.shape, dtype=np.int16)
    frame = np.clip(frame.astype(np.int16) + grain, 0, 255).astype(np.uint8)
    buffer = io.BytesIO()
    Image.fromarray(frame).save(buffer, format="PNG")
    return buffer.getvalue()


def _blurry_png() -> bytes:
    frame = np.full((320, 320, 3), SOIL, dtype=np.uint8)
    cv2.ellipse(frame, (160, 160), (120, 80), 0, 0, 360, LEAF_GREEN, -1)
    frame = cv2.GaussianBlur(frame, (61, 61), 0)
    buffer = io.BytesIO()
    Image.fromarray(frame).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def fake_model(app):
    def install(logits: list[float]):
        def runner(tensor: np.ndarray) -> np.ndarray:
            return np.array([logits], dtype=np.float32)

        app.dependency_overrides[get_runner] = lambda: runner

    yield install
    app.dependency_overrides.pop(get_runner, None)


def _item(scan_id: str, class_name: str = "grey_blight", confidence: float = 0.8):
    return {
        "scan_id": scan_id,
        "captured_at": "2026-10-20T08:30:00+07:00",
        "local_prediction": {"class_name": class_name, "confidence": confidence},
    }


def _post(client, items, files):
    return client.post(
        "/api/v1/sync/batch",
        data={"items": json.dumps(items)},
        files=[("images", (name, payload, "image/png")) for name, payload in files],
    )


def test_a_batch_of_two_returns_two_full_results(client, fake_model) -> None:
    fake_model([9.0, 0.0, 0.0, 0.0, 0.0])
    first, second = str(uuid.uuid4()), str(uuid.uuid4())

    response = _post(
        client,
        [_item(first), _item(second)],
        [(first, _leaf_png(1)), (second, _leaf_png(2))],
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"results", "failed"}
    assert body["failed"] == []
    assert {entry["scan_id"] for entry in body["results"]} == {first, second}
    for entry in body["results"]:
        assert entry["analysis_mode"] == "full"
        assert entry["captured_at"] == "2026-10-20T08:30:00+07:00"
        assert set(entry) >= {"prediction", "burn_analysis", "severity", "advice"}


def test_items_and_files_are_matched_by_scan_id_not_by_position(
    client, fake_model
) -> None:
    """The assertion that stops a diagnosis landing on the wrong photograph."""
    fake_model([9.0, 0.0, 0.0, 0.0, 0.0])
    first, second = str(uuid.uuid4()), str(uuid.uuid4())

    # Items in one order, files in the other.
    response = _post(
        client,
        [_item(first), _item(second)],
        [(second, _leaf_png(2)), (first, _leaf_png(1))],
    )

    assert response.status_code == 200, response.text
    assert {entry["scan_id"] for entry in response.json()["results"]} == {first, second}


def test_every_scan_id_sent_comes_back_exactly_once(client, fake_model) -> None:
    fake_model([9.0, 0.0, 0.0, 0.0, 0.0])
    ids = [str(uuid.uuid4()) for _ in range(3)]
    payloads = [_leaf_png(1), _blurry_png(), _leaf_png(3)]

    body = _post(
        client,
        [_item(scan_id) for scan_id in ids],
        list(zip(ids, payloads, strict=False)),
    ).json()

    returned = [entry["scan_id"] for entry in body["results"] + body["failed"]]
    assert sorted(returned) == sorted(ids)
    assert len(returned) == len(set(returned))


def test_one_unusable_frame_does_not_fail_the_batch(client, fake_model) -> None:
    fake_model([9.0, 0.0, 0.0, 0.0, 0.0])
    good, bad = str(uuid.uuid4()), str(uuid.uuid4())

    body = _post(
        client,
        [_item(good), _item(bad)],
        [(good, _leaf_png(1)), (bad, _blurry_png())],
    ).json()

    assert [entry["scan_id"] for entry in body["results"]] == [good]
    assert len(body["failed"]) == 1
    failure = body["failed"][0]
    assert failure["scan_id"] == bad
    assert failure["status"] == 422
    assert 400 <= failure["status"] <= 599
    assert failure["detail_th"] == "ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น"
    assert failure["detail"]


def test_an_item_with_no_file_is_a_422_for_the_whole_request(client, fake_model) -> None:
    fake_model([9.0, 0.0, 0.0, 0.0, 0.0])
    present, missing = str(uuid.uuid4()), str(uuid.uuid4())

    response = _post(client, [_item(present), _item(missing)], [(present, _leaf_png())])

    assert response.status_code == 422
    assert missing in response.json()["detail"]
    assert response.json()["detail_th"]


def test_a_file_with_no_item_is_a_422_for_the_whole_request(client, fake_model) -> None:
    fake_model([9.0, 0.0, 0.0, 0.0, 0.0])
    claimed, extra = str(uuid.uuid4()), str(uuid.uuid4())

    response = _post(
        client, [_item(claimed)], [(claimed, _leaf_png()), (extra, _leaf_png())]
    )

    assert response.status_code == 422
    assert extra in response.json()["detail"]


def test_too_many_items_is_refused(client, fake_model) -> None:
    fake_model([9.0, 0.0, 0.0, 0.0, 0.0])
    settings = get_settings()
    ids = [str(uuid.uuid4()) for _ in range(settings.max_batch_items + 1)]

    response = _post(
        client,
        [_item(scan_id) for scan_id in ids],
        [(scan_id, _leaf_png()) for scan_id in ids],
    )

    assert response.status_code == 422
    assert str(settings.max_batch_items) in response.json()["detail"]


def test_malformed_items_is_refused_rather_than_guessed(client, fake_model) -> None:
    fake_model([9.0, 0.0, 0.0, 0.0, 0.0])
    scan_id = str(uuid.uuid4())

    for payload in ("not json", "{}", '[{"captured_at": "x"}]', '["a"]'):
        response = client.post(
            "/api/v1/sync/batch",
            data={"items": payload},
            files=[("images", (scan_id, _leaf_png(), "image/png"))],
        )
        assert response.status_code == 422, payload
        assert set(response.json()) >= {"detail", "detail_th"}


def test_a_local_prediction_is_recorded_and_never_used_as_the_answer(
    client, fake_model
) -> None:
    # The phone said healthy; the server's model says grey blight. The server
    # answers, and the client's guess does not leak into the result.
    fake_model([9.0, 0.0, 0.0, 0.0, 0.0])
    scan_id = str(uuid.uuid4())

    body = _post(
        client,
        [_item(scan_id, class_name="healthy", confidence=0.99)],
        [(scan_id, _leaf_png())],
    ).json()

    assert body["results"][0]["prediction"]["class_name"] == "grey_blight"


def test_a_replayed_scan_id_returns_the_stored_result(client, fake_model) -> None:
    """Idempotency, section 8.3. A dropped connection means retries are normal."""
    fake_model([9.0, 0.0, 0.0, 0.0, 0.0])
    scan_id = str(uuid.uuid4())
    payload = _leaf_png()

    first = _post(client, [_item(scan_id)], [(scan_id, payload)]).json()["results"][0]
    assert first.get("replayed") in (None, False)

    second = _post(client, [_item(scan_id)], [(scan_id, payload)]).json()["results"][0]

    assert second["replayed"] is True
    assert second["scan_id"] == first["scan_id"]
    assert second["prediction"] == first["prediction"]
    assert second["severity"] == first["severity"]


def test_a_repeated_scan_is_not_analysed_twice(client, fake_model) -> None:
    # Not a performance test: a second analysis would produce a second history
    # entry on the client and a second diagnosis for one photograph.
    calls = {"count": 0}

    def counting(_tensor):
        calls["count"] += 1
        return np.array([[9.0, 0.0, 0.0, 0.0, 0.0]], dtype=np.float32)

    client.app.dependency_overrides[get_runner] = lambda: counting
    try:
        scan_id = str(uuid.uuid4())
        files = {"image": ("leaf.png", _leaf_png(), "image/png")}
        client.post("/api/v1/scan", files=files, data={"scan_id": scan_id})
        assert calls["count"] == 1

        again = client.post(
            "/api/v1/scan",
            files={"image": ("leaf.png", _leaf_png(), "image/png")},
            data={"scan_id": scan_id},
        )
        assert calls["count"] == 1, "the model ran again on a replay"
        assert again.json()["replayed"] is True
    finally:
        client.app.dependency_overrides.pop(get_runner, None)
