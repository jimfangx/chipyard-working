### This is a full chipyard setup

# BUILD BASE FOR CI

FROM ubuntu:24.04 AS base
ARG CHIPYARD_REPO=https://github.com/ucb-bar/chipyard.git
ARG CHIPYARD_REF=main

MAINTAINER https://groups.google.com/forum/#!forum/chipyard

SHELL ["/bin/bash", "-leo", "pipefail", "-c"]

ENV CONDA_INSTALL_DIR=/opt/conda
ENV FORCE_NON_EC2=1
ENV JVM_OPTS=-Xmx3200m
ENV PATH="${CONDA_INSTALL_DIR}/bin:${PATH}"

# Install host dependencies needed to clone Chipyard and bootstrap conda.
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    bc \
    bzip2 \
    ca-certificates \
    curl \
    findutils \
    git \
    gzip \
    kmod \
    make \
    patch \
    procps \
    python3 \
    sudo \
    tar \
    unzip \
    xz-utils \
    wget && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /root

# Clone Chipyard. CHIPYARD_REF can be a branch, tag, commit SHA, PR number, or refs/pull/... ref.
RUN git clone "${CHIPYARD_REPO}" chipyard && \
    cd chipyard && \
    if [[ "${CHIPYARD_REF}" =~ ^[0-9]+$ ]]; then \
        git fetch origin "pull/${CHIPYARD_REF}/merge" && \
        git checkout --detach FETCH_HEAD; \
    elif [[ "${CHIPYARD_REF}" =~ ^refs/pull/[0-9]+/(head|merge)$ ]]; then \
        git fetch origin "${CHIPYARD_REF}" && \
        git checkout --detach FETCH_HEAD; \
    else \
        git checkout "${CHIPYARD_REF}"; \
    fi && \
    git rev-parse --short HEAD

# Install Miniforge using the same bootstrap scheme as CI.
RUN wget -O Miniforge3.sh "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh" && \
    bash Miniforge3.sh -b -p "${CONDA_INSTALL_DIR}" && \
    rm Miniforge3.sh && \
    source "${CONDA_INSTALL_DIR}/etc/profile.d/conda.sh" && \
    if [ -f "${CONDA_INSTALL_DIR}/etc/profile.d/mamba.sh" ]; then \
        source "${CONDA_INSTALL_DIR}/etc/profile.d/mamba.sh"; \
    fi && \
    conda activate

# BUILD IMAGE WITH TOOLCHAINS

# Use above build as base
FROM base AS base-with-tools

# Fully initialize Chipyard.
RUN cd chipyard && \
    git config --global --add safe.directory "*" && \
    source "${CONDA_INSTALL_DIR}/etc/profile.d/conda.sh" && \
    if [ -f "${CONDA_INSTALL_DIR}/etc/profile.d/mamba.sh" ]; then \
        source "${CONDA_INSTALL_DIR}/etc/profile.d/mamba.sh"; \
    fi && \
    conda activate && \
    ./build-setup.sh riscv-tools && \
    grep -F "Setup complete!" build-setup.log

# Run script to set environment variables on entry
ENTRYPOINT ["chipyard/scripts/entrypoint.sh"]

# END IMAGE CUSTOMIZATIONS

CMD ["/bin/sh"]
