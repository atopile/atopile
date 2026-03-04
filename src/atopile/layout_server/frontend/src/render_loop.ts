export class RenderLoop {
    private rafHandle: number | null = null;

    constructor(private readonly tick: () => void) {}

    start(): void {
        if (this.rafHandle !== null) return;
        const loop = () => {
            this.tick();
            this.rafHandle = window.requestAnimationFrame(loop);
        };
        this.rafHandle = window.requestAnimationFrame(loop);
    }

    stop(): void {
        if (this.rafHandle === null) return;
        window.cancelAnimationFrame(this.rafHandle);
        this.rafHandle = null;
    }
}
