# Shifty

Shifty is a command-line tool that uses a local Ollama instance to transform raw, timestamped notes into a structured narrative summary. It employs a two-pass system to first extract key facts and then generate a coherent, human-readable report.

## Overview

The process works in two main stages:

1.  **Pass 1: Fact Extraction**: The script takes a raw notes file (e.g., a Markdown file) and uses a specified Ollama model to pull out structured facts. This is guided by a prompt template (e.g., `pass1.txt`).
2.  **Pass 2: Narrative Generation**: The extracted facts from the first pass are then fed into a second prompt template (e.g., `pass2.txt`). The Ollama model uses this to generate a final, polished narrative.

The `shifty.sh` script automates this process for all `.md` files in the directory.

## Prerequisites

Before you begin, ensure you have the following installed and running:

*   **Python 3**: The core script is written in Python.
*   **Ollama**: The script relies on a running Ollama instance. You can download it from [ollama.ai](https://ollama.ai/).
*   **An Ollama Model**: You need to have a model pulled. The default is `qwen2.5:32b`, but you can specify any model you have available.
    ```bash
    ollama pull qwen2.5:32b
    ```
*   **cURL**: The script uses `curl` to communicate with the Ollama API.

## Usage

There are two ways to use Shifty: the automated batch script or direct execution of the Python script.

### 1. Batch Processing with `shifty.sh`

This is the simplest method. It finds all Markdown files (`.md`) in the current directory and runs the two-pass process on each one, saving the output to a corresponding `.txt` file.

1.  Make sure your notes are in `.md` files (e.g., `barry.md`, `jane.md`).
2.  Make the script executable:
    ```bash
    chmod +x shifty.sh
    ```
3.  Run the script:
    ```bash
    ./shifty.sh
    ```

The script will create `barry.txt` and `jane.txt` with the final narrative summaries.

### 2. Direct Execution with `shifty.py`

You can run the Python script directly to process a single file and have more control over the options.

```bash
python3 shifty.py --notes-file <path_to_your_notes.md> --output-file <path_to_your_output.txt>
```

**Example:**

```bash
python3 shifty.py --notes-file barry.md --output-file barry_summary.txt
```

## Customization

You can customize the behavior by passing arguments to the `shifty.py` script.

### Changing the Model

Use the `--model` flag to specify a different Ollama model.

```bash
python3 shifty.py --notes-file barry.md --model llama3:8b
```

### Specifying Custom Prompt Files

Shifty uses two prompt files for its two-pass system. You can point to your own custom prompt files using the `--prompt-file-pass1` and `--prompt-file-pass2` arguments.

*   **Pass 1 Prompt**: This file should contain the `{{RAW_NOTES}}` placeholder.
*   **Pass 2 Prompt**: This file should contain the `{{OBSERVED_FACTS}}` placeholder.

**Example:**

```bash
python3 shifty.py \
  --notes-file barry.md \
  --prompt-file-pass1 my_extraction_prompt.txt \
  --prompt-file-pass2 my_narrative_prompt.txt
```

## Model Performance

The default model, `qwen2.5:32b`, is recommended as it has proven to be reliable for the two-pass generation task.

A smaller model (e.g., 7B parameter model) was tested with mixed results. It was prone to hallucinations and failed to reliably follow the prompt instructions accurately. YMMV.
