# 360foto - CUDA対応版

## 概要
全天球動画を複数方向の静止画に変換するツールです。NVIDIA CUDA GPUアクセラレーションに対応しています。

## 必要環境
- NVIDIA GPU（CUDA対応）
- Docker
- NVIDIA Container Toolkit
- Windows/Linux

## セットアップ

### 1. NVIDIA Container Toolkitのインストール

#### Ubuntu/Debian:
```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

#### Windows (WSL2):
WSL2でNVIDIA Container Toolkitをインストールしてください。

### 2. Dockerイメージのビルド

```bash
docker-compose build
```

### 3. コンテナの起動

```bash
# X11フォワーディングを有効にする（Linux）
xhost +local:docker

# コンテナを起動
docker-compose up
```

## GPU対応の確認

コンテナ内でGPUが認識されているか確認：

```bash
docker-compose run 360foto nvidia-smi
```

## 使用方法

1. GUIが起動したら、入力動画ファイルを選択
2. 出力フォルダを指定
3. 画像書出し間隔、フォーマット、出力方向を選択
4. 「ビデオ処理開始」ボタンをクリック

## GPU アクセラレーション

このバージョンでは以下のGPUアクセラレーションが有効になっています：
- CUDA ハードウェアアクセラレーション（デコード）
- NVIDIA GPU フィルタリング
- 高速ビデオ処理

## トラブルシューティング

### GPUが認識されない場合
```bash
# NVIDIA ドライバーの確認
nvidia-smi

# Docker のGPUサポート確認
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### X11エラーが出る場合（Linux）
```bash
xhost +local:docker
export DISPLAY=:0
```

## ファイル構成
- `360foto.py` - メインプログラム（GPU対応版）
- `Dockerfile` - CUDA対応Dockerイメージ
- `docker-compose.yml` - GPU設定を含むDocker Compose設定
- `requirements.txt` - Python依存関係

## 注意事項
- 初回ビルドには時間がかかります（ffmpegのコンパイルが必要）
- GPUメモリが不足する場合は、同時処理数を調整してください
