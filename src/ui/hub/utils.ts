export function requirePort(name: string): number {
  const port = parseInt(process.env[name] ?? "", 10);
  if (!port) {
    console.error(`${name} environment variable is required`);
    process.exit(1);
  }
  return port;
}
