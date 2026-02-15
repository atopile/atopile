import { Editor } from "./editor";

const canvas = document.getElementById("editor-canvas") as HTMLCanvasElement;
if (!canvas) {
    throw new Error("Canvas element #editor-canvas not found");
}

const baseUrl = window.location.origin;
const editor = new Editor(canvas, baseUrl);
editor.init().catch((err) => {
    console.error("Failed to initialize editor:", err);
});
