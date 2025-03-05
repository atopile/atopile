# 6. Saving Your Work

atopile strongly recommends using `git` for version control.

If you're not yet familiar with `git`, check out our short [`git` guide](../guides/git.md) for a general overview on the workflow.

## Committing

1. Survey what you've done: `git status`
2. Add the files you want to associate with this commit `git add <file>`

    !!! tip "Adding files"
        You can add multiple files at once by running `git add <file1> <file2> <file3>`

        You can also add all files in a directory by running `git add <directory>`

        This includes the current directory, if you use `git add .` - but careful! This is often a trap and you end up adding a lot of unrelated files. At the start of a project it often makes sense though.

3. Sanity check: `git status`. It'll tell you all the files you've got staged (ready to commit)

4. Commit your changes: `git commit -m "Add the RP2040 module"`. Commit messages should describe the changes you've made and why.

5. Push your changes up to Github: `git push`

    !!! tip "Pull Request"
        If you're on a branch other than `main`, the response from Github gives you a link to the pull request.

        Cmd+Click on Mac, Ctrl+Click on Windows to open the link in your browser.

## Up on Github

There are a few paths to contribute back to a repository.

If you have permissions to push directly to the repo, by far the easiest way to update it is to contribute directly.

As your project progresses and stabalises, you typically want to create a new branch and pull-request (PR) for each change you're making, even if you're working alone.


### Directly to `main`

If you're right at the start of your project, you might want to push straight to `main`. This is fast and dirty. All you need to do is:

1. Commit your changes: `git commit -m "Add the RP2040 module"`
2. Push your changes up to Github: `git push`

They'll be up on `main`


### Create a Branch and Pull Request

For a more controlled development process, especially as your project grows, it's best practice to work on feature branches and create pull requests. Here are some recommendations:

- Use descriptive branch names, like `feature/add-bluetooth-support` or `bugfix/fix-routing-error`.
- Keep your commits focused and well-documented. Write clear commit messages that explain the "why" behind a change, not just the "what".
- When you open a pull request, include a detailed description of the change, the rationale behind it, and steps for testing.
- If your repository is configured with [`Continuous Integration`](#continuous-integration), ensure that all tests pass before merging your PR.
- Request code reviews from your team. Peer reviews help catch potential issues early and improve code quality.

### Continuous Integration (CI)

atopile's project template include basic CI workflows to validate your design, build manufacturing data you can order with and run testing.

It builds in CI as a `frozen` project, meaning it'll try its hardest to rebuild your design exactly as it stands, with the exact same parts and layout. When it can't - whether because your source code has changes and the components no longer satisfy the design, or because the layout is out of date - it'll fail the build.

Additionally, CI is run to build all targets, which means it will also produce the gerber files to order your PCBs.

!!! tip "Git and CI Best Practice"
    Consistent use of pull requests and CI pipelines not only improves code quality but also fosters better team collaboration. Keep your `main` branch in a deployable state by merging only after successful CI runs.
