import * as fs from "fs";
import * as path from "path";
import * as vscode from "vscode";
import { execFile, spawn } from "child_process";

export interface ResolvedBinary {
  /** Path to the uv binary */
  command: string;
  /** Arguments prepended before any ato subcommand args */
  prefixArgs: string[];
  /** Whether we're running in local dev mode */
  isLocal: boolean;
  /** Resolved absolute path to the ato binary */
  atoBinary?: string;
}

export class AtoResolver {
  private readonly _context: vscode.ExtensionContext;
  private readonly _output: vscode.OutputChannel;

  constructor(context: vscode.ExtensionContext, output: vscode.OutputChannel) {
    this._context = context;
    this._output = output;
  }

  async resolve(version: string): Promise<ResolvedBinary> {
    const uvPath = await this._findOrBootstrapUv();
    const devPath = vscode.workspace
      .getConfiguration("atopile")
      .get<string>("devPath", "")
      .trim();

    const isLocal = !!devPath;
    const mode = isLocal ? "local" : "production";
    this._output.appendLine(`[AtoResolver] ${mode} mode${isLocal ? `: ${devPath}` : ""}`);

    // Dev: `uv run --directory <devPath> ato ...`
    // Prod: `uv tool run -p 3.14 --from atopile=={version} ato ...`
    let uvPrefix: string[];
    if (isLocal) {
      this._output.appendLine(`[AtoResolver] Running uv sync --dev in ${devPath}`);
      await this._spawnAndLog("uv sync", uvPath, ["sync", "--dev", "--directory", devPath]);
      uvPrefix = ["run", "--directory", devPath];
    } else {
      uvPrefix = ["tool", "run", "-p", "3.14", "--from", `atopile==${version}`];
    }

    const atoBinary = await this._resolveAtoBinary(uvPath, uvPrefix);
    return { command: uvPath, prefixArgs: [...uvPrefix, "ato"], isLocal, atoBinary };
  }

  /** Resolve the absolute path to the ato binary via the uv environment. */
  private async _resolveAtoBinary(
    uvPath: string,
    uvPrefix: string[],
  ): Promise<string | undefined> {
    const args = [...uvPrefix, "python", "-c", `import shutil; print(shutil.which("ato"))`];
    return new Promise((resolve) => {
      execFile(uvPath, args, (err, stdout) => {
        const result = stdout?.trim();
        if (err || !result || result === "None") {
          this._output.appendLine("[AtoResolver] Could not resolve ato binary");
          resolve(undefined);
        } else {
          this._output.appendLine(`[AtoResolver] ato binary: ${result}`);
          resolve(result);
        }
      });
    });
  }

  private async _findOrBootstrapUv(): Promise<string> {
    // 1. Check PATH
    const pathUv = await new Promise<string | null>((resolve) => {
      const cmd = process.platform === "win32" ? "where" : "which";
      execFile(cmd, ["uv"], (err, stdout) => {
        resolve(err || !stdout.trim() ? null : stdout.trim().split("\n")[0]);
      });
    });
    if (pathUv) {
      this._output.appendLine(`[AtoResolver] Found uv on PATH: ${pathUv}`);
      return pathUv;
    }

    // 2. Check previously-bootstrapped binary
    const bootstrapDir = path.join(
      this._context.globalStorageUri.fsPath,
      "uv"
    );
    const bootstrapBin = path.join(
      bootstrapDir,
      process.platform === "win32" ? "uv.exe" : "uv"
    );
    if (fs.existsSync(bootstrapBin)) {
      this._output.appendLine(
        `[AtoResolver] Found bootstrapped uv: ${bootstrapBin}`
      );
      return bootstrapBin;
    }

    // 3. Auto-install if allowed
    const autoInstall = vscode.workspace
      .getConfiguration("atopile")
      .get<boolean>("autoInstall", true);
    if (!autoInstall) {
      throw new Error(
        "uv not found on PATH and atopile.autoInstall is disabled. " +
          "Install uv manually or enable auto-install."
      );
    }

    await this._bootstrapUv(bootstrapDir);
    if (!fs.existsSync(bootstrapBin)) {
      throw new Error(
        `uv bootstrap completed but binary not found at ${bootstrapBin}`
      );
    }
    this._output.appendLine(
      `[AtoResolver] Bootstrapped uv to: ${bootstrapBin}`
    );
    return bootstrapBin;
  }

  private async _bootstrapUv(installDir: string): Promise<void> {
    fs.mkdirSync(installDir, { recursive: true });

    const [command, args] =
      process.platform === "win32"
        ? [
            "powershell",
            [
              "-NoProfile",
              "-Command",
              `$env:UV_INSTALL_DIR="${installDir}"; irm https://astral.sh/uv/install.ps1 | iex`,
            ],
          ]
        : [
            "sh",
            [
              "-c",
              `curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="${installDir}" sh`,
            ],
          ];

    await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: "atopile: Installing uv...",
        cancellable: false,
      },
      () => this._spawnAndLog("uv install", command, args),
    );
  }

  private _spawnAndLog(label: string, command: string, args: string[]): Promise<void> {
    return new Promise<void>((resolve, reject) => {
      const proc = spawn(command, args, { stdio: ["ignore", "pipe", "pipe"] });

      const log = (chunk: Buffer) => {
        for (const line of chunk.toString().trimEnd().split("\n")) {
          this._output.appendLine(`[${label}] ${line}`);
        }
      };

      proc.stdout?.on("data", log);
      proc.stderr?.on("data", log);
      proc.on("error", (err) =>
        reject(new Error(`${label} failed to start: ${err.message}`))
      );
      proc.on("exit", (code) => {
        if (code === 0) {
          resolve();
        } else {
          reject(new Error(`${label} exited with code ${code}`));
        }
      });
    });
  }
}
