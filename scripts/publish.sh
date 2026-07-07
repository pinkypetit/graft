#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

echo "=== GRAFT PUBLIC PUBLISHING PIPELINE ==="

# 1. Initialize local Git
echo "1. Initializing Git repository locally..."
git init

# 2. Stage files
echo "2. Staging codebase files..."
git add .

# 3. Initial commit
echo "3. Creating initial Git commit..."
git commit -m "Initial commit: GRAFT (Generative Resource for Academic and Fluency Techniques)"

# 4. Rename default branch to main
echo "4. Setting main branch..."
git branch -M main

# 5. Create remote repo on GitHub and push
echo "5. Creating public GitHub repository pinkypetit/graft..."
gh repo create pinkypetit/graft --public --source=. --push --description "GRAFT: Generative Resource for Academic and Fluency Techniques - A local AI-powered technical Anki deck builder"

# 6. Enable GitHub Pages pointing to /docs
echo "6. Configuring GitHub Pages to serve from the /docs directory..."
# Add a small delay for GitHub API to process repo creation
sleep 3
gh api \
  --method POST \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  /repos/pinkypetit/graft/pages \
  -f "source[branch]=main" -f "source[path]=/docs"

echo "=== GRAFT DEPLOYMENT SUCCESSFUL ==="
echo "Repository: https://github.com/pinkypetit/graft"
echo "GitHub Pages: https://pinkypetit.github.io/graft/"
