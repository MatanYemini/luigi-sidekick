#!/bin/bash
set -e

# Get the query from command-line argument
QUERY="$1"
REPO_PATH="$2"

# Create config directories
mkdir -p ~/.claude

# Set up an expect script to automatically handle the interactive prompts
cat > /tmp/claude_expect.exp << 'EOF'
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

chmod +x /tmp/claude_expect.exp

# Make sure expect is installed
if ! command -v expect &> /dev/null; then
    echo "Error: 'expect' is not installed." >&2
    echo "Please install it with: sudo apt-get install expect" >&2
    exit 1
fi

# Run the expect script with the query
cd "$REPO_PATH" && /tmp/claude_expect.exp "$QUERY" 