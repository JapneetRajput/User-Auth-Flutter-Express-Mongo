from github import Github, Auth
from groq import Client
from github.GithubException import GithubException
from typing import Optional, List, Dict
import json
import logging
import os
from pathlib import Path
import subprocess

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
        github_repo: str
    ):
        self.auth = Auth.Token(github_token)
        self.github = Github(auth=self.auth)
        self.client = Client(api_key=groq_api_key)
        self.github_owner = github_owner
        self.github_repo = github_repo
        self.wiki_url = f"https://{github_token}@github.com/{github_owner}/{github_repo}.wiki.git"
        self.wiki_path = Path("wiki")
        self.guidelines_file = self.wiki_path / "Guidelines.md"

    def clone_wiki(self):
        """Clone the GitHub Wiki repository."""
        if self.wiki_path.exists():
            subprocess.run(["rm", "-rf", str(self.wiki_path)], check=True)
        
        logging.info("Cloning the GitHub Wiki repository...")
        subprocess.run(["git", "clone", self.wiki_url, str(self.wiki_path)], check=True)

    def load_guidelines(self) -> List[str]:
        """Load existing guidelines from the Wiki."""
        if not self.guidelines_file.exists():
            logging.info("No existing guidelines found in Wiki, initializing an empty list.")
            return []

        with open(self.guidelines_file, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]

    def save_guidelines(self, guidelines: List[str]) -> None:
        """Save updated guidelines to the Wiki."""
        with open(self.guidelines_file, "w") as f:
            f.write("\n".join(guidelines) + "\n")

        logging.info("Committing and pushing updates to the Wiki...")
        subprocess.run(["git", "-C", str(self.wiki_path), "add", "Guidelines.md"], check=True)
        subprocess.run(["git", "-C", str(self.wiki_path), "commit", "-m", "Update guidelines based on PR comment"], check=True)
        subprocess.run(["git", "-C", str(self.wiki_path), "push"], check=True)

    def process_comment(self) -> None:
        """
        Process the current PR comment and update guidelines if necessary.
        """
        try:
            self.clone_wiki()
            guidelines = self.load_guidelines()

            event = self.get_github_event()
            if not event:
                logging.error("No GitHub event context found")
                return

            comment = {
                "pr_number": event["pull_request"]["number"],
                "comment_body": event["comment"]["body"],
                "user": event["comment"]["user"]["login"],
            }

            # Check if comment suggests a new guideline
            result = self.check_guideline_exists(comment)
            if not result.get("exists"):
                if new_guideline := result.get("new_guideline"):
                    guidelines.append(new_guideline)
                    self.save_guidelines(guidelines)
                    logging.info(f"Added new guideline: {new_guideline}")
            else:
                logging.info(f"Similar to existing guideline: {result.get('similar_to')}")

        except Exception as e:
            logging.error(f"Failed to process comment: {e}")
            raise

    def check_guideline_exists(self, comment: Dict[str, str]) -> Dict:
        """Ask Groq LLM to check if the guideline already exists in some form."""
        guidelines = self.load_guidelines()
        prompt = f"""
        You are a code review assistant. Your task is to analyze a comment and existing guidelines.

        Existing guidelines:
        {json.dumps(guidelines, indent=2)}

        New comment to analyze:
        {comment["comment_body"]}

        Instructions:
        1. Compare the comment against existing guidelines.
        2. Determine if it suggests a new guideline or matches an existing one.
        3. Respond ONLY with a JSON object in the exact format:

        {{
            "exists": boolean,
            "similar_to": string or null,
            "new_guideline": string or null
        }}

        DO NOT include any explanations outside the JSON structure.
        """
        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Respond in JSON only."}, {"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500,
            top_p=1,
        )
        response_text = response.choices[0].message.content.strip()
        return json.loads(response_text)

    @staticmethod
    def get_github_event() -> Optional[Dict]:
        """Get GitHub event context from environment."""
        try:
            with open(os.environ["GITHUB_EVENT_PATH"], "r") as f:
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
            github_repo=github_repo,
        )

        logging.info("Processing PR comment...")
        manager.process_comment()

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise
