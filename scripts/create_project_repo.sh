#!/bin/bash

# Get the absolute path of the script's directory
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

# Load environment variables from project root
if [ -f "$PROJECT_ROOT/.env" ]; then
  echo "🌍 Loading environment variables from project root .env..."
  export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
else
  echo "❌ Error: .env file not found in the project root."
  exit 1
fi

# Use PROJECT_ROOT from .env or fallback to calculated root
PROJECT_ROOT=${PROJECT_ROOT:-$(pwd)}
echo "📂 PROJECT_ROOT: $PROJECT_ROOT"

# Get the project name from the root directory
PROJECT_NAME=$(basename "$PROJECT_ROOT")
echo "🏷️ Project Name: $PROJECT_NAME"
PROJECT_NAME="repomix-copy"

# Create GitHub repository (default to private)
echo "🐙 Creating GitHub repository (private)..."
gh repo create "$PROJECT_NAME" --private --confirm

# Initialize git repository if not already initialized
if [ ! -d ".git" ]; then
  echo "🔄 Initializing Git repository..."
  git init
else
  echo "📂 Git repository already initialized."
fi

# Ensure branch is set to main
git branch -M main

# Add all files and commit if changes exist
if [ -n "$(git status --porcelain)" ]; then
  echo "📦 Adding and committing files..."
  git add .  # Add all files
  git commit -m "🎉 Initial commit"
else
  echo "⚠️  No changes to commit."
fi

# Handle existing remote
if git remote | grep -q origin; then
  echo "🔄 Remote 'origin' already exists. Updating it..."
  git remote remove origin
fi
git remote add origin "https://github.com/$(gh api user --jq '.login')/$PROJECT_NAME.git"

# Push to the remote repository
echo "🚀 Pushing code to remote repository..."
git push -u origin main || {
  echo "❌ Failed to push to remote. Check for errors."
  exit 1
}

echo "✅ Repository created and code pushed successfully!"
