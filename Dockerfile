FROM python:latest

ARG SETUPTOOLS_SCM_PRETEND_VERSION

RUN mkdir -p /atopile/src/atopile

COPY README.md pyproject.toml /atopile/
COPY src/atopile /atopile/src/atopile

RUN pip install -e /atopile"[dev,test,docs]"
