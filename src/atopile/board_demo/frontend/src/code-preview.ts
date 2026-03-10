/**
 * Lightweight .ato syntax highlighter for the demo embed.
 * Tokenizer is based on the TextMate grammar in vscode-atopile.
 */

type Token = { type: string; text: string };

const KEYWORDS = new Set([
    "import", "from", "module", "component", "interface",
    "new", "assert", "within", "is", "to", "for", "in",
    "pass", "pin", "signal", "trait",
]);

const CONSTANTS = new Set(["True", "False"]);

function tokenizeLine(line: string): Token[] {
    const tokens: Token[] = [];
    let i = 0;

    while (i < line.length) {
        // Whitespace
        if (/\s/.test(line[i])) {
            let j = i;
            while (j < line.length && /\s/.test(line[j])) j++;
            tokens.push({ type: "ws", text: line.slice(i, j) });
            i = j;
            continue;
        }

        // Comment
        if (line[i] === "#") {
            tokens.push({ type: "comment", text: line.slice(i) });
            break;
        }

        // Triple-quote docstring (single line)
        if (line.slice(i, i + 3) === '"""') {
            const end = line.indexOf('"""', i + 3);
            if (end !== -1) {
                tokens.push({ type: "string", text: line.slice(i, end + 3) });
                i = end + 3;
            } else {
                tokens.push({ type: "string", text: line.slice(i) });
                break;
            }
            continue;
        }

        // String
        if (line[i] === '"') {
            let j = i + 1;
            while (j < line.length && line[j] !== '"') {
                if (line[j] === "\\") j++;
                j++;
            }
            tokens.push({ type: "string", text: line.slice(i, j + 1) });
            i = j + 1;
            continue;
        }

        // Multi-char operators
        const op2 = line.slice(i, i + 2);
        if (op2 === "+/" && line[i + 2] === "-") {
            tokens.push({ type: "operator", text: "+/-" });
            i += 3;
            continue;
        }
        if (op2 === "~>" || op2 === "<~" || op2 === "->" || op2 === "::" || op2 === "+=" || op2 === "-=") {
            tokens.push({ type: "operator", text: op2 });
            i += 2;
            continue;
        }

        // Single-char operators/punctuation
        if ("~=.<>[](),:/+-*".includes(line[i])) {
            tokens.push({ type: "operator", text: line[i] });
            i++;
            continue;
        }

        // Number (possibly with unit)
        if (/\d/.test(line[i])) {
            const m = line.slice(i).match(/^\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/);
            if (m) {
                tokens.push({ type: "number", text: m[0] });
                i += m[0].length;
                // Unit suffix
                const um = line.slice(i).match(/^[a-zA-Z%Ωµμ°]+/);
                if (um) {
                    tokens.push({ type: "unit", text: um[0] });
                    i += um[0].length;
                }
                continue;
            }
        }

        // Word
        if (/[a-zA-Z_]/.test(line[i])) {
            const m = line.slice(i).match(/^[a-zA-Z_][a-zA-Z_0-9]*/)!;
            const word = m[0];
            i += word.length;

            if (KEYWORDS.has(word)) {
                tokens.push({ type: "keyword", text: word });
            } else if (CONSTANTS.has(word)) {
                tokens.push({ type: "constant", text: word });
            } else {
                const prev = tokens.filter(t => t.type !== "ws");
                const last = prev[prev.length - 1];
                if (last && (last.text === "new" || last.text === "import")) {
                    tokens.push({ type: "type", text: word });
                } else {
                    tokens.push({ type: "ident", text: word });
                }
            }
            continue;
        }

        // Fallback
        tokens.push({ type: "text", text: line[i] });
        i++;
    }

    return tokens;
}

function highlightCode(code: string): Token[][] {
    const raw = code.split("\n");
    const lines: Token[][] = [];
    let inDocstring = false;

    for (const line of raw) {
        if (inDocstring) {
            lines.push([{ type: "string", text: line }]);
            if (line.includes('"""')) inDocstring = false;
            continue;
        }

        const trimmed = line.trimStart();
        if (trimmed.startsWith('"""')) {
            if (trimmed.indexOf('"""', 3) !== -1) {
                lines.push(tokenizeLine(line));
            } else {
                inDocstring = true;
                lines.push([{ type: "string", text: line }]);
            }
            continue;
        }

        lines.push(tokenizeLine(line));
    }

    return lines;
}

const TOKEN_COLORS: Record<string, string> = {
    keyword:  "#c678dd",
    type:     "#e5c07b",
    string:   "#98c379",
    comment:  "#5c6370",
    number:   "#d19a66",
    unit:     "#56b6c2",
    operator: "#abb2bf",
    constant: "#d19a66",
    ident:    "#abb2bf",
};

/**
 * Mount the code preview pane into the given container.
 * Fetches the .ato source and renders syntax-highlighted code.
 */
export async function mountCodePreview(
    container: HTMLElement,
    codeUrl: string,
    filename: string,
): Promise<void> {
    const response = await fetch(codeUrl);
    if (!response.ok) {
        container.innerHTML = `<div style="padding:16px;color:#5c6370;">Failed to load source</div>`;
        return;
    }
    const code = await response.text();
    const lines = highlightCode(code);

    const lineNumWidth = String(lines.length).length + 1;

    let html = "";
    for (let i = 0; i < lines.length; i++) {
        const num = String(i + 1).padStart(lineNumWidth);
        let content = "";
        for (const t of lines[i]) {
            const escaped = t.text
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;");
            const color = TOKEN_COLORS[t.type];
            if (color && t.type === "comment") {
                content += `<span style="color:${color};font-style:italic">${escaped}</span>`;
            } else if (color) {
                content += `<span style="color:${color}">${escaped}</span>`;
            } else {
                content += escaped;
            }
        }
        html += `<div class="atopile-code-line"><span class="atopile-code-linenum">${num}</span><span class="atopile-code-content">${content}</span></div>`;
    }

    container.innerHTML = `
        <div class="atopile-code-header">
            <span class="atopile-code-filename">${filename}</span>
        </div>
        <div class="atopile-code-scroller">
            <pre class="atopile-code-pre"><code>${html}</code></pre>
        </div>
    `;
}
