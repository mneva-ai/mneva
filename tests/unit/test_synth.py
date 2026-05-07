from __future__ import annotations

from pathlib import Path

import pytest

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


def test_stage2_sends_shortlist_with_critical_pass_prompt() -> None:
    from mneva.synth import STAGE2_PROMPT, stage2

    provider = FakeProvider()
    provider.next_response = "criticism here"
    shortlist = "1. ship in 7 days\n2. only 4 backends"

    out = stage2(provider, shortlist, max_tokens=2048)

    assert out == "criticism here"
    sent_prompt, sent_max = provider.calls[0]
    assert STAGE2_PROMPT in sent_prompt
    assert shortlist in sent_prompt
    assert sent_max == 2048


def test_synthesize_2stage_full_loop(tmp_mneva_home: Path) -> None:
    from mneva.synth import synthesize_2stage

    _seed(tmp_mneva_home)
    provider = FakeProvider()
    responses = iter(["IDEAS_1_TO_100", "CRITICAL_PASS_OUTPUT"])

    def fake_complete(prompt: str, *, max_tokens: int) -> str:
        return next(responses)

    provider.complete = fake_complete  # type: ignore[method-assign]

    captured_outputs: list[str] = []
    shortlist_input_calls: list[str] = []

    def shortlist_input(stage1_output: str) -> str:
        shortlist_input_calls.append(stage1_output)
        return "1. keep idea seven\n2. keep idea forty-two"

    synthesize_2stage(
        provider,
        scope="x",
        home=tmp_mneva_home,
        shortlist_input=shortlist_input,
        output=captured_outputs.append,
    )

    assert shortlist_input_calls == ["IDEAS_1_TO_100"]
    assert captured_outputs == ["IDEAS_1_TO_100", "CRITICAL_PASS_OUTPUT"]


def test_synthesize_2stage_empty_scope_aborts(tmp_mneva_home: Path) -> None:
    from mneva.synth import synthesize_2stage

    provider = FakeProvider()
    outputs: list[str] = []

    with pytest.raises(ValueError, match="no records"):
        synthesize_2stage(
            provider,
            scope="empty-scope",
            home=tmp_mneva_home,
            shortlist_input=lambda _s: "ignored",
            output=outputs.append,
        )
