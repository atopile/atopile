export const HUB_READY_MARKER = "ATOPILE_HUB_READY";
export const CORE_SERVER_READY_MARKER = "ATOPILE_SERVER_READY";
export const HUB_PORT_ENV = "ATOPILE_HUB_PORT";
export const CORE_SERVER_PORT_ENV = "ATOPILE_CORE_SERVER_PORT";

export function hubWsUrl(port: number): string {
  return `ws://localhost:${port}/atopile-ui`;
}

export function findFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const net = require("net");
    const srv = net.createServer();
    srv.listen(0, "localhost", () => {
      const port = srv.address().port;
      srv.close(() => resolve(port));
    });
    srv.on("error", reject);
  });
}
