from github import Github, Auth
from groq import Client
from github.GithubException import GithubException
import json
import os
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class GuidelineManager:
    def __init__(self, github_token, groq_api_key, github_owner, github_repo):
        self.auth = Auth.Token(github_token)
        self.github = Github(auth=self.auth)
        self.client = Client(api_key=groq_api_key)
        self.github_owner = github_owner
        self.github_repo = github_repo
        self.repo = self.github.get_repo(f"{github_owner}/{github_repo}")

        # Branch & File Details
        self.guidelines_branch = "guidelines"
        self.guidelines_file = Path(".github/guidelines/guidelines.json")
        self.local_repo_path = Path("repo")

    def clone_guidelines_branch(self):
        """Clone the guidelines branch."""
        logging.info(f"Cloning the {self.guidelines_branch} branch...")
        if self.local_repo_path.exists():
            subprocess.run(["rm", "-rf", str(self.local_repo_path)], check=True)

        # Use the x-access-token format for the URL
        repo_url = f"https://x-access-token:{os.environ['GITHUB_TOKEN']}@github.com/{self.github_owner}/{self.github_repo}.git"
        subprocess.run(["git", "clone", "--branch", self.guidelines_branch, repo_url, str(self.local_repo_path)], check=True)

    def load_guidelines(self):
        """Load existing guidelines from the JSON file."""
        guidelines_path = self.local_repo_path / self.guidelines_file
        if not guidelines_path.exists():
            logging.info("No existing guidelines found, initializing an empty list.")
            return []  # Return an empty list if file doesn't exist

        with open(guidelines_path, "r") as f:
            data = json.load(f)
            # If data is a dictionary with a 'guidelines' key, extract the list.
            if isinstance(data, dict) and "guidelines" in data:
                return data["guidelines"]
            # If data is already a list, return it.
            elif isinstance(data, list):
                return data
            else:
                logging.info("Unexpected data format for guidelines. Initializing empty list.")
                return []

    def save_guidelines(self, guidelines):
        """Save the updated guidelines and push them back to the branch."""
        guidelines_path = self.local_repo_path / self.guidelines_file
        guidelines_path.parent.mkdir(parents=True, exist_ok=True)

        # Save the guidelines as a dictionary with key "guidelines"
        with open(guidelines_path, "w") as f:
            json.dump({"guidelines": guidelines}, f, indent=4)

        logging.info("Committing and pushing updates to the guidelines branch...")
        subprocess.run(["git", "-C", str(self.local_repo_path), "add", str(self.guidelines_file)], check=True)
        subprocess.run(["git", "-C", str(self.local_repo_path), "commit", "-m", "Update guidelines based on PR comment"], check=True)
        subprocess.run(["git", "-C", str(self.local_repo_path), "push"], check=True)

    def process_comment(self):
        """Process the PR comment and update guidelines if necessary."""
        try:
            self.clone_guidelines_branch()
            guidelines = self.load_guidelines()

            event = self.get_github_event()
            if not event:
                logging.error("No GitHub event context found")
                return

            comment = event["comment"]["body"]
            result = self.check_guideline_exists(comment, guidelines)

            if not result["exists"]:
                new_guideline = result["new_guideline"]
                if new_guideline:
                    guidelines.append(new_guideline)
                    self.save_guidelines(guidelines)
                    logging.info(f"Added new guideline: {new_guideline}")
            else:
                logging.info(f"Similar to existing guideline: {result['similar_to']}")

        except Exception as e:
            logging.error(f"Failed to process comment: {e}")
            raise

    def check_guideline_exists(self, comment, guidelines):
        """Use AI to check if the guideline already exists, retrying up to 5 times if needed."""
        prompt = f"""
        Existing guidelines:
        {json.dumps(guidelines, indent=2)}

        New comment:
        {comment}

        Instructions:
        - Compare the comment against existing guidelines.
        - If it suggests a new guideline, return it.
        - If it matches an existing guideline, return the match.

        Respond in JSON:
        {{
            "exists": boolean,
            "similar_to": string or null,
            "new_guideline": string or null
        }}
        """
        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            try:
                response = self.client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "Respond in JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=500,
                    top_p=1,
                )
                response_text = response.choices[0].message.content.strip()
                
                # Remove markdown code block formatting if present
                if response_text.startswith("```"):
                    # Split into lines and remove the first and last lines if they're code block markers
                    lines = response_text.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    response_text = "\n".join(lines).strip()
                
                result = json.loads(response_text)
                # Validate that the required keys exist
                required_keys = {"exists", "similar_to", "new_guideline"}
                if required_keys.issubset(result.keys()):
                    return result
                else:
                    print(f"Attempt {attempt}: JSON is missing required keys. Response: {result}")
            except json.JSONDecodeError as e:
                print(f"Attempt {attempt}: JSON decode error: {e}. Response text: {response_text}")
            except Exception as e:
                print(f"Attempt {attempt}: An error occurred: {e}")

        raise Exception("Failed to get valid JSON response after 5 attempts")

    @staticmethod
    def get_github_event():
        """Load GitHub event context."""
        try:
            with open(os.environ["GITHUB_EVENT_PATH"], "r") as f:
                return json.load(f)
        except (KeyError, FileNotFoundError) as e:
            logging.error(f"Failed to load GitHub event: {e}")
            return None

if __name__ == "__main__":
    try:
        github_token = os.environ["GITHUB_TOKEN"]
        groq_api_key = os.environ["GROQ_API_KEY"]
        github_owner = os.environ["GITHUB_OWNER"]
        github_repo = os.environ["GITHUB_REPO"]

        manager = GuidelineManager(github_token, groq_api_key, github_owner, github_repo)
        manager.process_comment()

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise
