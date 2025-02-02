from github import Github, Auth
from groq import Client  # Ensure Groq is installed and imported properly
from github.GithubException import GithubException
from typing import Optional, List, Dict
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class FetchComments:
    def __init__(
        self, github_token: str, groq_api_key: str, github_owner: str, github_repo: str, model: str = "llama-3.3-70b-versatile"
    ):
        self.auth = Auth.Token(github_token)
        self.github = Github(auth=self.auth)
        self.api_key = groq_api_key
        self.model = model
        self.github_owner = github_owner
        self.github_repo = github_repo
        self.category_id = category_id  # Store category ID for discussions
        self.graphql_url = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Content-Type": "application/json"
        }

    def get_all_pull_request_comments(self) -> List[Dict[str, str | int]]:
        """
        Fetches all comments from all pull requests (open or closed) in the repository.
        """
        try:
            repository = self.github.get_repo(f"{self.github_owner}/{self.github_repo}")
            print(f"repo: {repository}")
            pull_requests = repository.get_pulls(state="all")
            print(f" PRS: {pull_requests}")
            logging.info(
                f"Found {pull_requests.totalCount} pull requests in the repository {self.github_owner}/{self.github_repo}"
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

    def post_to_discussions(self, guidelines: str):
            """
            Posts the generated guidelines to GitHub Discussions using GraphQL API.
            """
            mutation = """
            mutation($repositoryId: ID!, $categoryId: ID!, $title: String!, $body: String!) {
            createDiscussion(input: {repositoryId: $repositoryId, categoryId: $categoryId, title: $title, body: $body}) {
                discussion {
                id
                url
                }
            }
            }
            """

            # Fetch repository ID
            repo_query = f"""
            {{
            repository(owner: "{self.github_owner}", name: "{self.github_repo}") {{
                id
            }}
            }}
            """

            response = requests.post(self.graphql_url, headers=self.headers, json={"query": repo_query})
            repo_data = response.json()

            if "errors" in repo_data:
                logging.error(f"Failed to fetch repository ID: {repo_data['errors']}")
                return

            repository_id = repo_data["data"]["repository"]["id"]

            # Create the discussion
            variables = {
                "repositoryId": repository_id,
                "categoryId": self.category_id,
                "title": "Coding Guidelines",
                "body": guidelines
            }

            response = requests.post(self.graphql_url, headers=self.headers, json={"query": mutation, "variables": variables})
            discussion_data = response.json()

            if "errors" in discussion_data:
                logging.error(f"Failed to create discussion: {discussion_data['errors']}")
            else:
                discussion_url = discussion_data["data"]["createDiscussion"]["discussion"]["url"]
                logging.info(f"Discussion created successfully: {discussion_url}")



if __name__ == "__main__":
    try:
        # Replace these with your actual environment variables
        github_token = os.environ.get("GITHUB_TOKEN")
        groq_api_key = os.environ.get("GROQ_API_KEY")
        github_owner = os.environ.get("GITHUB_OWNER")
        github_repo = os.environ.get("GITHUB_REPO")
        category_id = "DIC_kwDOLcf9Ac4Cmjfq"
        logging.info(f"github token:{github_token} github owner: {github_owner} github repo: {github_repo}")

        if not all([github_token, groq_api_key, github_owner, github_repo]):
            raise ValueError("Missing one or more required environment variables.")

        fetch_comments = FetchComments(
            github_token=github_token,
            groq_api_key=groq_api_key,
            github_owner=github_owner,
            github_repo=github_repo,
            category_id=category_id,
        )

        logging.info("Fetching comments from pull requests...")
        comments = fetch_comments.get_all_pull_request_comments()

        logging.info("Generating guidelines...")
        guidelines = fetch_comments.generate_guidelines(comments)

        logging.info(guidelines)
        logging.info("Posting guidelines to GitHub Discussions...")
        fetch_comments.post_to_discussions(guidelines)

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise
