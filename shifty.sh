#!/bin/bash

# Set the script to exit immediately if any command fails
set -e

echo "Starting conversion..."

# Construct the model argument if SHIFTY_MODEL is set
MODEL_ARGS=()
if [ -n "$SHIFTY_MODEL" ]; then
    MODEL_ARGS+=(--model "$SHIFTY_MODEL")
    echo "Using model from SHIFTY_MODEL environment variable: $SHIFTY_MODEL"
else
    echo "SHIFTY_MODEL environment variable not set. shifty.py will use its default model."
fi

# Loop through all files ending with .md in the current directory
for md_file in *.md; do
    # Skip README.md
    if [ "$md_file" == "README.md" ]; then
        continue
    fi

    # Check if the file actually exists (avoids errors if no .md files are found)
    if [ -f "$md_file" ]; then
        # Get the filename without the .md extension
        base_name="${md_file%.md}"
        
        # Define the new output filename
        txt_file="${base_name}.txt"
        
        # Print what is being processed
        echo "Processing: $md_file  ->  $txt_file"
        
        # Run python script
        # Quotes are used to handle filenames with spaces
        python3 shifty.py --notes-file "$md_file" --output-file "$txt_file" "${MODEL_ARGS[@]}"
    fi
done

echo "Processing complete"
