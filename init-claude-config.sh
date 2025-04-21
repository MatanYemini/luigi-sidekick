#!/bin/bash
set -e

echo "Starting Claude configuration setup..."

# Create Claude config directory
CLAUDE_CONFIG_DIR="/home/claudeuser/.claude"
mkdir -p "$CLAUDE_CONFIG_DIR"

# Print current user for debugging
echo "Running as user: $(whoami)"
echo "Current directory: $(pwd)"

# Copy or create the Claude configuration file
if [ -f "/workspace/claude.json" ]; then
    # If claude.json exists in the workspace, copy it
    echo "Using Claude configuration from workspace..."
    cp "/workspace/claude.json" "$CLAUDE_CONFIG_DIR/claude.json"
else
    # Create a default configuration
    echo "Creating default Claude configuration..."
    cat > "$CLAUDE_CONFIG_DIR/claude.json" << 'EOF'
{
  "tools": {
    "Edit": {
      "description": "Edit files in the codebase",
      "allowed": true
    },
    "Bash": {
      "description": "Run shell commands",
      "allowed": true,
      "patterns": ["git:*", "npm:*", "ls:*", "cat:*", "find:*", "grep:*"]
    },
    "Search": {
      "description": "Search through the codebase",
      "allowed": true
    },
    "FileSearch": {
      "description": "Find files by name",
      "allowed": true
    },
    "ListDir": {
      "description": "List directory contents",
      "allowed": true
    },
    "Read": {
      "description": "Read file contents",
      "allowed": true
    },
    "Git": {
      "description": "Perform Git operations",
      "allowed": true,
      "patterns": [
        "git:status",
        "git:log",
        "git:diff",
        "git:add",
        "git:commit",
        "git:checkout",
        "git:branch",
        "git:push",
        "git:pull"
      ]
    }
  },
  "permissionsStrategy": "toolFirst",
  "skipPromptOnPatternMatch": true,
  "trustLevel": "medium"
}
EOF
fi

# Ensure proper permissions
echo "Setting permissions..."
chmod 755 "$CLAUDE_CONFIG_DIR"
chmod 644 "$CLAUDE_CONFIG_DIR/claude.json" || echo "Warning: Could not set permissions on config file"

echo "Claude configuration is ready at $CLAUDE_CONFIG_DIR/claude.json"
echo "Contents of Claude config directory:"
ls -la "$CLAUDE_CONFIG_DIR" 