# Generation of build outputs

Continuous integration / continuous distribution (CI/CD) is a powerful process to automatically export and deploy your project to production.

## Continuous integration / continuous distribution

Our CI pipeline will automatically generate the following outputs for you:

- Gerbers (with githash automatically stamped on it!)
- BOM
- Pick and place file

Our [template project](https://github.com/atopile/project-template) has an example of a GitHub actions workflow.

## GitHub actions artifacts
To download the artifacts, go to the github action page, find the pipeline with the commit you are interested in and download the build artifacts from it.