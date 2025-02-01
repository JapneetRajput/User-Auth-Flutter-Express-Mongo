from github import Github, Auth
from groq import Client
from github.GithubException import GithubException
from typing import Optional, List, Dict
import json
import logging
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class GuidelineManager:
    def __init__(
        self,
        github_token: str,
        groq_api_key: str,
        github_owner: str,
        github_repo: str,
        model: str = "llama-3.3-70b-versatile"
    ):
        self.auth = Auth.Token(github_token)
        self.github = Github(auth=self.auth)
        self.client = Client(api_key=groq_api_key)
        self.model = model
        self.github_owner = github_owner
        self.github_repo = github_repo
        self.guidelines_path = Path('.github/guidelines/guidelines.json')

    def load_guidelines(self) -> List[str]:
        """Load existing guidelines from guidelines.json"""
        try:
            with open(self.guidelines_path, 'r') as f:
                data = json.load(f)
                return data.get('guidelines', [])
        except FileNotFoundError:
            return []

    def save_guidelines(self, guidelines: List[str]) -> None:
        """Save updated guidelines to guidelines.json"""
        # Ensure directory exists
        self.guidelines_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.guidelines_path, 'w') as f:
            json.dump({"guidelines": guidelines}, f, indent=2)

    def check_guideline_exists(self, comment: Dict[str, str]) -> Dict:
        """
        Ask Groq LLM to check if the guideline already exists in some form
        Returns: Dict with analysis results
        """
        try:
            guidelines = self.load_guidelines()
            
            prompt = f"""
            Given these existing code quality guidelines:
            {json.dumps(guidelines, indent=2)}
            
            And this new code review comment:
            {comment['comment_body']}
            
            Task: Determine if this comment suggests a guideline that's already covered by the existing guidelines.
            
            Respond in JSON format with these fields:
            - exists: boolean (true if the guideline already exists in some form)
            - similar_to: string (the existing similar guideline if exists is true, null if false)
            - new_guideline: string (a clear, concise new guideline if exists is false, null if true)
            
            The new guideline should be in a similar format to the existing ones - brief and actionable.
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=500,
                top_p=1,
            )
            
            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            logging.error(f"Failed to check guideline existence: {e}")
            raise

    def process_comment(self) -> None:
        """
        Process the current PR comment and update guidelines if necessary
        """
        try:
            event = self.get_github_event()
            
            if not event:
                logging.error("No GitHub event context found")
                return

            comment = {
                "pr_number": event['pull_request']['number'],
                "comment_body": event['comment']['body'],
                "user": event['comment']['user']['login'],
            }

            # Check if comment suggests a new guideline
            result = self.check_guideline_exists(comment)
            
            if not result.get('exists'):
                guidelines = self.load_guidelines()
                if new_guideline := result.get('new_guideline'):
                    guidelines.append(new_guideline)
                    self.save_guidelines(guidelines)
                    logging.info(f"Added new guideline: {new_guideline}")
            else:
                logging.info(f"Similar to existing guideline: {result.get('similar_to')}")

        except Exception as e:
            logging.error(f"Failed to process comment: {e}")
            raise

    @staticmethod
    def get_github_event() -> Optional[Dict]:
        """
        Get GitHub event context from environment
        """
        try:
            with open(os.environ['GITHUB_EVENT_PATH'], 'r') as f:
                return json.load(f)
        except (KeyError, FileNotFoundError) as e:
            logging.error(f"Failed to load GitHub event: {e}")
            return None

if __name__ == "__main__":
    try:
        github_token = os.environ.get("GITHUB_TOKEN")
        groq_api_key = os.environ.get("GROQ_API_KEY")
        github_owner = os.environ.get("GITHUB_OWNER")
        github_repo = os.environ.get("GITHUB_REPO")

        if not all([github_token, groq_api_key, github_owner, github_repo]):
            raise ValueError("Missing one or more required environment variables.")

        manager = GuidelineManager(
            github_token=github_token,
            groq_api_key=groq_api_key,
            github_owner=github_owner,
            github_repo=github_repo
        )

        logging.info("Processing PR comment...")
        manager.process_comment()

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise