#!/usr/bin/env bash
set -e

echo "Updating pip..."
python -m pip install --upgrade pip

echo "Installing Python packages..."
pip install \
    huggingface_hub[cli] \
    tree \
    requests \
    pyyaml \
    rich \
    typer \
    python-dotenv

echo "Setup complete."