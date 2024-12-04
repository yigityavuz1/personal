#!/usr/bin/env bash

# Generate a temporary requirements file from the current environment
temp_file=$(mktemp)
pip freeze > "$temp_file"

# Compare the generated file with the existing requirements.txt
if ! diff -q "$temp_file" backend/requirements.txt; then
    echo # Blank line
    echo "Error: requirements.txt is out of sync with the current environment."
    echo # Blank line
    echo "Differences:"
    diff "$temp_file" backend/requirements.txt
    echo # Blank line
    echo "Run 'pip freeze > requirements.txt' to update."
    rm "$temp_file"
    exit 1
else
    echo # Blank line
    echo "requirements.txt is up-to-date."
    # Clean up temporary file
    rm "$temp_file"
    exit 0
fi


