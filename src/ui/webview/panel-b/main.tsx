import { render, AppProps } from "../shared/render";
import { Badge } from "../shared/components";

function App({ panelId, logoUrl }: AppProps) {
  return (
    <div className="panel">
      {logoUrl && <img src={logoUrl} alt="atopile" className="logo" />}
      <h2>
        atopile &mdash; <Badge variant="secondary">{panelId}</Badge>
      </h2>
    </div>
  );
}

render(App);
