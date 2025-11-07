#!/bin/bash

# GPU対応確認スクリプト

echo "===== NVIDIA GPU確認 ====="
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi
else
    echo "nvidia-smiが見つかりません。NVIDIAドライバーがインストールされているか確認してください。"
    exit 1
fi

echo ""
echo "===== CUDA確認 ====="
if command -v nvcc &> /dev/null; then
    nvcc --version
else
    echo "CUDAがインストールされていません（オプション）"
fi

echo ""
echo "===== Docker GPU サポート確認 ====="
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ GPU対応の準備が完了しています！"
    echo ""
    echo "次のコマンドでアプリケーションをビルド・起動できます："
    echo "  docker-compose build"
    echo "  docker-compose up"
else
    echo ""
    echo "✗ Docker GPUサポートに問題があります。"
    echo "NVIDIA Container Toolkitをインストールしてください。"
fi
