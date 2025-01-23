import sys
import json
import os
from github import Github, Auth
from groq import Groq

from pr_review_helper import create_prompt, get_ai_response, create_comment


def process_inputs():
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
                "commitId": current_commit_id,
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


def analyze_code(
    modified_chunks, modified_files, pr_details, github_token, groq_api_key, github_owner, github_repo, github_pr_number
):
    all_comments = []

    for chunk in modified_chunks:
        file = {"to": chunk["fileName"]}
        chunk_data = {
            "content": chunk["codeChunk"],
            "changes": [
                {"content": line, "ln": i + 1}
                for i, line in enumerate(chunk["codeChunk"].split("\n"))
            ],
        }

        # Create AI review prompt
        prompt = create_prompt(file, chunk_data, pr_details)

        # Get AI review responses
        ai_responses = get_ai_response(prompt, api_key=groq_api_key)
        print(ai_responses)

        if ai_responses:
            # Create comments for GitHub PR
            comments = create_comment(file, chunk_data, ai_responses)
            all_comments.extend(comments)

    # Create GitHub review comments
    create_review_comment(
        owner=github_owner,
        repo=github_repo,
        pull_number=github_pr_number,
        comments=all_comments,
        token=github_token,
    )


def create_review_comment(
    owner: str, repo: str, pull_number: int, comments: list, token: str
) -> None:
    print('token',token)
    auth = Auth.Token(token)
    g = Github(auth=auth)

    repository = g.get_repo(f"{owner}/{repo}")
    pull_request = repository.get_pull(pull_number)

    # Get the last commit in the pull request
    commits = list(pull_request.get_commits())
    last_commit = commits[-1]

    for comment in comments:
        pull_request.create_review_comment(
            body=comment["body"],
            commit=last_commit,
            path=comment["path"],
            line=comment["line"],
        )


if __name__ == "__main__":
    # Get environment variables
    github_token = os.environ.get("GITHUB_TOKEN")
    groq_api_key = os.environ.get("GROQ_API_KEY")
    github_owner = os.environ.get("GITHUB_OWNER")
    github_repo = os.environ.get("GITHUB_REPO")
    github_pr_number = os.environ.get("GITHUB_PR_NUMBER")

    # Prepare PR details from environment variables
    pr_details = {
        "title": os.environ.get("GITHUB_PR_TITLE", "Code Review PR"),
        "description": os.environ.get("GITHUB_PR_DESCRIPTION", "Automated code review of recent changes"),
    }

    # Get modified files and chunks
    modified_chunks, modified_files = process_inputs()

    # Analyze code and create review
    analyze_code(
        modified_chunks, 
        modified_files, 
        pr_details, 
        github_token, 
        groq_api_key,
        github_owner,
        github_repo,
        int(github_pr_number)
    )