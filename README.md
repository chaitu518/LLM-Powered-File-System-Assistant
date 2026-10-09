# LLM-Powered File System Assistant

A small assistant that lets an LLM work with resume files through **function calling (tool use)**.
The model decides which tool to call, the Python code runs it, and the result goes back to the
model until it can answer.

This is tool calling, not RAG: there are no embeddings, chunks or vector database. Retrieval is
keyword-based and driven by the model's own tool calls.

## Project structure

```
├── fs_tools.py               Part A: the four file system tools
├── llm_file_assistant.py     Part B: tool schemas, registry and the tool-calling loop
├── generate_sample_data.py   Recreates the sample resumes
├── requirements.txt
└── resumes/                  10 dummy resumes (4 PDF, 3 DOCX, 3 TXT)
```

## The tools (`fs_tools.py`)

| Tool | What it does |
|---|---|
| `read_file(filepath)` | Reads a PDF, DOCX or TXT file. Returns text content and metadata. |
| `list_files(directory, extension=None)` | Lists files with name, path, size and modified date. Optional extension filter. |
| `write_file(filepath, content)` | Writes text to a file, creating folders if needed. |
| `search_in_file(filepath, keyword)` | Case-insensitive keyword search. Returns matches with surrounding text. |

Tools never raise on bad input. They return `{"success": False, "error": "..."}` so the model can
read the error and recover, for example by listing the folder after a wrong filename.

## Setup

Requires Python 3.10 or newer.

```bash
pip install -r requirements.txt
```

Get an API key from [openrouter.ai](https://openrouter.ai) and set it as an environment variable:

```bash
# macOS / Linux
export OPENROUTER_API_KEY="your-key"

# Windows (PowerShell)
$env:OPENROUTER_API_KEY="your-key"
```

The default model is `openai/gpt-4o-mini`. To use another model that supports tool calling, set
`OPENROUTER_MODEL`.

## Usage

Run one query:

```bash
python llm_file_assistant.py "Find resumes mentioning Python experience"
```

Or start interactive mode (type `exit` to quit):

```bash
python llm_file_assistant.py
```

Example queries:

- `Read all resumes in the resumes folder`
- `Find resumes mentioning Python experience`
- `Create a summary file for resume_john_doe.pdf`

Each tool call is printed as it happens:

```
  [tool] list_files({"directory":"resumes"})
  [tool] search_in_file({"filepath": "resumes/resume_ahmed_khan.docx", "keyword": "Python"})
  ...
```

Files the assistant creates are saved in `summaries/`.

### Using the tools directly

```python
from fs_tools import list_files, read_file, search_in_file, write_file

list_files("resumes", ".pdf")
read_file("resumes/resume_john_doe.pdf")
search_in_file("resumes/resume_john_doe.pdf", "python")
write_file("summaries/note.txt", "hello")
```

## How it works (`llm_file_assistant.py`)

1. **Tool descriptions.** Each tool's arguments are a Pydantic model. Its docstring becomes the
   tool description and `model_json_schema()` produces the JSON schema sent to the model.
2. **Registry.** A dict maps each tool name to its Python function and its Pydantic model.
3. **`run_tool`.** Looks up the tool the model asked for, validates the arguments with Pydantic,
   runs the function, and returns any error as data.
4. **`ask`.** The loop. It sends the conversation to the model. If the reply contains tool calls,
   it runs them, appends the results, and asks again. If the reply is plain text, that is the
   final answer. A step limit stops runaway loops.

## Sample data

The `resumes/` folder holds 10 fictional resumes with overlapping technologies, so different
searches return different sets. Regenerate them with:

```bash
python generate_sample_data.py
```

## Notes

- `search_in_file` matches substrings, so searching `java` also matches `JavaScript`.
- Scanned (image-only) PDFs contain no extractable text and are reported as empty content.
