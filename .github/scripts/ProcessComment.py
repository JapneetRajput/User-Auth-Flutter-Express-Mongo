from github import Github, Auth
from groq import Client
import requests
import json
import os
import logging
from typing import List, Dict, Optional, Tuple

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

    def get_repository_id(self) -> str:
        """Get the GitHub repository ID."""
        query = f"""
        {{
        repository(owner: "{self.github_owner}", name: "{self.github_repo}") {{
            id
        }}
        }}
        """

        response = requests.post(self.graphql_url, headers=self.headers, json={"query": query})
        data = response.json()

        if "errors" in data:
            logging.error(f"Failed to fetch repository ID: {data['errors']}")
            raise ValueError("Failed to get repository ID")

        return data["data"]["repository"]["id"]

    def find_guidelines_discussion(self) -> Tuple[Optional[str], Optional[List[str]]]:
        """Find the existing guidelines discussion and return its ID and content."""
        query = f"""
        {{
        repository(owner: "{self.github_owner}", name: "{self.github_repo}") {{
            discussions(first: 10, orderBy: {{field: CREATED_AT, direction: DESC}}) {{
            nodes {{
                id
                title
                body
            }}
            }}
        }}
        }}
        """

        response = requests.post(self.graphql_url, headers=self.headers, json={"query": query})
        data = response.json()

        if "errors" in data:
            logging.error(f"Failed to fetch discussions: {data['errors']}")
            return None, None

        discussions = data["data"]["repository"]["discussions"]["nodes"]
        for discussion in discussions:
            if discussion["title"] == "Coding Guidelines":
                try:
                    guidelines = json.loads(discussion["body"])
                    return discussion["id"], guidelines.get("guidelines", [])
                except json.JSONDecodeError:
                    logging.warning(f"Found guidelines discussion but couldn't parse JSON: {discussion['body']}")
                    return discussion["id"], []

        return None, None

    def create_or_update_discussion(self, guidelines: List[str]) -> None:
        """Create a new discussion or update existing one with guidelines."""
        discussion_id, existing_guidelines = self.find_guidelines_discussion()

        if discussion_id:
            # Update existing discussion
            mutation = """
            mutation($discussionId: ID!, $body: String!) {
                updateDiscussion(input: {discussionId: $discussionId, body: $body}) {
                    discussion {
                        url
                    }
                }
            }
            """
            
            variables = {
                "discussionId": discussion_id,
                "body": json.dumps({"guidelines": guidelines}, indent=2)
            }
        else:
            # Create new discussion
            mutation = """
            mutation($repositoryId: ID!, $title: String!, $body: String!) {
                createDiscussion(input: {repositoryId: $repositoryId, title: $title, body: $body}) {
                    discussion {
                        url
                    }
                }
            }
            """
            
            variables = {
                "repositoryId": self.get_repository_id(),
                "title": "Coding Guidelines",
                "body": json.dumps({"guidelines": guidelines}, indent=2)
            }

        response = requests.post(
            self.graphql_url,
            headers=self.headers,
            json={"query": mutation, "variables": variables}
        )
        
        data = response.json()
        if "errors" in data:
            logging.error(f"Failed to {'update' if discussion_id else 'create'} discussion: {data['errors']}")
            raise ValueError(f"Failed to {'update' if discussion_id else 'create'} discussion")

    def process_comment(self) -> None:
        """Process the PR comment and update guidelines if necessary."""
        try:
            # Load existing guidelines from discussion
            _, guidelines = self.find_guidelines_discussion()
            guidelines = guidelines or []  # Initialize empty list if None

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
                    self.create_or_update_discussion(guidelines)
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