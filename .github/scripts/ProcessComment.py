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
        max_retries = 5
        retry_count = 0

        try:
            guidelines = self.load_guidelines()
            
            prompt = f"""
            You are a code review assistant. Your task is to analyze a comment and existing guidelines.
            
            Existing guidelines:
            {json.dumps(guidelines, indent=2)}
            
            New comment to analyze:
            {comment['comment_body']}
            
            Instructions:
            1. Compare the comment against existing guidelines
            2. Determine if it suggests a new guideline or matches an existing one
            3. Respond ONLY with a JSON object in the exact format shown below:

            {{
                "exists": boolean,
                "similar_to": string or null,
                "new_guideline": string or null
            }}

            Rules:
            - 'exists' must be true if the guideline already exists, false otherwise
            - 'similar_to' must contain the existing guideline text if exists is true, null otherwise
            - 'new_guideline' must contain a new concise guideline if exists is false, null otherwise
            - The response must be valid JSON with no additional text
            - New guidelines should be brief and actionable, similar to existing ones
            
            DO NOT include any explanations or additional text outside the JSON structure.
            """

            while retry_count < max_retries:
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are a JSON-response code review assistant. Always respond with valid JSON only."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,  # Lower temperature for more consistent formatting
                        max_tokens=500,
                        top_p=1,
                    )
                    
                    logging.info(f"API Response: {response}")
                    response_text = response.choices[0].message.content.strip()
                    
                    # Try to clean the response if it contains markdown code blocks
                    if response_text.startswith("```json"):
                        response_text = response_text.replace("```json", "").replace("```", "").strip()
                    elif response_text.startswith("```"):
                        response_text = response_text.replace("```", "").strip()
                    
                    result = json.loads(response_text)
                    
                    # Validate the expected keys exist
                    required_keys = {'exists', 'similar_to', 'new_guideline'}
                    if not all(key in result for key in required_keys):
                        raise ValueError("Response missing required keys")
                    
                    logging.info(f"Parsed Result: {result}")
                    return result
                
                except json.JSONDecodeError as e:
                    logging.warning(f"Attempt {retry_count + 1} failed to parse JSON: {e}")
                    retry_count += 1
                    if retry_count == max_retries:
                        raise Exception("Maximum retries reached - could not get valid JSON response")
                except ValueError as e:
                    logging.warning(f"Attempt {retry_count + 1} had invalid response structure: {e}")
                    retry_count += 1
                    if retry_count == max_retries:
                        raise Exception("Maximum retries reached - could not get valid response structure")

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