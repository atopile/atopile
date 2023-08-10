# Developer


## Prerequisites

You'll need >= `python3.10` and `pip` (Use `brew`).
I'd strongly recommend developing within a `venv`.
You'll need `npm` for front-end development (`brew install node`).

## Getting started

For cli development: `pip install -e ."[dev,test,docs]"`

For any front-end development, you'll also need to install the front-end dependencies: `npm install`

To check out front-end changes live, run `npm run start` in one terminal and make sure to run `ato view` on a project in another (to provide API access).

Your changes there should flow through live

