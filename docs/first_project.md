# Creating an ato project

## With `ato create` <small>recommended</small>

To create a project, you can run the command

```
ato create
```

This command will start by asking for a name to your project. It will then clone the [project template](https://github.com/atopile/project-template) on github. Once created on github, paste the url of your repository into the command line. Your project should be up and running!

## Manually

You can create your own project instead of using ato create. Make sure to follow this project structure:

```
atopile-workspace
├── .venv --> your virtual environment
├── atopile --> this repo
├── atopile.code-workspace --> vscode workspace file
└── bike-light --> project using atopile
```