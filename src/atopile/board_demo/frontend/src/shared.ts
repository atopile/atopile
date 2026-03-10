export interface DemoManifest {
    title?: string;
    subtitle?: string;
    layoutModelPath: string;
    modelPath: string;
    posterPath?: string;
    hiddenLayoutLayers?: string[];
    showStats?: boolean;
}

export interface MountOptions {
    assetBase?: string;
    manifest?: string | DemoManifest;
}
