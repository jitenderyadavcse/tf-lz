# Use locally available Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install uv package manager
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY main.py ./

# Install dependencies using uv
RUN uv sync --frozen

# Expose the port that MCP typically uses (optional, depends on transport)
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MCP_LOG_LEVEL=info

# Command to run the MCP server
CMD ["uv", "run", "python", "main.py"]
