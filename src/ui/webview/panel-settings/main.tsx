import { render } from "../shared/render";
import { WebviewRpcClient, rpcClient } from "../shared/rpcClient";
import {
  Field,
  FieldLabel,
  FieldDescription,
  Input,
  Button,
  Checkbox,
  Badge,
  Separator,
  Table,
  TableBody,
  TableRow,
  TableCell,
} from "../shared/components";

function App() {
  const coreStatus = WebviewRpcClient.useSubscribe("coreStatus");
  const settings = WebviewRpcClient.useSubscribe("extensionSettings");

  const updateSetting = (key: string, value: string | boolean) => {
    rpcClient?.sendAction("updateExtensionSetting", { key, value });
  };

  return (
    <div className="panel-centered">
      <h2>Settings</h2>

      <h3>Configuration</h3>

      <Field>
        <FieldLabel>Local Path</FieldLabel>
        <div style={{ display: "flex", gap: "var(--spacing-sm)" }}>
          <Input
            value={settings.devPath}
            placeholder="/path/to/atopile"
            onChange={(e) => updateSetting("devPath", e.target.value)}
            style={{ flex: 1 }}
          />
          <Button
            variant="outline"
            onClick={async () => {
              const path = await rpcClient?.requestAction<string | undefined>(
                "vscode.browseFolder",
              );
              if (path) {
                updateSetting("devPath", path);
              }
            }}
          >
            Browse
          </Button>
        </div>
        <FieldDescription>
          Path to a local atopile checkout. Leave empty for production mode.
        </FieldDescription>
      </Field>

      <Field>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-sm)" }}>
          <Checkbox
            id="autoInstall"
            checked={settings.autoInstall}
            onCheckedChange={(checked) => updateSetting("autoInstall", checked)}
          />
          <FieldLabel htmlFor="autoInstall" style={{ margin: 0 }}>
            Auto-install dependencies
          </FieldLabel>
        </div>
      </Field>

      <Separator />

      <h3>Status</h3>

      <Table>
        <TableBody>
          <TableRow>
            <TableCell>Version</TableCell>
            <TableCell>{coreStatus.version || "..."}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell>Mode</TableCell>
            <TableCell>
              <Badge variant={coreStatus.mode === "local" ? "warning" : "success"}>
                {coreStatus.mode === "local" ? "Local" : "Production"}
              </Badge>
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell>ato binary</TableCell>
            <TableCell><code>{coreStatus.atoBinary || "not resolved"}</code></TableCell>
          </TableRow>
          <TableRow>
            <TableCell>UV path</TableCell>
            <TableCell><code>{coreStatus.uvPath || "not resolved"}</code></TableCell>
          </TableRow>
        </TableBody>
      </Table>

      <Separator />

      <h3>Developer</h3>

      <Field>
        <FieldDescription>
          Open the developer panel for rewrite-specific diagnostics and tooling.
        </FieldDescription>
        <Button
          variant="outline"
          onClick={() => {
            void rpcClient?.requestAction("vscode.openPanel", {
              panelId: "panel-developer",
            });
          }}
        >
          Open Developer Panel
        </Button>
      </Field>
    </div>
  );
}

render(App);
