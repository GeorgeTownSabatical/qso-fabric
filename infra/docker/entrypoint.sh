#!/bin/bash
set -euo pipefail

echo "Starting Solis Node..."
python -m solis.services.solis_star_service
