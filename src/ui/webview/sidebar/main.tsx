import { render, AppProps } from "../shared/render";
import { Button } from "../shared/components";

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
        <Button onClick={() => openPanel("panel-developer")}>Developer</Button>
        <Button onClick={() => openPanel("panel-b")}>Open Panel B</Button>
      </div>
    </div>
  );
}

render(App);
