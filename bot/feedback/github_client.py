"""
GitHub API client for creating feedback issues.
"""

from datetime import datetime
from typing import Dict, List, Optional

import aiohttp

from monitoring import get_logger, track_errors_async

logger = get_logger(__name__)


class GitHubFeedbackClient:
    """Client for creating GitHub issues from user feedback."""

    def __init__(self, token: str, repo: str):
        """
        Initialize GitHub client.

        Args:
            token: GitHub Personal Access Token
            repo: Repository in format 'owner/repo'
        """
        self.token = token
        self.repo = repo
        self.base_url = "https://api.github.com"

    @track_errors_async("github_api")
    async def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a GitHub issue.

        Args:
            title: Issue title
            body: Issue body (markdown)
            labels: Issue labels
            user_id: Telegram user ID for tracking
            username: Telegram username

        Returns:
            URL of created issue or None if failed
        """
        if not self.token:
            logger.warning("GitHub token not configured, cannot create issue")
            return None

        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Doyobi-Diary-Bot/1.0",
        }

        # Build issue data
        issue_data = {"title": title, "body": body}

        if labels:
            issue_data["labels"] = labels

        url = f"{self.base_url}/repos/{self.repo}/issues"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=issue_data) as response:
                    if response.status == 201:
                        result = await response.json()
                        issue_url = result.get("html_url")
                        issue_number = result.get("number")

                        logger.info(
                            f"Created GitHub issue #{issue_number}: {issue_url}",
                            extra={
                                "user_id": user_id,
                                "username": username,
                                "issue_number": issue_number,
                                "issue_url": issue_url,
                            },
                        )

                        return issue_url
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Failed to create GitHub issue: {response.status} - {error_text}",
                            extra={"status_code": response.status, "user_id": user_id, "username": username},
                        )
                        return None

        except Exception as e:
            logger.error(
                f"Error creating GitHub issue: {e}", extra={"user_id": user_id, "username": username, "error": str(e)}
            )
            return None

    def format_bug_report(
        self, user_description: str, user_id: int, username: Optional[str], user_language: str, bot_version: str = "2.1.0"
    ) -> Dict[str, str]:
        """Format bug report for GitHub issue."""
        timestamp = datetime.now().isoformat()

        title = f"🐛 Bug Report from User {user_id}"
        if username:
            title = f"🐛 Bug Report from @{username}"

        body = (
            f"## 🐛 User Bug Report\n\n"
            f"**Description from user:**\n{user_description}\n\n"
            f"**User Information:**\n"
            f"- User ID: {user_id}\n"
            f"- Username: @{username if username else 'N/A'}\n"
            f"- Language: {user_language}\n"
            f"- Timestamp: {timestamp}\n"
            f"- Bot Version: {bot_version}\n\n"
            f"**Category:** Bug Report\n"
            f"**Source:** Telegram Bot Feedback\n\n"
            f"---\n"
            f"*This issue was automatically created from user feedback in the Doyobi Diary Telegram bot.*"
        )

        return {"title": title, "body": body, "labels": ["user-feedback", "bug-report"]}

    def format_feature_request(
        self, user_description: str, user_id: int, username: Optional[str], user_language: str, bot_version: str = "2.1.0"
    ) -> Dict[str, str]:
        """Format feature request for GitHub issue."""
        timestamp = datetime.now().isoformat()

        title = f"💡 Feature Request from User {user_id}"
        if username:
            title = f"💡 Feature Request from @{username}"

        body = (
            f"## 💡 User Feature Request\n\n"
            f"**Suggestion from user:**\n{user_description}\n\n"
            f"**User Information:**\n"
            f"- User ID: {user_id}\n"
            f"- Username: @{username if username else 'N/A'}\n"
            f"- Language: {user_language}\n"
            f"- Timestamp: {timestamp}\n"
            f"- Bot Version: {bot_version}\n\n"
            f"**Category:** Feature Request\n"
            f"**Source:** Telegram Bot Feedback\n\n"
            f"---\n"
            f"*This issue was automatically created from user feedback in the Doyobi Diary Telegram bot.*"
        )

        return {"title": title, "body": body, "labels": ["user-feedback", "enhancement"]}

    def format_general_feedback(
        self, user_description: str, user_id: int, username: Optional[str], user_language: str, bot_version: str = "2.1.0"
    ) -> Dict[str, str]:
        """Format general feedback for GitHub issue."""
        timestamp = datetime.now().isoformat()

        title = f"📝 General Feedback from User {user_id}"
        if username:
            title = f"📝 General Feedback from @{username}"

        body = (
            f"## 📝 User Feedback\n\n"
            f"**Feedback from user:**\n{user_description}\n\n"
            f"**User Information:**\n"
            f"- User ID: {user_id}\n"
            f"- Username: @{username if username else 'N/A'}\n"
            f"- Language: {user_language}\n"
            f"- Timestamp: {timestamp}\n"
            f"- Bot Version: {bot_version}\n\n"
            f"**Category:** General Feedback\n"
            f"**Source:** Telegram Bot Feedback\n\n"
            f"---\n"
            f"*This issue was automatically created from user feedback in the Doyobi Diary Telegram bot.*"
        )

        return {"title": title, "body": body, "labels": ["user-feedback", "feedback"]}
