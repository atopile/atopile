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

3. Sanity check: `git status`

4. Commit your changes: `git commit -m "Add the RP2040 module"`

5. Push your changes up to Github: `git push`

    !!! tip "Pull Request"
        If you're on a branch other than `main`, the response from Github gives you a link to the pull request.

        Cmd+Click on Mac, Ctrl+Click on Windows to open the link in your browser.
