"""Durable exploration control-plane and API recovery coverage."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import explorations as exploration_api
from app.exploration.model_gateway import NoModelGateway
from app.exploration.worker import ExplorationWorker
from app.main import create_app
from app.schemas.exploration import ImportExplorationRequest, SourceFormat
from app.services.exploration_service import ExplorationStore


def test_snapshot_recovers_without_copying_private_text_into_sqlite(tmp_path):
    state_dir = tmp_path / "state"
    private_phrase = "只应存在于私有来源与快照文件中的句子"
    first_store = ExplorationStore(state_dir=state_dir)
    created = first_store.create(
        ImportExplorationRequest(
            source_format=SourceFormat.MARKDOWN,
            content=f"# 私有书籍\n\n{private_phrase}",
        )
    )
    database_bytes = (state_dir / "explorations.sqlite3").read_bytes()
    assert private_phrase.encode("utf-8") not in database_bytes
    assert str(state_dir).encode("utf-8") not in database_bytes
    first_store.close()

    rebuilt_store = ExplorationStore(state_dir=state_dir)
    recovered = rebuilt_store.get(created.id)
    assert recovered.model_dump(mode="json") == created.model_dump(mode="json")
    rebuilt_store.close()


def test_analysis_run_api_is_typed_durable_and_worker_external(tmp_path, monkeypatch):
    store = ExplorationStore(state_dir=tmp_path / "state")
    monkeypatch.setattr(exploration_api, "exploration_store", store)
    client = TestClient(create_app(enable_private_explorations=True, mount_tiles=False))
    imported = client.post(
        "/api/explorations/import",
        json={
            "source_format": "markdown",
            "content": "# 第一章\n\n755 年，军队抵达范阳。\n\n# 第二章\n\n因此局势发生变化。",
        },
    ).json()

    created = client.post(
        f"/api/explorations/{imported['id']}/analysis-runs",
        json={"base_revision": imported["revision"]},
    )
    assert created.status_code == 201, created.text
    run = created.json()
    assert run["state"] == "queued"
    assert run["dispatch"] == "external_worker_required"
    assert run["work_items"]
    assert "content" not in created.text
    assert str(tmp_path) not in created.text

    listed = client.get(
        f"/api/explorations/{imported['id']}/analysis-runs"
    ).json()
    assert [item["id"] for item in listed["items"]] == [run["id"]]
    cancelled = client.post(
        f"/api/explorations/{imported['id']}/analysis-runs/{run['id']}/cancel"
    ).json()
    assert cancelled["state"] == "cancelled"
    resumed = client.post(
        f"/api/explorations/{imported['id']}/analysis-runs/{run['id']}/resume"
    ).json()
    assert resumed["state"] == "queued"

    response = client.delete(f"/api/explorations/{imported['id']}")
    assert response.status_code == 204
    assert not (tmp_path / "state" / "vault" / imported["id"]).exists()
    store.close()


def test_analysis_result_and_review_api_resume_only_through_worker(
    tmp_path, monkeypatch
):
    gateway = NoModelGateway()
    store = ExplorationStore(
        state_dir=tmp_path / "state",
        model_gateway=gateway,
    )
    monkeypatch.setattr(exploration_api, "exploration_store", store)
    client = TestClient(create_app(enable_private_explorations=True, mount_tiles=False))
    imported = client.post(
        "/api/explorations/import",
        json={
            "source_format": "markdown",
            "content": "# 第一章\n\n755 年，军队抵达范阳。",
        },
    ).json()
    run = client.post(
        f"/api/explorations/{imported['id']}/analysis-runs",
        json={"base_revision": imported["revision"]},
    ).json()
    worker = ExplorationWorker(store.control_plane, gateway)
    assert worker.process_next().state == "waiting_review"

    result_response = client.get(
        f"/api/explorations/{imported['id']}/analysis-runs/{run['id']}/result"
    )
    assert result_response.status_code == 200, result_response.text
    result = result_response.json()
    assert result["review_required"] is True
    assert result["review_submitted"] is False
    assert result["artifacts"]["claims"] == []
    assert result["published_projections"]["timeline"]["items"] == []

    reviewed = client.post(
        f"/api/explorations/{imported['id']}/analysis-runs/{run['id']}/review",
        json={"review_token": result["review_token"], "decisions": []},
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"]["state"] == "waiting_review"
    assert reviewed.json()["review_submitted"] is True

    # HTTP stores only the decision. The independent worker owns the resume.
    assert client.get(
        f"/api/explorations/{imported['id']}/analysis-runs/{run['id']}"
    ).json()["state"] == "waiting_review"
    assert worker.process_next().state == "completed"
    final = client.get(
        f"/api/explorations/{imported['id']}/analysis-runs/{run['id']}/result"
    ).json()
    assert final["status"]["state"] == "completed"
    assert final["review_required"] is False
    store.close()
