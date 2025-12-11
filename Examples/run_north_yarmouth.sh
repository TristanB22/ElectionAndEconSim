#!/bin/bash
# Quick runner script for North Yarmouth simulation
# Uses local environment and NAS database

set -e  # Exit on error

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Starting North Yarmouth Simulation"
echo "Project root: $PROJECT_ROOT"
echo ""

# Check if virtual environment exists
if [ -d "$PROJECT_ROOT/../world_sim_env" ]; then
    echo "Found virtual environment"
    source "$PROJECT_ROOT/../world_sim_env/bin/activate"
elif [ -d "$PROJECT_ROOT/world_sim_env" ]; then
    echo "Found virtual environment"
    source "$PROJECT_ROOT/world_sim_env/bin/activate"
else
    echo "Warning: Virtual environment not found. Continuing anyway..."
fi

# Check .env file exists
ENV_FILE="$PROJECT_ROOT/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found at $ENV_FILE"
    exit 1
fi

echo "Found .env file"
echo ""

# Check DATABASE_TARGET
if grep -q "DATABASE_TARGET=nas" "$ENV_FILE"; then
    echo "DATABASE_TARGET=nas (using NAS database)"
else
    echo "Warning: DATABASE_TARGET not set to 'nas'"
fi

# Check QDRANT_TARGET
if grep -q "QDRANT_TARGET=docker" "$ENV_FILE"; then
    echo "QDRANT_TARGET=docker (using local Qdrant)"
elif grep -q "QDRANT_TARGET=nas" "$ENV_FILE"; then
    echo "QDRANT_TARGET=nas (using NAS Qdrant)"
fi

echo ""
echo "Running simulation..."
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Run the script with provided arguments or defaults
python World_Sim/Examples/north_yarmouth_week_sim.py "$@"

