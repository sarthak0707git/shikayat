"""The tools the model is allowed to ask for.

A tool is a plain Python function. Put @tool above it and the model can use it.
The tool's description comes from its docstring. Its inputs come from its type hints.
Type hints can be str, int, float or bool.

SAFETY: there is no shell tool, no network tool, and no file access outside notes/.
"""

import ast
import inspect
import operator
import typing
from datetime import datetime
from pathlib import Path

TOOLS = {}  # tool name -> {"func": ..., "declaration": ..., "stop": bool, "pause": bool}

_TYPE_NAMES = {str: "string", int: "integer", float: "number", bool: "boolean"}
NOTES_FILE = Path(__file__).resolve().parent.parent / "notes" / "notes.txt"


def tool(func=None, *, stop=False, pause=False):
    """Register a function as a tool the model can ask for.

    Plain:              @tool
    Ends the run:       @tool(stop=True)    the run returns this result, with no extra model round
    Waits for a human:  @tool(pause=True)   the run returns status="needs_input" and can be resumed

    A stop or pause tool whose result starts with "Error" does NOT end the run: the model sees the
    error and gets to try again. That is how the limits in complaints/tools.py are enforced.
    """
    if func is None:  # used as @tool(stop=True)
        return lambda f: _register(f, stop=stop, pause=pause)
    return _register(func, stop=stop, pause=pause)


def _register(func, stop=False, pause=False):
    hints = typing.get_type_hints(func)
    docstring = inspect.cleandoc(func.__doc__ or "")
    properties, required = {}, []
    for name, param in inspect.signature(func).parameters.items():
        py_type = hints.get(name, str)
        if py_type not in _TYPE_NAMES:
            raise TypeError(f"Tool '{func.__name__}': use str, int, float or bool for '{name}'.")
        # A docstring line like "expression: the sum to work out" describes that input.
        lines = [l.strip() for l in docstring.splitlines() if l.strip().startswith(name + ":")]
        description = lines[0].split(":", 1)[1].strip() if lines else name
        properties[name] = {"type": _TYPE_NAMES[py_type], "description": description}
        if param.default is inspect.Parameter.empty:
            required.append(name)

    declaration = {"name": func.__name__, "description": docstring.split("\n\n")[0].replace("\n", " ")}
    if properties:
        declaration["parameters"] = {"type": "object", "properties": properties, "required": required}
    TOOLS[func.__name__] = {"func": func, "declaration": declaration, "stop": stop, "pause": pause}
    return func


def get_declarations(names=None):
    """Declarations for `names`, or for every registered tool when names is None.

    Sending only the tools an agent actually needs keeps the model from wandering into
    unrelated ones, and makes the request smaller.
    """
    if names is None:
        return [t["declaration"] for t in TOOLS.values()]
    missing = [n for n in names if n not in TOOLS]
    if missing:
        raise KeyError(f"No such tool(s): {', '.join(missing)}")
    return [TOOLS[n]["declaration"] for n in names]


def is_stop(name):
    """True if a successful result from this tool should end the run."""
    return bool(TOOLS.get(name, {}).get("stop"))


def is_pause(name):
    """True if this tool hands control back to a human."""
    return bool(TOOLS.get(name, {}).get("pause"))


def _convert(py_type, value):
    """The model sends numbers and text loosely. Turn each value into the type we expect."""
    if py_type is bool and isinstance(value, str):
        return value.strip().lower() == "true"
    return py_type(value)


def run_tool(name, args):
    """Run a tool by name. Always returns text. Problems come back as text starting with 'Error'."""
    if name not in TOOLS:
        return f"Error: there is no tool called '{name}'."
    func = TOOLS[name]["func"]
    hints = typing.get_type_hints(func)
    try:
        clean = {key: _convert(hints.get(key, str), value) for key, value in (args or {}).items()}
        return str(func(**clean))
    except Exception as error:
        return f"Error: {error}"


# ---------- calculator: safe maths, never eval() ----------

_OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
}


def _calc(node):
    """Work out a maths expression. Allows numbers, + - * / ** % and brackets. Nothing else."""
    if isinstance(node, ast.Expression):
        return _calc(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _calc(node.operand)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        left, right = _calc(node.left), _calc(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("That power is too big.")
        result = _OPERATORS[type(node.op)](left, right)
        if isinstance(result, int) and result.bit_length() > 4000:
            raise ValueError("That number is too big.")
        return result
    raise ValueError("Only numbers and + - * / ** % ( ) are allowed.")


@tool
def calculator(expression: str):
    """Work out a maths sum such as (12 + 8) * 3. Allows numbers, + - * / ** % and brackets.

    expression: the sum to work out, for example 2 * (3 + 4)
    """
    if len(expression) > 200:
        raise ValueError("That sum is too long.")
    return _calc(ast.parse(expression.strip(), mode="eval"))


@tool
def get_time():
    """Get the current date and time on this computer."""
    return datetime.now().strftime("%A %d %B %Y, %H:%M")


@tool
def save_note(text: str):
    """Save a short note. The note is added to notes/notes.txt.

    text: the note to save
    """
    NOTES_FILE.parent.mkdir(exist_ok=True)
    with NOTES_FILE.open("a", encoding="utf-8") as file:
        file.write(text[:500].replace("\n", " ") + "\n")
    return "Saved the note."
