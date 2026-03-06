import * as vscode from 'vscode';

const WEB_IDE_DEFAULT_BACKEND_PORT = 8501;

export function isWebIdeHost(): boolean {
    return (
        isTruthyEnv(process.env.WEBIDE) ||
        isTruthyEnv(process.env.WEB_IDE_MODE) ||
        Boolean(process.env.OPENVSCODE_SERVER_ROOT)
    );
}

export function isWebIdeUi(): boolean {
    return vscode.env.uiKind === vscode.UIKind.Web || isWebIdeHost();
}

function isTruthyEnv(value: string | undefined): boolean {
    if (!value) {
        return false;
    }
    const normalized = value.toLowerCase();
    return normalized === '1' || normalized === 'true' || normalized === 'yes';
}

export function hasConfiguredBackendPort(): boolean {
    return getConfiguredBackendPort() !== undefined;
}

export function getConfiguredBackendPort(): number | undefined {
    const portString = process.env.ATOPILE_BACKEND_PORT?.trim();
    if (portString) {
        const parsed = parseInt(portString, 10);
        if (!Number.isNaN(parsed)) {
            return parsed;
        }
    }

    // OpenVSCode's web extension host does not reliably inherit container env vars.
    // In web-idectl mode the backend is always pre-started on the fixed internal port.
    if (isWebIdeUi()) {
        return WEB_IDE_DEFAULT_BACKEND_PORT;
    }

    return undefined;
}
