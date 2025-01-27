from github import Github, Auth
from github.GithubException import GithubException
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

#sample comment to test
class GitHubPRHandler:
    def __init__(self, token: str):
        self.auth = Auth.Token(token)
        self.github = Github(auth=self.auth)

    def get_all_pull_request_comments(
        self, owner: str, repo: str
    ) -> list[dict[str, str | int]]:
        """
        Fetches all comments from all pull requests (open or closed) in the repository
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
            logging.error(f"Failed to fetch pull reuqest comments: {e}")
            return []

    def get_single_pull_request_comments(
        self, owner: str, repo: str, pull_number: int
    ) -> list[dict[str, str | int]]:
        """Fetches the comments of a pull request."""
        try:
            repository = self.github.get_repo(f"{owner}/{repo}")
            pull_request = repository.get_pull(pull_number)

            comments = [
                {
                    "body": comment.body,
                    "path": comment.path,
                    "line": comment.position,
                    "user": comment.user.login,
                }
                for comment in pull_request.get_review_comments()
            ]
            logging.info(
                f"Fetched {len(comments)} comments from PR #{pull_number} from repo: {repo}"
            )
            return comments
        except GithubException as e:
            logging.error(f"Failed to fetch comments: {e}")
            return []

    def create_review_comment(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        comments: list[dict[str, str | int]],
    ) -> None:
        """Creates review comments on a pull request."""
        try:
            repository = self.github.get_repo(f"{owner}/{repo}")
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
                logging.info(
                    f"Comment added on {comment['path']} at line {comment['line']}: {comment['body']}"
                )
        except GithubException as e:
            logging.error(f"Failed to create review comments: {e}")
