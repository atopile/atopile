import { render, panelId, logoUrl } from "../shared/render";
import { Badge } from "../shared/components";

function App() {
  return (
    <div className="panel">
      {logoUrl ? <img src={logoUrl} alt="atopile" className="logo" /> : null}
      <h2>
        atopile <Badge variant="secondary">{panelId}</Badge>
      </h2>
      <p>Manufacturing workflows are not wired in the rewrite yet.</p>
    </div>
  );
}

render(App);
