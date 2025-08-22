#!/bin/bash

# Script to run the TokenForge UI Dashboard

# Change to the ui-dashboard directory
cd "$(dirname "$0")/../ui/ui-dashboard" || exit

# Check if node_modules exists, if not, run npm install
if [ ! -d "node_modules" ]; then
  echo "Installing dependencies..."
  npm install
fi

# Start the development server
echo "Starting UI Dashboard..."
npm run dev
