from github import Github, Auth
from groq import Client  # Ensure Groq is installed and imported properly
from github.GithubException import GithubException
from typing import Optional, List, Dict
import logging
import sys
import json
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class FetchComments:
    def __init__(
        self, token: str, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"
    ):
        self.auth = Auth.Token(token)
        self.github = Github(auth=self.auth)
        self.api_key = api_key
        self.model = model

    def get_all_pull_request_comments(
        self, owner: str, repo: str
    ) -> List[Dict[str, str | int]]:
        """
        Fetches all comments from all pull requests (open or closed) in the repository.
        """
        try:
            repository = self.github.get_repo(f"{owner}/{repo}")
            pull_requests = repository.get_pulls(state="all")
            logging.info(
                f"Found {pull_requests.totalCount} pull requests in the repository {owner}/{repo}"
            )

            all_comments = []
            for pr in pull_requests:
                logging.info(f"Fetching comments for PR #{pr.number}: {pr.title}")
                for comment in pr.get_review_comments():
                    all_comments.append(
                        {
                            "pr_number": pr.number,
                            "pr_title": pr.title,
                            "comment_body": comment.body,
                            "comment_path": comment.path,
                            "line": comment.position,
                            "user": comment.user.login,
                            "pr_state": pr.state,
                        }
                    )
            logging.info(
                f"Fetched {len(all_comments)} comments from all pull requests."
            )
            return all_comments
        except GithubException as e:
            logging.error(f"Failed to fetch pull request comments: {e}")
            return []

    def generate_guidelines(self, comments: List[Dict[str, str | int]]) -> str:
        """
        Sends comments to the AI to generate guidelines.
        """
        if not self.api_key:
            raise ValueError("API key is required to generate guidelines.")


        client = Client(api_key=self.api_key)
        all_comments = "\n".join(
            [
                f"PR #{comment['pr_number']} ({comment['pr_title']}):\n{comment['comment_body']}"
                for comment in comments
            ]
        )

        prompt = (
            f"Based on the following pull request comments, generate coding guidelines:\n\n{all_comments}"
        )
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": prompt}],
            temperature=0.2,
            max_tokens=700,
            top_p=1,
        )
        return response.choices[0].message.content.strip()


if __name__ == "__main__":
    try:
        # Replace these with your actual values
        github_token = os.environ.get("GITHUB_TOKEN")
        groq_api_key = os.environ.get("GROQ_API_KEY")
        github_owner = os.environ.get("GITHUB_OWNER")
        github_repo = os.environ.get("GITHUB_REPO")

        fetch_comments = FetchComments(token=github_token, api_key=groq_api_key)

        logging.info("Fetching comments from pull requests...")
        comments = fetch_comments.get_all_pull_request_comments(github_owner, github_repo)
        logging.info(f"Fetched {len(comments)} comments from pull requests.")

        logging.info("Generating guidelines...")
        guidelines = fetch_comments.generate_guidelines(comments)

        # Save the guidelines to a file
        output_file = "generated_guidelines.txt"
        with open(output_file, "w") as f:
            f.write(guidelines)

        logging.info(f"Guidelines generated and saved to {output_file}.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise
