# Version control using git

git is a powerful way to version control your design and one of the key reason we started atopile. If you don't know about git, we strongly recommend learning it. There is a high chance you will end up loving it.

## Get stuff from the server / sync
git fetch origin <some-branch>
git pull

## Make a new branch

`git checkout -b <branch-name>`

`git checkout -b <branch-name> <from-branch>`

eg. `git checkout -b mawildoer/new-feature origin/main`

## Save some work

**1.**

`git add <whatever-you-wanna-save>`

`git add .`  -- save everything I've changed (including perhaps things we forgot to `.gitignore`)

**2.**

`git commit`

`git commit -m "<message-here>"`

## Push it back for everyone else

`git push` works if you didn't spec a "from" branch in `git checkout -b ...`

`git push -u origin HEAD` always works

Will respond with a way to make a branch:

```
remote:
remote: To create a merge request for mawildoer/dummy-branch, visit:
remote:   https://gitlab.atopile.io/atopile/servo-drive/-/merge_requests/new?merge_request%5Bsource_branch%5D=mawildoer%2Fdummy-branch
remote:
To gitlab.atopile.io:atopile/servo-drive.git
```

Cmd+<click> on the link to gitlab