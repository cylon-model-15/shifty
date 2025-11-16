#!/bin/bash

# Set the script to exit immediately if any command fails
set -e

echo "Starting conversion..."

# --- File Check ---
# Use ls and grep to count .md files, excluding README.md
file_count=$(ls *.md 2>/dev/null | grep -v "README.md" | wc -l)

if [ "$file_count" -eq 0 ]; then
    echo "No .md files to process (excluding README.md). Exiting."
    exit 0
fi

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
        
        # Run python script. It will pick up environment variables automatically.
        # Quotes are used to handle filenames with spaces
        python3 shifty.py --notes-file "$md_file" --output-file "$output_file"
    fi
done

echo "Processing complete"
