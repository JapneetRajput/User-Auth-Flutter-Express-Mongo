import json
from typing import List, Dict, Any, Optional
from groq import Groq


class AIReviewHelper:
    def __init__(
        self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"
    ):
        self.api_key = api_key
        self.model = model

    def create_prompt(
        self, file: Dict[str, str], chunk: Dict[str, Any], pr_details: Dict[str, str]
    ) -> str:
        """
        Create a prompt for AI code review.
        """
        changes = "\n".join(
            [
                f"{c.get('ln', c.get('ln2', ''))} {c['content']}"
                for c in chunk["changes"]
            ]
        )

        return f"""Your task is to review pull requests. Instructions:
        - Provide the response in following JSON format:  {{"reviews": [{{"lineNumber":  <line_number>, "reviewComment": "<review comment>"}}]}}
        - Do not give positive comments or compliments.
        - Provide comments and suggestions ONLY if there is something to improve, otherwise "reviews" should be an empty array.
        - Write the comment in GitHub Markdown format.
        - Use the given description only for the overall context and only comment the code.
        - IMPORTANT: NEVER suggest adding comments to the code.

        Review the following code diff in the file "{file["to"]}" and take the pull request title and description into account when writing the response.
        
        Pull request title: {pr_details["title"]}
        Pull request description:

        ---
        {pr_details["description"]}
        ---

        Git diff to review:

        ```diff
        {chunk["content"]}
        {changes}
        ```"""

    def get_ai_response(self, prompt: str) -> Optional[List[Dict[str, str]]]:
        """
        Get AI review response from Groq.
        """
        client = Groq(api_key=self.api_key)

        while True:  # Keep retrying until a valid, non-empty response is obtained
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "system", "content": prompt}],
                    temperature=0.2,
                    max_tokens=700,
                    top_p=1,
                )

                # Parse the response content
                res = response.choices[0].message.content.strip()
                if res:  # If response is non-empty, attempt to parse it as JSON
                    try:
                        parsed_res = json.loads(res)
                        return parsed_res.get("reviews", [])
                    except json.JSONDecodeError:
                        print("Error: Failed to parse AI response as JSON.")
                        return []

                print("Warning: Received an empty response, retrying...")
            except Exception as error:
                print(f"Error while fetching AI response: {error}")
                return None

    def create_comment(
        self,
        file: Dict[str, str],
        chunk: Dict[str, Any],
        ai_responses: List[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        """
        Create GitHub review comments from AI responses.
        """
        return [
            {
                "body": response["reviewComment"],
                "path": file["to"],
                "line": int(response["lineNumber"]),
            }
            for response in ai_responses
            if file.get("to")
        ]
