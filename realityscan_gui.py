import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from threading import Thread
import subprocess
import platform
import queue

# RealityScan.exeのパス
REALITYSCAN_EXE = r"C:\Program Files\Epic Games\RealityScan_2.1\RealityScan.exe"

# ログメッセージ用のキュー
log_queue = queue.Queue()

def check_realityscan():
    """RealityScan.exeの存在を確認"""
    if not os.path.exists(REALITYSCAN_EXE):
        messagebox.showerror(
            "エラー",
            f"RealityScan.exeが見つかりません。\nパス: {REALITYSCAN_EXE}\n\nインストールされているか確認してください。"
        )
        return False
    return True

def select_image_folder():
    """画像フォルダを選択"""
    folder = filedialog.askdirectory(title="画像フォルダを選択")
    if folder:
        image_folder_var.set(folder)

def select_output_folder():
    """保存先フォルダを選択"""
    folder = filedialog.askdirectory(title="RSデータ保存先を選択")
    if folder:
        output_folder_var.set(folder)

def log_message(message):
    """ログメッセージをキューに追加"""
    log_queue.put(message)

def update_log():
    """キューからログメッセージを取得してGUIを更新"""
    try:
        while True:
            message = log_queue.get_nowait()
            log_text.insert(tk.END, message + "\n")
            log_text.see(tk.END)
    except queue.Empty:
        pass
    app.after(100, update_log)  # 100msごとに更新

def run_realityscan():
    """RealityScanを実行"""
    if not check_realityscan():
        return
    
    image_folder = image_folder_var.get()
    output_folder = output_folder_var.get()
    
    if not image_folder or not output_folder:
        messagebox.showerror("エラー", "画像フォルダと保存先フォルダを指定してください。")
        return
    
    if not os.path.exists(image_folder):
        messagebox.showerror("エラー", f"画像フォルダが存在しません: {image_folder}")
        return
    
    # 出力フォルダを作成
    os.makedirs(output_folder, exist_ok=True)
    
    # ボタンを無効化
    run_button.config(state=tk.DISABLED)
    status_var.set("処理中...")
    log_text.delete(1.0, tk.END)
    
    # バックグラウンドで処理を実行
    Thread(target=process_realityscan, args=(image_folder, output_folder)).start()

def process_realityscan(image_folder, output_folder):
    """RealityScan処理を実行（バックグラウンド）"""
    try:
        log_message("=== RealityScan処理を開始 ===")
        log_message(f"画像フォルダ: {image_folder}")
        log_message(f"保存先: {output_folder}")
        
        # プロジェクトファイルのパス
        project_path = os.path.join(output_folder, "project.rsproj")
        cameras_csv = os.path.join(output_folder, "cameras.csv")
        pointcloud_ply = os.path.join(output_folder, "pointcloud.ply")
        mesh_obj = os.path.join(output_folder, "mesh.obj")
        
        # RealityScan CLIコマンドを構築
        # calculatePointCloudコマンドを削除（存在しない可能性）
        commands = [
            REALITYSCAN_EXE,
            "-newScene",
            "-addFolder", image_folder,
            "-align",
            "-selectMaximalComponent",  # 最大のアライメント枚数を持つコンポーネントを選択
            "-setReconstructionRegionAuto",
            "-exportRegistration", cameras_csv,
            "-calculateNormalModel",  # モデルを計算
            "-calculateTexture",  # テクスチャ(カラー情報)を計算
            "-exportRegistration", os.path.join(output_folder, "colmap_cameras.txt"),  # COLMAP形式でカメラをエクスポート
            "-save", project_path,
            "-quit"
        ]
        
        command_str = " ".join([f'"{cmd}"' if " " in str(cmd) else str(cmd) for cmd in commands])
        
        log_message("\n実行コマンド:")
        log_message(command_str)
        log_message("\nRealityScanを実行中...")
        
        # コマンドを実行（リスト形式で渡す）
        process = subprocess.Popen(
            commands,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 出力をリアルタイムで表示
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                log_message(output.strip())
        
        # プロセスの完了を待つ
        return_code = process.wait()
        
        if return_code == 0:
            log_message("\n=== 処理が完了しました ===")
            log_message(f"プロジェクト: {project_path}")
            log_message(f"カメラCSV: {cameras_csv}")
            log_message(f"COLMAPカメラ: {os.path.join(output_folder, 'colmap_cameras.txt')}")
            log_message("\nモデルとテクスチャ（カラー）が計算されました。")
            log_message("メッシュ(OBJ)と点群(PLY)は、プロジェクトをRealityScan GUIで開いて")
            log_message("「エクスポート」から手動で出力してください。")
            
            try:
                app.after(0, lambda: messagebox.showinfo("成功", "RealityScan処理が完了しました。"))
                app.after(0, lambda: status_var.set("完了"))
            except:
                pass
        else:
            log_message(f"\n=== エラー: リターンコード {return_code} ===")
            stderr_output = process.stderr.read()
            if stderr_output:
                log_message("エラー出力:")
                log_message(stderr_output)
            
            try:
                app.after(0, lambda: messagebox.showerror("エラー", f"RealityScan処理中にエラーが発生しました。\nリターンコード: {return_code}"))
                app.after(0, lambda: status_var.set("エラー"))
            except:
                pass
    
    except Exception as e:
        log_message(f"\n=== 例外が発生しました ===")
        log_message(str(e))
        try:
            app.after(0, lambda: messagebox.showerror("エラー", f"処理中にエラーが発生しました:\n{e}"))
            app.after(0, lambda: status_var.set("エラー"))
        except:
            pass
    
    finally:
        # ボタンを再度有効化
        try:
            app.after(0, lambda: run_button.config(state=tk.NORMAL))
        except:
            pass

# GUIの作成
app = tk.Tk()
app.title("RealityScan GUI ラッパー")
app.geometry("700x550")

# 変数
image_folder_var = tk.StringVar()
output_folder_var = tk.StringVar()
status_var = tk.StringVar(value="待機中")

# 画像フォルダ選択
tk.Label(app, text="画像フォルダ:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
tk.Entry(app, textvariable=image_folder_var, width=50).grid(row=0, column=1, padx=10, pady=10, sticky="ew")
tk.Button(app, text="選択", command=select_image_folder).grid(row=0, column=2, padx=10, pady=10)

# 保存先フォルダ選択
tk.Label(app, text="保存先フォルダ:").grid(row=1, column=0, padx=10, pady=10, sticky="e")
tk.Entry(app, textvariable=output_folder_var, width=50).grid(row=1, column=1, padx=10, pady=10, sticky="ew")
tk.Button(app, text="選択", command=select_output_folder).grid(row=1, column=2, padx=10, pady=10)

# 状態表示
tk.Label(app, text="状態:").grid(row=2, column=0, padx=10, pady=10, sticky="e")
tk.Label(app, textvariable=status_var).grid(row=2, column=1, padx=10, pady=10, sticky="w")

# 実行ボタン
run_button = tk.Button(app, text="実行", command=run_realityscan, bg="green", fg="white", font=("Arial", 12, "bold"))
run_button.grid(row=3, column=1, padx=10, pady=20)

# ログ表示エリア
tk.Label(app, text="ログ:").grid(row=4, column=0, padx=10, pady=5, sticky="ne")
log_text = scrolledtext.ScrolledText(app, width=80, height=20, wrap=tk.WORD)
log_text.grid(row=4, column=1, columnspan=2, padx=10, pady=5, sticky="nsew")

# グリッドの重み設定
app.columnconfigure(1, weight=1)
app.rowconfigure(4, weight=1)

# 起動時にRealityScanの存在を確認
if check_realityscan():
    log_message("RealityScan.exeが見つかりました。")
    log_message(f"パス: {REALITYSCAN_EXE}")
else:
    log_message("警告: RealityScan.exeが見つかりません。")

# ログ更新を開始
update_log()

app.mainloop()
