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
            return path.join(os.homedir(), 'atopile');
    }
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

    if (!config.telemetry) {
        config.telemetry = true;
        fs.writeFileSync(configFile, stringify(config));
    }

    distinctId = config.id;
    enabled = config.telemetry;
}

async function getEmail() {
    const gitExtension = vscode.extensions.getExtension<GitExtension>('vscode.git')?.exports;
    const git = gitExtension?.getAPI(1);
    return await git?.repositories[0]?.getConfig('user.email');
}

export async function initializeTelemetry(context: vscode.ExtensionContext) {
    const email = await getEmail();

    defaultProperties = {
        version: context.extension.packageJSON.version,
        platform: process.platform,
        arch: process.arch,
        machineId: vscode.env.machineId,
        email: email,
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

    client.capture({
        distinctId,
        event,
        properties: {
            ...defaultProperties,
            ...properties,
        },
    });
}