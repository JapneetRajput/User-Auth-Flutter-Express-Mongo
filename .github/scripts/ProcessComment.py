from github import Github, Auth
from groq import Client
import requests
import json
import os
import logging
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class GuidelineManager:
    def __init__(self, github_token: str, groq_api_key: str, github_owner: str, github_repo: str):
        self.auth = Auth.Token(github_token)
        self.github = Github(auth=self.auth)
        self.client = Client(api_key=groq_api_key)
        self.github_owner = github_owner
        self.github_repo = github_repo
        self.repo = self.github.get_repo(f"{github_owner}/{github_repo}")
        
        # GraphQL settings
        self.graphql_url = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v4+json"
        }
        self.category_id = "DIC_kwDOLM6ads4CZK8E"  # Use your actual category ID here

    def load_guidelines(self) -> List[str]:
        """Load existing guidelines from the discussion."""
        try:
            # First, let's verify the response structure with a simpler query
            test_query = """
            query($owner: String!, $repo: String!) {
              repository(owner: $owner, name: $repo) {
                id
              }
            }
            """
            
            test_variables = {
                "owner": self.github_owner,
                "repo": self.github_repo
            }
            
            test_response = requests.post(
                self.graphql_url,
                headers=self.headers,
                json={"query": test_query, "variables": test_variables}
            )
            
            logging.info(f"Test response: {test_response.text}")

            # Now try the actual discussion query
            query = """
            query($owner: String!, $repo: String!, $categoryId: ID!) {
              repository(owner: $owner, name: $repo) {
                discussions(first: 1, categoryId: $categoryId, orderBy: {field: CREATED_AT, direction: DESC}) {
                  nodes {
                    body
                  }
                }
              }
            }
            """
            
            variables = {
                "owner": self.github_owner,
                "repo": self.github_repo,
                "categoryId": self.category_id
            }
            
            response = requests.post(
                self.graphql_url,
                headers=self.headers,
                json={"query": query, "variables": variables}
            )
            
            # Log the full response for debugging
            logging.info(f"Full response: {response.text}")
            
            # Check for response status
            response.raise_for_status()
            
            data = response.json()
            
            # Check for GraphQL errors
            if "errors" in data:
                logging.error(f"GraphQL errors: {data['errors']}")
                return []
                
            # Safely traverse the response
            repository = data.get("data", {}).get("repository")
            if repository is None:
                logging.error("Repository data not found in response")
                return []
                
            discussions = repository.get("discussions", {}).get("nodes", [])
            if not discussions:
                logging.info("No discussions found")
                return []
                
            try:
                guidelines_text = discussions[0]["body"]
                guidelines_data = json.loads(guidelines_text)
                return guidelines_data.get("guidelines", [])
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                logging.error(f"Error parsing guidelines: {e}")
                return []
                
        except Exception as e:
            logging.error(f"Error loading guidelines: {e}")
            return []

    def save_guidelines(self, guidelines: List[str]) -> None:
        """Save guidelines to the discussion."""
        try:
            # First get repository ID
            repo_query = """
            query($owner: String!, $repo: String!) {
              repository(owner: $owner, name: $repo) {
                id
              }
            }
            """
            
            repo_variables = {
                "owner": self.github_owner,
                "repo": self.github_repo
            }
            
            repo_response = requests.post(
                self.graphql_url,
                headers=self.headers,
                json={"query": repo_query, "variables": repo_variables}
            )
            
            repo_data = repo_response.json()
            if "errors" in repo_data:
                logging.error(f"Failed to get repository ID: {repo_data['errors']}")
                raise Exception("Failed to get repository ID")
                
            repository_id = repo_data.get("data", {}).get("repository", {}).get("id")
            if not repository_id:
                raise Exception("Repository ID not found in response")
            
            # Prepare guidelines JSON
            guidelines_json = json.dumps({"guidelines": guidelines}, indent=2)
            
            # Create discussion
            mutation = """
            mutation($repositoryId: ID!, $categoryId: ID!, $title: String!, $body: String!) {
              createDiscussion(input: {repositoryId: $repositoryId, categoryId: $categoryId, title: $title, body: $body}) {
                discussion {
                  url
                }
              }
            }
            """
            
            variables = {
                "repositoryId": repository_id,
                "categoryId": self.category_id,
                "title": "Coding Guidelines",
                "body": guidelines_json
            }
            
            response = requests.post(
                self.graphql_url,
                headers=self.headers,
                json={"query": mutation, "variables": variables}
            )
            
            logging.info(f"Save response: {response.text}")
            
            data = response.json()
            if "errors" in data:
                logging.error(f"Failed to save guidelines: {data['errors']}")
                raise Exception("Failed to save guidelines")
                
        except Exception as e:
            logging.error(f"Error saving guidelines: {e}")
            raise

    def process_comment(self) -> None:
        """Process the PR comment and update guidelines if necessary."""
        try:
            # Load existing guidelines
            logging.info("Loading existing guidelines...")
            guidelines = self.load_guidelines()
            logging.info(f"Loaded guidelines: {guidelines}")

            event = self.get_github_event()
            if not event:
                logging.error("No GitHub event context found")
                return

            comment = event["comment"]["body"]
            logging.info(f"Processing comment: {comment}")
            
            result = self.check_guideline_exists(comment, guidelines)
            logging.info(f"Check result: {result}")

            if not result["exists"]:
                new_guideline = result["new_guideline"]
                if new_guideline:
                    guidelines.append(new_guideline)
                    logging.info("Saving updated guidelines...")
                    self.save_guidelines(guidelines)
                    logging.info(f"Added new guideline: {new_guideline}")
            else:
                logging.info(f"Similar to existing guideline: {result['similar_to']}")

        except Exception as e:
            logging.error(f"Failed to process comment: {e}")
            raise

    def check_guideline_exists(self, comment: str, guidelines: List[str]) -> Dict:
        """Use Groq to check if the guideline already exists."""
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
                
                if response_text.startswith("```"):
                    lines = response_text.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    response_text = "\n".join(lines).strip()
                
                result = json.loads(response_text)
                required_keys = {"exists", "similar_to", "new_guideline"}
                if required_keys.issubset(result.keys()):
                    return result
                else:
                    logging.warning(f"Attempt {attempt}: JSON is missing required keys. Response: {result}")
            except json.JSONDecodeError as e:
                logging.error(f"Attempt {attempt}: JSON decode error: {e}. Response text: {response_text}")
            except Exception as e:
                logging.error(f"Attempt {attempt}: An error occurred: {e}")

        raise Exception("Failed to get valid JSON response after 5 attempts")

    @staticmethod
    def get_github_event() -> Optional[Dict]:
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