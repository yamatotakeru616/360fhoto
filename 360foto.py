
import os
import platform
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from threading import Thread
import psutil
from tkinter import ttk
import cv2
import time
import queue
from datetime import datetime, timedelta
import shutil

# If running in a headless Unix-like environment (not Windows), exit with an informative message
if platform.system() != 'Windows' and os.environ.get('DISPLAY','') == '' and os.environ.get('CI','') == '':
    print('Warning: No DISPLAY found. This script opens a Tkinter GUI and requires a display.\nIf running inside Docker, run the container with X11 forwarding (e.g. -e DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix) or run on host.')
    exit(1)

def ensure_ffmpeg_on_path():
    """Ensure ffmpeg is discoverable on PATH (especially for Windows user install)."""
    if shutil.which('ffmpeg') is not None:
        return
    if platform.system() == 'Windows':
        default_bin = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'ffmpeg', 'bin')
        if default_bin and os.path.isdir(default_bin):
            os.environ['PATH'] = default_bin + os.pathsep + os.environ.get('PATH', '')

ensure_ffmpeg_on_path()

def select_input_files():
    files_selected = filedialog.askopenfilenames(filetypes=[("ビデオファイル", "*.mp4;*.avi;*.mov")])
    input_files_var.set(';'.join(files_selected))
    update_total_frames()

def select_output_folder():
    folder_selected = filedialog.askdirectory()
    output_folder_var.set(folder_selected)

def kill_ffmpeg_process():
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == 'ffmpeg.exe':
            try:
                proc.kill()
            except psutil.NoSuchProcess:
                pass

def update_total_frames():
    total_frames = 0
    frame_rate = frame_rate_var.get()
    num_directions = 1 if direction_var.get() == "1" else (12 if direction_var.get() == "12" else (8 if direction_var.get() == "8" else (8 if direction_var.get() == "8_20" else (6 if direction_var.get() == "6_h3_45" else (9 if direction_var.get() == "9_h3_45x2" else (5 if direction_var.get() == "5_down" else (4 if direction_var.get() == "4_h1_45" else 2)))))))

    for file in input_files_var.get().split(';'):
        cap = cv2.VideoCapture(file)
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
            frames_for_file = int(duration / frame_rate * num_directions)
            total_frames += frames_for_file
            cap.release()

    total_frames_var.set(total_frames)

def process_video():
    global processing, start_time
    processing = True
    status_var.set("処理中...")
    input_paths = input_files_var.get().split(';')
    output_path = output_folder_var.get()
    size = 1600  # 画素数を1600x1600に固定
    format = format_var.get()
    total_frames = total_frames_var.get()
    processed_frames = 0
    start_time = time.time()

    if not input_paths or not output_path:
        messagebox.showerror("エラー", "入力ファイルと保存先フォルダを指定してください。")
        status_var.set("待機中")
        return

    # ffmpeg の存在チェック（見つからない場合は案内して終了）
    if shutil.which('ffmpeg') is None:
        messagebox.showerror(
            "エラー",
            "ffmpeg が見つかりません。\nインストール済みであれば、環境変数 PATH に C:/Users/<ユーザー名>/AppData/Local/ffmpeg/bin を追加してから再実行してください。"
        )
        status_var.set("待機中")
        return

    try:
        os.makedirs(output_path, exist_ok=True)

        transforms = get_transforms()

        for input_path in input_paths:
            if not processing:
                break

            fps = 1 / frame_rate_var.get()

            for index, transform in enumerate(transforms):
                if not processing:
                    break

                base_name = os.path.basename(input_path)
                name_part = base_name[-7:-4]
                output_file_path = os.path.join(output_path, f'{name_part}_ot_{index}_%04d.{format}')

                v360_options = ':'.join([
                    'input=e', 'output=rectilinear',
                    'h_fov=90', 'v_fov=90',
                    f'w={size}', f'h={size}',
                    f'yaw={transform[0]}',
                    f'pitch={transform[1]}',
                    f'roll={transform[2]}'
                ])

                # GPU acceleration with CUDA (適応的に使用)
                # 大きな解像度の動画の場合、CPUデコード→GPU処理を使用
                cap = cv2.VideoCapture(input_path)
                video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                cap.release()
                
                if video_width > 4096:
                    # 大きな解像度：CPUデコード、GPUエンコード（利用可能な場合）
                    command = f'ffmpeg -i "{input_path}" -vf v360={v360_options} -c:v mjpeg -q 1 -r {fps} "{output_file_path}"'
                else:
                    # 小さな解像度：CUDAアクセラレーション
                    command = f'ffmpeg -hwaccel cuda -hwaccel_output_format cuda -i "{input_path}" -vf v360={v360_options},hwdownload,format=nv12 -q 1 -r {fps} "{output_file_path}"'
                
                process = subprocess.Popen(command, shell=True)

                while process.poll() is None:
                    time.sleep(0.1)
                    output_files = [f for f in os.listdir(output_path) if f.endswith(f'.{format}')]
                    processed_frames = len(output_files)
                    progress = (processed_frames / total_frames) * 100
                    update_queue.put(('progress', progress))
                    update_queue.put(('frames', processed_frames))

                    elapsed_time = time.time() - start_time
                    if processed_frames > 0:
                        estimated_total_time = (elapsed_time / processed_frames) * total_frames
                        estimated_remaining_time = estimated_total_time - elapsed_time
                        estimated_completion_time = datetime.now() + timedelta(seconds=estimated_remaining_time)
                        update_queue.put(('estimated_time', estimated_completion_time.strftime("%Y-%m-%d %H:%M:%S")))
                        update_queue.put(('estimated_work_time', time.strftime("%H:%M:%S", time.gmtime(estimated_total_time))))
                
                process.wait()
                
                if not processing:
                    kill_ffmpeg_process()
                    break
        
        if processing:
            messagebox.showinfo("成功", "ビデオ処理が完了しました。")
    except Exception as e:
        messagebox.showerror("エラー", f"ビデオ処理中にエラーが発生しました: {e}")
    finally:
        processing = False
        status_var.set("待機中")

def get_transforms():
    if direction_var.get() == "1":  # 正面のみ
        return [(0, 0, 0)]
    elif direction_var.get() == "2":  # 2方向（正-45）
        return [
            (0, 0, 0),
            (0, -45, 0)
        ]
    elif direction_var.get() == "4_h1_45":  # 4方向（H1-45）
        return [
            (0, 0, 0),
            (-60, -45, 0),
            (60, -45, 0),
            (180, -45, 0)
        ]
    elif direction_var.get() == "8":  # 下8方向（45度）
        return [
            (-90, 0, 0),
            (0, 0, 0),
            (90, 0, 0),
            (180, 0, 0),
            (-45, -45, 0),
            (45, -45, 0),
            (135, -45, 0),
            (-135, -45, 0)
        ]
    elif direction_var.get() == "12":  # 12方向
        return [
            (-90, 0, 0),
            (0, 0, 0),
            (90, 0, 0),
            (180, 0, 0),
            (-135, 45, 0),
            (-45, 45, 0),
            (45, 45, 0),
            (135, 45, 0),
            (-135, -45, 0),
            (-45, -45, 0),
            (45, -45, 0),
            (135, -45, 0)
        ]
    elif direction_var.get() == "8_20": # 8方向（ななめ20度）
        return [
            (0, -20, 0),
            (-90, -20, 0),
            (90, -20, 0),
            (180, -20, 0),
            (0, 20, 0),
            (-90, 20, 0),
            (90, 20, 0),
            (180, 20, 0)
        ]
    elif direction_var.get() == "6_h3_45": # 6方向（H3-45）
        return [
            (0, 0, 0),
            (-120, 0, 0),
            (120, 0, 0),
            (-60, -45, 0),
            (60, -45, 0),
            (180, -45, 0)
        ]
    elif direction_var.get() == "9_h3_45x2": # 9方向（H3-45×2）
        return [
            (0, 0, 0),
            (-120, 0, 0),
            (120, 0, 0),
            (-60, -45, 0),
            (60, -45, 0),
            (180, -45, 0),
            (-60, 45, 0),
            (60, 45, 0),
            (180, 45, 0)
        ]
    elif direction_var.get() == "5_down": # 下5方向（H4+下）
        return [
            (0, -90, 0),
            (-90, 0, 0),
            (0, 0, 0),
            (90, 0, 0),
            (180, 0, 0)
        ]
    else:
        return []

def start_processing():
    global update_queue
    update_queue = queue.Queue()
    Thread(target=process_video).start()
    app.after(100, update_gui)

def update_gui():
    global start_time
    if processing:
        try:
            while True:
                update_type, value = update_queue.get_nowait()
                if update_type == 'progress':
                    progress_var.set(value)
                elif update_type == 'frames':
                    processed_frames_var.set(value)
                elif update_type == 'estimated_time':
                    estimated_time_var.set(value)
                elif update_type == 'estimated_work_time':
                    estimated_work_time_var.set(value)
        except queue.Empty:
            pass
        
        elapsed_time = time.time() - start_time
        elapsed_time_var.set(time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))
        
        app.after(100, update_gui)

def cancel_processing():
    global processing
    processing = False
    kill_ffmpeg_process()
    subprocess.call("taskkill /f /im cmd.exe", shell=True)
    messagebox.showinfo("キャンセル", "ビデオ処理がキャンセルされました。")
    status_var.set("待機中")

app = tk.Tk()
app.title("全天球画像変換")

input_files_var = tk.StringVar()
output_folder_var = tk.StringVar()
frame_rate_var = tk.DoubleVar(value=1.5)
size_var = tk.IntVar(value=1600)
format_var = tk.StringVar(value="jpg")
status_var = tk.StringVar(value="待機中")
total_frames_var = tk.IntVar(value=0)
processed_frames_var = tk.IntVar(value=0)
progress_var = tk.DoubleVar(value=0)
elapsed_time_var = tk.StringVar(value="00:00:00")
estimated_time_var = tk.StringVar(value="")
direction_var = tk.StringVar(value="6_h3_45")  # デフォルトを6方向（H3-45）に設定
estimated_work_time_var = tk.StringVar(value="00:00:00")
processing = False
update_queue = None

tk.Label(app, text="入力ファイル:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
tk.Entry(app, textvariable=input_files_var, width=50).grid(row=0, column=1, columnspan=3, padx=5, pady=5, sticky="ew")
tk.Button(app, text="選択", command=select_input_files).grid(row=0, column=4, padx=5, pady=5)

tk.Label(app, text="保存先フォルダ:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
tk.Entry(app, textvariable=output_folder_var, width=50).grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky="ew")
tk.Button(app, text="選択", command=select_output_folder).grid(row=1, column=4, padx=5, pady=5)

tk.Label(app, text="画像書出し間隔:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
tk.Radiobutton(app, text="1秒", variable=frame_rate_var, value=1.0, command=update_total_frames).grid(row=2, column=1, padx=5, pady=5, sticky="w")
tk.Radiobutton(app, text="1.5秒", variable=frame_rate_var, value=1.5, command=update_total_frames).grid(row=2, column=2, padx=5, pady=5, sticky="w")
tk.Radiobutton(app, text="2秒", variable=frame_rate_var, value=2.0, command=update_total_frames).grid(row=2, column=3, padx=5, pady=5, sticky="w")
tk.Radiobutton(app, text="3秒", variable=frame_rate_var, value=3.0, command=update_total_frames).grid(row=2, column=4, padx=5, pady=5, sticky="w")

tk.Label(app, text="フォーマット:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
tk.Radiobutton(app, text="JPG", variable=format_var, value="jpg").grid(row=3, column=1, padx=5, pady=5, sticky="w")
tk.Radiobutton(app, text="PNG", variable=format_var, value="png").grid(row=3, column=2, padx=5, pady=5, sticky="w")

# 方向選択ラジオボタン（更新）
tk.Label(app, text="出力方向:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
tk.Radiobutton(app, text="正面のみ", variable=direction_var, value="1", command=update_total_frames).grid(row=4, column=1, padx=5, pady=5, sticky="w")
tk.Radiobutton(app, text="2方向（正-45）", variable=direction_var, value="2", command=update_total_frames).grid(row=5, column=1, padx=5, pady=5, sticky="w")
tk.Radiobutton(app, text="4方向（H1-45）", variable=direction_var, value="4_h1_45", command=update_total_frames).grid(row=6, column=1, padx=5, pady=5, sticky="w")
# 前のコードの続き
tk.Radiobutton(app, text="6方向（H3-45度）", variable=direction_var, value="6_h3_45", command=update_total_frames).grid(row=7, column=1, padx=5, pady=5, sticky="w")
tk.Radiobutton(app, text="9方向（H3-45×2）", variable=direction_var, value="9_h3_45x2", command=update_total_frames).grid(row=8, column=1, padx=5, pady=5, sticky="w")
tk.Radiobutton(app, text="下5方向（H4+下）", variable=direction_var, value="5_down", command=update_total_frames).grid(row=9, column=1, padx=5, pady=5, sticky="w")
tk.Radiobutton(app, text="8方向（ななめ20度）", variable=direction_var, value="8_20", command=update_total_frames).grid(row=10, column=1, padx=5, pady=5, sticky="w")
tk.Radiobutton(app, text="下8方向（H4-45度）", variable=direction_var, value="8", command=update_total_frames).grid(row=11, column=1, padx=5, pady=5, sticky="w")
tk.Radiobutton(app, text="全12方向（H4+斜め上下45度）", variable=direction_var, value="12", command=update_total_frames).grid(row=12, column=1, padx=5, pady=5, sticky="w")

tk.Label(app, text="フレーム数:").grid(row=13, column=0, padx=5, pady=5, sticky="e")
tk.Label(app, textvariable=total_frames_var).grid(row=13, column=1, padx=5, pady=5, sticky="w")

tk.Label(app, text="処理済みフレーム数:").grid(row=14, column=0, padx=5, pady=5, sticky="e")
tk.Label(app, textvariable=processed_frames_var).grid(row=14, column=1, padx=5, pady=5, sticky="w")

tk.Label(app, text="進捗:").grid(row=15, column=0, padx=5, pady=5, sticky="e")
progress_bar = ttk.Progressbar(app, variable=progress_var, maximum=100)
progress_bar.grid(row=15, column=1, columnspan=3, padx=5, pady=5, sticky="ew")

tk.Label(app, text="経過時間:").grid(row=16, column=0, padx=5, pady=5, sticky="e")
tk.Label(app, textvariable=elapsed_time_var).grid(row=16, column=1, padx=5, pady=5, sticky="w")

tk.Label(app, text="予想終了時刻:").grid(row=17, column=0, padx=5, pady=5, sticky="e")
tk.Label(app, textvariable=estimated_time_var).grid(row=17, column=1, columnspan=3, padx=5, pady=5, sticky="w")

tk.Label(app, text="予定作業時間:").grid(row=18, column=0, padx=5, pady=5, sticky="e")
tk.Label(app, textvariable=estimated_work_time_var).grid(row=18, column=1, padx=5, pady=5, sticky="w")

tk.Label(app, text="状態:").grid(row=19, column=0, padx=5, pady=5, sticky="e")
tk.Label(app, textvariable=status_var).grid(row=19, column=1, columnspan=3, pady=5, sticky="w")

tk.Button(app, text="ビデオ処理開始", command=start_processing).grid(row=20, column=1, pady=10, padx=5)
tk.Button(app, text="キャンセル", command=cancel_processing).grid(row=20, column=2, pady=10, padx=5)

app.columnconfigure(1, weight=1)
app.columnconfigure(2, weight=1)
app.columnconfigure(3, weight=1)

app.mainloop()