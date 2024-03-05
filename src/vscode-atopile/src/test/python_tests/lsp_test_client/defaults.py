# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
"""
Default initialize request params.
"""

import os

from .constants import PROJECT_ROOT
from .utils import as_uri, get_initialization_options

VSCODE_DEFAULT_INITIALIZE = {
    "processId": os.getpid(),
    "clientInfo": {"name": "vscode", "version": "1.45.0"},
    "rootPath": str(PROJECT_ROOT),
    "rootUri": as_uri(str(PROJECT_ROOT)),
    "capabilities": {
        "workspace": {
            "applyEdit": True,
            "workspaceEdit": {
                "documentChanges": True,
                "resourceOperations": ["create", "rename", "delete"],
                "failureHandling": "textOnlyTransactional",
            },
            "didChangeConfiguration": {"dynamicRegistration": True},
            "didChangeWatchedFiles": {"dynamicRegistration": True},
            "symbol": {
                "dynamicRegistration": True,
                "symbolKind": {
                    "valueSet": [
                        1,
                        2,
                        3,
                        4,
                        5,
                        6,
                        7,
                        8,
                        9,
                        10,
                        11,
                        12,
                        13,
                        14,
                        15,
                        16,
                        17,
                        18,
                        19,
                        20,
                        21,
                        22,
                        23,
                        24,
                        25,
                        26,
                    ]
                },
                "tagSupport": {"valueSet": [1]},
            },
            "executeCommand": {"dynamicRegistration": True},
            "configuration": True,
            "workspaceFolders": True,
        },
        "textDocument": {
            "publishDiagnostics": {
                "relatedInformation": True,
                "versionSupport": False,
                "tagSupport": {"valueSet": [1, 2]},
                "complexDiagnosticCodeSupport": True,
            },
            "synchronization": {
                "dynamicRegistration": True,
                "willSave": True,
                "willSaveWaitUntil": True,
                "didSave": True,
            },
            "completion": {
                "dynamicRegistration": True,
                "contextSupport": True,
                "completionItem": {
                    "snippetSupport": True,
                    "commitCharactersSupport": True,
                    "documentationFormat": ["markdown", "plaintext"],
                    "deprecatedSupport": True,
                    "preselectSupport": True,
                    "tagSupport": {"valueSet": [1]},
                    "insertReplaceSupport": True,
                },
                "completionItemKind": {
                    "valueSet": [
                        1,
                        2,
                        3,
                        4,
                        5,
                        6,
                        7,
                        8,
                        9,
                        10,
                        11,
                        12,
                        13,
                        14,
                        15,
                        16,
                        17,
                        18,
                        19,
                        20,
                        21,
                        22,
                        23,
                        24,
                        25,
                    ]
                },
            },
            "hover": {
                "dynamicRegistration": True,
                "contentFormat": ["markdown", "plaintext"],
            },
            "signatureHelp": {
                "dynamicRegistration": True,
                "signatureInformation": {
                    "documentationFormat": ["markdown", "plaintext"],
                    "parameterInformation": {"labelOffsetSupport": True},
                },
                "contextSupport": True,
            },
            "definition": {"dynamicRegistration": True, "linkSupport": True},
            "references": {"dynamicRegistration": True},
            "documentHighlight": {"dynamicRegistration": True},
            "documentSymbol": {
                "dynamicRegistration": True,
                "symbolKind": {
                    "valueSet": [
                        1,
                        2,
                        3,
                        4,
                        5,
                        6,
                        7,
                        8,
                        9,
                        10,
                        11,
                        12,
                        13,
                        14,
                        15,
                        16,
                        17,
                        18,
                        19,
                        20,
                        21,
                        22,
                        23,
                        24,
                        25,
                        26,
                    ]
                },
                "hierarchicalDocumentSymbolSupport": True,
                "tagSupport": {"valueSet": [1]},
            },
            "codeAction": {
                "dynamicRegistration": True,
                "isPreferredSupport": True,
                "codeActionLiteralSupport": {
                    "codeActionKind": {
                        "valueSet": [
                            "",
                            "quickfix",
                            "refactor",
                            "refactor.extract",
                            "refactor.inline",
                            "refactor.rewrite",
                            "source",
                            "source.organizeImports",
                        ]
                    }
                },
            },
            "codeLens": {"dynamicRegistration": True},
            "formatting": {"dynamicRegistration": True},
            "rangeFormatting": {"dynamicRegistration": True},
            "onTypeFormatting": {"dynamicRegistration": True},
            "rename": {"dynamicRegistration": True, "prepareSupport": True},
            "documentLink": {
                "dynamicRegistration": True,
                "tooltipSupport": True,
            },
            "typeDefinition": {
                "dynamicRegistration": True,
                "linkSupport": True,
            },
            "implementation": {
                "dynamicRegistration": True,
                "linkSupport": True,
            },
            "colorProvider": {"dynamicRegistration": True},
            "foldingRange": {
                "dynamicRegistration": True,
                "rangeLimit": 5000,
                "lineFoldingOnly": True,
            },
            "declaration": {"dynamicRegistration": True, "linkSupport": True},
            "selectionRange": {"dynamicRegistration": True},
        },
        "window": {"workDoneProgress": True},
    },
    "trace": "verbose",
    "workspaceFolders": [{"uri": as_uri(str(PROJECT_ROOT)), "name": "my_project"}],
    "initializationOptions": get_initialization_options(),
}
