# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re
from pathlib import Path

from faebryk.core.trait import Trait

logger = logging.getLogger(__name__)

s = r"\s*"


def p_group(pattern: str, name: str | None = None):
    if not name:
        return pattern
    return rf"(?P<{name}>{pattern})"


def p_string(name: str | None = None):
    inner = p_group(r'([^"]*?)', name)
    return rf'"{inner}"'


def p_assignment(key_name: str | None = None, value_name: str | None = None):
    return rf"{p_group(r'\w+', key_name)}{s}={s}{p_string(value_name)}{s}"


class AtoCodeParse:
    """
    Ghetto ato code parser. Only good for quick prototyping.
    Better use Bob.
    """

    class TraitNotFound(Exception):
        pass

    class ComponentFile:
        def __init__(self, content: str | Path):
            if isinstance(content, Path):
                self.ato = content.read_text("utf-8")
            else:
                self.ato = content

            self.ato_no_comments = re.sub(r"#.*", "", self.ato)

        def parse_trait(
            self,
            trait: str,
        ) -> tuple[str | None, dict[str, str]]:
            trait_match = re.search(
                rf"trait {trait}(?P<constructor>::[a-zA-Z0-9_]+)?(?P<args><.+?>)?",
                self.ato_no_comments,
                re.DOTALL,
            )
            if not trait_match:
                raise AtoCodeParse.TraitNotFound(f"Could not find {trait} trait")
            args_stmt = trait_match.group("args") or ""
            m_args = re.finditer(
                f"{p_assignment(key_name='k', value_name='v')}[,>]", args_stmt
            )
            args = {match.group("k"): match.group("v") for match in m_args if match}

            parsed_constructor = (
                trait_match.group("constructor").removeprefix("::")
                if trait_match.group("constructor")
                else None
            )

            return parsed_constructor, args

        def parse_trait_args(
            self,
            trait: str,
            require_args: list[str],
            require_constructor: str | None = None,
        ) -> dict[str, str]:
            trait_constructor, trait_args = self.parse_trait(trait)

            missing = [arg for arg in require_args if arg not in trait_args]
            if missing:
                raise AtoCodeParse.TraitNotFound(
                    f"Missing required arguments for trait {trait}: {missing}"
                )

            if require_constructor and trait_constructor != require_constructor:
                raise AtoCodeParse.TraitNotFound(
                    f"Constructor mismatch for trait"
                    f" {trait}: {trait_constructor} != {require_constructor}"
                )

            return trait_args

        def get_trait[T: Trait](self, trait: type[T]) -> T:
            constructor, args = self.parse_trait(trait.__name__)
            f = trait if constructor is None else getattr(trait, constructor)
            return f(**args)

        def try_get_trait[T: Trait](self, trait: type[T]) -> T | None:
            try:
                return self.get_trait(trait)
            except AtoCodeParse.TraitNotFound:
                return None

        def parse_docstring(self) -> str:
            docstring = re.search(
                r'component [a-zA-Z0-9_]+:\n    """(.*?)"""',
                self.ato_no_comments,
                re.DOTALL,
            )
            if docstring:
                return docstring.group(1)
            else:
                return ""
