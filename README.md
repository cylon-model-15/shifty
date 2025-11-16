# Shifty

Shifty is a command-line tool that uses a local Ollama instance to transform raw, timestamped shift notes into a professional, structured narrative assessment. It employs a flexible two-pass system and a customizable style guide to generate reports tailored to your needs.

## Overview

The process works in two main stages:

1.  **Pass 1: Fact Extraction**: The script first runs a linter to validate the format of the raw notes file. If the notes are valid, it uses a specified Ollama model and the `pass1.txt` prompt to extract structured data (timestamp, level, name, text) from the notes.
2.  **Pass 2: Narrative Generation**: The structured facts from the first pass are then combined with a style guide (e.g., `style_guide.txt`) and fed into the `pass2.txt` prompt. The model uses this combined information to generate the final, polished narrative in the desired format.

The `shifty.sh` script automates this process for all `.md` files in the directory, using environment variables for configuration.

## Features

-   **Two-Pass System**: Separates fact extraction from narrative generation for more reliable and consistent output.
-   **Customizable Style Guides**: Control the final output format by providing a style guide. Change the summary structure, add or remove sections, and tailor the output without editing the core prompts.
-   **Configurable**: Set the Ollama model and style guide via environment variables for easy integration into different workflows.
-   **Note Linter**: Includes `shifty_linter.py` to automatically check your notes for formatting errors before processing, preventing common issues.
-   **Caching**: Automatically skips processing if an up-to-date output file already exists. Use the `--force` flag to regenerate.
-   **Standardized Output**: Generates files with a `.shifty` extension to keep outputs organized.

## Note Formatting

The raw notes files are expected to follow a specific format for successful processing. The included linter will check for these rules.

-   The participant's name must be in a level-3 markdown heading (e.g., `### Sam`).
-   Each log entry must start with a timestamp (e.g., `08:15 Woke up...`).
-   The line *immediately after* the timestamp line must be the Assistance Level code (e.g., `l8`, `lx`).
-   All lines *after* the level (until the next timestamp) are considered details for that entry.

### Example Notes File (`sam.md`)

```markdown
### Sam

08:15 Woke up and got out of bed
l8

08:30 Morning hygiene routine
l6
Needed a verbal prompt to brush teeth.

09:00 Breakfast
l8
Ate a bowl of cereal with milk and a glass of orange juice.
```

## Prerequisites

-   **Python 3**: The core script is written in Python.
-   **Ollama**: A running Ollama instance is required. Download from [ollama.ai](https://ollama.ai/).
-   **An Ollama Model**: You need a model pulled. The default is `qwen2.5:32b`.
    ```bash
    ollama pull qwen2.5:32b
    ```
-   **cURL**: The script uses `curl` to communicate with the Ollama API.

## Usage

### Batch Processing with `shifty.sh` (Recommended)

This is the simplest method. It finds all `.md` files in the current directory (except `README.md`) and runs the two-pass process on each, saving the output to a corresponding `.shifty` file.

1.  Make sure your notes are in `.md` files (e.g., `sam.md`, `jane.md`).
2.  Make the script executable:
    ```bash
    chmod +x shifty.sh
    ```
3.  Run the script:
    ```bash
    ./shifty.sh
    ```

The script will create `sam.shifty` and `jane.shifty` with the final narrative summaries.

### Direct Execution with `shifty.py`

For more granular control, you can run the Python script directly.

```bash
python3 shifty.py --notes-file <path_to_your_notes.md>
```

**Example:**

```bash
python3 shifty.py --notes-file sam.md --output-file sam_summary.shifty
```

## Philosophy and Intended Use

**Garbage In, Garbage Out.**

The quality of the final assessment is directly related to the quality of the raw notes you provide. The model is instructed not to infer or invent information that isn't present in the source notes.

The intended workflow is:
1.  Take brief, shorthand notes during a shift, focusing on capturing key events and observations accurately.
2.  Run `shifty` to generate a structured, skeleton assessment based on those notes.
3.  Manually review the generated `.shifty` file, adding more detailed context, professional insights, and any necessary corrections by hand.

Shifty is a tool to accelerate the report-writing process, not to replace the critical thinking and detailed observations of the support worker.

## Customization

### Configuring the Model and Style Guide (Environment Variables)

The `shifty.sh` script uses environment variables for configuration. This is the recommended way to customize behavior.

-   `SHIFTY_MODEL`: Sets the Ollama model to use.
-   `SHIFTY_STYLE_GUIDE`: Sets the path to a custom style guide file.

```bash
# Example: Use a different model and a custom style guide for a single run
SHIFTY_MODEL="llama3:8b" SHIFTY_STYLE_GUIDE="my_style_guide.txt" ./shifty.sh

# Example: Export the variables for the current session
export SHIFTY_MODEL="llama3:8b"
export SHIFTY_STYLE_GUIDE="my_style_guide.txt"
./shifty.sh
```

If these variables are not set, the script defaults to the model `qwen2.5:32b` and the `style_guide.txt` file.

### Command-line Arguments (`shifty.py`)

When running `shifty.py` directly, you can use command-line arguments for customization.

-   `--model`: Specify a different Ollama model.
-   `--style-guide-file`: Path to a custom style guide.
-   `--prompt-file-pass1`, `--prompt-file-pass2`: Paths to custom prompt files.
-   `--force`: Force regeneration of the output file, ignoring the cache.

### Customizing Prompts and Style Guides

-   **Pass 1 Prompt (`pass1.txt`)**: This file must contain the `{{RAW_NOTES}}` placeholder.
-   **Pass 2 Prompt (`pass2.txt`)**: This file must contain `{{OBSERVED_FACTS}}` and `{{OPTIONAL_STYLE_GUIDE}}` placeholders. The content of your style guide will be injected into the `{{OPTIONAL_STYLE_GUIDE}}` location.
-   **Style Guide (`style_guide.txt`)**: This file contains the desired format for the final output. You can create your own and point to it using the `SHIFTY_STYLE_GUIDE` environment variable or the `--style-guide-file` argument.

## Model Performance

The default model, `qwen2.5:32b`, is recommended as it has proven to be reliable for the two-pass generation task. Smaller models (e.g., 7B parameters) have been tested with mixed results, sometimes failing to follow instructions accurately.
