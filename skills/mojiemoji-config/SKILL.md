---
name: mojiemoji-config
description: "mojiemoji の<img src="https://mojiemoji.jozo.beer/emoji/%E6%B0%B8%E7%B6%9A?font=tamanegi&amp;color=06b6d4&amp;animation=mozaiku&amp;background=transparent&amp;outline=d406b6&amp;outline_width=2" alt="永続" height="24" align="absmiddle"><img src="https://mojiemoji.jozo.beer/emoji/%E8%A8%AD%E5%AE%9A?font=maru-bold&amp;color=f472b6&amp;animation=mochimochi&amp;background=transparent&amp;outline=b6f472&amp;outline_width=2" alt="設定" height="24" align="absmiddle">（現状は prestamp の intensity のみ）を管理する<img src="https://mojiemoji.jozo.beer/emoji/%E3%82%B9%E3%82%AD%E3%83%AB?font=noto&amp;color=fbbf24&amp;animation=yoko_scroll&amp;background=transparent&amp;outline=06d977&amp;outline_width=2" alt="スキル" height="24" align="absmiddle">。ユーザーが「intensity を normal に固定」「装飾強度を minimal にしておいて」「現在の mojiemoji <img src="https://mojiemoji.jozo.beer/emoji/%E8%A8%AD%E5%AE%9A?font=maru-bold&amp;color=f472b6&amp;animation=mochimochi&amp;background=transparent&amp;outline=b6f472&amp;outline_width=2" alt="設定" height="24" align="absmiddle">を見せて」「intensity <img src="https://mojiemoji.jozo.beer/emoji/%E8%A8%AD%E5%AE%9A?font=maru-bold&amp;color=f472b6&amp;animation=mochimochi&amp;background=transparent&amp;outline=b6f472&amp;outline_width=2" alt="設定" height="24" align="absmiddle">を解除して」などと依頼したときに起動する。"
allowed-tools:
  - Bash(python3 -c *)
  - Bash(python3 skills/mojiemoji-github/scripts/*)
  - Bash(python3 */skills/mojiemoji-github/scripts/*)
  - Bash(cat ~/.config/mojiemoji/config.json*)
  - Bash(cat */mojiemoji/config.json*)
  - Read
---

# Mojiemoji Config

〜/.config/mojiemoji/config.json に prestamp の intensity などを<img src="https://mojiemoji.jozo.beer/emoji/%E4%BF%9D%E5%AD%98?font=akzk&amp;color=10b981&amp;animation=shuchusen&amp;background=transparent&amp;outline=8110b9&amp;outline_width=2" alt="保存" height="24" align="absmiddle">し、毎回 CLI <img src="https://mojiemoji.jozo.beer/emoji/%E3%83%95%E3%83%A9%E3%82%B0?font=maru&amp;color=fbbf24&amp;animation=tate_scroll&amp;background=transparent&amp;outline=06d977&amp;outline_width=2" alt="フラグ" height="24" align="absmiddle">を付けなくても既定<img src="https://mojiemoji.jozo.beer/emoji/%E5%8B%95%E4%BD%9C?font=gothic-bold&amp;color=60a5fa&amp;animation=psycho&amp;background=transparent&amp;outline_width=0" alt="動作" height="24" align="absmiddle">を揃えるための skill です。

## 起動条件

- ユーザーが `/mojiemoji-config` を叩いたとき
- ユーザーが intensity（装飾強度）を<img src="https://mojiemoji.jozo.beer/emoji/%E4%BF%9D%E5%AD%98?font=akzk&amp;color=10b981&amp;animation=shuchusen&amp;background=transparent&amp;outline=8110b9&amp;outline_width=2" alt="保存" height="24" align="absmiddle">・<img src="https://mojiemoji.jozo.beer/emoji/%E7%A2%BA%E8%AA%8D?font=noto&amp;color=fb7185&amp;animation=mochimochi&amp;background=transparent&amp;outline=85fb71&amp;outline_width=2" alt="確認" height="24" align="absmiddle">・解除したいと明示したとき

## なぜ<img src="https://mojiemoji.jozo.beer/emoji/%E5%BF%85%E8%A6%81?font=tamanegi&amp;color=10b981&amp;animation=kage_kaiten&amp;speed=slow&amp;background=transparent&amp;outline=8110b9&amp;outline_width=2" alt="必要" height="24" align="absmiddle">か

`prestamp.py` の `--intensity` を毎回指定するのは手間なので、<img src="https://mojiemoji.jozo.beer/emoji/%E8%A8%AD%E5%AE%9A?font=rampart&amp;color=60a5fa&amp;animation=mabataki&amp;background=transparent&amp;outline=fa60a5&amp;outline_width=2" alt="設定" height="24" align="absmiddle">ファイルに一度書いておけば、CLI 無指定時はその値が使われます（解決順は CLI <img src="https://mojiemoji.jozo.beer/emoji/%E5%84%AA%E5%85%88?font=gothic-bold&amp;color=60a5fa&amp;animation=zairu&amp;background=transparent&amp;outline=eb2563&amp;outline_width=2" alt="優先" height="24" align="absmiddle">）。

## <img src="https://mojiemoji.jozo.beer/emoji/%E8%A8%AD%E5%AE%9A?font=maru&amp;color=60a5fa&amp;animation=yurayura&amp;background=transparent&amp;outline=eb2563&amp;outline_width=2" alt="設定" height="24" align="absmiddle">の<img src="https://mojiemoji.jozo.beer/emoji/%E7%A2%BA%E8%AA%8D?font=toge&amp;color=f59e0b&amp;animation=zanzo&amp;background=transparent&amp;outline=0bf59e&amp;outline_width=2" alt="確認" height="24" align="absmiddle">

```bash
python3 -c "import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github/scripts'); from lib.config import get_intensity, get_config_path; print(f'config={get_config_path()}'); print(f'intensity={get_intensity() or \"(unset, default aggressive)\"}')"
```

## intensity の<img src="https://mojiemoji.jozo.beer/emoji/%E5%A4%89%E6%9B%B4?font=hachimaru&amp;color=eab308&amp;animation=yokomoya&amp;background=transparent&amp;outline=08eab3&amp;outline_width=2" alt="変更" height="24" align="absmiddle">

`aggressive` / `normal` / `minimal` のいずれかを<img src="https://mojiemoji.jozo.beer/emoji/%E4%BF%9D%E5%AD%98?font=akzk&amp;color=10b981&amp;animation=shuchusen&amp;background=transparent&amp;outline=8110b9&amp;outline_width=2" alt="保存" height="24" align="absmiddle">します。

```bash
python3 -c "import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github/scripts'); from lib.config import set_intensity; set_intensity('normal')"
```

```bash
python3 -c "import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github/scripts'); from lib.config import set_intensity; set_intensity('minimal')"
```

```bash
python3 -c "import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github/scripts'); from lib.config import set_intensity; set_intensity('aggressive')"
```

## intensity の unset

```bash
python3 -c "import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github/scripts'); from lib.config import unset_intensity; unset_intensity()"
```

## config ファイルの場所

XDG <img src="https://mojiemoji.jozo.beer/emoji/%E6%BA%96%E6%8B%A0?font=zero&amp;color=fb923c&amp;animation=neruneru&amp;background=transparent&amp;outline=0cea58&amp;outline_width=2" alt="準拠" height="24" align="absmiddle">で、`XDG_CONFIG_HOME` があれば `<XDG_CONFIG_HOME>/mojiemoji/config.json`、なければ `~/.config/mojiemoji/config.json` です。

## <img src="https://mojiemoji.jozo.beer/emoji/%E5%84%AA%E5%85%88?font=gothic-bold&amp;color=60a5fa&amp;animation=zairu&amp;background=transparent&amp;outline=eb2563&amp;outline_width=2" alt="優先" height="24" align="absmiddle">順位

CLI の `--intensity` が最<img src="https://mojiemoji.jozo.beer/emoji/%E5%84%AA%E5%85%88?font=pixel&amp;color=f472b6&amp;animation=zanzo&amp;background=transparent&amp;outline=b6f472&amp;outline_width=2" alt="優先" height="24" align="absmiddle">。無指定なら<img src="https://mojiemoji.jozo.beer/emoji/%E8%A8%AD%E5%AE%9A?font=maru-bold&amp;color=f472b6&amp;animation=mochimochi&amp;background=transparent&amp;outline=b6f472&amp;outline_width=2" alt="設定" height="24" align="absmiddle">ファイルの値。どちらも無ければ従来どおり `aggressive`（sentinel 無しの従来互換<img src="https://mojiemoji.jozo.beer/emoji/%E5%87%BA%E5%8A%9B?font=tamanegi&amp;color=22c55e&amp;animation=kage_bokashi&amp;background=transparent&amp;outline=5e22c5&amp;outline_width=2" alt="出力" height="24" align="absmiddle">）。

## <img src="https://mojiemoji.jozo.beer/emoji/%E9%96%A2%E9%80%A3?font=noto&amp;color=f87171&amp;animation=nami&amp;background=transparent&amp;outline=26dc26&amp;outline_width=2" alt="関連" height="24" align="absmiddle">

- #125 — 本 skill と<img src="https://mojiemoji.jozo.beer/emoji/%E8%A8%AD%E5%AE%9A?font=maru-bold&amp;color=f472b6&amp;animation=mochimochi&amp;background=transparent&amp;outline=b6f472&amp;outline_width=2" alt="設定" height="24" align="absmiddle">レイヤの<img src="https://mojiemoji.jozo.beer/emoji/%E5%AE%9F%E8%A3%85?font=toge&amp;color=fb7185&amp;animation=tate_ekken&amp;background=transparent&amp;outline=85fb71&amp;outline_width=2" alt="実装" height="24" align="absmiddle">
