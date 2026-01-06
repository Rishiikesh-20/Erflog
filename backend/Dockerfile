# Use Ubuntu-based Python image (better Playwright compatibility)
FROM python:3.11-slim-bookworm

# 1. Install System Dependencies
# Added 'libreoffice' for DOCX support if needed (replaces docx2pdf)
# Added 'procps' which is often needed for browser automation to find processes
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    curl \
    procps \
    # LaTeX for resume generation (Heavy but necessary)
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-latex-extra \
    # WeasyPrint dependencies
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    # LibreOffice for DOCX -> PDF conversion (Linux alternative to docx2pdf)
    libreoffice-writer \
    libreoffice-java-common \
    default-jre \
    # General build tools
    build-essential \
    # Playwright/Chromium dependencies (manual install for Debian)
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    fonts-liberation \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# 2. Set the working directory
WORKDIR /app

# 3. Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Download spaCy English model
RUN python -m spacy download en_core_web_sm

# 5. Install Playwright Browsers
# Dependencies already installed in step 1, just install the browser
RUN playwright install chromium

# 6. Copy the rest of the application code
COPY . .

# 7. Environment variables
# PYTHONUNBUFFERED ensures logs show up in Cloud Logging immediately
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/credential.json

# 8. Expose the port
EXPOSE 8080

# 9. Health check
# This ensures Cloud Run knows if your app is actually ready
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# 10. Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]