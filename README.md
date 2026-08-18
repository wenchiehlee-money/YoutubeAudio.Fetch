# YoutubeAudio.Fetch
Working space for YoutubeAudio.Fetch

財經 YouTube 影片的音訊來源 repo，透過 `skills/skill-mlx-api-client-whisper` 觸發 Mac-mini 上的
whisper 轉錄 pipeline（`skill-mlx-api-server-whisper`），產出人工可校正的 `GT.srt` 與 pipeline
選出的 `FIN.srt`。與 `InvestorConference`（法說會音訊）共用同一套 Mac-mini pipeline，差別只在
`source_type=youtube` 與 stem 命名慣例。

## 內容索引

### [富邦證券](data/fubonsec/)

| 影片 | 日期 |
| --- | --- |
| [你的股票最後會留給誰？律師揭存股族最容易忽略的財產傳承觀念｜蘇家宏專訪 EP1](data/fubonsec/fubonsec_W_cLHLRD1m8_keyframes.md) | 2026-08-14 |
| [AI零組件漲價潮再起？下半年受惠產業與ETF一次掌握｜富邦投顧 陶治瑋 副總《富邦說趨勢》 EP 92 eT富攻略](data/fubonsec/fubonsec_DfN9yS3xkuU_keyframes.md) | 2026-08-12 |
| [破解股市利空虛實：台股已從反彈走向反轉？｜富邦投顧 陳奕光 董事長《富邦說趨勢》 EP 91](data/fubonsec/fubonsec_-KLEA_c88xI_keyframes.md) | 2026-08-07 |
| [富邦證券授信開戶四合一](data/fubonsec/fubonsec_mhIgas9TsMU_keyframes.md) | 2026-08-06 |
| [AI投資新選擇！KOSPI 50如何一次掌握韓國50大企業？\| 富邦Global Sight EP10](data/fubonsec/fubonsec_ehESBhQSWyM_keyframes.md) | 2026-08-05 |

### [游庭皓的財經皓角](data/yutinghaofinance/)

| 影片 | 日期 |
| --- | --- |
| [2026/8/18(二)美股買盤停止追高 散戶等回檔?台灣游資氾濫 普發成常態?【早晨財經速解讀】](data/yutinghaofinance/yutinghaofinance_aRPmzQfTLFc_keyframes.md) | 2026-08-18 |
| [2026/8/17(一)指數創高 回檔等加碼?美課100%關稅 無人機大戰開打!【早晨財經速解讀】](data/yutinghaofinance/yutinghaofinance_OJ5vxmwQrE0_keyframes.md) | 2026-08-17 |
| [2026/8/14(五)AI股不再雞犬升天 債市開始算帳!AI帳單 誰會來買單?【早晨財經速解讀】](data/yutinghaofinance/yutinghaofinance_oLPxNHRAPEI_keyframes.md) | 2026-08-14 |
| [2026/8/13(四)通膨退一步 股市進兩步?情緒轉彎 槓桿資金回來了?【早晨財經速解讀】](data/yutinghaofinance/yutinghaofinance_KS_BkfqfALI_keyframes.md) | 2026-08-13 |
| [2026/8/12(三)GPU金融化狂潮 2008正在重演？兆元商機還是下一場危機？【早晨財經速解讀】](data/yutinghaofinance/yutinghaofinance_ApykW90PQ58_keyframes.md) | 2026-08-12 |
| [2026/8/11(二)AI舉債時代 自由現金流能翻正?外資再加空單!台股還能攻?【早晨財經速解讀】](data/yutinghaofinance/yutinghaofinance_v7TpiWK5DTQ_keyframes.md) | 2026-08-11 |
| [2026/8/10(一)非農爆冷 升息機率降?美股創高!波克夏也開始買股了?【早晨財經速解讀】](data/yutinghaofinance/yutinghaofinance_5_poweJsVBA_keyframes.md) | 2026-08-10 |

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
   也可以指定日期區間，抓某段期間內的所有影片（而非「最新 N 支」）：
   ```bash
   python skills/skill-youtube-channel-fetch/scripts/channel_fetch.py fetch \
       https://www.youtube.com/@yutinghaofinance --date-after 2026-08-01 --date-before 2026-08-07
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

## 自動化（每日排程）

`.github/workflows/daily-channel-fetch.yml` 每天自動：

1. 對 `channels.json` 裡列的每個頻道跑 `channel_fetch.py fetch <url> --limit 5 --sync`，
   抓新影片、寫逐字稿/manifest、觸發 whisper
2. 對每個「有 `FIN.srt`（沒有的話退而求其次用 `GT.srt`）但還沒有 `_keyframes.md`」的
   stem 跑 `skill-youtube-channel-srt-keyframe-extract`，補齊關鍵畫面擷取（每支重試一次；
   YouTube 端偶發限流導致某支失敗不會擋住其他支，會留到隔天的排程自動重試，因為判斷條件
   就是「還沒有 `_keyframes.md`」）
3. 重新產生 README「內容索引」並 commit——新影片跑完關鍵畫面擷取後就會自動出現在這裡

也可用 `workflow_dispatch` 手動觸發並自訂 `limit`。要追蹤新頻道，直接編輯 `channels.json`
加一行 URL 即可，不用改 workflow。

此 workflow 需要在 repo 的 GitHub Actions Secrets 設定：
- `YOUTUBE_COOKIES_B64`：YouTube cookies.txt 內容的 base64 編碼；給 `yt-dlp` 通過
  YouTube「Sign in to confirm you’re not a bot」檢查用
- `REPO_FILE_SYNC_WENCHIEHLEE_MONEY`：對本 repo `Contents: Read and write`（發布音訊 Release、
  push commit）
- `REPO_FILE_SYNC_ZHONGZHENG782_MONEY`：對 `WHISPER_TARGET_REPO`（Mac-mini repo）
  `Issues: Read and write`（`--sync` 觸發轉錄用）
- `GEMINI_API_KEY`、`CODEX_API_URL`、`CODEX_API_KEY`：關鍵畫面擷取要判斷「哪些時間點值得
  截圖」時呼叫的 `llm` 套件 provider 憑證（`../llm` 的 codex → gemini → mlx 備援鏈；CI
  環境連不到僅限內網/Tailscale 的 `MLX_API_URL`，所以沒設 mlx 相關 secrets，鏈路會直接
  落到 codex/gemini 其中之一）

手動字幕來源、只有 `GT.srt` 沒有 `FIN.srt` 的 stem，也會照常被拿去做關鍵畫面擷取（找不到
`FIN.srt` 時改用 `GT.srt` 當來源）——截圖跟逐字稿片段仍然有效，之後若跑了 `refine` 讓
Mac-mini pipeline 產出正式版 `FIN.srt`，可以再手動重跑一次關鍵畫面擷取讓內容更新。

## 詳細設計

issue metadata schema、stem 解析規則、company-configs 調校/GT 校正迴圈見
`Mac-mini` repo 的 `skills/skill-mlx-api-server-whisper/SKILL.md`。
