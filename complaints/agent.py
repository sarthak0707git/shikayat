"""One report in, one ReportResult out.

Two Gemma calls per complaint:
    1. the report (and the photo) -> Gemma calls find_similar
    2. the find_similar result    -> Gemma calls file_new / merge_into / ask_student / reject

Those four are terminal or pause tools in the harness, so the run ends on the second call.
The starter's loop would have needed a third and fourth call to write a final answer.
"""

import uuid

from complaints import prompt
from complaints import tools as complaint_tools
from harness import Agent

# thread_id -> {"agent": Agent, "ctx": dict, "state": dict}
THREADS = {}
MAX_OPEN_THREADS = 200


def _new_thread_id():
    return "t_" + uuid.uuid4().hex[:6]


def _make_agent():
    return Agent(
        system=prompt.build(),
        tools=complaint_tools.TOOL_NAMES,
        label_fn=complaint_tools.label_for,
        max_steps=4,
    )


def _result(thread_id, run, ctx):
    """Turn a harness RunResult plus the triage context into the API's ReportResult."""
    steps = [{"kind": step["kind"], "label": step["label"]} for step in run.steps
             if step["kind"] in ("tool_call", "image", "answer_in")]

    if run.status == "needs_input":
        return {"thread_id": thread_id, "status": "needs_input",
                "message": "Gemma needs one more detail before filing this.",
                "question": run.question, "complaint": None, "steps": steps}

    if run.status == "error":
        return {"thread_id": thread_id, "status": "error",
                "message": run.result or "Gemma could not be reached. Please try again.",
                "question": None, "complaint": None, "steps": steps}

    outcome = ctx.get("outcome")
    if outcome in ("filed", "merged"):
        return {"thread_id": thread_id, "status": outcome,
                "message": ctx.get("message") or run.result,
                "question": None, "complaint": ctx.get("complaint"), "steps": steps}
    if outcome == "rejected":
        return {"thread_id": thread_id, "status": "rejected",
                "message": ctx.get("message") or run.result,
                "question": None, "complaint": None, "steps": steps}

    # Gemma answered in prose without committing to a tool, or ran out of steps.
    return {"thread_id": thread_id, "status": "error",
            "message": "Gemma could not decide what to do with this. Please try rewording it.",
            "question": None, "complaint": None, "steps": steps}


def _forget_old_threads():
    while len(THREADS) > MAX_OPEN_THREADS:
        THREADS.pop(next(iter(THREADS)))


def handle_report(text, photo_path=None, thread_id=None):
    """Triage one new report. Returns a ReportResult dict (section 6 of the brief)."""
    thread_id = thread_id or _new_thread_id()
    ctx = complaint_tools.new_context(text, photo_path=photo_path, thread_id=thread_id)
    token = complaint_tools.CURRENT.set(ctx)
    try:
        agent = _make_agent()
        question = text if not photo_path else f"{text}\n\n(The student also attached a photo.)"
        run = agent.run_task(question, image_path=photo_path, thread_id=thread_id)
    finally:
        complaint_tools.CURRENT.reset(token)

    if run.status == "needs_input":
        THREADS[thread_id] = {"agent": agent, "ctx": ctx, "state": run.state}
        _forget_old_threads()
    else:
        THREADS.pop(thread_id, None)
    return _result(thread_id, run, ctx)


def handle_answer(thread_id, answer):
    """Continue a paused report once the student has answered Gemma's question."""
    thread = THREADS.get(thread_id)
    if not thread:
        return {"thread_id": thread_id, "status": "error",
                "message": "That conversation has expired. Please send the report again.",
                "question": None, "complaint": None, "steps": []}

    ctx, agent = thread["ctx"], thread["agent"]
    for followup in reversed(ctx["followups"]):
        if followup["a"] is None:
            followup["a"] = answer
            break
    ctx["pending_question"] = None

    token = complaint_tools.CURRENT.set(ctx)
    try:
        run = agent.resume(thread["state"], answer)
    finally:
        complaint_tools.CURRENT.reset(token)

    if run.status == "needs_input":
        thread["state"] = run.state
    else:
        THREADS.pop(thread_id, None)
    return _result(thread_id, run, ctx)
