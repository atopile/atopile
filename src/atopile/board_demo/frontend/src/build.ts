import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

declare const Bun: {
    build(options: unknown): Promise<{
        success: boolean;
        logs: Array<{ message: string }>;
    }>;
};

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const buildDir = path.join(rootDir, "build");
const distDir = path.join(rootDir, "dist");
const embedEntry = path.join(rootDir, "src", "embed.ts");
const embedStyles = path.join(rootDir, "src", "embed.css");
const embedTemplate = path.join(rootDir, "src", "embed.hbs");
const generatedStylesModule = path.join(buildDir, "styles.ts");
const generatedTemplateModule = path.join(buildDir, "template.ts");
const earcutSource = path.join(rootDir, "node_modules", "earcut", "src", "earcut.js");

await rm(distDir, { recursive: true, force: true });
await rm(buildDir, { recursive: true, force: true });
await mkdir(distDir, { recursive: true });
await mkdir(buildDir, { recursive: true });
await writeFile(
    generatedStylesModule,
    `export default ${JSON.stringify(await readFile(embedStyles, "utf8"))};\n`,
    "utf8",
);
await writeFile(
    generatedTemplateModule,
    `export default ${JSON.stringify(await readFile(embedTemplate, "utf8"))};\n`,
    "utf8",
);

const buildResult = await Bun.build({
    entrypoints: [embedEntry],
    outdir: distDir,
    naming: "embed.js",
    format: "iife",
    target: "browser",
    minify: true,
    sourcemap: "none",
    plugins: [
        {
            name: "demo-aliases",
            setup(build: {
                onResolve(
                    options: { filter: RegExp },
                    callback: () => { path: string },
                ): void;
            }) {
                build.onResolve({ filter: /^earcut$/ }, () => ({ path: earcutSource }));
            },
        },
    ],
});

if (!buildResult.success) {
    for (const log of buildResult.logs) {
        console.error(log.message);
    }
    process.exit(1);
}
