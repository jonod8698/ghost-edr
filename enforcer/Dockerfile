# Multi-stage build for minimal attack surface
FROM python:3.12-alpine AS builder

WORKDIR /build
COPY pyproject.toml .
COPY src/ src/

# Install build dependencies and create wheel
RUN pip install --no-cache-dir build && \
    python -m build --wheel

# --- Production stage ---
FROM python:3.12-alpine

# Security: Create non-root user
RUN addgroup -g 1000 ghost && \
    adduser -u 1000 -G ghost -s /sbin/nologin -D ghost

WORKDIR /app

# Install only runtime dependencies
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && \
    rm -rf /tmp/*.whl /root/.cache

# Security hardening
USER ghost

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8766/health || exit 1

EXPOSE 8766

ENTRYPOINT ["ghost-enforcer"]
CMD ["run", "--port", "8766"]
