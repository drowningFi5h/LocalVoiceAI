#!/usr/bin/env bash
set -e

mkdir -p ../models/llm

hf download \
DavidAU/Qwen3-4B-Hivemind-Instruct-Heretic-Abliterated-Uncensored-NEO-Imatrix-GGUF \
--include "*Q5_K_M.gguf" \
--local-dir ../models/llm