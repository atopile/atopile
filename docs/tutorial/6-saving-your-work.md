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


### Create a branch and PR

As described in the typical workflow, you create a branch and PR for each change you're making.

Once you've pushed your changes to Github, create a PR with the link
