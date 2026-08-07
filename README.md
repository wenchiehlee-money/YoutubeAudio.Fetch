# YoutubeAudio.Fetch
Working space for YoutubeAudio.Fetch

財經 YouTube 影片的音訊來源 repo，透過 `skills/skill-mlx-api-client-whisper` 觸發 Mac-mini 上的
whisper 轉錄 pipeline（`skill-mlx-api-server-whisper`），產出人工可校正的 `GT.srt` 與 pipeline
選出的 `FIN.srt`。與 `InvestorConference`（法說會音訊）共用同一套 Mac-mini pipeline，差別只在
`source_type=youtube` 與 stem 命名慣例。

## 目錄慣例
```
data/{channel}/{channel}_{video_id}_GT.srt   # 人工校正後的 ground truth（單一真相來源）
data/{channel}/{channel}_{video_id}_FIN.srt  # pipeline 依 CER 挑選出的最終逐字稿
```
`video_id` 為固定 11 碼的 YouTube 影片 ID；stem = `{channel}_{video_id}`。

## 使用方式

1. 複製 `.env.example` 為 `.env`，填入 GitHub PAT 與 repo 設定
2. 在 `audio_manifest.json` 加入 `{stem: audio_url}`（格式範例見 `audio_manifest.example.json`）
3. 執行：
   ```bash
   pip install -r requirements.txt
   python skills/skill-mlx-api-client-whisper/scripts/whisper_issue_client.py sync audio_manifest.json
   ```
   對每個尚未有 `FIN.srt` 的 stem，會在 `WHISPER_TARGET_REPO`（Mac-mini repo）開一張
   `generate-FIN` issue 觸發轉錄；已完成的 stem 則自動關閉對應 issue。
4. 若某支影片的 `GT.srt` 被人工修正過，想讓 pipeline 重新評分（不重新轉錄），呼叫
   `open_fin_request(stem, audio_url, task_type="refine_fin_srt")`（見 skill SKILL.md）。

詳細設計（issue metadata schema、stem 解析規則、company-configs 調校/GT 校正迴圈）見
`Mac-mini` repo 的 `skills/skill-mlx-api-server-whisper/SKILL.md`。
