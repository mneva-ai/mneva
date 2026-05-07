from __future__ import annotations

from pathlib import Path

from mneva.store import Record, write_record


class FakeProvider:
    name = "fake"

    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []
        self.next_response = "default"

    def complete(self, prompt: str, *, max_tokens: int) -> str:
        self.calls.append((prompt, max_tokens))
        return self.next_response


def _seed(home: Path) -> None:
    write_record(
        Record(id="a", scope="x", lifespan="permanent", tool="claude", body="alpha body"),
        home=home,
    )
    write_record(
        Record(id="b", scope="x", lifespan="permanent", tool="claude", body="beta body"),
        home=home,
    )
    write_record(
        Record(id="c", scope="y", lifespan="permanent", tool="claude", body="gamma body"),
        home=home,
    )


def test_dump_records_filters_by_scope(tmp_mneva_home: Path) -> None:
    from mneva.synth import dump_records

    _seed(tmp_mneva_home)
    dumped = dump_records(scope="x", home=tmp_mneva_home)
    assert "alpha body" in dumped
    assert "beta body" in dumped
    assert "gamma body" not in dumped


def test_stage1_calls_provider_with_dumped_context(tmp_mneva_home: Path) -> None:
    from mneva.synth import STAGE1_PROMPT, dump_records, stage1

    _seed(tmp_mneva_home)
    dumped = dump_records(scope="x", home=tmp_mneva_home)
    provider = FakeProvider()
    provider.next_response = "1. idea one\n2. idea two"

    out = stage1(provider, dumped, max_tokens=4096)

    assert out == "1. idea one\n2. idea two"
    assert len(provider.calls) == 1
    sent_prompt, sent_max = provider.calls[0]
    assert STAGE1_PROMPT in sent_prompt
    assert "alpha body" in sent_prompt
    assert sent_max == 4096
