#!/bin/bash

echo "🚀 Setting up World_Sim Financial Dashboard..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    echo "   Visit: https://nodejs.org/"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

echo "✅ Node.js and npm are installed"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo ""
echo "🎉 Setup complete! To start the dashboard:"
echo ""
echo "1. Start the backend API (from World_Sim root):"
echo "   uvicorn Reporting.api:app --reload --port 8000"
echo ""
echo "2. Start the frontend (from this directory):"
echo "   npm run dev"
echo ""
echo "3. Access the dashboard at: http://localhost:5173"
echo ""
echo "📚 For more information, see README.md"
