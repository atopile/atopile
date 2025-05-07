# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import re
import subprocess


class GithubException(Exception):
    pass


class GithubCLINotFound(GithubException):
    pass


class GithubUserNotLoggedIn(GithubException):
    pass


class GithubCLI:
    def __init__(self):
        try:
            subprocess.check_output(["gh", "--version"])
        except Exception:
            raise GithubCLINotFound()

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

        auth = subprocess.check_output(["gh", "auth", "status"]).decode(
            encoding="utf-8"
        )
        logged_in = [
            line.strip() for line in auth.split("\n") if "Logged in to" in line
        ]
        users = [
            match.group(1)
            for line in logged_in
            if (match := re.match(r"^.*account\s+(\w+)\s+.*$", line))
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
