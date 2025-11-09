#!/usr/bin/env python3
"""
A generic script to interact with a local Ollama instance.
"""

import json
import subprocess
from pathlib import Path
import argparse
from typing import Optional
import sys # Added for sys.exit

# --- Core Functions (call_ollama and load_prompt are unchanged) ---

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
    # ... (Keep your existing argparse setup)
    # ... (args = parser.parse_args() is the same)
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
    args = parser.parse_args()
    
    # --- Load Notes (Same as before) ---
    notes_file_path = Path(args.notes_file)
    if not notes_file_path.exists():
        print(f"Error: Notes file not found at: {notes_file_path}")
        sys.exit(1)
    raw_notes = notes_file_path.read_text(encoding='utf-8')
    
    # --- PASS 1: FACT EXTRACTION ---
    print("--- Starting Pass 1: Fact Extraction ---")
    
    # Load the *new* pass 1 prompt template
    # You could hardcode this or add a new arg like --prompt-file-pass1
    pass1_prompt_path = Path(args.prompt_file_pass1) 
    if not pass1_prompt_path.exists():
        print(f"Error: Pass 1 prompt not found at: {pass1_prompt_path}")
        sys.exit(1)
        
    pass1_template = pass1_prompt_path.read_text(encoding='utf-8')
    
    # Inject raw notes into the first template
    pass1_final_prompt = pass1_template.replace("{{RAW_NOTES}}", raw_notes)
    
    # Call Ollama for Pass 1
    observed_facts = call_ollama(pass1_final_prompt, args.model)
    
    if not observed_facts:
        print("Error: Pass 1 (Fact Extraction) failed to return a response.")
        sys.exit(1)
        
    print(f"Pass 1 Complete. Facts: {observed_facts}")

    # --- PASS 2: NARRATIVE GENERATION ---
    print("--- Starting Pass 2: Narrative Generation ---")
    
    # Load the *new* pass 2 prompt template
    pass2_prompt_path = Path(args.prompt_file_pass2)
    if not pass2_prompt_path.exists():
        print(f"Error: Pass 2 prompt not found at: {pass2_prompt_path}")
        sys.exit(1)
        
    pass2_template = pass2_prompt_path.read_text(encoding='utf-8')
    
    # Inject the *result* of Pass 1 into the second template
    pass2_final_prompt = pass2_template.replace("{{OBSERVED_FACTS}}", observed_facts)
    
    # Call Ollama for Pass 2
    final_assessment = call_ollama(pass2_final_prompt, args.model)

    if not final_assessment:
        print("Error: Pass 2 (Narrative Generation) failed to return a response.")
        sys.exit(1)

    print(f"Pass 2 Complete. Assessment: {final_assessment}")

    # --- Save Final Output (Same as before) ---
    output_file_path = Path(args.output_file) if args.output_file else Path('shifty_output.txt')
    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(final_assessment)
    print(f"--- SUCCESS: Final assessment saved to: {output_file_path} ---")

if __name__ == "__main__":
    main()

