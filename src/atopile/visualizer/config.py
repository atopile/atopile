"""
This file handels visual configuration files.
These files contain information such as:
    - layout of the schematic symbols
    - stubbing
    - link colours

It shall:
    - yaml -> JSON
    - update -> yaml
"""

class VisConfigManager:
    def __init__(self) -> None:
        pass

    def load(self, ato_file: str):
        """
        Load the contents of a config matching an .ato file to the cache
        """

    def save(self, ato_file: str):
        """
        Save the cached config file to disk
        TODO: consider rate limiting
        """

    def do_update(self, ato_file: str, content: dict):
        """
        Update the YAML file based on the given content, and save to disk
        """
        raise NotImplementedError
