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
        self.category_id = "DIC_kwDOLcf9Ac4Cmjfq"
        
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
        
        # Log the raw response for debugging
        logging.debug(f"Raw GraphQL response: {response.text}")
        
        # Check for HTTP errors
        response.raise_for_status()
        
        data = response.json()
        
        # Check for GraphQL errors
        if "errors" in data:
            error_message = json.dumps(data["errors"])
            logging.error(f"GraphQL errors: {error_message}")
            raise ValueError(f"GraphQL query failed: {error_message}")
            
        # Validate response structure
        if "data" not in data:
            logging.error("No 'data' in GraphQL response")
            raise ValueError("Invalid GraphQL response: missing 'data' field")
            
        repository = data.get("data", {}).get("repository")
        if not repository:
            logging.error("No 'repository' in GraphQL response")
            raise ValueError("Invalid GraphQL response: missing 'repository' field")
            
        categories = repository.get("discussionCategories", {}).get("nodes", [])
        if not categories:
            logging.error("No discussion categories found")
            raise ValueError("No discussion categories found in repository")
        
        # Look for matching category
        for category in categories:
            if category and isinstance(category, dict) and category.get("name") == category_name:
                return category["id"]
                
        # If we get here, we didn't find the category
        logging.error(f"Discussion category '{category_name}' not found. Available categories: {[c.get('name') for c in categories if c]}")
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
        
        # Log the raw response for debugging
        logging.debug(f"Raw GraphQL response: {response.text}")
        
        # Check for HTTP errors
        response.raise_for_status()
        
        data = response.json()
        
        # Check for GraphQL errors
        if "errors" in data:
            error_message = json.dumps(data["errors"])
            logging.error(f"GraphQL errors: {error_message}")
            return []
            
        repository = data.get("data", {}).get("repository", {})
        discussions = repository.get("discussions", {}).get("nodes", [])
        
        if not discussions:
            logging.info("No existing discussions found")
            return []
            
        # Parse the guidelines from the discussion body
        try:
            guidelines_text = discussions[0]["body"]
            # Assuming the guidelines are stored as a JSON string in the discussion
            guidelines_data = json.loads(guidelines_text)
            return guidelines_data.get("guidelines", [])
        except (json.JSONDecodeError, KeyError) as e:
            logging.error(f"Failed to parse guidelines from discussion: {e}")
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

    def post_to_discussions(self, guidelines: str) -> None:
        """Create a new discussion with the guidelines."""
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

        # Get repository ID
        repo_query = """
        query($owner: String!, $name: String!) {
          repository(owner: $owner, name: $name) {
            id
          }
        }
        """

        # Get repository ID
        repo_response = requests.post(
            self.graphql_url,
            headers=self.headers,
            json={
                "query": repo_query,
                "variables": {
                    "owner": self.github_owner,
                    "name": self.github_repo
                }
            }
        )
        
        repo_data = repo_response.json()
        
        if "errors" in repo_data:
            logging.error(f"Failed to fetch repository ID: {repo_data['errors']}")
            raise ValueError("Failed to fetch repository ID")
            
        repository_id = repo_data.get("data", {}).get("repository", {}).get("id")
        if not repository_id:
            raise ValueError("Repository ID not found in response")

        # Create the discussion
        variables = {
            "repositoryId": repository_id,
            "categoryId": self.category_id,
            "title": "Coding Guidelines",
            "body": guidelines
        }

        response = requests.post(
            self.graphql_url,
            headers=self.headers,
            json={"query": mutation, "variables": variables}
        )
        
        data = response.json()
        if "errors" in data:
            logging.error(f"Failed to create discussion: {data['errors']}")
            raise ValueError("Failed to create discussion")
        else:
            discussion_url = data.get("data", {}).get("createDiscussion", {}).get("discussion", {}).get("url")
            if discussion_url:
                logging.info(f"Discussion created successfully: {discussion_url}")
            else:
                logging.error("Discussion created but URL not found in response")

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
        
        try:
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
                raise ValueError("Failed to update discussion")
            else:
                logging.info("Guidelines discussion updated successfully")
                
        except Exception as e:
            logging.error(f"Error updating discussion: {e}")
            raise

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
        
        if "errors" in data:
            logging.error(f"Failed to fetch discussion ID: {data['errors']}")
            raise ValueError("Failed to fetch discussion ID")
            
        discussions = data.get("data", {}).get("repository", {}).get("discussions", {}).get("nodes", [])
        
        if not discussions:
            raise ValueError("No existing guidelines discussion found")
            
        discussion_id = discussions[0].get("id")
        if not discussion_id:
            raise ValueError("Discussion ID not found in response")
            
        return discussion_id

    # Rest of the class methods remain the same...

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