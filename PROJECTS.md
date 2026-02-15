# Projects

Here we keep the current roadmap of projects and their status.
Make sure to update the status whenever a worker makes progress.

## fabll zig & solver zig

fabll is a python library within faebryk to define typegraph types with python classes.
We want to provide the same functionality in zig.
We have started by implementing roughly 80% of the functionality in zig.
We port features from py-fabll to zig-fabll by demand.
Our main application that we want to use zig-fabll for is the solver.
The solver has a deep dependency tree:
literals, units, parameters, expressions, ...
We have already implemented quite a lot of those.

As a next step I suggest looking at exposing the new zig types to python so we can replace literals etc with their zig counterparts to check whether they work correctly.
This is a delicate task, because exposing fabll types to python is not trivial.

Phase: Implementation

## web-ide

atopile is currently designed as a vscode-extension.
A lot of people have expressed interest in using atopile in the web.
We have determined that the easiest way is to host a openvscode-server that is preconfigured opionated with atopile and has the extension installed.
Everything runs in a docker container and the browser.

Open tasks

- central python fast-api server that dynamically spawns docker containers for users
  - will require some smart port handling for the websockets that are opened by the extension
- in progress: make secure since users will use our server, so we want to prevent them from executing arbitrary code
- in progress: give the agent the ability to end-to-end test the web-ide
  - lots of logs are only available in the browser
  - also the ui is relevant to investigate sometimes
- resource constrain the containers to prevent abuse

Phase: Prototype

## kicanvas editable layout

We are currently using kicanvas in the atopile extension to render the layout of a pcb.
Kicanvas looks great and is fast.
It would be great if we could extend kicanvas to allow editing the layout.
The only high-priority feature is move footprints around.
Its possible that the best course-of-action is to rewrite kicanvas to make use of our faebryk and atopile library.
We have a very robust high-performance kicad pcb file parser and serializer. kicanvas probably only can parse.
A good architecture for that would be to have a local pcb-viewer.py fastapi server that communicates with the frontend via websockets.
And the try to use as much as possible from kicanvas for the actual rendering.
The protocol between the server and the frontend should be minimal and just contain the info that the frontend needs to render.
On repositioning the frontend would just send a "move_fp(id)" event to the server. This way the frontend doesn't need a full representation of the pcb.
And we can keep the protocol small.

Phase: Planning
