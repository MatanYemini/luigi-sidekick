import os

# Base directory and repository location configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
REPOS_DIR = os.path.join(BASE_DIR, "..", "repos")

# Ensure the repos directory exists with proper permissions
os.makedirs(REPOS_DIR, exist_ok=True)
# Make sure the directory is writable by the current user
os.chmod(REPOS_DIR, 0o755) 