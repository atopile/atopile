#!/bin/bash

antlr4 -visitor -no-listener -Dlanguage=Python3 AtopileLexer.g4 AtopileParser.g4
