"""ComfyUI のワークフロー（manga/workflows/*.json）を作る。

python manga/scripts/make_workflow.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "workflows"

CHECKPOINT = "waiIllustriousSDXL_v170.safetensors"
CN_SCRIBBLE = "noob_sdxl_scribble_fp16.safetensors"
POSITIVE = ("masterpiece, best quality, amazing quality, monochrome, greyscale, manga, "
            "lineart, screentone, 1girl, solo, short black hair, school uniform, "
            "surprised, looking back, classroom")
NEGATIVE = ("bad quality, worst quality, worst detail, lowres, bad anatomy, bad hands, "
            "censor, signature, watermark, username, text, speech bubble, frame, border, "
            "color")
BYPASS = 4  # ComfyUI のノードを「バイパス（一時的に無効）」にする設定値


class Graph:
    def __init__(self):
        self.nodes, self.links, self.groups = [], [], []

    def node(self, type_, pos, size, widgets=None, inputs=(), outputs=(), title=None,
             mode=0, color=None):
        n = {
            "id": len(self.nodes) + 1, "type": type_, "pos": list(pos), "size": list(size),
            "flags": {}, "order": len(self.nodes), "mode": mode,
            "inputs": [{"name": name, "type": t, "link": None} for name, t in inputs],
            "outputs": [{"name": name, "type": t, "links": [], "slot_index": i}
                        for i, (name, t) in enumerate(outputs)],
            "properties": {"Node name for S&R": type_},
            "widgets_values": widgets or [],
        }
        if title:
            n["title"] = title
        if color:
            n["color"], n["bgcolor"] = color
        self.nodes.append(n)
        return n

    def link(self, src, out_slot, dst, in_name):
        link_id = len(self.links) + 1
        t = src["outputs"][out_slot]["type"]
        slot = next(i for i, x in enumerate(dst["inputs"]) if x["name"] == in_name)
        dst["inputs"][slot]["link"] = link_id
        src["outputs"][out_slot]["links"].append(link_id)
        self.links.append([link_id, src["id"], out_slot, dst["id"], slot, t])

    def group(self, title, x, y, w, h, color):
        self.groups.append({"title": title, "bounding": [x, y, w, h], "color": color,
                            "font_size": 24, "flags": {}})

    def note(self, text, pos, size):
        return self.node("Note", pos, size, widgets=[text], color=("#432", "#653"))

    def dump(self, path):
        data = {
            "last_node_id": len(self.nodes), "last_link_id": len(self.links),
            "nodes": self.nodes, "links": self.links, "groups": self.groups,
            "config": {}, "extra": {"ds": {"scale": 0.65, "offset": [40, 60]}},
            "version": 0.4,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def panel_workflow():
    g = Graph()
    green = ("#232", "#353")

    g.note(
        "【コマのラフ → キャラで描く】\n"
        "1. 左の「コマのラフ」で、コマ切り出しツールが作った画像（p1_c01.png など）を選ぶ\n"
        "2. 「指示文」をコマ表からコピーして貼る\n"
        "3. 出したいキャラのLoRAをオンにする（ノードを選んで Ctrl+B で切替）\n"
        "4. 「保存名」をコマの番号に合わせる（例: manga/p1_c03）\n"
        "5. 右上の「Run（実行）」→ 候補が4枚 ComfyUI/output/manga に保存される\n"
        "6. 気に入った1枚を「〇〇_コマ/採用」フォルダにコピー\n\n"
        "■ ラフに似せたい → 「ラフの効き具合」の strength を上げる（0.8 くらいまで）\n"
        "■ キャラの顔が崩れる → end_percent を下げる（0.5〜0.6）\n"
        "■ ラフをそのまま下絵にしたい → 「描く」の denoise を 0.6〜0.7 に下げる",
        (20, 20), (560, 330))

    ckpt = g.node("CheckpointLoaderSimple", (20, 400), (380, 100), [CHECKPOINT],
                  outputs=[("MODEL", "MODEL"), ("CLIP", "CLIP"), ("VAE", "VAE")],
                  title="モデル（WAI-Illustrious）")
    lora_a = g.node("LoraLoader", (20, 560), (380, 130), ["キャラA.safetensors", 0.9, 0.9],
                    inputs=[("model", "MODEL"), ("clip", "CLIP")],
                    outputs=[("MODEL", "MODEL"), ("CLIP", "CLIP")],
                    title="キャラA の LoRA（Ctrl+B でオン/オフ）", mode=BYPASS)
    lora_b = g.node("LoraLoader", (20, 740), (380, 130), ["キャラB.safetensors", 0.9, 0.9],
                    inputs=[("model", "MODEL"), ("clip", "CLIP")],
                    outputs=[("MODEL", "MODEL"), ("CLIP", "CLIP")],
                    title="キャラB の LoRA（2人のコマは両方 0.5 に）", mode=BYPASS)
    g.link(ckpt, 0, lora_a, "model")
    g.link(ckpt, 1, lora_a, "clip")
    g.link(lora_a, 0, lora_b, "model")
    g.link(lora_a, 1, lora_b, "clip")
    g.group("① モデルとキャラ", 0, 360, 420, 530, "#3f789e")

    pos = g.node("CLIPTextEncode", (450, 400), (420, 200), [POSITIVE],
                 inputs=[("clip", "CLIP")], outputs=[("CONDITIONING", "CONDITIONING")],
                 title="指示文（コマ表からコピー）", color=green)
    neg = g.node("CLIPTextEncode", (450, 640), (420, 160), [NEGATIVE],
                 inputs=[("clip", "CLIP")], outputs=[("CONDITIONING", "CONDITIONING")],
                 title="描かせないもの（ふだんは変えない）", color=("#322", "#533"))
    g.link(lora_b, 1, pos, "clip")
    g.link(lora_b, 1, neg, "clip")
    g.group("② 指示文", 430, 360, 460, 460, "#88a")

    load = g.node("LoadImage", (20, 960), (380, 420), ["p1_c01.png", "image"],
                  outputs=[("IMAGE", "IMAGE"), ("MASK", "MASK")], title="コマのラフ")
    scale = g.node("ImageScaleToTotalPixels", (450, 960), (320, 110), ["lanczos", 1.0, 64],
                   inputs=[("image", "IMAGE")], outputs=[("IMAGE", "IMAGE")],
                   title="大きさをそろえる（約100万画素）")
    invert = g.node("ImageInvert", (450, 1110), (320, 50),
                    inputs=[("image", "IMAGE")], outputs=[("IMAGE", "IMAGE")],
                    title="白黒反転（ControlNet用）")
    preview = g.node("PreviewImage", (450, 1200), (320, 260),
                     inputs=[("images", "IMAGE")], title="AIに見せているラフ")
    g.link(load, 0, scale, "image")
    g.link(scale, 0, invert, "image")
    g.link(invert, 0, preview, "images")
    g.group("③ コマのラフ", 0, 920, 790, 560, "#a1309b")

    cn = g.node("ControlNetLoader", (920, 400), (380, 60), [CN_SCRIBBLE],
                outputs=[("CONTROL_NET", "CONTROL_NET")], title="ControlNet（落書き用）")
    apply = g.node("ControlNetApplyAdvanced", (920, 500), (380, 190), [0.6, 0.0, 0.7],
                   inputs=[("positive", "CONDITIONING"), ("negative", "CONDITIONING"),
                           ("control_net", "CONTROL_NET"), ("image", "IMAGE"), ("vae", "VAE")],
                   outputs=[("positive", "CONDITIONING"), ("negative", "CONDITIONING")],
                   title="ラフの効き具合")
    g.link(pos, 0, apply, "positive")
    g.link(neg, 0, apply, "negative")
    g.link(cn, 0, apply, "control_net")
    g.link(invert, 0, apply, "image")
    g.link(ckpt, 2, apply, "vae")

    enc = g.node("VAEEncode", (920, 740), (220, 50),
                 inputs=[("pixels", "IMAGE"), ("vae", "VAE")], outputs=[("LATENT", "LATENT")])
    rep = g.node("RepeatLatentBatch", (1160, 740), (220, 60), [4],
                 inputs=[("samples", "LATENT")], outputs=[("LATENT", "LATENT")],
                 title="候補の枚数")
    g.link(scale, 0, enc, "pixels")
    g.link(ckpt, 2, enc, "vae")
    g.link(enc, 0, rep, "samples")

    ks = g.node("KSampler", (1340, 400), (320, 270),
                [0, "randomize", 28, 5.5, "euler_ancestral", "normal", 1.0],
                inputs=[("model", "MODEL"), ("positive", "CONDITIONING"),
                        ("negative", "CONDITIONING"), ("latent_image", "LATENT")],
                outputs=[("LATENT", "LATENT")], title="描く")
    g.link(lora_b, 0, ks, "model")
    g.link(apply, 0, ks, "positive")
    g.link(apply, 1, ks, "negative")
    g.link(rep, 0, ks, "latent_image")

    dec = g.node("VAEDecode", (1340, 720), (220, 50),
                 inputs=[("samples", "LATENT"), ("vae", "VAE")], outputs=[("IMAGE", "IMAGE")])
    save = g.node("SaveImage", (1700, 400), (560, 620), ["manga/p1_c01"],
                  inputs=[("images", "IMAGE")], title="保存名（コマの番号に合わせる）")
    g.link(ks, 0, dec, "samples")
    g.link(ckpt, 2, dec, "vae")
    g.link(dec, 0, save, "images")
    g.group("④ 描いて保存", 900, 360, 1380, 680, "#b58b2a")

    g.dump(OUT / "コマのラフからキャラを描く.json")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    panel_workflow()
    print("OK")
