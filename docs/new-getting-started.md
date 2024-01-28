# Getting started

`atopile` brings the best of software development to the world of hardware design.

We're starting with an electronics compiler and a new language called `ato`. Files with the `.ato` extension can be used to describe your circuit, and compiles it to netlists that can be laid out and fabricated.

The `.ato` files are human readable and can be version controlled, so you can collaborate with your team on the design of your hardware. They're modular, so you can reuse components from other projects, and share them with the community. They provide a way to save the intelligence of your design and the validation required to make sure it works as intended, so you can be confident that your design will work as expected.

## Installation

To run atopile, you will need the atopile compiler, the VSCode extension for synthax highlighting and git credential manager.

### atopile compiler - with pip <small>recommended</small>

atopile is published as a [python package](https://pypi.org/project/atopile/) on pypi. You can install it using `pip` from your command line. We recommend setting up a virtual environment for atopile so that atopile's dependencies don't calsh with the rest of your system.

Start by making sure you have `python@3.11` or later installed on your machine.

??? question "How to install python 3.11 or later"

    To install python 3.11 or later, you can use [brew](https://brew.sh)

    `brew install python@3.11`

    once you create your venv, make sure to run:

    `python3.11 -m venv venv`

Setup the venv:
``` sh
python3.11 -m venv venv
```
Activate the venv:
``` sh
source venv/bin/activate
```

Now you can install atopile:
``` sh
pip install atopile
```

atopile should be installed. You can verify that it worked with the following command which should give you the current version of atopile.
``` sh
ato --version
```
---

:fontawesome-brands-youtube:{ style="color: #EE0F0F" }
__[Getting started with atopile - get setup and build your first project from scratch]__ – :octicons-clock-24:
32m – We have a video of how to install atopile and setup your project here.

  [How to set up atopile]: https://www.youtube.com/watch?v=7aeZLlA_VYA

---

### atopile compiler - with git

atopile can be directly installed from [GitHub](https://github.com/atopile/atopile) by cloning the repository into a subfolder of your project root. This could be useful if you want to use the latest version of atopile:

```
git clone https://github.com/atopile/atopile.git
```
This will create a repository with the latest version of atopile. You can install it using pip:

```
pip install -e atopile
```

### VSCode extension - extension store

We recomend using [VSCode](https://code.visualstudio.com) to run atopile as it will provide synthax highlighting.

From VSCode, navigate to the VSCode extensions and install atopile.

![](images/ato_extension.png)