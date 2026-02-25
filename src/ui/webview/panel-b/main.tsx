import { render, AppProps } from "../shared/render";

function App({ panelId, logoUrl }: AppProps) {
  return (
    <div className="panel">
      {logoUrl && <img src={logoUrl} alt="atopile" className="logo" />}
      <h2>atopile &mdash; {panelId}</h2>
    </div>
  );
}

render(App);
