import { PostHog } from "posthog-node";
import * as vscode from 'vscode';
import { GitExtension } from '../git';
import path = require("path");
import * as os from "os";
import * as fs from "fs";
import { randomUUID } from "crypto";
import { parse, stringify } from 'yaml'
import { traceError } from "./log/logging";
import { getExtensionSettings } from "./settings";
import { createHash } from 'node:crypto';

// write-only API key, intended to be made public
const client = new PostHog('phc_IIl9Bip0fvyIzQFaOAubMYYM2aNZcn26Y784HcTeMVt', {
    host: 'https://telemetry.atopileapi.com',
});

let defaultProperties: Record<string, any> = {};
let distinctId: string | undefined = undefined;
let enabled: boolean = true;

function getConfigDir(): string {
    switch (process.platform) {
        case 'win32': {
            const localAppData = process.env.LOCALAPPDATA;
            if (localAppData) {
                return path.join(localAppData, 'atopile', 'atopile');
            }
            return path.join(os.homedir(), 'AppData', 'Local', 'atopile', 'atopile');
        }
        case 'linux':
        case 'darwin':
        default:
            const xdg = process.env.XDG_CONFIG_HOME;
            if (xdg) {
                return path.join(xdg, 'atopile');
            }
            return path.join(os.homedir(), '.config', 'atopile');
    }
}

export function updateConfig(enabled: boolean) {
    const configDir = getConfigDir();
    const configFile = path.join(configDir, 'telemetry.yaml');
    const config = parse(fs.readFileSync(configFile, 'utf8'));
    config.telemetry = enabled;
    fs.writeFileSync(configFile, stringify(config));
    enabled = config.telemetry;
}

function loadConfig() {
    const configDir = getConfigDir();
    const configFile = path.join(configDir, 'telemetry.yaml');

    if (!fs.existsSync(configFile)) {
        const config = { telemetry: true, id: randomUUID() };
        fs.mkdirSync(configDir, { recursive: true });
        fs.writeFileSync(configFile, stringify(config));
        distinctId = config.id;
        enabled = config.telemetry;
        return;
    }

    const config = parse(fs.readFileSync(configFile, 'utf8'));
    if (!config.id) {
        config.id = randomUUID();
        fs.writeFileSync(configFile, stringify(config));
    }

    if (typeof config.telemetry !== 'boolean') {
        config.telemetry = true;
        fs.writeFileSync(configFile, stringify(config));
    }

    distinctId = config.id;
    enabled = config.telemetry;
}

async function getGitExtension(): Promise<vscode.Extension<GitExtension> | undefined> {
    try {
        return vscode.extensions.getExtension<GitExtension>('vscode.git');
    } catch (error) {
        traceError('Git extension not enabled', error);
        return undefined;
    }
}

async function getEmail() {
    const gitExtension = await getGitExtension();
    if (!gitExtension) {
        return;
    }
    const git = gitExtension.exports.getAPI(1);
    return await git?.repositories[0]?.getConfig('user.email');
}

async function getProjectId() {
    const gitExtension = await getGitExtension();
    if (!gitExtension) {
        return;
    }
    const git = gitExtension.exports.getAPI(1);
    const repo = git?.repositories[0];
    if (!repo) {
        return;
    }
    let remote = await repo.getConfig('remote.origin.url');
    if (!remote) {
        return;
    }

    // Normalize git remote URL to a common format
    // Convert from:
    //   - https://github.com/atopile/atopile.git
    //   - git@github.com:atopile/atopile.git
    // To: github.com/atopile/atopile
    if (remote.startsWith('git@')) {
        remote = remote.replace('git@', '');
        remote = remote.replace(':', '/');
    } else {
        remote = remote.replace('https://', '');
    }

    remote = remote.replace('.git', '');

    const projectId = createHash('sha256').update(remote).digest('hex');
    return projectId;
}

export async function initializeTelemetry(context: vscode.ExtensionContext) {
    defaultProperties = {
        version: context.extension.packageJSON.version,
        platform: process.platform,
        arch: process.arch,
        machineId: vscode.env.machineId,
    };

    loadConfig();

    const settings = await getExtensionSettings();
    for (const setting of settings) {
        if (setting.telemetry === false) {
            enabled = false;
            break;
        }
    }
}

export function deinitializeTelemetry() {
    client.shutdown();
}

export async function captureEvent(event: string, properties: Record<string, any> = {}) {
    if (!enabled) {
        return;
    }

    if (!distinctId) {
        traceError('Telemetry not yet initialized');
        return;
    }

    const email = await getEmail();
    const projectId = await getProjectId();

    client.capture({
        distinctId,
        event,
        properties: {
            ...defaultProperties,
            email: email,
            projectId: projectId,
            ...properties,
        },
    });
}