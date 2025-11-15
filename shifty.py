#!/usr/bin/env python3
"""
A generic script to interact with a local Ollama instance.
"""

import json
import subprocess
from pathlib import Path
import argparse
import sys
import re

from shifty_linter import lint_notes, Colors

# --- Core Functions ---



def call_ollama(prompt: str, model: str) -> str:
    """Call Ollama API locally."""
    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:11434/api/generate', '-d', json.dumps(payload)],
            capture_output=True,
            text=True,
            check=True
        )
        response = json.loads(result.stdout)
        return response.get('response', '').strip()
    except Exception as e:
        print(f"Error calling Ollama: {e}")
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
        default='qwen2.5:32b',
        help='Ollama model to use (default: qwen2.5:32b)'
    )
    parser.add_argument(
        '--output-file',
        help='Path to save the final assessment. Defaults to ollama_output.txt.'
    )
    parser.add_argument(
        '--style-guide-file',
        default='style_guide.txt',
        help='Optional path to a .txt file containing a style guide example for Pass 2.'
    )
    # Optional arguments for custom prompt files
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
        '--no-post-processing',
        action='store_false',
        dest='apply_post_processing',
        help='Disable all post-processing (text replacement and newline formatting) to output the raw LLM response.')
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force regeneration of the output file, ignoring the cache.'
    )

    args = parser.parse_args()

    # --- Determine Output Path ---
    output_file_path = Path(args.output_file) if args.output_file else Path('shifty_output.txt')

    # --- Cache Check ---
    if output_file_path.exists() and not args.force:
        print(f"{Colors.OKBLUE}--- SKIPPING: Output file already exists at: {output_file_path} ---{Colors.ENDC}")
        print(f"{Colors.OKBLUE}Use --force to regenerate.{Colors.ENDC}")
        sys.exit(0)

    # --- Load Notes and Lint ---
    notes_file_path = Path(args.notes_file)
    if not notes_file_path.exists():
        print(f"Error: Notes file not found at: {notes_file_path}")
        sys.exit(1)
    
    # Run the linter on the notes file before proceeding
    if not lint_notes(notes_file_path):
        sys.exit(1) # Exit if linting fails

    raw_notes = notes_file_path.read_text(encoding='utf-8')

    # --- PASS 1: FACT EXTRACTION ---
    print("--- Starting Pass 1: Fact Extraction ---")
    pass1_prompt_path = Path(args.prompt_file_pass1)
    if not pass1_prompt_path.exists():
        print(f"Error: Pass 1 prompt not found at: {pass1_prompt_path}")
        sys.exit(1)
    pass1_template = pass1_prompt_path.read_text(encoding='utf-8')
    pass1_final_prompt = pass1_template.replace("{{RAW_NOTES}}", raw_notes)
    observed_facts = call_ollama(pass1_final_prompt, args.model)
    if not observed_facts:
        print("Error: Pass 1 (Fact Extraction) failed to return a response.")
        sys.exit(1)
    print(f"Pass 1 Complete. Facts: {observed_facts}")

    # --- PASS 2: NARRATIVE GENERATION ---
    print("--- Starting Pass 2: Narrative Generation ---")
    pass2_prompt_path = Path(args.prompt_file_pass2)
    if not pass2_prompt_path.exists():
        print(f"Error: Pass 2 prompt not found at: {pass2_prompt_path}")
        sys.exit(1)
    pass2_template = pass2_prompt_path.read_text(encoding='utf-8')

    # --- Load Optional Style Guide ---
    style_guide_text = ""
    if args.style_guide_file:
        style_path = Path(args.style_guide_file)
        if style_path.exists():
            print(f"--- Loading optional style guide from: {style_path} ---")
            style_guide_text = style_path.read_text(encoding='utf-8')
        else:
            print(f"Warning: Style guide file not found at: {style_path}. Proceeding without it.")

    # Inject the style guide (or an empty string) into the template
    pass2_template = pass2_template.replace("{{OPTIONAL_STYLE_GUIDE}}", style_guide_text)

    # Inject the observed facts
    pass2_final_prompt = pass2_template.replace("{{OBSERVED_FACTS}}", observed_facts)

    final_assessment = call_ollama(pass2_final_prompt, args.model)
    if not final_assessment:
        print("Error: Pass 2 (Narrative Generation) failed to return a response.")
        sys.exit(1)
    print(f"Pass 2 Complete. Assessment: {final_assessment}")

    # --- POST-PROCESSING ---

    # Start with the raw LLM output
    processed_assessment = final_assessment

    # args.apply_post_processing is True by default
    if args.apply_post_processing:
        print("--- Applying Post-Processing ---")
        # 1. Add newlines
        print("Adding newline formatting...")
        # Use regex to add a newline before any timestamp (HH:MM)
        # that is preceded by a space (to skip the very first line).
        # We also strip any whitespace at the start, just in case.
        processed_assessment = re.sub(r' (\d{2}:\d{2})', r'\n\1', processed_assessment)
        processed_assessment = processed_assessment.strip()
    else:
        print("--- Skipping Post-Processing (Raw LLM Output) ---")
        # No action needed, processed_assessment already holds the raw output

    # --- Save Final Output ---
    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(processed_assessment)
    print(f"--- SUCCESS: Final assessment saved to: {output_file_path} ---")


if __name__ == "__main__":
    main()
