#!/usr/bin/env python3
"""
A generic script to interact with a local Ollama instance.
"""

import json
import subprocess
from pathlib import Path
import argparse
import sys
import os
import logging

from shifty_linter import lint_notes, Colors

# --- Core Functions ---

def read_file_content(file_path: Path, description: str, logger: logging.Logger) -> str:
    """Reads content from a file, exiting if the file is not found."""
    if not file_path.exists():
        logger.error(f"{description} not found at: {file_path}")
        sys.exit(1)
    return file_path.read_text(encoding='utf-8')


def call_ollama(prompt: str, model: str, host: str, logger: logging.Logger) -> str:
    """Call Ollama API locally."""
    api_url = f"{host}/api/generate"
    logger.debug(f"Calling Ollama API at {api_url} with model {model}")
    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        result = subprocess.run(
            ['curl', '-s', api_url, '-d', json.dumps(payload)],
            capture_output=True,
            text=True,
            check=True
        )
        response = json.loads(result.stdout)
        return response.get('response', '').strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"The command to call Ollama failed with exit code {e.returncode}.")
        logger.error(f"Stderr: {e.stderr}")
        return ""
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON response from Ollama.")
        logger.error(f"Received: {result.stdout}")
        return ""
    except Exception as e:
        logger.error(f"An unexpected error occurred when calling Ollama: {e}")
        return ""


def main():
    parser = argparse.ArgumentParser(
        description='Interact with a local Ollama instance using a two-pass system.'
    )
    parser.add_argument(
        '--notes-file',
        help='Path to the raw notes file (Markdown or text).',
        required=True
    )
    parser.add_argument(
        '--model',
        help=f"Ollama model to use. Overrides SHIFTY_MODEL env var. (Default: 'qwen2.5:32b')"
    )
    parser.add_argument(
        '--output-file',
        help='Path to save the final assessment. Defaults to shifty_output.shifty.'
    )
    parser.add_argument(
        '--style-guide-file',
        help='Path to a style guide file. Overrides SHIFTY_STYLE_GUIDE env var.'
    )
    parser.add_argument(
        '--shorthand-file',
        help='Path to a JSON file containing shorthand definitions.'
    )
    parser.add_argument(
        '--ollama-host',
        help="Ollama host URL. Overrides OLLAMA_HOST env var. (Default: 'http://localhost:11434')"
    )
    parser.add_argument(
        '--prompt-file-pass1',
        default='pass1.txt',
        help='Path to the prompt file for Pass 1 (Fact Extraction).'
    )
    parser.add_argument(
        '--prompt-file-pass2',
        default='pass2.txt',
        help='Path to the prompt file for Pass 2 (Narrative Generation).'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force regeneration of the output file, ignoring the cache.'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_const',
        dest='loglevel',
        const=logging.DEBUG,
        default=logging.INFO,
        help='Enable verbose, debug-level logging.'
    )

    args = parser.parse_args()

    # --- Configure Logging ---
    logging.basicConfig(level=args.loglevel, format='%(levelname)s: %(message)s')
    logger = logging.getLogger()

    # --- Determine Configuration (Argument > Environment Variable > Default) ---
    model = args.model or os.environ.get('SHIFTY_MODEL') or 'qwen2.5:32b'
    style_guide_path_str = args.style_guide_file or os.environ.get('SHIFTY_STYLE_GUIDE') or 'style_guide.txt'
    shorthand_path_str = args.shorthand_file or os.environ.get('SHIFTY_SHORTHAND') or 'shorthand.json'
    ollama_host = args.ollama_host or os.environ.get('OLLAMA_HOST') or 'http://localhost:11434'


    # --- Determine Output Path ---
    output_file_path = Path(args.output_file) if args.output_file else Path('shifty_output.shifty')

    # --- Cache Check ---
    if output_file_path.exists() and not args.force:
        logger.info(f"{Colors.OKBLUE}--- SKIPPING: Output file already exists at: {output_file_path} ---{Colors.ENDC}")
        logger.info(f"{Colors.OKBLUE}Use --force to regenerate.{Colors.ENDC}")
        sys.exit(0)

    # --- Load Notes and Lint ---
    notes_file_path = Path(args.notes_file)
    raw_notes = read_file_content(notes_file_path, "Notes file", logger)
    
    # Run the linter on the notes file before proceeding
    if not lint_notes(notes_file_path, logger):
        sys.exit(1) # Exit if linting fails

    # --- PASS 1: FACT EXTRACTION ---
    logger.info("--- Starting Pass 1: Fact Extraction ---")
    pass1_template = read_file_content(Path(args.prompt_file_pass1), "Pass 1 prompt", logger)
    pass1_final_prompt = pass1_template.replace("{{RAW_NOTES}}", raw_notes)
    observed_facts = call_ollama(pass1_final_prompt, model, ollama_host, logger)
    if not observed_facts:
        logger.error("Pass 1 (Fact Extraction) failed to return a response.")
        sys.exit(1)
    logger.info(f"Pass 1 Complete.")
    logger.debug(f"Facts: {observed_facts}")


    # --- PASS 2: NARRATIVE GENERATION ---
    logger.info("--- Starting Pass 2: Narrative Generation ---")
    pass2_template = read_file_content(Path(args.prompt_file_pass2), "Pass 2 prompt", logger)

    # --- Load Shorthand Definitions ---
    shorthand_text = ""
    shorthand_path = Path(shorthand_path_str)
    if shorthand_path.exists():
        try:
            with shorthand_path.open('r', encoding='utf-8') as f:
                shorthand_data = json.load(f)
                shorthand_text = "\n".join(f"- {key}: {value}" for key, value in shorthand_data.items())
                logger.info(f"--- Loading shorthand definitions from: {shorthand_path} ---")
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from shorthand file: {shorthand_path}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to read or process shorthand file: {e}")
            sys.exit(1)
    else:
        logger.warning(f"Shorthand file not found at: {shorthand_path}. Proceeding without it.")

    # --- Load Optional Style Guide ---
    style_guide_text = ""
    if style_guide_path_str:
        style_guide_path = Path(style_guide_path_str)
        if style_guide_path.exists():
            logger.info(f"--- Loading optional style guide from: {style_guide_path} ---")
            style_guide_text = style_guide_path.read_text(encoding='utf-8')
        else:
            logger.warning(f"Style guide file not found at: {style_guide_path}. Proceeding without it.")

    # Inject definitions into the template
    pass2_template = pass2_template.replace("{{SHORTHAND_DEFINITIONS}}", shorthand_text)
    pass2_template = pass2_template.replace("{{OPTIONAL_STYLE_GUIDE}}", style_guide_text)

    # Inject the observed facts
    pass2_final_prompt = pass2_template.replace("{{OBSERVED_FACTS}}", observed_facts)

    final_assessment = call_ollama(pass2_final_prompt, model, ollama_host, logger)
    if not final_assessment:
        logger.error("Pass 2 (Narrative Generation) failed to return a response.")
        sys.exit(1)
    logger.info("Pass 2 Complete.")
    logger.debug(f"Assessment: {final_assessment}")

    # --- Save Final Output ---
    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(final_assessment)
    logger.info(f"--- SUCCESS: Final assessment saved to: {output_file_path} ---")



if __name__ == "__main__":
    main()
