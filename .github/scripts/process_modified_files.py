import sys
import json
import os

def process_inputs():
    # Simulating input retrieval from GitHub Actions
    modified_chunks = []
    modified_files = []

    # Reading input from stdin (simulating GitHub Actions output piped here)
    data = sys.stdin.read()

    current_file = None
    current_chunk = None
    current_commit_id = None

    for line in data.splitlines():
        if line.startswith("commitId:"):
            current_commit_id = line.split("commitId:")[1].strip()
        elif line.startswith("fileName:"):
            current_file = line.split("fileName:")[1].strip()
        elif line.startswith("lineNo. range:"):
            current_chunk = {
                "lineRange": line.split("lineNo. range:")[1].strip(),
                "fileName": current_file,
                "codeChunk": "",
                "commitId": current_commit_id
            }
            modified_chunks.append(current_chunk)
        elif line.startswith("code chunk:"):
            continue  # Skip this line
        elif current_chunk and line.startswith("+"):
            current_chunk["codeChunk"] += line[1:] + "\n"
        elif line.startswith("Fetching full content of file:"):
            file_name = line.split("Fetching full content of file:")[1].strip()
            code = ""
            current_file = file_name
            modified_files.append({"fileName": file_name, "code": code})
        elif current_file and modified_files and not line.startswith("fileName:"):
            modified_files[-1]["code"] += line + "\n"

    return modified_chunks, modified_files

if __name__ == "__main__":
    modified_chunks, modified_files = process_inputs()

    # Output the processed data
    print("Modified Chunks:")
    print(json.dumps(modified_chunks, indent=2))

    print("\nModified Files:")
    print(json.dumps(modified_files, indent=2))
