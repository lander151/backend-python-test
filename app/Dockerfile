FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim

WORKDIR /code

# Copiar e instalar dependencias en una sola capa
COPY pyproject.toml uv.lock ./
RUN uv sync --locked 
COPY . .

EXPOSE 5000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]