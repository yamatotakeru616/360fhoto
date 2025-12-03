# 360fhoto

簡潔な説明
----------------

`360fhoto` は 360° 写真 / リアリティキャプチャー向けの補助ツール群をまとめたリポジトリです。Python スクリプトや GUI、Docker 環境、GPU 向けの補助ドキュメントを含みます。

主なファイル
----------------
- `360foto.py` — コアスクリプト（用途に応じて実行）。
- `realityscan_gui.py` — GUI アプリケーション（未追跡だったファイルを追加）。
- `requirements.txt` — Python 依存パッケージリスト。
- `Dockerfile` / `docker-compose.yml` — コンテナ化用設定。
- `README_CUDA.md` — CUDA / GPU に関する補足と手順。

インストール（ローカル Python 環境）
----------------
1. Python 3.8 以上を用意します。
2. 仮想環境を作成して有効化します。

```pwsh
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -r requirements.txt
```

使い方（基本）
----------------
- スクリプトを直接実行する場合（例）:

```pwsh
python 360foto.py
```

- GUI を起動する場合（`realityscan_gui.py` を使用）:

```pwsh
python realityscan_gui.py
```

Docker を使う
----------------
プロジェクトには `Dockerfile` と `docker-compose.yml` が含まれます。Docker を使う場合は以下を参照してください。

```pwsh
docker build -t 360fhoto .
docker run --rm -it 360fhoto
```

GPU / CUDA
----------------
GPU を利用する場合は `README_CUDA.md` に詳細手順を載せています。CUDA ドライバや対応するライブラリのインストール、Docker の nvidia runtime 設定などを確認してください。

貢献
----------------
- バグ報告や改善提案は Issue を作成してください。
- プルリクエストは歓迎します。コードスタイルやテストを簡潔にまとめて送ってください。

ライセンス
----------------
特に指定がない場合はリポジトリのルートまたは別ファイルでライセンスを明示してください。

その他
----------------
追加したい情報（実行例、スクリーンショット、設定例、既知の問題）があれば教えてください。README に追記します。