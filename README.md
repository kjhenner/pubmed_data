## Basic Docker Setup

Install and launch [Docker for Mac](https://www.docker.com/docker-mac)

From this directory, build the docker image defined by this repository's
Dockerfile:

    docker build -t pubmed_env .

Run the following command to begin an interactive session on the container.
This will mount the repository directory as `/app` on the container.

    docker run -it \
      --rm -v `pwd`:/app \
      -w /app \
      pubmed_env bash

Run python:

    python
