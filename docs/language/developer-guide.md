# Developer Guide

## Getting Started

ANTLR (or more specifically Java) was a PITA to get working on my Mac... so, I didn't 🤷‍♂️, I just wrapped up ANTLR in a neat little dockerised bundle and make a script that calls out to it easily.

As of writing, that lives in [mawildoer/antlr4](https://github.com/mawildoer/antlr4/tree/mawildoer/simplified-portable-docker/docker-simplified), but [hopefully we can get it into ANTLR mainline](https://github.com/antlr/antlr4/pull/4244) soon.

For now, clone the branch in the first link (eg. to your "repos" or "projects" directory), and then follow the [instructions](https://github.com/mawildoer/antlr4/tree/mawildoer/simplified-portable-docker/docker-simplified) on how to build it.

## Building the Grammar

`cd src/atopile/parser`

`/Users/mattwildoer/Projects/antlr4/docker-simplified/antlr4 -Dlanguage=Python3 -visitor AtopileParser.g4 AtopileLexer.g4`
