# Windows Runbook: ARTISE EEG + Gazepoint GP3-HD + LabRecorder

## 角色分工

- 桌機：刺激呈現、PsychoPy resting-state task、GP3-HD 連線與校正、GP3-HD LSL bridge。
- 筆電：LabRecorder 與 EEG 端錄製，負責把 EEG、Gaze、Markers 一起存成 `.xdf`。
- Mac：開發與 dry-run 檢查用；正式 GP3-HD 採集請用 Windows，因為 Gazepoint 官方軟體不支援 Mac/Linux。

## 開始前

1. 讓桌機與筆電在同一個私人網路，優先使用有線網路；若用 Wi-Fi，確認沒有 client isolation。
2. Windows 防火牆允許 LSL discovery/streaming。LSL 預設會使用 UDP discovery 16571，以及 16572-16604 的 TCP/UDP ports。
3. 桌機接上 GP3-HD，使用 USB3.0。
4. 桌機開啟 Gazepoint Control/OpenGaze，完成校正。
5. 桌機啟動 GP3-HD LSL bridge，確認 gaze stream 已發布。
6. 筆電啟動 EEG 軟體，確認 EEG LSL stream 已發布。

## 桌機刺激檢查

在桌機專案目錄啟動 Python 環境後，先 dry-run：

```powershell
python -m resting_task.run_resting --config configs/resting_hbn_inspired.yaml --dry-run
```

確認看到 HBN-inspired 5 分鐘流程：EO 20 秒、EC 40 秒，EO/EC 各 5 次：

```text
000.000s task_start task
002.000s instructed_toOpenEyes eyes_open
022.000s instructed_toCloseEyes eyes_closed
...
302.000s task_end task
```

正式 task 會顯示 fixation cross，從第 2 秒開始播放張眼/閉眼語音並送 marker，結束於第 302 秒。實際 LSL marker 只送 `task_start`、`instructed_toCloseEyes`、`instructed_toOpenEyes`、`task_end` 這些 label；不要送 clean-window marker。

## 筆電 LabRecorder

1. 開啟 LabRecorder。
2. 按 `Update`。
3. 確認可見 streams：
   - EEG stream
   - Gazepoint/GP3-HD gaze stream
   - `RestingStateMarkers`
4. Study Root 選擇資料儲存資料夾。
5. 檔名建議：

```text
sub-%p_task-RestingState_run-%n.xdf
```

6. 先在 LabRecorder 按 `Start`。
7. 再回桌機執行正式刺激：

```powershell
python -m resting_task.run_resting --config configs/resting_hbn_inspired.yaml
```

8. task 結束後再按 LabRecorder `Stop`。

## 錄完驗證

在可以讀到錄製檔的 Windows 機器上執行：

```powershell
python tools\verify_xdf.py C:\path\to\recording.xdf --config configs\resting_hbn_inspired.yaml
```

期望看到：

```text
XDF verification passed.
```

LabRecorder 原始同步資料格式是 `.xdf`。請把 `.xdf` 保留為 raw source；若後續分析需要 `.bdf`、`.edf` 或其他格式，等 streams 與 marker 驗證通過後再轉檔。
