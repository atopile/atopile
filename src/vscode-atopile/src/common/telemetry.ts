import { PostHog } from "posthog-node";
import * as vscode from 'vscode';
import { traceInfo } from "./log/logging";

const client = new PostHog('phc_IIl9Bip0fvyIzQFaOAubMYYM2aNZcn26Y784HcTeMVt', {
    host: 'https://telemetry.atopileapi.com',
});

let defaultProperties: Record<string, any> = {};

export function initializeTelemetry(context: vscode.ExtensionContext) {
    defaultProperties = {
        version: context.extension.packageJSON.version,
        platform: process.platform,
        arch: process.arch,
    };
}

export function deinitializeTelemetry() {
    client.shutdown().then(() => {
        traceInfo('Telemetry client shutdown');
    });
}

export function captureEvent(event: string, properties: Record<string, any> = {}) {
    client.capture({
        distinctId: vscode.env.machineId, // FIXME: check this is populated
        event,
        properties: {
            ...defaultProperties,
            ...properties,
        },
    });
}