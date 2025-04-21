#!/bin/bash
set -e

echo "Starting Claude wrapper..."

# Get the query from command-line arguments
QUERY="$1"
REPO_PATH="$2"

# Print debug info
echo "Running as user: $(whoami)"
echo "Current directory: $(pwd)"
echo "Repository path: $REPO_PATH"
echo "CLAUDE_CONFIG_DIR: $CLAUDE_CONFIG_DIR"

# Support for file-based input queries
if [[ $QUERY == @* ]]; then
    QUERY_FILE="${QUERY:1}"
    if [ -f "$QUERY_FILE" ]; then
        echo "Reading query from file: $QUERY_FILE"
        QUERY=$(cat "$QUERY_FILE")
    else
        echo "Error: Query file not found: ${QUERY_FILE}" >&2
        exit 1
    fi
fi

# Use the environment variable if set, otherwise use default
CLAUDE_CONFIG_DIR=${CLAUDE_CONFIG_DIR:-"/home/claudeuser/.claude"}
echo "Using Claude config directory: $CLAUDE_CONFIG_DIR"

# Create config directories with proper permissions
mkdir -p "$CLAUDE_CONFIG_DIR"
chmod 755 "$CLAUDE_CONFIG_DIR" || echo "Warning: Could not set permissions on config directory"

# Copy the claude.json file to the config directory if it exists at source
if [ -f "/workspace/claude.json" ]; then
    echo "Copying config from /workspace/claude.json"
    cp "/workspace/claude.json" "$CLAUDE_CONFIG_DIR/claude.json"
    chmod 644 "$CLAUDE_CONFIG_DIR/claude.json" || echo "Warning: Could not set permissions on config file"
else
    echo "No config file found at /workspace/claude.json"
    # Check if we have a config file already
    if [ ! -f "$CLAUDE_CONFIG_DIR/claude.json" ]; then
        echo "Warning: No Claude config file found at $CLAUDE_CONFIG_DIR/claude.json"
    fi
fi

# List config directory contents
echo "Contents of Claude config directory:"
ls -la "$CLAUDE_CONFIG_DIR" || echo "Could not list directory"

# Set up an expect script to automatically handle the interactive prompts
EXPECT_SCRIPT="/tmp/claude_expect.exp"
echo "Creating expect script at $EXPECT_SCRIPT"

cat > "$EXPECT_SCRIPT" << 'EOF'
#!/usr/bin/expect -f
set query [lindex $argv 0]
set timeout 300

spawn claude $query
expect {
    "Do you want to allow Claude to" {
        send "y\r"
        exp_continue
    }
    "May Claude" {
        send "y\r"
        exp_continue
    }
    "Do you want to proceed" {
        send "y\r"
        exp_continue
    }
    "Continue?" {
        send "y\r"
        exp_continue
    }
    "Would you like Claude to" {
        send "y\r"
        exp_continue
    }
    # Add more patterns as needed
    eof
}
EOF

chmod +x "$EXPECT_SCRIPT"

# Make sure expect is installed
if ! command -v expect &> /dev/null; then
    echo "Error: 'expect' is not installed." >&2
    echo "Please install it with: sudo apt-get install expect" >&2
    exit 1
fi

# Set environment variable for Claude config
export CLAUDE_CONFIG_DIR
echo "Exported CLAUDE_CONFIG_DIR=$CLAUDE_CONFIG_DIR"

# Create a temporary debug file to store command output
DEBUG_FILE="/tmp/claude_output.log"

# Run the expect script with the query
echo "Running Claude in $REPO_PATH with query: ${QUERY:0:50}..."
cd "$REPO_PATH" && "$EXPECT_SCRIPT" "$QUERY" 2>&1 | tee "$DEBUG_FILE"

# Check if command succeeded
if [ $? -eq 0 ]; then
    echo "Claude command completed successfully"
else
    echo "Claude command failed. Debug log:"
    cat "$DEBUG_FILE"
fi 