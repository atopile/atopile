export interface HtmlBuilderOptions {
    title: string;
    styles?: string;
    scripts?: Array<{ type?: string; src: string }>;
    body: string;
}

export function buildHtml(options: HtmlBuilderOptions): string {
    const scriptTags = options.scripts
        ?.map(script => {
            const type = script.type ? ` type="${script.type}"` : '';
            return `<script${type} src="${script.src}"></script>`;
        })
        .join('\n        ') || '';

    return /* html */ `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>${options.title}</title>
            ${scriptTags ? scriptTags + '\n            ' : ''}<style>
                html, body {
                    padding: 0;
                    margin: 0;
                    height: 100%;
                    width: 100%;
                    overflow: hidden;
                }
                ${options.styles || ''}
            </style>
        </head>
        <body>
            ${options.body}
        </body>
        </html>`;
}