# Superfine production rollback

## Scope

2026-09-22のSuperfine初回本番登録だけを戻す手順である。既存4テーマ、candidate C2 / C3 / C4、
Opus 5 source packageは削除・変更しない。

昇格時のrollback record:

`Builds/ModelReplacementBackups/Superfine_P_20260922_111623`

初回登録前にSuperfine本番assetは存在しなかったため、復元対象の旧assetはない。rollbackは新規Superfine本番rootの
除去と、theme registration codeの復帰で構成する。

## Remove only these production roots

- `Assets/MatsuMotoMeterAR/Content/Themes/Superfine`
- `Assets/MatsuMotoMeterAR/Content/Themes/Superfine.meta`
- `Assets/MatsuMotoMeterAR/Resources/Superfine`
- `Assets/MatsuMotoMeterAR/Resources/Superfine.meta`

Unity Editorまたはversion controlから、上記の正確な4 targetだけを削除する。candidate staging、
`ArtSource/Blender/BrushUp/Opus5`、他theme rootへ範囲を広げない。

## Revert runtime registration

同じ変更単位で次をSuperfine登録前へ戻す。

1. `MockInstrumentTheme.Superfine = 4`を除き、catalogue countを4へ戻す。
2. ID `superfine`、表示名、palette、normalize / parse / cycle / persistenceを除く。
3. `OrbitalAnalogVisualFactory`と`MockInstrumentFactory`のSuperfine resource routingを除く。
4. `AudioModuleSignalFlowView`、`AudioModuleDisplayView`、`InstrumentAudioClipLibrary`のSuperfine固有色・音差を除く。
5. validator、motion / signal audit、visual reviewのtheme列挙を既存4テーマへ戻す。
6. Superfine production promoter / readiness menuと、5テーマ前提で追加・変更したテストを同じ昇格変更単位で戻す。

`SuperfineProductionPromoter`を再実行してrollbackしない。これは初回登録用promoterであり、rollback操作ではない。

## Verification after rollback

- `Resources/Superfine`と`Content/Themes/Superfine`が存在しない。
- runtime catalogueが既存4テーマだけを返す。
- 既存4テーマのGUIDとasset hashにrollback由来の変更がない。
- active prefabからSuperfine pathへの参照がない。
- EditMode一式を再実行し、既存4テーマの回帰がない。

Q1/B1のdeferred、C2/C3/C4のcandidate証跡、Opus 5成果物はrollback後も保存する。
