---
name: comfy_t2i
description: ComfyUI 文生圖 (T2I) 專用任務分發器。
tags: [comfyui, flux, t2i, image-generation, automation]
---

# comfy_t2i (文生圖專用)

## 描述
專門用於將文字描述轉換為高品質影像的工作流。

## 觸發條件
當使用者請求「畫一張...」、「生成照片」、「文生圖」等指令時，載入此技能。

## 使用說明
1. **執行模式**: 必須使用背景非同步執行。
2. **指令格式**: `python3 ~/.hermes/skills/mlops/comfy_t2i/scripts/t2i_engine.py [workflow_path] "[prompt]"`
3. **Prompt 注入規則**:
   - **直接指定 Node 107**（`CR Prompt Text`），因為 Node 107 的輸出直接連到 Node 97 (CLIPTextEncode Positive)，再連到 CFGGuider 的 `positive` 輸入。
   - 資料流向：`Node 107` → `text` → `Node 97` → `positive` → `Node 86 (CFGGuider)`

## 完整交付流程（三端協作）

以下是 Engine、Agent、Gateway 三者的協作流程：

### 1. Engine（生成端）
Engine 腳本在背景執行，職責：
1. 注入 prompt 到 Node 107
2. 發送工作流到 ComfyUI
3. 輪詢生成狀態直到完成
4. 下載圖片到 `~/.hermes/hermes-agent/output/t2i_transient_output.png`
5. 輸出 `MEDIA:{path}` 和 `SIGNAL:DELIVERY_COMPLETE:{path}`
6. **由 Agent 觸發後續清理** (不再自行刪除)

### 2. Agent（協調端）
Agent 收到 Engine 的工具輸出後，職責：
1. 解析 `MEDIA:{path}` 字串
2. 在回覆文字中**包含** `MEDIA:{path}`（不作任何修改或翻譯）
3. Gateway 會自動攔截並處理 `MEDIA:` 標記

**重要**：Agent 必須把 `MEDIA:` 訊號原封不動放進回覆文字裡，這樣 Gateway 才能識別並傳送圖片。如果 Agent 只回「照片已生成」，Telegram 就只會收到文字連結。

### 3. Gateway（發送端）
Gateway 監聽 Agent 的回覆文字，職責：
1. 偵測回覆中的 `MEDIA:{path}` 標記
2. 從硬碟讀取圖片檔案
3. 以原生 Telegram 照片（`send_photo`）發送給用戶
4. 從文字中移除 `MEDIA:` 標記，避免顯示在聊天中

## 交付協定（解耦清理機制）

### 問題背景：Race Condition
原先 Engine 在輸出 `MEDIA:<path>` 後自行 Fork 子進程刪除檔案，導致在某些系統環境下，檔案在 Gateway 讀取前就被刪除，導致使用者僅收到文字而無圖片。

### 解決方案：將生成與刪除解耦
Engine 僅負責生產圖片並輸出路徑，不再包含刪除邏輯。檔案的生命週期由 Agent 協調：
1. **Engine** $\rightarrow$ 生成圖片 $\rightarrow$ 輸出 `MEDIA:path`。
2. **Agent** $\rightarrow$ 截獲路徑 $\rightarrow$ 回覆 `MEDIA:path` $\rightarrow$ 觸發 Gateway 發送。
3. **清理** $\\rightarrow$ Agent 在回覆後，啟動獨立的清理腳本 `python3 ~/.hermes/skills/mlops/comfy_t2i/scripts/t2i_cleanup.py [path] [delay]`，確保發送完成後才清理。

這樣的好處：
- **絕對可靠**：照片在交付完成前絕對不會消失。
- **單一責任**：Engine 只負責生產，Agent 負責生命週期管理。

## 磁碟衛生 (Disk Hygiene)
本技能遵循「**零留存 (Zero-Retention)**」原則：
- **Agent 協調清理**：生成完成並通過 `MEDIA:` 訊號交付後，由 Agent 啟動清理腳本 `t2i_cleanup.py`，確保在 Gateway 上傳完成後清理檔案。
- **單一責任**：Engine 負責生產，Agent 負責生命週期管理。

## 工作流資訊
- **工作流檔案**: `~/.hermes/skills/mlops/comfy_t2i/references/01-Flux2-Klein-T2I.json`
- **正向 Prompt 節點**: Node 107 (`CR Prompt Text`)
- **雜訊種子節點**: Node 93 (`RandomNoise`) - 引擎會自動隨機化此節點之 `noise_seed` 以防止 ComfyUI 快取導致的重複圖片。
- **負向 Prompt 節點**: Node 90 (`CLIPTextEncode Negative Prompt`)

## 執行指令範例
```bash
python3 ~/.hermes/skills/mlops/comfy_t2i/scripts/t2i_engine.py ~/.hermes/skills/mlops/comfy_t2i/references/01-Flux2-Klein-T2I.json "A beautiful sunset over the ocean"
```

## ⚠️ 關鍵陷阱 (Critical Pitfalls)

| 問題 | 原因 | 解決方案 |
|------|------|---------|
| Telegram 僅收到 Raw Log 而無照片 | 使用 `notify_on_complete=true` 會導致系統等待所有子進程（包括延遲刪除進程）結束後才發送通知，此時檔案已被刪除。 | **禁用 `notify_on_complete`**。必須使用 `process(action="poll")` 監控輸出，在偵測到 `MEDIA:` 訊號後立即回覆，確保在 150s 緩衝期內完成交付。 |
| 相同 prompt 生成重複圖片 | ComfyUI 快取機制 | 引擎已實作自動隨機化 Node 93 (`RandomNoise`) 的 `noise_seed`，確保每次生成均為唯一。 |
