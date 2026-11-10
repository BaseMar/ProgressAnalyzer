FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install -r requirements.txt \
    && useradd --create-home --uid 10001 appuser

COPY --chown=appuser:appuser data_loader.py data_manager.py mapper.py streamlit_app.py ./
COPY --chown=appuser:appuser db/ db/
COPY --chown=appuser:appuser metrics/ metrics/
COPY --chown=appuser:appuser models/ models/
COPY --chown=appuser:appuser services/ services/
COPY --chown=appuser:appuser ui/ ui/
COPY --chown=appuser:appuser .streamlit/config.toml .streamlit/config.toml

USER appuser
EXPOSE 8501

HEALTHCHECK --interval=5s --timeout=5s --start-period=30s --retries=12 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4).read()"]

ENTRYPOINT ["python", "-m", "db.container_start"]
CMD ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false"]
