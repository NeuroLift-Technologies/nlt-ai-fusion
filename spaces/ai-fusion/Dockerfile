# AI-Fusion runtime — Hugging Face Docker Space image.
#
# Build context is the ASSEMBLED Space payload produced by
# spaces/ai-fusion/sync-to-hub.sh (README.md, Dockerfile, requirements.txt,
# .env.example, app/ and a copy of src/), not the repository root: the Space gets
# the runtime, not the whole repository.

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    PORT=7860 \
    NLT_ARTIFACTS_DIR=/data \
    NEUROLIFT_MODELS_DIR=/data/models \
    FUSION_AGENT_LOOP_MODEL=baseline

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# src/ is the cognitive core (Avatar, Aide, Advocate, fusion, agent-loop seam).
# Nothing from apps/, backend/, archive/, supabase/ or tests/ ships in the image.
COPY src/ ./src/
COPY app/ ./app/

# Run unprivileged; /data is the Space's persistent bucket mount (checkpoints,
# eval artifacts) and is the only writable path the runtime needs.
RUN useradd --create-home --uid 1000 space \
    && mkdir -p /data/models \
    && chown -R space:space /app /data
USER space

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:7860/health', timeout=4).status == 200 else 1)"

# --factory: the app is built at startup, so a bad configuration fails the boot
# instead of serving a half-initialised process.
CMD ["uvicorn", "app.main:create_runtime_app", "--factory", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers", "--forwarded-allow-ips", "*"]
