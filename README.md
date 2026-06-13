

> **Hybrid C++ bug detection for RDI/SmartRDI code.**
> Deterministic rules first. LLM fallback second. MCP validation always.

## Quick Start
Run the CLI tool that takes a CSV of C++ RDI code samples and outputs a CSV with detected bugs, using a combination of deterministic rules and an LLM fallback.

### 1. Requirements

Install dependencies using `pip`:
```bash
pip install -r requirements.txt
```

Set the Groq API key:
```bash
# Windows
set GROQ_API_KEY=your_key_here

# Linux/Mac
export GROQ_API_KEY=your_key_here
```

### 2. (Optional) Run the MCP Server for LLM Fallback Docs
In a separate terminal, to give the LLM Fallback access to RDI docs context:
```bash
python server/mcp_server.py
```

### 3. Execution Commands
Run the main script against your inputs. This will generate an `output.csv` automatically in your current directory.

```bash
# To run set of samples:
python code/main.py samples.csv
```

## Output Format
The tool will strictly format `output.csv` into 3 columns.
```csv
ID,Bug Line,Explanation
2,3,"Invalid vForceRange(35.0 V): not a valid range for AVI64."
```

## Project Structure
```text
. (Current Folder)
├── code/
│   ├── main.py                       # CLI entry point
│   ├── config.py                     
│   └── agents/                       # Bug hunting & validation pipelines
├── rules/
│   └── learned_rules.py              # Auto-learned rules
├── server/
│   └── mcp_server.py                 # FastMCP server (Context)
├── samples.csv                       # Input data 1
└── README.md                         # This file
```

