import { render, AppProps } from "../shared/render";

const vscode = acquireVsCodeApi();

function openPanel(panelId: string) {
  vscode.postMessage({ type: "openPanel", panelId });
}

function App({ logoUrl }: AppProps) {
  return (
    <div className="panel">
      {logoUrl && <img src={logoUrl} alt="atopile" className="logo" />}
      <h2>atopile</h2>
      <div className="nav-list">
        <button onClick={() => openPanel("panel-developer")}>Developer</button>
        <button onClick={() => openPanel("panel-b")}>Open Panel B</button>
      </div>
    </div>
  );
}

render(App);
