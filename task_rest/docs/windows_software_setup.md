# Windows Software Setup

這份文件是給 ARTISE 8ch EEG + Gazepoint GP3-HD + PsychoPy + LSL + LabRecorder 的雙 Windows 電腦配置。

## 機器分工

| 機器 | 主要任務 | 一定要裝 |
| --- | --- | --- |
| Windows 桌機 | 呈現 fixation、播放 EO/EC 語音、連接 GP3-HD、送 PsychoPy LSL marker、送 gaze LSL stream | Gazepoint software、Gazepoint LSL tool、uv/Python、PsychoPy task 環境 |
| Windows 筆電 | 收 EEG / gaze / marker，輸出 `.xdf` | LabRecorder、uv/Python 驗證環境、ARTISE EEG 軟體或 EEG LSL outlet |
| MacBook Pro M3 | 開發與改程式 | 不需要接 GP3-HD；只負責開發與測試 |

建議：如果 ARTISE EEG 接收端可以放在筆電，就把 ARTISE 軟體裝在 Windows 筆電，讓筆電同時負責 EEG LSL outlet + LabRecorder。GP3-HD 因為要接 USB3.0 和校正顯示器，放在 Windows 桌機。

## 共同前置設定：兩台 Windows 都做

### 1. 更新 Windows

- 使用 Windows 10/11。
- 兩台電腦接同一個私人網路；有線網路優先。
- Windows 網路類型設為 `Private network`。
- 暫時避免公司/學校 VPN，VPN 常會阻擋 LSL discovery。

### 2. 安裝 Git

PowerShell：

```powershell
winget install --id Git.Git -e
```

如果 `winget` 不可用，從 https://git-scm.com/download/win 手動安裝。

### 3. 安裝 uv

PowerShell：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

關掉 PowerShell 再重開，確認：

```powershell
uv --version
```

### 4. 安裝 Python 3.10

PsychoPy 在 Windows 上建議先用 Python 3.10，少踩一點版本相容問題。

```powershell
uv python install 3.10
```

確認：

```powershell
uv python list
```

### 5. 下載專案並建立 uv 環境

到你想放專案的位置，例如：

```powershell
cd C:\Users\%USERNAME%\Desktop
git clone https://github.com/chienming-lo/ruitu_tasks.git
cd ruitu_tasks\task_rest
uv venv --python 3.10
uv sync --extra dev
```

如果專案還沒有 `pyproject.toml`，先用這個臨時安裝方式：

```powershell
uv venv --python 3.10
uv pip install psychopy pylsl pyxdf PyYAML pytest
```

確認 Python 環境可用：

```powershell
uv run python --version
uv run python -c "import pylsl, pyxdf, yaml; print('core packages ok')"
```

桌機還要確認 PsychoPy 可 import：

```powershell
uv run python -c "import psychopy; print('psychopy ok')"
```

## Windows 桌機：刺激呈現 + GP3-HD

### 必裝軟體

1. Gazepoint Control / GP3-HD 官方軟體  
   來源：https://www.gazept.com/downloads/

2. Gazepoint LSL tool  
   優先使用 Gazepoint 官方新版軟體內建或附帶的 LSL streaming tool。Gazepoint 2025 年文件說新版軟體已可把 Gazepoint API data 串到 LSL。  
   來源：https://www.gazept.com/blog/integrating-gazepoint-eye-tracking-with-lab-streaming-layer-lsl/

3. PsychoPy task Python 環境  
   用上面 uv 步驟建立。

4. Visual C++ Redistributable  
   如果 PsychoPy、LabRecorder、或 Gazepoint 工具啟動時抱怨 DLL，安裝 Microsoft Visual C++ Redistributable：  
   https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist

### 桌機硬體設定

- GP3-HD 插 USB3.0，不要接 USB hub。
- PsychoPy 顯示的螢幕要跟 GP3-HD 校正的螢幕是同一個。
- Windows 顯示縮放先設 `100%` 或固定一個比例，不要實驗中更動。
- 關閉螢幕休眠、通知彈窗、系統音效。

### 桌機測試順序

1. 啟動 Gazepoint Control。
2. 完成 GP3-HD calibration。
3. 啟動 Gazepoint LSL streaming。
4. 在專案資料夾測 PsychoPy dry run：

   ```powershell
   cd C:\Users\%USERNAME%\Desktop\ruitu_tasks\task_rest
   uv run python -m resting_task.run_resting --config configs\resting_hbn_inspired.yaml --dry-run
   ```

   預期看到：

   ```text
   000.000s task_start task
   002.000s instructed_toOpenEyes eyes_open
   022.000s instructed_toCloseEyes eyes_closed
   ...
   302.000s task_end task
   ```

5. 放入語音檔：

   ```text
   assets\audio\close_eyes.wav
   assets\audio\open_eyes.wav
   ```

6. 跑正式刺激程式：

   ```powershell
   uv run python -m resting_task.run_resting --config configs\resting_hbn_inspired.yaml
   ```

7. 預期行為：

   - 全螢幕先顯示「準備好後按空白鍵或滑鼠開始」。
   - 按空白鍵或滑鼠後才開始正式計時。
   - 正式開始後顯示 fixation cross。
   - 第 2 秒播放張眼語音並送 `instructed_toOpenEyes`。
   - 之後 EO 20 秒、EC 40 秒交替，各 5 次。
   - 第 302 秒結束並送 `task_end`，接著顯示「實驗結束」3 秒。

## Windows 筆電：LabRecorder + EEG 收訊

### 必裝軟體

1. LabRecorder  
   下載 Windows release：  
   https://github.com/labstreaminglayer/App-LabRecorder/releases

2. ARTISE EEG 軟體 / LSL outlet  
   安裝 ARTISE 廠商提供的 Windows 軟體，並確認它可以輸出 LSL stream。  
   目標是讓 LabRecorder 看到 EEG stream，例如 stream name 裡含 `ARTISE` 或廠商實際使用的名稱。

3. uv/Python 驗證環境  
   用共同前置設定安裝。筆電主要會跑：

   ```powershell
   uv run python tools\check_lsl_streams.py --config configs\resting_hbn_inspired.yaml --timeout 5
   uv run python tools\verify_xdf.py C:\path\to\recording.xdf --config configs\resting_hbn_inspired.yaml
   ```

4. Visual C++ Redistributable  
   LabRecorder Windows builds 通常已帶多數依賴，但缺 runtime 時需要安裝。

### 筆電測試順序

1. 啟動 ARTISE EEG 軟體，確認 EEG 串流已開始。
2. 啟動 LabRecorder。
3. 桌機端先開 Gazepoint LSL streaming，並跑 PsychoPy task 或至少讓 marker outlet 啟動。
4. 在 LabRecorder 按 `Update`。
5. 確認看到三類 stream：

   ```text
   ARTISE EEG stream
   Gazepoint / GP3-HD gaze stream
   RestingStateMarkers
   ```

6. 用 Python 做一次 stream check：

   ```powershell
   cd C:\Users\%USERNAME%\Desktop\ruitu_tasks\task_rest
   uv run python tools\check_lsl_streams.py --config configs\resting_hbn_inspired.yaml --timeout 5
   ```

   預期：

   ```text
   All required streams are visible.
   ```

7. 在 LabRecorder 設定儲存路徑與檔名，例如：

   ```text
   sub-test01_task-RestingState_run-01.xdf
   ```

8. 按 `Start`。
9. 到桌機跑 PsychoPy task。
10. PsychoPy 結束後，在 LabRecorder 按 `Stop`。
11. 確認 `.xdf` 檔案大小不是 0，而且 recording 過程中 file size 有增加。

### 錄完驗證

PowerShell：

```powershell
uv run python tools\verify_xdf.py C:\path\to\sub-test01_task-RestingState_run-01.xdf --config configs\resting_hbn_inspired.yaml
```

預期：

```text
XDF verification passed.
```

## LSL 網路檢查

如果筆電看不到桌機的 gaze 或 marker stream：

1. 確認兩台電腦在同一個 subnet。
2. Windows 網路類型設為 Private。
3. 允許 Python、Gazepoint LSL tool、ARTISE 軟體、LabRecorder 通過 Windows Defender Firewall。
4. 檢查 LSL 常用 discovery/streaming ports 沒被擋：

   ```text
   UDP 16571
   TCP/UDP 16572-16604
   ```

5. 暫時關閉 VPN。
6. 兩台電腦都重開相關程式，再按 LabRecorder `Update`。

## 明天 Demo 的最小成功標準

在老闆面前不用先展示完整分析，先展示同步收訊閉環：

1. 桌機畫面出現 fixation。
2. GP3-HD gaze stream 在 LabRecorder 看得到。
3. ARTISE EEG stream 在 LabRecorder 看得到。
4. `RestingStateMarkers` 在 LabRecorder 看得到。
5. LabRecorder 錄出一個 `.xdf`。
6. `.xdf` 驗證通過，包含：

   ```text
   task_start
   instructed_toCloseEyes
   instructed_toOpenEyes
   task_end
   ```

## 資料格式決策

LabRecorder 原始檔保留 `.xdf`。這是 LSL 多串流同步的主格式。`.bdf` 或 `.edf` 如果後續分析需要，再從 `.xdf` 轉出；不要把 `.bdf` 當成這套系統的第一手同步收訊格式。

## 參考來源

- uv Windows installation: https://github.com/astral-sh/uv/blob/main/docs/getting-started/installation.md
- LabRecorder releases: https://github.com/labstreaminglayer/App-LabRecorder/releases
- LabRecorder records XDF: https://github.com/labstreaminglayer/App-LabRecorder
- LSL quick start: https://labstreaminglayer.readthedocs.io/info/getting_started.html
- LSL network troubleshooting: https://labstreaminglayer.readthedocs.io/info/network-connectivity.html
- Gazepoint downloads: https://www.gazept.com/downloads/
- Gazepoint LSL integration: https://www.gazept.com/blog/integrating-gazepoint-eye-tracking-with-lab-streaming-layer-lsl/
