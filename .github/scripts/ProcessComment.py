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
        
        # Category ID for coding guidelines discussions
        self.category_id = self.get_discussion_category_id("Coding Guidelines")
        
    def get_discussion_category_id(self, category_name: str) -> str:
        """Fetch the discussion category ID for the given category name."""
        query = """
        query($owner: String!, $repo: String!) {
          repository(owner: $owner, name: $repo) {
            discussionCategories(first: 10) {
              nodes {
                id
                name
              }
            }
          }
        }
        """
        
        variables = {
            "owner": self.github_owner,
            "repo": self.github_repo
        }
        
        response = requests.post(
            self.graphql_url,
            headers=self.headers,
            json={"query": query, "variables": variables}
        )
        data = response.json()
        
        for category in data["data"]["repository"]["discussionCategories"]["nodes"]:
            if category["name"] == category_name:
                return category["id"]
                
        raise ValueError(f"Discussion category '{category_name}' not found")

    def get_guidelines_from_discussions(self) -> List[str]:
        """Load existing guidelines from the GitHub Discussions."""
        query = """
        query($owner: String!, $repo: String!, $category: String!) {
          repository(owner: $owner, name: $repo) {
            discussions(first: 1, categoryId: $category, orderBy: {field: CREATED_AT, direction: DESC}) {
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
            "category": self.category_id
        }
        
        response = requests.post(
            self.graphql_url,
            headers=self.headers,
            json={"query": query, "variables": variables}
        )
        data = response.json()
        
        discussions = data["data"]["repository"]["discussions"]["nodes"]
        if not discussions:
            return []
            
        # Parse the guidelines from the discussion body
        try:
            guidelines_text = discussions[0]["body"]
            # Assuming the guidelines are stored as a JSON string in the discussion
            guidelines_data = json.loads(guidelines_text)
            return guidelines_data.get("guidelines", [])
        except json.JSONDecodeError:
            logging.error("Failed to parse guidelines from discussion")
            return []

    def update_guidelines_discussion(self, guidelines: List[str]) -> None:
        """Update the guidelines in GitHub Discussions."""
        # First, check if a discussion exists
        existing_guidelines = self.get_guidelines_from_discussions()
        
        # Prepare the guidelines JSON
        guidelines_json = json.dumps({"guidelines": guidelines}, indent=2)
        
        if not existing_guidelines:
            # Create new discussion if none exists
            self.post_to_discussions(guidelines_json)
        else:
            # Update existing discussion
            self.update_existing_discussion(guidelines_json)

    def update_existing_discussion(self, guidelines: str) -> None:
        """Update the existing guidelines discussion."""
        query = """
        mutation($discussionId: ID!, $body: String!) {
          updateDiscussion(input: {discussionId: $discussionId, body: $body}) {
            discussion {
              url
            }
          }
        }
        """
        
        # First, get the discussion ID
        discussion_id = self.get_latest_discussion_id()
        
        variables = {
            "discussionId": discussion_id,
            "body": guidelines
        }
        
        response = requests.post(
            self.graphql_url,
            headers=self.headers,
            json={"query": query, "variables": variables}
        )
        
        data = response.json()
        if "errors" in data:
            logging.error(f"Failed to update discussion: {data['errors']}")
        else:
            logging.info("Guidelines discussion updated successfully")

    def get_latest_discussion_id(self) -> str:
        """Get the ID of the latest guidelines discussion."""
        query = """
        query($owner: String!, $repo: String!, $category: String!) {
          repository(owner: $owner, name: $repo) {
            discussions(first: 1, categoryId: $category, orderBy: {field: CREATED_AT, direction: DESC}) {
              nodes {
                id
              }
            }
          }
        }
        """
        
        variables = {
            "owner": self.github_owner,
            "repo": self.github_repo,
            "category": self.category_id
        }
        
        response = requests.post(
            self.graphql_url,
            headers=self.headers,
            json={"query": query, "variables": variables}
        )
        
        data = response.json()
        discussions = data["data"]["repository"]["discussions"]["nodes"]
        
        if not discussions:
            raise ValueError("No existing guidelines discussion found")
            
        return discussions[0]["id"]

    def process_comment(self) -> None:
        """Process the PR comment and update guidelines if necessary."""
        try:
            # Load existing guidelines from discussions
            guidelines = self.get_guidelines_from_discussions()

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
                    self.update_guidelines_discussion(guidelines)
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
                
                # Remove markdown code block formatting if present
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