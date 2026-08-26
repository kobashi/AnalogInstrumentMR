# V6 texture tooling

`build_v6_material_atlases.py` は3テーマ × 3 density classのPBR atlasを
master sourceから生成する。Blenderは使わず、**numpyとPillow**を要求する。

## 環境

system pythonにもBlender同梱pythonにもPillowが無い。Blender 5.2の同梱python
（numpy同梱済み）からrepo-localのvenvを作り、Pillowだけ足す。

```bash
"/Applications/Blender 5.2.app/Contents/Resources/5.2/python/bin/python3.13" \
  -m venv --system-site-packages .venv-textures
.venv-textures/bin/python -m pip install -r Tools/Textures/requirements.txt
```

`.venv-textures/` は `.gitignore` 済み。`--system-site-packages` によりnumpyは
Blenderのものをそのまま使うので、Blender側とバージョンがずれない。
texture authoring専用のlocal dependencyであり、Unityのruntime/build依存では
ない（`docs/OPUS5_CODEX_ALIGNMENT.md` §5.5）。

## 回帰ゲート

builderのdefaultは出荷済みatlasを再現しなければならない。変更したら必ず走らせる。

```bash
.venv-textures/bin/python Tools/Textures/verify_v6_atlas_equivalence.py --project-root "$PWD"
```

45枚を一時ディレクトリへ再生成して出荷済みPNGとピクセル比較し、差があれば
non-zeroで終了する。本番pathへは書かない。現状は45枚中43枚がbyte一致、
2枚がPNGエンコード差のみでpixel一致。

## 本番atlasの再生成

```bash
.venv-textures/bin/python Tools/Textures/build_v6_material_atlases.py --project-root "$PWD"
```

`--output-dir` を省略すると
`Assets/MatsuMotoMeterAR/Content/Themes/<Theme>/Textures/ThemeMaterialV6/`
へ**直接書き込む**。実験時は必ず `--output-dir` を付ける。

## 採択済みprofile

Standard classのKineticSafety atlasは、Quest 3の実機比較で **profile B** を採択した
（2026-08-10、`docs/OPUS5_CODEX_ALIGNMENT.md` §18.3）。
採択値は repeats `body=16, metal=21, gasket=16`、tuningはdefault。

```bash
.venv-textures/bin/python Tools/Textures/build_v6_material_atlases.py \
  --project-root "$PWD" \
  --output-dir ArtSource/Blender/BrushUp/Opus5/KineticSafety/textures/Adopted_Standard_B \
  --theme KineticSafety --scale-class Standard --adopted
```

Large classは§33.3で現行1K profileを維持すると決定したため、次で採択値
`body=8, metal=12, gasket=7`を再現できる。

```bash
.venv-textures/bin/python Tools/Textures/build_v6_material_atlases.py \
  --project-root "$PWD" \
  --output-dir ArtSource/Blender/BrushUp/Opus5/KineticSafety/textures/Adopted_Large_1K \
  --theme KineticSafety --scale-class Large --adopted
```

Medium classは§43でFineとの差を1 mのQuest表示で判別できず、現行profileを維持すると
決定した。次で採択値`body=5, metal=8, gasket=5`を再現できる。

```bash
.venv-textures/bin/python Tools/Textures/build_v6_material_atlases.py \
  --project-root "$PWD" \
  --output-dir ArtSource/Blender/BrushUp/Opus5/KineticSafety/textures/Adopted_Medium_Control \
  --theme KineticSafety --scale-class Medium --adopted
```

`--adopted` は `ADOPTED_REPEATS` の値を使う。Questで採択したprofileを丸ごと再現する
契約なので、repeat数だけでなく**swatch tuningもdefaultに固定**する。次はすべて拒否する。

| 入力 | 理由 |
| --- | --- |
| `--output-dir` 省略 | 既定の出力先はactive Unity texture path。stop gate中にproductionを誤更新できる |
| `--repeats` との併用 | 採択値と衝突する |
| tuning引数の明示指定 | 値がdefaultと同じでも拒否する。`--adopted` はtuningも固定するため |
| `--scale-class` が0個または2個以上 | 採択値はclass単位で1つずつ指定する |

tuning引数（`--*-radius-tiles`、`--*-gain-scale`）のdefaultは `None` で、
「未指定」と「defaultと同じ値の明示指定」を区別できるようにしてある。
通常profileでは `None` を `DEFAULT_TUNING` の値へ解決する。

**Standardの採択値はまだ `DETAIL_PROFILES` のdefaultではない。** defaultを差し替えることは
出荷textureの更新と同じ変更であり、まだgateされている。差し替えると
`verify_v6_atlas_equivalence.py` は設計上失敗する（3/5/3で作られた出荷済みsheetと
比較しているため）。本番texture更新が承認された時点で、`DETAIL_PROFILES` の変更と
gateのre-baselineを同じcommitで行うこと。

Large classは1K/2KをQuestで比較し、**1Kの現行profile（repeats 8/12/7、150 tx/m）を
維持**する決定になった（2026-08-10、§33.3）。2 mでは2Kの追加解像度も3倍細かい粒も
判別できず、sourceが1254 pxでupsampleを含むため。再検討はnative 2K以上のsourceを
用意できた場合に限る。したがってLargeは `DETAIL_PROFILES` の既定値がそのまま採択値。

Medium classもControl / FineをQuestで比較し、**現行profile（repeats 5/8/5、520 tx/m）を
維持**する決定になった（2026-08-10、§43）。1 mで見た目の差を感じず、固定画像を並べないと
細部差を判別できない一方、どちらにもちらつきはなかった。したがってMediumも
`DETAIL_PROFILES`の既定値がそのまま採択値。

## 候補atlas

`--output-dir <DIR>` は `<DIR>/<Theme>/` へ出力する。

```bash
.venv-textures/bin/python Tools/Textures/build_v6_material_atlases.py \
  --project-root "$PWD" \
  --output-dir ArtSource/Blender/BrushUp/Opus5/KineticSafety/textures/RepeatsBT \
  --theme KineticSafety --scale-class Standard \
  --repeats body=16,metal=21,gasket=16 \
  --high-pass-radius-tiles 9.5 --base-gain-scale 2.5 --normal-strength-scale 2.5
```

### tuning options

`normalize_swatch` と `normal_from_swatch` の半径は元々**絶対pixel値**で、
出荷時のrepeat数（1タイル171 px）に合わせてあった。repeatsを上げるとタイルだけが
小さくなり半径は動かないため、ディテールが細かくなるどころか**濾し取られる**。
16 repeatsではタイル32 pxに対し18 pxのhigh-passがかかる。

| Option | 効果 | default |
| --- | --- | --- |
| `--high-pass-radius-tiles N` | high-pass半径を `tile / N` にする | 絶対18 px |
| `--relief-radius-tiles N` | normal生成の半径を `tile / N` にする | 絶対2.2 px |
| `--smoothness-radius-tiles N` | smoothness detailの半径を `tile / N` にする | 絶対1.2 px |
| `--base-gain-scale` | BaseColorの高周波gain倍率 | 1.0 |
| `--smoothness-gain-scale` | smoothness detail gain倍率 | 1.0 |
| `--normal-strength-scale` | normal strength倍率 | 1.0 |
| `--repeats body=..,metal=..,gasket=..` | repeat数の上書き | profile値 |
| `--theme` / `--scale-class` | 生成対象を絞る | 全部 |

defaultはすべて出荷時の挙動。manifestへ `swatch_tuning` と `tile_pixels` が
記録されるので、生成物から設定を追える。

入力は検証される。`--repeats` はrole名、整数、1以上、重複なしを要求し、
`readout` の上書きは明示的に拒否する（readout象限はdial graphicであって
タイリング素材ではなく、repeats=1はreadout契約の一部）。`*-radius-tiles` は
正数、`*-gain-scale` は0以上でなければならない。

bodyの象限で実測した効果（`docs/OPUS5_BRUSHUP_PILOT_REVIEW.md` §5.8）:

| 設定 | BaseColor rms | Normal 起伏 | 粒の物理サイズ |
| --- | ---: | ---: | ---: |
| 現行 3/5/3 | 0.00203 | 0.14182 | 224 mm |
| 16/21/16 default | 0.00082 | 0.03474 | 42 mm |
| 16/21/16 tile-relative | 0.00094 | **0.08320** | 42 mm |

Standard classはB（16/21/16）、Medium classは現行Control（5/8/5）、Large classは
現行1K（8/12/7）で決着した。tuningはいずれもdefault（上記「採択済みprofile」）。

## Pillow 13対応

`as_image()` は `Image.fromarray(values, mode)` の `mode` 引数（Pillow 13で削除）を
使わず、配列形状からmodeを推論するようにした。`(h, w, 3)` は RGB、`(h, w, 4)` は
RGBA になる。呼び出し側の意図が黙って崩れないよう、推論結果が期待modeと違えば
例外を投げる。45枚のpixel-equivalenceは維持されている。
