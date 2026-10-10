"""Tests for what we added to the starter harness (docs/BRIEF.md section 5).

Like test_agent.py these use a fake model, so they need no key and no internet.
Run from the repo root:  python -m pytest harness
"""

import pytest

from harness import Agent, RunResult, tools

from .test_agent import fake_model, final_answer, tool_request


@pytest.fixture
def demo_tools():
    """Three tools that exercise normal, terminal and pause behaviour."""

    @tools.tool
    def look(query: str):
        """Look something up.

        query: what to look for
        """
        return f"found: {query}"

    @tools.tool(stop=True)
    def decide(choice: str):
        """Make the final decision.

        choice: what was decided
        """
        if choice == "bad":
            return "Error: that choice is not allowed."
        return f"decided: {choice}"

    @tools.tool(pause=True)
    def ask(question: str):
        """Ask the human a question.

        question: what to ask
        """
        if question == "too many":
            return "Error: you have already asked twice."
        return f"asked: {question}"

    yield
    for name in ("look", "decide", "ask"):
        tools.TOOLS.pop(name, None)


# ---------- 1. per-agent tool sets ----------

def test_agent_sends_only_its_own_tools(demo_tools):
    sent = {}

    def generate(contents, config):
        sent["names"] = [getattr(d, "name", None) or d["name"] for d in config.tools[0].function_declarations]
        return final_answer("ok")

    Agent(tools=["look", "decide"], generate=generate).run_task("hi")
    assert sent["names"] == ["look", "decide"]


def test_agent_sends_every_tool_by_default(demo_tools):
    sent = {}

    def generate(contents, config):
        sent["names"] = [getattr(d, "name", None) or d["name"] for d in config.tools[0].function_declarations]
        return final_answer("ok")

    Agent(generate=generate).run_task("hi")
    assert {"look", "decide", "ask", "calculator"} <= set(sent["names"])


def test_unknown_tool_name_is_caught_early(demo_tools):
    with pytest.raises(KeyError):
        Agent(tools=["look", "nope"], generate=fake_model([])).run_task("hi")


# ---------- 2. image input ----------

def test_image_is_sent_as_a_part_before_the_text(tmp_path, demo_tools):
    photo = tmp_path / "leak.jpg"
    photo.write_bytes(b"\xff\xd8\xff\xd9")  # not a real JPEG; we only check it is carried
    seen = {}

    def generate(contents, config):
        seen["parts"] = contents[0].parts
        return final_answer("saw it")

    result = Agent(generate=generate).run_task("what is this?", image_path=str(photo))
    assert result.status == "done"
    assert seen["parts"][0].inline_data.data == b"\xff\xd8\xff\xd9"
    assert seen["parts"][0].inline_data.mime_type == "image/jpeg"
    assert seen["parts"][1].text == "what is this?"
    assert any(s["kind"] == "image" for s in result.steps)


# ---------- 3. terminal tools ----------

def test_terminal_tool_ends_the_run_with_no_extra_model_call(demo_tools):
    model = fake_model([tool_request("decide", {"choice": "merge"})])
    result = Agent(tools=["decide"], generate=model).run_task("decide please")
    assert isinstance(result, RunResult)
    assert (result.status, result.tool, result.result) == ("done", "decide", "decided: merge")
    assert model.sent == [1]  # exactly ONE model call; the old loop always needed two


def test_terminal_tool_that_errors_does_not_end_the_run(demo_tools):
    model = fake_model([tool_request("decide", {"choice": "bad"}),
                        tool_request("decide", {"choice": "good"})])
    result = Agent(tools=["decide"], generate=model).run_task("decide please")
    assert result.result == "decided: good"
    assert model.sent == [1, 3]  # the model saw the error and tried again


# ---------- 4. pause for a human ----------

def test_pause_tool_returns_needs_input_with_the_question(demo_tools):
    model = fake_model([tool_request("ask", {"question": "Kaunsa hostel aur room number?"})])
    result = Agent(tools=["ask"], generate=model).run_task("ac leaking")
    assert result.status == "needs_input"
    assert result.question == "Kaunsa hostel aur room number?"
    assert result.state is not None


def test_resume_continues_the_same_conversation(demo_tools):
    agent = Agent(tools=["ask", "decide"],
                  generate=fake_model([tool_request("ask", {"question": "Which room?"})]))
    paused = agent.run_task("ac leaking", thread_id="t_1")
    assert paused.status == "needs_input"

    turns_before = len(paused.state["contents"])
    agent.generate = fake_model([tool_request("decide", {"choice": "file BH2 E207"})])
    done = agent.resume(paused.state, "BH2 E207")

    assert done.status == "done"
    assert done.result == "decided: file BH2 E207"
    assert len(paused.state["contents"]) > turns_before  # same conversation, not a fresh one
    assert any("BH2 E207" in str(s["text"]) for s in done.steps)


def test_resume_by_thread_id(demo_tools):
    agent = Agent(tools=["ask", "decide"],
                  generate=fake_model([tool_request("ask", {"question": "Which room?"})]))
    agent.run_task("ac leaking", thread_id="t_2")
    agent.generate = fake_model([tool_request("decide", {"choice": "ok"})])
    assert agent.resume("t_2", "BH2 E207").status == "done"


def test_resume_with_an_unknown_thread_is_an_error(demo_tools):
    result = Agent(generate=fake_model([])).resume("t_nope", "hello")
    assert result.status == "error"


def test_pause_tool_that_errors_does_not_pause(demo_tools):
    model = fake_model([tool_request("ask", {"question": "too many"}),
                        tool_request("decide", {"choice": "with what we have"})])
    result = Agent(tools=["ask", "decide"], generate=model).run_task("vague")
    assert result.status == "done"
    assert result.result == "decided: with what we have"


# ---------- 5. step labels and RunResult ----------

def test_steps_carry_a_readable_label(demo_tools):
    model = fake_model([tool_request("look", {"query": "BH2"}), final_answer("all done")])
    agent = Agent(tools=["look"], generate=model,
                  label_fn=lambda name, args: f"Looking for similar reports in {args.get('query')}")
    result = agent.run_task("anything in BH2?")
    assert result.steps[0]["label"] == "Looking for similar reports in BH2"
    assert all(s.get("label") for s in result.steps)


def test_run_result_to_dict_matches_the_api_contract(demo_tools):
    result = Agent(tools=["decide"],
                   generate=fake_model([tool_request("decide", {"choice": "x"})])).run_task("go")
    assert set(result.to_dict()) == {"status", "tool", "result", "question", "steps"}


def test_model_failure_becomes_an_error_result(demo_tools):
    def boom(contents, config):
        raise RuntimeError("network is down")

    result = Agent(generate=boom).run_task("hi")
    assert result.status == "error"
    assert result.result  # a friendly sentence, not a traceback


# ---------- the old entry point still behaves exactly as before ----------

def test_run_still_returns_a_plain_string():
    model = fake_model([tool_request("calculator", {"expression": "17 * 23"}),
                        final_answer("It is 391.")])
    agent = Agent(generate=model)
    assert agent.run("What is 17 * 23?") == "It is 391."
    assert [s["kind"] for s in agent.steps] == ["tool_call", "tool_result", "answer"]
