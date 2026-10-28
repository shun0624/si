# マンガ制作セット（ComfyUI）をまとめて入れるスクリプト
# setup.bat から呼び出す。何度実行しても大丈夫（入っているものは飛ばす）。

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# ---- 設定（必要ならここだけ変える） ----
$InstallRoot = "C:\AI"                      # ComfyUI を置く場所（何も入力しなかったとき）
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Log = Join-Path $Here "install_log.txt"

$Models = @(
    @{ Name = "WAI-Illustrious（メインのモデル）"; Dir = "checkpoints"; File = "waiIllustriousSDXL_v170.safetensors"; Size = 6938040682
       Url = "https://huggingface.co/LyliaEngine/waiIllustriousSDXL_v170/resolve/main/waiIllustriousSDXL_v170.safetensors" },
    @{ Name = "ControlNet 落書き（ラフ用）"; Dir = "controlnet"; File = "noob_sdxl_scribble_fp16.safetensors"; Size = 2502139136
       Url = "https://huggingface.co/Eugeoter/noob-sdxl-controlnet-scribble_pidinet/resolve/main/diffusion_pytorch_model.fp16.safetensors" },
    @{ Name = "ControlNet 線画"; Dir = "controlnet"; File = "noob_sdxl_lineart_anime_fp16.safetensors"; Size = 2502139136
       Url = "https://huggingface.co/Eugeoter/noob-sdxl-controlnet-lineart_anime/resolve/main/diffusion_pytorch_model.fp16.safetensors" },
    @{ Name = "ControlNet 奥行き（写真の構図用）"; Dir = "controlnet"; File = "noob_sdxl_depth_midas_fp16.safetensors"; Size = 2502139136
       Url = "https://huggingface.co/Eugeoter/noob-sdxl-controlnet-depth_midas-v1-1/resolve/main/diffusion_pytorch_model.fp16.safetensors" },
    @{ Name = "ControlNet 骨格（ポーズ用）"; Dir = "controlnet"; File = "noob_sdxl_openpose_fp16.safetensors"; Size = 2502139136
       Url = "https://huggingface.co/r3gm/controlnet-noobai-openpose-sdxl-fp16/resolve/main/diffusion_pytorch_model.fp16.safetensors" },
    @{ Name = "顔の自動検出（顔の描き直し用）"; Dir = "ultralytics\bbox"; File = "face_yolov8m.pt"; Size = 52026019
       Url = "https://huggingface.co/Bingsu/adetailer/resolve/main/face_yolov8m.pt" }
)

$MossModels = @(
    @{ Name = "MOSS-Image 本体"; Dir = "diffusion_models"; File = "moss_image_sft_int8_convrot.safetensors"; Size = 5413698958
       Url = "https://huggingface.co/Comfy-Org/MOSS-Image/resolve/main/diffusion_models/moss_image_sft_int8_convrot.safetensors" },
    @{ Name = "MOSS-Image 文章読み取り部分"; Dir = "text_encoders"; File = "qwen3.5_9b_int8_convrot.safetensors"; Size = 9748121532
       Url = "https://huggingface.co/Comfy-Org/MOSS-Image/resolve/main/text_encoders/qwen3.5_9b_int8_convrot.safetensors" },
    @{ Name = "MOSS-Image 8ステップ高速化"; Dir = "loras"; File = "moss_image_sft_8step_dmd.safetensors"; Size = 1189176800
       Url = "https://huggingface.co/lodestones/MOSS-Image-SFT-8-steps-dmd/resolve/main/lora.safetensors" },
    @{ Name = "マンガ透明素材LoRA"; Dir = "loras"; File = "moss_manga_alpha_image_lora.safetensors"; Size = 132162296
       Url = "https://huggingface.co/paralaif/MOSS-Manga-Alpha-Image-LoRA/resolve/main/moss_manga_alpha_image_lora.safetensors" },
    @{ Name = "透明対応VAE"; Dir = "vae"; File = "flux2_klein_alpha_rgba_vae.safetensors"; Size = 336222776
       Url = "https://huggingface.co/paralaif/MOSS-Manga-Alpha-Image-LoRA/resolve/main/vae/flux2_klein_alpha_rgba_vae.safetensors" }
)

$Nodes = @(
    @{ Name = "comfyui_controlnet_aux（ラフ・写真から線や骨格を取り出す）"; Url = "https://github.com/Fannovel16/comfyui_controlnet_aux" },
    @{ Name = "ComfyUI-Impact-Pack（顔の描き直し）"; Url = "https://github.com/ltdrdata/ComfyUI-Impact-Pack" },
    @{ Name = "ComfyUI-Impact-Subpack（顔の自動検出）"; Url = "https://github.com/ltdrdata/ComfyUI-Impact-Subpack" },
    @{ Name = "ComfyUI-MangaScreen（トーン処理）"; Url = "https://github.com/ashukae/ComfyUI-MangaScreen" }
)

# ---- 表示用 ----
function Step($t) { Write-Host ""; Write-Host "■ $t" -ForegroundColor Cyan }
function Ok($t) { Write-Host "  OK  $t" -ForegroundColor Green }
function Warn($t) { Write-Host "  注意 $t" -ForegroundColor Yellow; $script:Warnings += $t }
$script:Warnings = @()

function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
}

function Install-Tool($Command, $WingetId, $Label) {
    if (Get-Command $Command -ErrorAction SilentlyContinue) { Ok "$Label は入っています"; return $true }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Warn "$Label を自動で入れられません（winget がありません）。Microsoft Store で「アプリ インストーラー」を更新してから、もう一度実行してください。"
        return $false
    }
    Write-Host "  $Label を入れています…（確認画面が出たら「はい」）"
    & winget install -e --id $WingetId --accept-source-agreements --accept-package-agreements --silent | Out-Host
    Refresh-Path
    if (Get-Command $Command -ErrorAction SilentlyContinue) { Ok "$Label を入れました"; return $true }
    Warn "$Label のインストールに失敗しました。"
    return $false
}

function Get-File($Url, $Dest, [int64]$Size, $Label) {
    if ((Test-Path $Dest) -and ($Size -eq 0 -or (Get-Item $Dest).Length -eq $Size)) {
        Ok "$Label（ダウンロード済み）"; return $true
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Dest) | Out-Null
    $part = "$Dest.part"
    $sizeText = ""
    if ($Size -gt 100MB) { $sizeText = "（約 $([math]::Round($Size / 1GB, 1)) GB）" }
    Write-Host "  ダウンロード中: $Label$sizeText"
    # 途中で止まっても、もう一度実行すると続きから再開する
    & curl.exe -L --fail --retry 5 --retry-delay 5 -C - -o $part $Url
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $part)) {
        Warn "$Label のダウンロードに失敗しました（もう一度 setup.bat を実行すると続きから再開します）"
        return $false
    }
    if ($Size -ne 0 -and (Get-Item $part).Length -ne $Size) {
        Remove-Item $part
        Warn "$Label の大きさが合いません（もう一度 setup.bat を実行してください）"
        return $false
    }
    Move-Item -Force $part $Dest
    Ok $Label
    return $true
}

function Pip-Install($Py, $Req) {
    if (Test-Path $Req) {
        & $Py -s -m pip install -q -r $Req | Out-Host
        if ($LASTEXITCODE -ne 0) { Warn "追加部品の準備に失敗: $Req" }
    }
}

function New-Shortcut($Name, $Target, $WorkDir) {
    $desktop = [Environment]::GetFolderPath("Desktop")
    $sh = New-Object -ComObject WScript.Shell
    $lnk = $sh.CreateShortcut((Join-Path $desktop "$Name.lnk"))
    $lnk.TargetPath = $Target
    $lnk.WorkingDirectory = $WorkDir
    $lnk.Save()
}

# ================================================================
Start-Transcript -Path $Log -Append | Out-Null
Write-Host "マンガ制作セットのインストールを始めます。" -ForegroundColor Cyan
Write-Host "全部で 25GB ほどダウンロードします。回線によっては1〜2時間かかります。"

# ---- インストール先を決める ----
# 前回入れた場所があれば、それを最初の候補にする
$locFile = Join-Path $Here "comfyui_location.txt"
if (Test-Path $locFile) {
    $prev = "$(Get-Content $locFile -Encoding Default | Select-Object -First 1)".Trim()
    if ($prev) { $InstallRoot = $prev }
}
while ($true) {
    $ans = "$(Read-Host "ComfyUI を入れるフォルダ（そのまま Enter で $InstallRoot）")".Trim().Trim('"')
    $root = $InstallRoot
    if ($ans) { $root = $ans }
    if ($root -notmatch '^[A-Za-z]:\\') {
        Write-Host "  「D:\AI」のように、ドライブ名から入力してください。" -ForegroundColor Yellow
        continue
    }
    if (-not (Test-Path $root.Substring(0, 3))) {
        Write-Host "  $($root.Substring(0, 2)) ドライブが見つかりません。" -ForegroundColor Yellow
        continue
    }
    if ($root.Length -gt 3) { $root = $root.TrimEnd("\") }
    # すでにある ComfyUI のフォルダ（python_embeded がある所）を指定されたら、それをそのまま使う
    $Portable = Join-Path $root "ComfyUI_windows_portable"
    if (Test-Path (Join-Path $root "python_embeded\python.exe")) {
        $Portable = $root
        $root = Split-Path -Parent $root
    }
    if ($root -match '[^\x21-\x7E]') {
        $yes = Read-Host "  日本語や空白が入った場所だと、一部の部品が動かないことがあります。このまま進めますか？[y/N]"
        if ($yes -notmatch "^[yYｙＹ]") { continue }
    }
    $InstallRoot = $root
    break
}
Ok "インストール先: $Portable"

$withMoss = (Read-Host "透明素材用の MOSS-Image も入れますか？（さらに約17GB）[y/N]") -match "^[yYｙＹ]"

# ---- 1. 事前チェック ----
Step "1/7 パソコンの確認"
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    $gpu = (& nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader) -join " / "
    Ok "グラフィックボード: $gpu"
} else {
    Warn "NVIDIA のドライバーが見つかりません。NVIDIA のサイトから最新のドライバーを入れてください（RTX 50シリーズは新しいドライバーが必要です）。"
}
$drive = (Split-Path -Qualifier $InstallRoot).TrimEnd(":")
$free = [math]::Round((Get-PSDrive $drive).Free / 1GB)
# まだ入っていない分だけ空きが必要（ComfyUI 本体と部品で約10GB＋余裕5GB）
$need = 5
if (-not (Test-Path (Join-Path $Portable "python_embeded\python.exe"))) { $need += 10 }
$check = $Models
if ($withMoss) { $check = $Models + $MossModels }
foreach ($m in $check) {
    if (-not (Test-Path (Join-Path $Portable "ComfyUI\models\$($m.Dir)\$($m.File)"))) { $need += [math]::Ceiling($m.Size / 1GB) }
}
if ($free -lt $need) {
    Warn "$drive ドライブの空きが $free GB しかありません（$need GB 以上必要）。空きを作るか、もう一度 setup.bat を実行して別のドライブを指定してください。"
    Stop-Transcript | Out-Null
    exit 1
}
Ok "$drive ドライブの空き: $free GB"

# ---- 2. 必要な道具 ----
Step "2/7 必要な道具（Git・7-Zip）"
$hasGit = Install-Tool "git" "Git.Git" "Git"
$sevenZip = "C:\Program Files\7-Zip\7z.exe"
$cmd = Get-Command 7z -ErrorAction SilentlyContinue
if (-not (Test-Path $sevenZip) -and $cmd) { $sevenZip = $cmd.Source }
if ((-not (Test-Path $sevenZip)) -and (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "  7-Zip を入れています…（確認画面が出たら「はい」）"
    & winget install -e --id 7zip.7zip --accept-source-agreements --accept-package-agreements --silent | Out-Host
}
if (Test-Path $sevenZip) { Ok "7-Zip は入っています" }

# ---- 3. ComfyUI 本体 ----
Step "3/7 ComfyUI 本体"
$Py = Join-Path $Portable "python_embeded\python.exe"
$Comfy = Join-Path $Portable "ComfyUI"
if (Test-Path $Py) {
    Ok "ComfyUI は入っています（$Portable）"
} else {
    if (-not (Test-Path $sevenZip)) {
        Warn "7-Zip がないため ComfyUI を展開できません。7-Zip を入れてから、もう一度実行してください。"
        Stop-Transcript | Out-Null
        exit 1
    }
    New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
    $url = "https://github.com/comfyanonymous/ComfyUI/releases/latest/download/ComfyUI_windows_portable_nvidia.7z"
    try {
        $rel = Invoke-RestMethod "https://api.github.com/repos/comfyanonymous/ComfyUI/releases/latest" -Headers @{ "User-Agent" = "manga-setup" }
        $asset = $rel.assets | Where-Object { $_.name -eq "ComfyUI_windows_portable_nvidia.7z" } | Select-Object -First 1
        if (-not $asset) {
            $asset = $rel.assets | Where-Object { $_.name -like "ComfyUI_windows_portable_nvidia*.7z" } | Select-Object -First 1
        }
        if ($asset) { $url = $asset.browser_download_url; Write-Host "  最新版: $($rel.tag_name)" }
    } catch { Write-Host "  最新版の確認に失敗したので、標準の場所から取得します" }
    $archive = Join-Path $InstallRoot "ComfyUI_windows_portable_nvidia.7z"
    if (-not (Get-File $url $archive 0 "ComfyUI 本体（約2GB）")) { Stop-Transcript | Out-Null; exit 1 }
    Write-Host "  展開しています…"
    & $sevenZip x $archive "-o$InstallRoot" -y | Out-Null
    if (-not (Test-Path $Py)) { Warn "ComfyUI の展開に失敗しました。"; Stop-Transcript | Out-Null; exit 1 }
    Remove-Item $archive
    Ok "ComfyUI を入れました（$Portable）"
}

# 起動用ファイル（マネージャー機能付き）
$runBat = Join-Path $Portable "run_manga.bat"
@(
    "@echo off",
    "cd /d `"%~dp0`"",
    ".\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build --enable-manager",
    "pause"
) | Set-Content -Path $runBat -Encoding ASCII
Pip-Install $Py (Join-Path $Comfy "manager_requirements.txt")
Ok "起動用ファイル run_manga.bat を作りました"

# ---- 4. 追加の部品（カスタムノード） ----
Step "4/7 追加の部品（カスタムノード）"
$customDir = Join-Path $Comfy "custom_nodes"
foreach ($n in $Nodes) {
    $dest = Join-Path $customDir ([IO.Path]::GetFileName($n.Url))
    if (-not (Test-Path $dest)) {
        if ($hasGit) {
            & git clone --depth 1 -q $n.Url $dest
        } else {
            $zip = "$dest.zip"
            & curl.exe -L --fail -o $zip "$($n.Url)/archive/refs/heads/main.zip"
            if ($LASTEXITCODE -eq 0) {
                Expand-Archive $zip $customDir -Force
                Rename-Item (Join-Path $customDir "$([IO.Path]::GetFileName($n.Url))-main") $dest
                Remove-Item $zip
            }
        }
    }
    if (Test-Path $dest) {
        Pip-Install $Py (Join-Path $dest "requirements.txt")
        Ok $n.Name
    } else {
        Warn "$($n.Name) を入れられませんでした"
    }
}

# ---- 5. モデル ----
Step "5/7 モデルのダウンロード"
$all = $Models
if ($withMoss) { $all = $Models + $MossModels }
foreach ($m in $all) {
    Get-File $m.Url (Join-Path $Comfy "models\$($m.Dir)\$($m.File)") $m.Size $m.Name | Out-Null
}
if ($withMoss) {
    $rgba = Join-Path $customDir "ComfyUI-RGBA-VAE"
    $base = "https://huggingface.co/paralaif/MOSS-Manga-Alpha-Image-LoRA/resolve/main/comfyui"
    Get-File "$base/ComfyUI-RGBA-VAE/__init__.py" (Join-Path $rgba "__init__.py") 0 "透明対応VAEの読み込み部品" | Out-Null
}

# ---- 6. ワークフロー（設定ファイル） ----
Step "6/7 ワークフローを登録"
$wfDir = Join-Path $Comfy "user\default\workflows"
New-Item -ItemType Directory -Force -Path $wfDir | Out-Null
Copy-Item (Join-Path $Here "workflows\*.json") $wfDir -Force
$lite = Join-Path $customDir "ComfyUI-MangaScreen\workflows\Manga-Lite.json"
if (Test-Path $lite) { Copy-Item $lite (Join-Path $wfDir "トーン処理（MangaScreen-Lite）.json") -Force }
if ($withMoss) {
    Get-File "https://huggingface.co/paralaif/MOSS-Manga-Alpha-Image-LoRA/resolve/main/comfyui/moss-manga-alpha-image-t2i.json" `
        (Join-Path $wfDir "透明素材（MOSS マンガ）.json") 0 "透明素材のワークフロー" | Out-Null
}
Ok "ComfyUI の左側の「ワークフロー」一覧に出ます"

# ---- 7. コマ切り出しツールの準備 ----
Step "7/7 コマ切り出し・はめ込みツール"
# 日本語のフォルダ名でもバッチファイルが読めるよう、ANSI（Shift-JIS）で保存する
Set-Content -Path (Join-Path $Here "comfyui_location.txt") -Value $Portable -Encoding Default
& $Py -s (Join-Path $Here "scripts\split_panels.py") (Join-Path $Here "sample\p1.png") --comfy $Portable | Out-Host
New-Shortcut "ComfyUI（マンガ）" $runBat $Portable
New-Shortcut "コマ切り出し" (Join-Path $Here "split_panels.bat") $Here
New-Shortcut "コマはめ込み" (Join-Path $Here "assemble_page.bat") $Here
Ok "デスクトップにショートカットを3つ作りました"

# ---- 結果 ----
Write-Host ""
if ($script:Warnings.Count -eq 0) {
    Write-Host "すべて完了しました。" -ForegroundColor Green
} else {
    Write-Host "完了しましたが、次の注意があります（もう一度 setup.bat を実行すると、残りだけやり直します）:" -ForegroundColor Yellow
    $script:Warnings | ForEach-Object { Write-Host "  ・$_" -ForegroundColor Yellow }
}
Write-Host "デスクトップの「ComfyUI（マンガ）」をダブルクリックすると起動します。"
Write-Host "記録: $Log"
Stop-Transcript | Out-Null
