# Dockerfile following platform best practices
# References:
# - https://github.com/navapbc/platform-cli/blob/main/Dockerfile
# - https://docs.astral.sh/uv/guides/integration/docker/

FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS base

# install runtime dependencies
RUN apt-get update -qq \
    && apt-get install --no-install-recommends --yes \
        build-essential \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_SYSTEM_PYTHON=true

WORKDIR /app

RUN touch README.md
COPY pyproject.toml uv.lock* /app/

# Development stage with dev dependencies
FROM base AS dev

# Install project dependencies including dev dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --all-extras

# Copy application code
COPY src/ /app/src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --all-extras

# Add project's virtual env to the PATH so we can directly run scripts defined in pyproject.toml
ENV PATH="/app/.venv/bin:$PATH"

CMD ["documentai_api"]

# Production stage without dev dependencies
FROM base AS release

# Install project dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy application code
COPY src/ /app/src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Add project's virtual env to the PATH so we can directly run scripts defined in pyproject.toml
ENV PATH="/app/.venv/bin:$PATH"

# Lambda runtime contract: every function uses this image and overrides ImageConfig.Command
# to select its handler (e.g. "documentai_api.app.handler" for the API,
# "documentai_api.jobs.document_processor.handler.handler" for the job).
ENTRYPOINT ["python", "-m", "awslambdaric"]
CMD ["documentai_api.app.handler"]
