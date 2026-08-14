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
2. （可選）用 `skill-youtube-channel-fetch` 自動從頻道抓最新影片音訊並寫入
   `audio_manifest.json`；也可手動在 `audio_manifest.json` 加入 `{stem: audio_url}`
   （格式範例見 `audio_manifest.example.json`）：
   ```bash
   pip install -r requirements.txt
   python skills/skill-youtube-channel-fetch/scripts/channel_fetch.py fetch \
       https://www.youtube.com/@fubonsec --limit 5
   ```
3. 觸發轉錄：
   ```bash
   python skills/skill-mlx-api-client-whisper/scripts/whisper_issue_client.py sync audio_manifest.json
   ```
   對每個尚未有 `FIN.srt` 的 stem，會在 `WHISPER_TARGET_REPO`（Mac-mini repo）開一張
   `generate-FIN` issue 觸發轉錄；已完成的 stem 則自動關閉對應 issue。
   （步驟 2 加 `--sync` 可以合併這一步。）
4. 若某支影片的 `GT.srt` 被人工修正過，想讓 pipeline 重新評分（不重新轉錄），呼叫
   `open_fin_request(stem, audio_url, task_type="refine_fin_srt")`（見 skill SKILL.md）。
5. 有 `FIN.srt` 後，用 `skill-youtube-channel-srt-keyframe-extract` 分析逐字稿找出圖表／簡報等
   視覺重點時刻，擷取對應畫面存成帶時間碼的 PNG：
   ```bash
   python skills/skill-youtube-channel-srt-keyframe-extract/scripts/keyframe_extract.py extract <stem> \
       --srt data/<channel>/<stem>_FIN.srt \
       --video-url https://www.youtube.com/watch?v=<video_id>
   ```

## 內容索引

### [fubonsec](data/fubonsec/)

| 影片 | 日期 |
| --- | --- |
| [破解股市利空虛實：台股已從反彈走向反轉？｜富邦投顧 陳奕光 董事長《富邦說趨勢》 EP 91](data/fubonsec/fubonsec_-KLEA_c88xI_keyframes.md) | 2026-08-07 |

### [yutinghaofinance](data/yutinghaofinance/)

| 影片 | 日期 |
| --- | --- |
| [2026/8/12(三)GPU金融化狂潮 2008正在重演？兆元商機還是下一場危機？【早晨財經速解讀】](data/yutinghaofinance/yutinghaofinance_ApykW90PQ58_keyframes.md) | 2026-08-12 |
| [2026/8/11(二)AI舉債時代 自由現金流能翻正?外資再加空單!台股還能攻?【早晨財經速解讀】](data/yutinghaofinance/yutinghaofinance_v7TpiWK5DTQ_keyframes.md) | 2026-08-11 |

## 詳細設計

issue metadata schema、stem 解析規則、company-configs 調校/GT 校正迴圈見
`Mac-mini` repo 的 `skills/skill-mlx-api-server-whisper/SKILL.md`。
