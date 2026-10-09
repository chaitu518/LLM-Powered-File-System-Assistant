"""
llm_file_assistant.py - Part B: connects the tools in fs_tools.py to an LLM.

Usage:
    python llm_file_assistant.py "Find resumes mentioning Python experience"
    python llm_file_assistant.py            (interactive mode, type 'exit' to quit)

Needs the OPENROUTER_API_KEY environment variable.
"""

import json
import os
import sys

from openai import OpenAI
from pydantic import BaseModel, Field

from fs_tools import list_files, read_file, search_in_file, write_file

MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")

SYSTEM = (
    "You are a resume assistant. Resumes are stored in the 'resumes' folder. "
    "Use the tools to list, read, search and write files. "
    "Save any files you create in the 'summaries' folder. "
    "When asked for a summary, write 3 to 4 sentences in plain text, not a copy of the resume."
)


# ---- 1. Tool arguments, described with Pydantic -------------------------
# Field names must match the parameter names of the Python functions.

class ListFilesArgs(BaseModel):
    """List files in a directory with name, path, size and modified date. Optionally filter by extension."""
    directory: str = Field(description="Folder to list, e.g. 'resumes'")
    extension: str = Field("", description="Optional filter, e.g. '.pdf'. Leave empty for all files.")


class ReadFileArgs(BaseModel):
    """Read a resume file (PDF, TXT or DOCX) and return its full text and metadata."""
    filepath: str = Field(description="Path to the file, e.g. 'resumes/resume_john_doe.pdf'")


class WriteFileArgs(BaseModel):
    """Write text content to a file. Creates folders if needed."""
    filepath: str = Field(description="Where to save, e.g. 'summaries/john_doe_summary.txt'")
    content: str = Field(description="The text to write")


class SearchInFileArgs(BaseModel):
    """Case-insensitive keyword search inside one file. Returns matches with surrounding text."""
    filepath: str = Field(description="Path to the file to search")
    keyword: str = Field(description="Word or phrase to look for, e.g. 'Python'")


# ---- 2. Registry: tool name -> (function, argument model) ---------------

REGISTRY = {
    "list_files":     (list_files,     ListFilesArgs),
    "read_file":      (read_file,      ReadFileArgs),
    "write_file":     (write_file,     WriteFileArgs),
    "search_in_file": (search_in_file, SearchInFileArgs),
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": name,
            "description": model.__doc__,
            "parameters": model.model_json_schema(),
        },
    }
    for name, (func, model) in REGISTRY.items()
]


# ---- 3. Run one tool call requested by the model ------------------------

def run_tool(call):
    """Look up the tool, validate its arguments, run it. Errors come back as data."""
    try:
        func, ArgsModel = REGISTRY[call.function.name]
        args = ArgsModel.model_validate_json(call.function.arguments)
        return func(**args.model_dump())
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}


# ---- 4. The tool-calling loop -------------------------------------------

def ask(client, query, max_steps=10):
    """Send a query, run whatever tools the model requests, return its final answer."""
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": query},
    ]

    for step in range(max_steps):
        reply = client.chat.completions.create(
            model=MODEL, messages=messages, temperature=0, tools=TOOLS, tool_choice="auto",
        )
        msg = reply.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:          # no tool requested: this is the final answer
            return msg.content

        for call in msg.tool_calls:     # run every tool the model asked for
            print(f"  [tool] {call.function.name}({call.function.arguments})")
            result = run_tool(call)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result),
            })

    return "Stopped: too many steps."


def main():
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        sys.exit("Set the OPENROUTER_API_KEY environment variable first.")

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    if len(sys.argv) > 1:               # one query passed on the command line
        print(ask(client, " ".join(sys.argv[1:])))
        return

    print("Resume assistant. Type a question, or 'exit' to quit.")
    while True:
        query = input("\nYou: ").strip()
        if query.lower() in ("exit", "quit"):
            break
        if query:
            print(ask(client, query))


if __name__ == "__main__":
    main()
