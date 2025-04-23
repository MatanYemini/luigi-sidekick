FROM ubuntu:22.04

# Avoid interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Use bash for all RUN commands and enable pipefail for safer builds
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# ------------------------------------------------------------
# Install core system packages and languages (rarely changes)
# ------------------------------------------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
        ca-certificates \
        python3 \
        python3-pip \
        python3-venv \
        sudo \
        expect && \
    # Clean up to reduce image size
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------
# Install Node.js (v22 LTS) via NodeSource (rarely changes)
# ------------------------------------------------------------
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get update && \
    apt-get install -y nodejs && \
    npm config set prefix /usr/local && \
    # Clean up to reduce image size
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------
# Install Python dependencies (changes occasionally)
# ------------------------------------------------------------
RUN pip install --no-cache-dir fastapi uvicorn[standard] httpx

# ------------------------------------------------------------
# Create non-root user for running Claude Code (rarely changes)
# ------------------------------------------------------------
RUN useradd -m -s /bin/bash -G sudo claudeuser && \
    echo "claudeuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    mkdir -p /workspace && \
    chown -R claudeuser:claudeuser /workspace

# ------------------------------------------------------------
# Global npm packages (change more frequently)
# ------------------------------------------------------------
# OpenAI Codex CLI
RUN npm install -g @openai/codex

# Anthropic Claude Code CLI + MCPs
RUN npm install -g @anthropic-ai/claude-code
RUN claude mcp add context7 -- npx -y @upstash/context7-mcp@latest

# ------------------------------------------------------------
# Configure Claude Code permissions (changes infrequently)
# ------------------------------------------------------------
# Create proper Claude config directory structure
RUN mkdir -p /home/claudeuser/.claude && \
    chown -R claudeuser:claudeuser /home/claudeuser/.claude && \
    chmod 755 /home/claudeuser/.claude

# Copy the config file
COPY claude.json /home/claudeuser/.claude/claude.json
RUN chown claudeuser:claudeuser /home/claudeuser/.claude/claude.json && \
    chmod 644 /home/claudeuser/.claude/claude.json

# ------------------------------------------------------------
# Define default working directory
# ------------------------------------------------------------
WORKDIR /workspace

# Switch to non-root user
USER claudeuser

CMD ["/bin/bash"] 