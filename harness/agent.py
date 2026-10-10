"""The harness loop: the model asks for a tool, we run it, and we give the answer back.

The starter version of this file was text-only, stateless, sent every registered tool on
every call, and always needed one extra model round just to write a final answer. What we
added, and why (docs/BRIEF.md section 5):

  1. Per-agent tool sets      Agent(tools=["find_similar", "file_new"]) sends only those.
  2. Image input              run_task(question, image_path=...) adds the photo as a Part.
  3. Terminal tools           @tool(stop=True) ends the run with its own result. No extra round.
  4. Pause for a human        @tool(pause=True) returns status="needs_input"; resume() continues
                              the same conversation once a human has answered.
  5. Step labels              every step carries a human-readable `label` a UI can show.

Together these take one complaint from four model calls down to two.

Old callers are unaffected:
    agent = Agent(system="You are a helpful assistant.", verbose=True)
    print(agent.run("What is 17 * 23?"))        # still returns a plain string

New callers get structure:
    result = Agent(tools=["find_similar"], system=PROMPT).run_task(text, image_path="x.jpg")
    if result.status == "needs_input":
        result = agent.resume(result.state, "BH2 E207")
"""

import mimetypes
from dataclasses import dataclass, field
from pathlib import Path

from google.genai import types

import gemma_client

from . import tools as toolbox

# Resumable runs, keyed by thread_id. In memory on purpose: this is a demo, and a restart
# losing half-finished conversations is an acceptable trade for having no extra moving parts.
# Production would put this in Redis or a `threads` table.
THREADS = {}
MAX_THREADS = 200


def _remember(thread_id, state):
    """Save a paused run, discarding the oldest once there are too many."""
    THREADS[thread_id] = state
    while len(THREADS) > MAX_THREADS:
        THREADS.pop(next(iter(THREADS)))


@dataclass
class RunResult:
    """What one run of the loop produced.

    status: done        the model (or a terminal tool) finished the job
            needs_input a pause tool wants a human to answer `question` before deciding
            stopped     hit max_steps without finishing
            error       the model call itself failed
    """

    status: str
    result: str = ""
    tool: str | None = None
    question: str | None = None
    steps: list = field(default_factory=list)
    state: dict | None = None

    def to_dict(self):
        return {"status": self.status, "tool": self.tool, "result": self.result,
                "question": self.question, "steps": self.steps}


def _image_part(image_path):
    """A photo as an inline Part. Falls back to the Files API if inline bytes are refused."""
    path = Path(image_path)
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return types.Part.from_bytes(data=path.read_bytes(), mime_type=mime)


def _uploaded_part(image_path):
    """The documented path for Gemma on the Gemini API: upload, then reference the file."""
    return gemma_client.get_client().files.upload(file=str(image_path))


class Agent:
    def __init__(self, system=None, max_steps=5, verbose=False, generate=None, tools=None,
                 label_fn=None):
        self.system = system
        self.max_steps = max_steps  # the most tool rounds before we stop
        self.verbose = verbose  # True prints each step as it happens
        self.generate = generate or gemma_client.generate_raw  # tests swap in a fake
        self.tool_names = list(tools) if tools else None  # None means "every registered tool"
        self.label_fn = label_fn  # (tool_name, args) -> a sentence a student can read
        self.steps = []  # a list a screen can show: {"kind": ..., "text": ..., "label": ...}

    # ---------- internals ----------

    def _log(self, kind, text, label=None):
        step = {"kind": kind, "text": text, "label": label or _default_label(kind, text)}
        self.steps.append(step)
        if self.verbose:
            print(f"[{kind}] {step['label']}")
        return step

    def _config(self):
        return types.GenerateContentConfig(
            system_instruction=self.system,
            tools=[types.Tool(function_declarations=toolbox.get_declarations(self.tool_names))],
        )

    def _label(self, name, args):
        if self.label_fn:
            try:
                return self.label_fn(name, args)
            except Exception:
                pass
        return f"Running {name.replace('_', ' ')}"

    # ---------- the old entry point, unchanged behaviour ----------

    def run(self, question):
        """Ask the model a question and get its final answer as a string.

        Kept exactly as it was so existing callers and tests keep working.
        """
        self.steps = []
        contents = [types.Content(role="user", parts=[types.Part(text=question)])]
        config = self._config()

        for _ in range(self.max_steps):
            response = self.generate(contents, config)
            calls = response.function_calls

            # No tool request means the model gave its final answer.
            if not calls:
                answer = response.text or ""
                self._log("answer", answer)
                return answer

            # Keep the model's own turn in the conversation, then answer each request.
            contents.append(response.candidates[0].content)
            replies = []
            for call in calls:
                args = dict(call.args or {})
                self._log("tool_call", f"Model asked to run {call.name} with {args}",
                          self._label(call.name, args))
                result = toolbox.run_tool(call.name, args)
                self._log("tool_result", f"Our code returned: {result}")
                reply = types.FunctionResponse(id=call.id, name=call.name, response={"result": result})
                replies.append(types.Part(function_response=reply))
            contents.append(types.Content(role="user", parts=replies))

        message = f"Stopped after {self.max_steps} steps without a final answer. Try a simpler question."
        self._log("stopped", message)
        return message

    # ---------- the new entry point ----------

    def run_task(self, question, image_path=None, thread_id=None):
        """Run the loop over one task, optionally with a photo, and return a RunResult."""
        self.steps = []
        parts = []
        if image_path:
            try:
                parts.append(_image_part(image_path))
                self._log("image", f"Attached {Path(image_path).name} inline",
                          "Looking at the photo")
            except Exception as error:  # inline bytes refused: use the Files API instead
                self._log("image", f"Inline bytes failed ({error}); uploading instead",
                          "Uploading the photo")
                parts.append(_uploaded_part(image_path))
        parts.append(types.Part(text=question))

        contents = [types.Content(role="user", parts=parts)]
        return self._loop(contents, thread_id)

    def resume(self, state, answer):
        """Continue a paused run once a human has answered the question."""
        if isinstance(state, str):  # a thread_id
            state = THREADS.get(state)
        if not state:
            return RunResult(status="error", result="Error: that conversation has expired.")

        self.steps = list(state.get("steps") or [])
        # A copy: a failed resume must not leave the saved conversation half-advanced,
        # or a retry would send two responses for the same call.
        contents = list(state["contents"])
        pending = state.get("pending") or {}

        # If the model asked for several tools in one turn, the ones that ran before the
        # pause already have results. They have to go back in the SAME user turn, or the
        # conversation has more function calls than function responses.
        parts = list(state.get("pending_replies") or [])
        if pending:
            parts.append(types.Part(function_response=types.FunctionResponse(
                id=pending.get("id"), name=pending["name"],
                response={"result": f"The student answered: {answer}"})))
        parts.append(types.Part(text=f"The student answered: {answer}"))
        contents.append(types.Content(role="user", parts=parts))

        self._log("answer_in", f"The student answered: {answer}", "Got the student's reply")
        return self._loop(contents, state.get("thread_id"))

    def _loop(self, contents, thread_id):
        config = self._config()

        for _ in range(self.max_steps):
            try:
                response = self.generate(contents, config)
            except Exception as error:
                message = gemma_client.describe_error(error)
                self._log("error", message, "Gemma could not be reached")
                return RunResult(status="error", result=message, steps=self.steps)

            calls = response.function_calls
            if not calls:
                answer = response.text or ""
                self._log("answer", answer, "Done")
                return RunResult(status="done", result=answer, steps=self.steps)

            contents.append(response.candidates[0].content)
            replies = []
            for call in calls:
                args = dict(call.args or {})
                self._log("tool_call", f"Model asked to run {call.name} with {args}",
                          self._label(call.name, args))
                result = toolbox.run_tool(call.name, args)
                self._log("tool_result", f"Our code returned: {result}")
                failed = result.startswith("Error")

                # A pause tool hands the conversation back to a human.
                if toolbox.is_pause(call.name) and not failed:
                    question = args.get("question") or result
                    state = {"contents": contents, "pending": {"id": call.id, "name": call.name},
                             "pending_replies": replies, "steps": list(self.steps),
                             "thread_id": thread_id}
                    if thread_id:
                        _remember(thread_id, state)
                    return RunResult(status="needs_input", tool=call.name, result=result,
                                     question=question, steps=self.steps, state=state)

                # A terminal tool ends the run with its own result. No extra model round.
                if toolbox.is_stop(call.name) and not failed:
                    if thread_id:
                        THREADS.pop(thread_id, None)
                    return RunResult(status="done", tool=call.name, result=result, steps=self.steps)

                reply = types.FunctionResponse(id=call.id, name=call.name, response={"result": result})
                replies.append(types.Part(function_response=reply))
            contents.append(types.Content(role="user", parts=replies))

        message = f"Stopped after {self.max_steps} steps without a decision."
        self._log("stopped", message, "Gave up after too many steps")
        return RunResult(status="stopped", result=message, steps=self.steps)


def _default_label(kind, text):
    return {"tool_call": "Working on it", "tool_result": "Got a result",
            "answer": "Done", "stopped": "Gave up", "error": "Something went wrong"}.get(kind, kind)
