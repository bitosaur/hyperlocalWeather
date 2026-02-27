#!/usr/bin/env bash
# Local development setup (not needed for Docker).
# Run once: bash setup.sh
set -e

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Copy secrets template if secrets.env doesn't exist yet
if [ ! -f secrets.env ]; then
  cp secrets.env.example secrets.env
  echo "Created secrets.env — fill in your WU_API_KEY before running."
fi

echo ""
echo "Setup complete. To run locally:"
echo "  source venv/bin/activate"
echo "  export \$(cat secrets.env | grep -v '^#' | xargs)"
echo "  export REFRESH_INTERVAL=600"
echo "  cd app && python app.py"
