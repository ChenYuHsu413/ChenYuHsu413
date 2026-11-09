# tools

`build_a2_assets.py` 會產生 profile README 用的所有自製 SVG（`assets/a2/`）。深色版沒有後綴，淺色版加 `-light`。

## 重新產生

1. 安裝相依套件（建議在 venv 裡）：

   ```bash
   python -m venv .venv && . .venv/bin/activate   # Windows：.venv\Scripts\activate
   pip install fonttools brotli
   ```

2. 準備字型（SIL Open Font License 1.1，來源 <https://github.com/google/fonts>）：

   ```
   <fonts_dir>/spacegrotesk/SpaceGrotesk[wght].ttf
   <fonts_dir>/jetbrainsmono/JetBrainsMono[wght].ttf
   ```

3. 準備圖示（Simple Icons，CC0）：把 `ICON_SLUGS` 列出的每個 `<slug>.svg` 放進 `<icons_dir>`，例如從
   `https://cdn.jsdelivr.net/npm/simple-icons@16.37.0/icons/<slug>.svg` 下載。`css3` 只在舊版有，請改用 `simple-icons@13.21.0`。

4. 執行：

   ```bash
   python tools/build_a2_assets.py <fonts_dir> <icons_dir>
   ```

## 要改什麼就改哪裡

- **配色**：改 `PALETTES`（`dark` / `light`）。每張 SVG 開頭會以 CSS 變數輸出這組配色。文字和背景的對比要維持在 4.5:1 以上。
- **文字內容**：改 `build_all()` 裡的卡片說明、`TECH`、`ABOUT`。這些要和 README 的 `alt` 保持一致。
- **限制**：SVG 只能用 SMIL 或內嵌 CSS 動畫，不能有 JS；嵌入字型的檔案要在 120KB 以內。
- **snake 配色**：在 `.github/workflows/snake.yml`，和 `PALETTES` 是手動同步的。
