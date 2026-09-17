#!/usr/bin/env bash
set -e

LLAMA_DIR=~/workspace/llama.cpp
MODEL_DIR=~/workspace/models/llm

export LD_LIBRARY_PATH=$LLAMA_DIR/build/bin:$LD_LIBRARY_PATH

$LLAMA_DIR/build/bin/llama-server \
    -m $MODEL_DIR/Qwen3-4B-Hivemind-Inst-Hrtic-Ablit-Uncensored-Q5_K_M-imat.gguf \
    -ngl 999 \
    -c 4096 \
    --host 0.0.0.0 \
    --port 8080