# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import re
import subprocess
from pathlib import Path

GITHUB_USERNAME_REGEX_PART = r"[a-zA-Z0-9](?:[a-zA-Z0-9]|(-[a-zA-Z0-9])){0,38}"
GITHUB_USERNAME_REGEX = rf"^{GITHUB_USERNAME_REGEX_PART}$"


class GithubException(Exception):
    pass


class GithubCLINotFound(GithubException):
    pass


class GithubUserNotLoggedIn(GithubException):
    pass


class GithubRepoAlreadyExists(GithubException):
    pass


class GithubRepoNotFound(GithubException):
    pass


class GithubCLI:
    def __init__(self):
        try:
            subprocess.check_output(["gh", "--version"])
        except Exception:
            raise GithubCLINotFound()

        # check if logged in
        self.get_usernames()

    @property
    def use_ssh(self) -> bool:
        # BUG
        # subprocess.check_output(
        #    ["gh", "config", "get", "git_protocol"], stderr=subprocess.DEVNULL
        # )
        configs = (
            subprocess.check_output(["gh", "config", "list"], stderr=subprocess.DEVNULL)
            .decode(encoding="utf-8")
            .splitlines()
        )
        return "git_protocol=ssh" in configs

    def get_usernames(self) -> list[str]:
        # github.com
        #  ✓ Logged in to github.com account <USERNAME> (~/.config/gh/hosts.yml)
        #  - Active account: true
        #  - Git operations protocol: ssh
        #  - Token: gho_************************************
        #  - Token scopes: 'admin:public_key', 'gist', 'read:org', 'repo'
        #
        #  ✓ Logged in to github.com account <USERNAME> (~/.config/gh/hosts.yml)
        #  - Active account: false
        #  - Git operations protocol: ssh
        #  - Token: gho_************************************
        #  - Token scopes: 'admin:public_key', 'gist', 'read:org', 'repo'

        try:
            auth = subprocess.check_output(
                ["gh", "auth", "status"], stderr=subprocess.DEVNULL
            ).decode(encoding="utf-8")
        except subprocess.CalledProcessError:
            raise GithubUserNotLoggedIn()
        logged_in = [
            line.strip() for line in auth.split("\n") if "Logged in to" in line
        ]
        users = [
            match.group(1)
            for line in logged_in
            if (
                match := re.match(
                    rf"^.*account\s+({GITHUB_USERNAME_REGEX_PART})\s+.*$", line
                )
            )
        ]
        if not users:
            raise GithubUserNotLoggedIn()
        return users

    def get_orgs(self) -> list[str]:
        # Showing 2 of 2 organizations

        # faebryk
        # atopile

        orgs_res = subprocess.check_output(["gh", "org", "list"]).decode(
            encoding="utf-8"
        )
        orgs = [
            stripped
            for line in orgs_res.split("\n")
            if (stripped := line.strip()) and not stripped.startswith("Showing")
        ]

        user_orgs = self.get_usernames()
        return orgs + user_orgs

    def create_repo(
        self,
        repo_id: str,
        visibility: str = "public",
        add_remote: bool = False,
        path: Path | None = None,
    ) -> str:
        """
        Creates a GitHub repository.
        repo_id: The repository identifier, e.g., "owner/repo_name".
        visibility: "public" or "private".
        add_remote: If True, adds the new repo as a remote named 'origin'
        to the local git repo in CWD and pushes.
        Returns the URL of the created repository.
        """
        cmd = ["gh", "repo", "create", repo_id, f"--{visibility}"]
        if add_remote:
            cmd.extend(["--source=.", "--remote=origin", "--push"])

        try:
            # gh repo create prints the URL of the new repo to stdout
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, cwd=path
            )
            # The URL is usually the last line of the output if successful
            url = result.stdout.strip().split("\\n")[-1]
            if not url.startswith("https://"):  # simple check if it's a URL
                # if --source=. is used, the output is just the URL
                # if not, it's like
                # "✓ Created repository <user>/<repo> on GitHub\n<URL>"
                match = re.search(r"(https://github.com/[\w-]+/[\w.-]+)", result.stdout)
                if match:
                    url = match.group(1)
                else:
                    raise GithubException(
                        f"Could not parse URL from gh repo create output:"
                        f" {result.stdout}"
                    )
            return url
        except subprocess.CalledProcessError as e:
            if "already exists" in e.stderr:
                raise GithubRepoAlreadyExists(
                    f"Repository {repo_id} already exists."
                ) from e
            raise GithubException(
                f"Failed to create repository {repo_id}: {e.stderr}"
            ) from e

    def get_repo_url(self, repo_id: str) -> str:
        """
        Gets the URL of an existing GitHub repository.
        repo_id: The repository identifier, e.g., "owner/repo_name".
        Returns the URL of the repository.
        """
        if self.use_ssh:
            cmd = ["gh", "repo", "view", repo_id, "--json", "sshUrl", "-q", ".sshUrl"]
        else:
            cmd = ["gh", "repo", "view", repo_id, "--json", "url", "-q", ".url"]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, cwd=None
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            if (
                "Could not find repository" in e.stderr
                or "Could not resolve" in e.stderr
            ):
                raise GithubRepoNotFound(f"Repository {repo_id} not found.") from e
            raise GithubException(
                f"Failed to get URL for repository {repo_id}: {e.stderr}"
            ) from e
