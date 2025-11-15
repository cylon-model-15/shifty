#!/bin/bash

# Set the script to exit immediately if any command fails
set -e

echo "Starting conversion..."

# --- Argument Construction ---
# Initialize an empty array for arguments
CMD_ARGS=()

# Pass the names of the environment variables to the Python script
# The Python script will then read these environment variables
CMD_ARGS+=(--model-env-var "SHIFTY_MODEL")
CMD_ARGS+=(--style-guide-env-var "SHIFTY_STYLE_GUIDE")

# --- File Processing Loop ---
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
        
        # Define the new output filename with the .shifty extension
        output_file="${base_name}.shifty"
        
        # Print what is being processed
        echo "Processing: $md_file  ->  $output_file"
        
        # Run python script with all constructed arguments
        # Quotes are used to handle filenames with spaces
        python3 shifty.py --notes-file "$md_file" --output-file "$output_file" "${CMD_ARGS[@]}"
    fi
done

echo "Processing complete"
