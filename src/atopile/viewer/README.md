![](https://github.com/xyflow/web/blob/main/assets/codesandbox-header-ts.png?raw=true)

# React Flow starter (Vite + TS)

We've put together this template to serve as a starting point for folks
interested in React Flow. You can use this both as a base for your own React
Flow applications, or for small experiments or bug reports.

**TypeScript not your thing?** We also have a vanilla JavaScript starter template,
just for you!

## Getting up and running

You can get this template without forking/cloning the repo using `degit`:

```bash
npx degit xyflow/vite-react-flow-template your-app-name
```

The template contains mostly the minimum dependencies to get up and running, but
also includes eslint and some additional rules to help you write React code that
is less likely to run into issues:

```bash
npm install # or `pnpm install` or `yarn install`
```

Vite is a great development server and build tool that we recommend our users to
use. You can start a development server with:

```bash
npm run dev
```

While the development server is running, changes you make to the code will be
automatically reflected in the browser!

## Things to try:

- Create a new custom node inside `src/nodes/` (don't forget to export it from `src/nodes/index.ts`).
- Change how things look by [overriding some of the built-in classes](https://reactflow.dev/learn/customization/theming#overriding-built-in-classes).
- Add a layouting library to [position your nodes automatically](https://reactflow.dev/learn/layouting/layouting)

## Resources

Links:

- [React Flow - Docs](https://reactflow.dev)
- [React Flow - Discord](https://discord.com/invite/Bqt6xrs)

Learn:

- [React Flow – Custom Nodes](https://reactflow.dev/learn/customization/custom-nodes)
- [React Flow – Layouting](https://reactflow.dev/learn/layouting/layouting)
