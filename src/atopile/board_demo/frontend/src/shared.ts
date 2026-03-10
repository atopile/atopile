export interface DemoManifest {
    title?: string;
    subtitle?: string;
    layoutModelPath: string;
    modelPath: string;
    codePath?: string;
    posterPath?: string;
    hiddenLayoutLayers?: string[];
    showStats?: boolean;
}

export interface MountOptions {
    assetBase?: string;
    manifest?: string | DemoManifest;
    /** Show the title bar with build name and badge. Defaults to true. */
    showHero?: boolean;
}
