import sys
import json
import os
from github import Github, Auth
from groq import Groq

from pr_review_helper import AIReviewHelper
from github_handler import GitHubPRHandler


class CodeReviewProcessor:
    def __init__(self, github_token, groq_api_key, github_owner, github_repo, github_pr_number, pr_details):
        self.github_token = github_token
        self.groq_api_key = groq_api_key
        self.github_owner = github_owner
        self.github_repo = github_repo
        self.github_pr_number = github_pr_number
        self.pr_details = pr_details
        self.modified_chunks = []
        self.modified_files = []

    def process_inputs(self):
        current_file = None
        current_chunk = None
        current_commit_id = None

        # Reading input from stdin (simulating GitHub Actions output piped here)
        data = sys.stdin.read()

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
                self.modified_chunks.append(current_chunk)
            elif line.startswith("code chunk:"):
                continue  # Skip this line
            elif current_chunk and line.startswith("+"):
                current_chunk["codeChunk"] += line[1:] + "\n"
            elif line.startswith("Fetching full content of file:"):
                file_name = line.split("Fetching full content of file:")[1].strip()
                code = ""
                current_file = file_name
                self.modified_files.append({"fileName": file_name, "code": code})
            elif current_file and self.modified_files and not line.startswith("fileName:"):
                self.modified_files[-1]["code"] += line + "\n"

    def analyze_code(self):
        all_comments = []

        for chunk in self.modified_chunks:
            file = {"to": chunk["fileName"]}
            chunk_data = {
                "content": chunk["codeChunk"],
                "changes": [
                    {"content": line, "ln": i + 1}
                    for i, line in enumerate(chunk["codeChunk"].split("\n"))
                ],
            }
            review_helper = AIReviewHelper(api_key=self.groq_api_key)

            # Create AI review prompt
            prompt = review_helper.create_prompt(file, chunk_data, self.pr_details)

            # Get AI review responses
            ai_responses = review_helper.get_ai_response(prompt)
            print(ai_responses)

            if ai_responses:
                # Create comments for GitHub PR
                comments = review_helper.create_comment(file, chunk_data, ai_responses)
                all_comments.extend(comments)

        github_handler = GitHubPRHandler(self.github_token)

        # Create GitHub review comments
        github_handler.create_review_comment(
            owner=self.github_owner,
            repo=self.github_repo,
            pull_number=self.github_pr_number,
            comments=all_comments,
        )


def main():
    # Get environment variables
    github_token = os.environ.get("GITHUB_TOKEN")
    groq_api_key = os.environ.get("GROQ_API_KEY")
    github_owner = os.environ.get("GITHUB_OWNER")
    github_repo = os.environ.get("GITHUB_REPO")
    github_pr_number = os.environ.get("GITHUB_PR_NUMBER")

    # Prepare PR details from environment variables
    pr_details = {
        "title": os.environ.get("GITHUB_PR_TITLE", "Code Review PR"),
        "description": os.environ.get(
            "GITHUB_PR_DESCRIPTION", "Automated code review of recent changes"
        ),
    }

    # Initialize the CodeReviewProcessor instance
    review_processor = CodeReviewProcessor(
        github_token,
        groq_api_key,
        github_owner,
        github_repo,
        int(github_pr_number),
        pr_details,
    )

    # Get modified files and chunks
    review_processor.process_inputs()

    # Analyze code and create review
    review_processor.analyze_code()


if __name__ == "__main__":
    main()
