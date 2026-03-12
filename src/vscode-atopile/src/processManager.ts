import * as vscode from "vscode";
import { ChildProcess, spawn } from "child_process";

export interface ProcessConfig {
  /** Display name, e.g. "Hub", "CoreServer" */
  name: string;
  /** Command to spawn, e.g. "ato" */
  command: string;
  /** Arguments, e.g. ["serve", "hub", "--port", "12345"] */
  args: string[];
  /** Line printed to stdout when the process is ready */
  readyMarker: string;
  /** Extra environment variables */
  env?: Record<string, string>;
  /** How long to wait for readyMarker before rejecting (default 30_000) */
  timeoutMs?: number;
}

/**
 * Generic managed-process class.
 *
 * Spawns a child process, waits for a readyMarker on stdout,
 * and provides stop/restart/dispose lifecycle.
 */
export class ProcessManager implements vscode.Disposable {
  private _process: ChildProcess | null = null;
  private _disposed = false;

  private readonly _output: vscode.OutputChannel;
  private readonly _config: ProcessConfig;

  constructor(output: vscode.OutputChannel, config: ProcessConfig) {
    this._output = output;
    this._config = config;
  }

  /**
   * Spawn the process and wait for the readyMarker on stdout.
   * Rejects if the process exits, errors, or times out before the marker.
   */
  async start(): Promise<void> {
    const { name, command, args, readyMarker, env, timeoutMs = 30_000 } = this._config;

    this._output.appendLine(`[${name}] Starting: ${command} ${args.join(" ")}`);

    const proc = spawn(command, args, {
      stdio: ["ignore", "pipe", "pipe"],
      env: { ...process.env, ...env },
    });

    this._process = proc;

    // Forward stderr
    proc.stderr?.on("data", (chunk: Buffer) => {
      for (const line of chunk.toString().trimEnd().split("\n")) {
        this._output.appendLine(`[${name}] ${line}`);
      }
    });

    // Wait for readyMarker on stdout
    await new Promise<void>((resolve, reject) => {
      let resolved = false;

      proc.stdout?.on("data", (chunk: Buffer) => {
        const text = chunk.toString();
        for (const line of text.trimEnd().split("\n")) {
          this._output.appendLine(`[${name}] ${line}`);
        }

        if (!resolved && text.includes(readyMarker)) {
          resolved = true;
          resolve();
        }
      });

      proc.on("error", (err) => {
        this._output.appendLine(`[${name}] Process error: ${err.message}`);
        if (!resolved) {
          resolved = true;
          reject(new Error(`Failed to start ${name}: ${err.message}`));
        }
      });

      proc.on("exit", (code, signal) => {
        const suffix = signal ? ` (signal ${signal})` : "";
        this._output.appendLine(`[${name}] Exited with code ${code}${suffix}`);
        if (!resolved) {
          resolved = true;
          reject(new Error(`${name} exited with code ${code} before ready`));
        }
      });

      setTimeout(() => {
        if (!resolved) {
          resolved = true;
          reject(new Error(`${name} did not become ready within ${timeoutMs}ms`));
        }
      }, timeoutMs);
    });

    this._output.appendLine(`[${name}] Ready`);
  }

  /** Send SIGTERM, wait 2s, then SIGKILL if needed. */
  async stop(): Promise<void> {
    if (!this._process) return;

    const proc = this._process;
    this._process = null;
    const name = this._config.name;

    this._output.appendLine(`[${name}] Stopping...`);

    proc.kill("SIGTERM");

    const exited = await new Promise<boolean>((resolve) => {
      const timer = setTimeout(() => resolve(false), 2000);
      proc.on("exit", () => {
        clearTimeout(timer);
        resolve(true);
      });
    });

    if (!exited) {
      this._output.appendLine(`[${name}] Force killing...`);
      proc.kill("SIGKILL");
    }

    this._output.appendLine(`[${name}] Stopped`);
  }

  /** Stop then start. */
  async restart(): Promise<void> {
    await this.stop();
    await this.start();
  }

  /** Immediate SIGKILL for extension deactivation. */
  dispose(): void {
    this._disposed = true;
    if (this._process) {
      this._process.kill("SIGKILL");
      this._process = null;
    }
  }
}
