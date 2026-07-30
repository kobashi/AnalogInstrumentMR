# Geminiレビュー反映モデル候補

## 成果物

Geminiの3Dモデルレビューを形状へ反映し、11種類 × 3テーマ、計33モデルを
生成した。候補検証後、全33モデルを本番FBXとVisual Prefabへ展開済み。
`RefinedCandidates`は再生成・比較・ロールバック判断用として保持する。

| 成果物 | 場所 |
| --- | --- |
| Blender原本 | `ArtSource/Blender/Refined/<Theme>/BL_*_Refined.blend` |
| レンダリング画像 | `ArtSource/Blender/Refined/<Theme>/Preview_*_Refined.png` |
| Blender検証結果 | `ArtSource/Blender/Refined/<Theme>/BL_*_Refined.report.json` |
| Unity確認用FBX | `Assets/MatsuMotoMeterAR/Content/RefinedCandidates/<Theme>/Models/` |
| Unity一括検証結果 | `Builds/Reports/gemini-refined-candidate-validation.md` |

テーマは`OrbitalAnalog`、`ForgeBrass`、`KineticSafety`の3種類。

## レビュー反映内容

| モデル | 主な変更 |
| --- | --- |
| Round Meter | 多層ベゼル、固定ボルト、二重目盛リング、針ハブ強調 |
| Lever | 軸受カバー、ガイド、5段デテント、基部クリアランス |
| Toggle | 六角ナット、スプリングカラー、ON/OFF方向表示 |
| Rotary | 段付きベゼル、9段目盛、外周グリップ |
| Button | ストローク隙間、二重ベゼル、発光ファンクションマーク |
| Lamp | 保護ケージ、保持リング、内部LED構造 |
| Throttle | エンジン出力象限、エンドストップ、保護トラック、掌グリップ |
| Power Slider | 11段目盛、機械式エンドストップ、ガイドレール |
| Status Indicator | SAFE／WARN／DANGER独立セグメント、スモークハウジング |
| Window Meter | 補強窓枠、積層ダイヤル、大型発光針 |
| Window Panel | 隔壁フレーム、中央表示面、露出型ステータスベーン |

各テーマの形状言語は維持し、可動部と固定部のノードは分離した。
Runtime側が参照するPivot名、motion target名、1 m単位、mount面`Z = 0`の
契約も維持している。

## 検証結果

- Blender生成・FBX round-trip検証: 33 / 33 PASS
- Unity 6インポート・Visual契約検証: 33 / 33 PASS
- 小型モデル: 5,000 triangles以下
- 大型Windowモデル: 25,000 triangles以下
- 共有Material: 2以下
- Collider、Animator、Camera、realtime Light: なし
- 全モデルが種類別Visual Envelope内
- mount面より後方へのはみ出し: なし
- 必須可動ノードとStatus 3状態ノード: 存在

検証はUnityメニュー
`Tools > MatsuMotoMeterAR > Model Replacement >
Prepare and Validate All Candidates`から再実行できる。

## 本番導入状況

`OrbitalAnalog`のRound Meter、Lever、Throttleを先行導入した後、
全3テーマ・全11種類へ展開した。Leverの軸受は全テーマで
`handle_pivot`中心へ一致させ、Grip操作はレバーの回転弧に追従する。
2026-07-29時点のUnity検証結果は33 / 33 PASS、可動監査は12 / 12 PASS。

候補から本番への入れ替えでは、`_Refined`を除いた本番FBX名へ昇格し、
`Rebuild Instrument Theme Assets`を実行する。保存schema、type ID、
InteractionCollider、Spatial Anchorは変更しない。
