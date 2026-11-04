import json

import pytest

from exp001_agent.golden import load_items


@pytest.fixture
def golden(tmp_path):
    path = tmp_path / "items.jsonl"
    items = [{"id": "ts-001", "split": "dev"}, {"id": "ts-002", "split": "test"}]
    path.write_text("\n".join(json.dumps(item) for item in items) + "\n", encoding="utf-8")
    return path


def test_loads_the_dev_split_only(golden):
    assert [item["id"] for item in load_items(golden, "dev")] == ["ts-001"]


def test_refuses_the_test_split_outside_the_final_run(golden):
    with pytest.raises(PermissionError, match="final"):
        load_items(golden, "test")


def test_gives_the_test_split_for_the_final_run(golden):
    assert [item["id"] for item in load_items(golden, "test", final=True)] == ["ts-002"]
