# AgentCore Runtime requires linux/arm64. This dev machine is Apple Silicon,
# so this builds natively -- no QEMU cross-build penalty.
FROM --platform=linux/arm64 python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["python", "-m", "guardrail.app"]
