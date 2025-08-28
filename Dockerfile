# Dockerfile with dependency caching
FROM python:3.13-slim

# Install uv for faster installs
RUN pip install --no-cache-dir uv==0.4.20

# Copy only dependency files first (cache layer)
WORKDIR /app
COPY pyproject.toml .

# Install dependencies (this layer is cached if pyproject.toml doesn't change)
RUN uv pip install --system -e .

# Copy application code (changes frequently)
COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]