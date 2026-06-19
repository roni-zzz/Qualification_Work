# MicroPython syntax validation environment
FROM python:3.11-slim

WORKDIR /app

# Install MicroPython stub packages for syntax checking
RUN pip install --no-cache-dir micropython-esp32-stubs

# Copy source files
COPY src ./src
COPY boot.py .

# Validate syntax
CMD ["sh", "-c", "python -m py_compile src/*.py boot.py"]
