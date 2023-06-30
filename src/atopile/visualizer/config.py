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

# eg. update this junk
def do_move(self, elementid, x, y):
    # as of writing, the elementid is the element's path
    # so just use that
    self._vis_data.setdefault(elementid, {})['position'] = {"x": x, "y": y}
    with self.vis_file_path.open('w') as f:
        yaml.dump(self._vis_data, f)
    self._ignore_files.append(self.vis_file_path)
    asyncio.get_event_loop().call_soon(self.rebuild_view)