# Dockerfiles

These describe how to build the docker images used by the project.

## Building

To build the docker images, run the following command from the **root** of the project:

`docker build -f dockerfiles/Dockerfile.ci -t atopile/user:latest .`

Again, you need to run this from the project root, not this directory.
