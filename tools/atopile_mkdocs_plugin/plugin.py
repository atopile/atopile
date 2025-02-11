import logging
import re

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page

from atopile.config import ProjectConfig

logger = logging.getLogger(__name__)


def get_dict_path(path: str, data: dict) -> str:
    obj = data
    *start, last = path.split(".")
    for part in start:
        obj = obj.get(part, {})
    return obj.get(last, "")


class JsonSchemaPlugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.schema = ProjectConfig.model_json_schema()

    def on_page_markdown(
        self, markdown: str, *, page: Page, config: MkDocsConfig, files: Files
    ):
        """Process the markdown content of each page"""

        def replace_docstring(match) -> str:
            logger.debug(f"Replacing docstring {match.group(1)}")
            try:
                return get_dict_path(match.group(1), self.schema)
            except Exception as e:
                logger.exception(
                    f"Failed to replace docstring {match.group(1)}", exc_info=e
                )
                return ""

        return re.sub(r"!json-schema::([\$\w\.\-_]+)", replace_docstring, markdown)
