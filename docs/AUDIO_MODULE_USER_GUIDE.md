# 音響モジュール 使い方ガイド

AnalogInstrumentMR のモジュラー音響モジュールについて、トリガとゲートの使い所、
エンベロープ、接続方法を中心にまとめたもの。

> **この文書が説明する実装について**
>
> 記載した port 名・初期値・範囲・振る舞いは、すべて
> `Assets/MatsuMotoMeterAR/Runtime/Audio/` の実装
> （`ModularAudioPort.cs`、`ModularAudioNodes.cs`、`ModularAudioGraph.cs`、
> `ModularAudioPatchPolicy.cs`）から読み取ったもので、一般的なシンセサイザの
> 解説ではない。
>
> **執筆時点で、その実装は `main` にはマージされていない**
> （ブランチ `codex/audio-module-visuals`、コミット `d419d44`）。
> `main` を見ても該当コードは存在しないので注意。実装が変われば本書も合わなくなる。

---

## 全体像

このシステムの信号には **5 つのドメイン**があり、**同じドメイン同士しか繋がらない**。
これが一番大事な規則で、繋がらないときの理由のほとんどはこれ。

| ドメイン | 中身 | 更新粒度 |
|---|---|---|
| **Audio** | 音そのもの。おおむね −1〜+1 | 1 サンプルごと |
| **Control** | 連続値。音量や音高を動かす | **1 ブロック 1 回**（後述） |
| **Gate** | 0 か 1。**長さのある** ON/OFF | 1 サンプルごと |
| **Trigger** | 0 か 1。**瞬間の**合図 | 1 サンプルごと |
| **Clock** | 拍を送るパルス | 1 サンプルごと |

### モジュールとポート一覧

`in` で終わるのが入力、`out` が出力。

| モジュール | 入力 | 出力 |
|---|---|---|
| **Oscillator** | `pitch.in`→C、`gate.in`→G、`fm.in`→A | `audio.out`→A |
| **Noise** | `gate.in`→G | `audio.out`→A |
| **Lfo** | `rate.in`→C、`reset.in`→T | `control.out`→C、`clock.out`→K、`gate.out`→G、`trigger.out`→T、`audio.out`→A |
| **Sequencer** | `clock.in`→K、`trigger.in`→T | `control.out`→C、`gate.out`→G、`trigger.out`→T |
| **Envelope** | `gate.in`→G、`trigger.in`→T | `control.out`→C |
| **Vca** | `audio.in`→A、`level.in`→C | `audio.out`→A |
| **Filter** | `audio.in`→A、`cutoff.in`→C | `audio.out`→A |
| **Delay** | `audio.in`→A、`time.in`→C | `audio.out`→A |
| **Mixer** | `audio.in`→A | `audio.out`→A |
| **AudioOutput** | `audio.in`→A | なし（終端） |

A=Audio, C=Control, G=Gate, T=Trigger, K=Clock

計器類（Meter / Trend / Panel など）も信号源になり、`value.out`、`slope.out`、
`energy.out` などの Control 出力と `trigger.out`、`audio.out` を持つ。

### 見るべき順番

信号は必ずこの向きに流れる。

> **拍を作る**（Lfo / Sequencer）→ **形を作る**（Envelope）→
> **音を作る**（Oscillator / Noise）→
> **音を加工する**（Vca / Filter / Delay / Mixer）→ **AudioOutput**

**AudioOutput に辿り着かないモジュールは動かない。**
パッチは AudioOutput ごとに、その上流をたどって組み立てられるから。

---

## トリガとゲート

この 2 つはどちらも 0 か 1 の信号だが、**伝える情報が違う**。

| | ゲート | トリガ |
|---|---|---|
| 伝えるもの | 「**いま押されている**」 | 「**今始まった**」 |
| 形 | 押している間 1、離すと 0 | 瞬間だけ 1、すぐ 0 |
| 長さ | **意味がある** | 意味がない |
| 鍵盤で言うと | 鍵を押している間ずっと | 鍵を押した瞬間だけ |

### 使い分けの実際

違いが一番はっきり出るのが **Envelope**。

- **Gate を使う** → 押している間は音が持続する（A→D→**S で待機**→離したら R）。
  オルガンやストリングスのような「伸びる音」
- **Trigger を使う** → 長さに関係なく一発で鳴り切る（A→D→**そのまま R**）。
  打楽器やプラックのような「短い音」

コード上もそのとおりで、Gate が低いまま Trigger だけが来ると
エンベロープは `triggerOnly` 状態になり、Decay が終わったところで
Sustain を飛ばして Release へ入る。

### どこから出て、どこへ入るか

**ゲートの出元**: `Lfo.gate.out`、`Sequencer.gate.out`、操作系の `gate.out`
**ゲートの行先**: `Envelope.gate.in`、`Oscillator.gate.in`、`Noise.gate.in`

**トリガの出元**: `Lfo.trigger.out`、`Sequencer.trigger.out`（ステップが進む瞬間）、
計器類の `trigger.out`
**トリガの行先**: `Envelope.trigger.in`、`Lfo.reset.in`（位相を 0 に戻す）、
`Sequencer.trigger.in`（ステップを 1 つ進める）

### Clock との違い

Clock はトリガと形は似ているが別ドメインで、**Sequencer の歩を進める専用**。
`Lfo.clock.out` → `Sequencer.clock.in` として使う。

Sequencer のステップ進行には 3 つのモードがある。

1. **何も繋がない** → 内部テンポ（`TempoBpm`、初期 120、範囲 20〜300）で自走
2. **`clock.in` に Clock を繋ぐ** → その立ち上がりで 1 歩
3. **モードを StepTrigger にして `trigger.in` を繋ぐ** → トリガ 1 発で 1 歩

注意: 3 番目は **`PlaybackMode` を StepTrigger に切り替えないと効かない**。
Clock モードのまま `trigger.in` に繋いでもステップは進まない。

---

## エンベロープ

エンベロープは **音を出さない**。「合図が来てからの時間経過」を 0〜1 の値にして
吐くだけのモジュール。その値を何に使うかは繋ぎ先が決める。

入力は `gate.in`（Gate）と `trigger.in`（Trigger）の 2 つだけ。
出力は `control.out`（Control）の 1 つだけ。

### 4 つのパラメータ（ADSR）

| 名前 | 意味 | 初期値 | 範囲 |
|---|---|---:|---|
| **Attack** | 0 から 1 まで上がる時間 | 0.05 s | 0.001〜10 s |
| **Decay** | 1 から Sustain まで下がる時間 | 0.2 s | 0.001〜10 s |
| **Sustain** | 押している間保つ**高さ**（時間ではない） | 0.7 | 0〜1 |
| **Release** | 離してから 0 に戻る時間 | 0.35 s | 0.001〜10 s |

Sustain だけが時間ではなくレベル。ここは混乱しやすい。

### 状態の遷移

ゲートで駆動した場合:

> Idle →（ゲート立上がり）→ **Attack** → **Decay** →
> **Sustain**（ゲートが高い間ずっと）→（ゲート立下がり）→ **Release** → Idle

トリガだけで駆動した場合:

> Idle →（トリガ）→ **Attack** → **Decay** → **Release** → Idle（Sustain を飛ばす）

### 知らないとハマるところ

**`gate.in` に何も繋がっていないと、ゲートはずっと押されたままになる。**

内部に `ManualGate` という設定があり、**初期値が true**。ケーブルがなければ
これが使われるので、エンベロープは A→D と進んで
**Sustain で止まったままになる**。

これが「音が鳴りっぱなしになる」「エンベロープを繋いだのに変化しない」の
最もよくある原因。**エンベロープを使うなら、まず `gate.in` か `trigger.in` に
何かを繋ぐ**。

### どこへ繋ぐか

`control.out` は Control なので、Control 入力ならどこへでも入る。
よく使うのはこの 3 つ。

| 繋ぎ先 | どうなるか |
|---|---|
| `Vca.level.in` | **音量の形**。一番基本。これがないと音は鳴りっぱなし |
| `Filter.cutoff.in` | **音色の形**。発音の瞬間だけ明るくなる |
| `Oscillator.pitch.in` | **音高の形**。立ち上がりでピッチが落ちるなど |

さらに `Delay.time.in` へ入れればディレイ時間が動く。

**1 つのエンベロープを複数の行先へ同時に繋げる。**
音量とカットオフを同じエンベロープで動かすのは定番。

---

## 接続方法

### 3 つの規則

1. **出力から入力へ**。出力同士、入力同士は繋がらない
2. **同じドメイン同士**。Audio を Control 入力へ、Gate を Trigger 入力へは入らない
3. 上の 2 つを満たせば繋がる。特別な組み合わせ制限はない

繋がらないときの理由は `SourceMustBeOutput` / `TargetMustBeInput` /
`DomainMismatch` のいずれか。**ほとんどは 3 番目**で、例えば LFO の `gate.out` を
Envelope の `trigger.in` へ直接は入らない（Gate ≠ Trigger）。
LFO には `trigger.out` もあるのでそちらを使う。

### 自動で選ばれる組み合わせ

2 つのモジュールを繋ぐとき、ポートを指定しなければ
**よく使う組み合わせが自動で選ばれる**。主なものはこれ。

| 繋ぎ元 → 繋ぎ先 | 選ばれる経路 |
|---|---|
| Sequencer → Oscillator | `control.out` → `pitch.in` |
| Sequencer → Envelope | `gate.out` → `gate.in` |
| Sequencer → Lfo | `trigger.out` → `reset.in` |
| Lfo → Sequencer | `clock.out` → `clock.in` |
| Lfo → Vca | `control.out` → `level.in` |
| Lfo → Filter | `control.out` → `cutoff.in` |
| Lfo → Envelope | `gate.out` → `gate.in` |
| Envelope →（何か） | `control.out` から |
| その他 | `audio.out` → `audio.in` |

LFO から Oscillator / Delay へは、**Control と Audio の 2 通り**がある。
Control ならゆっくりした揺らぎ（`pitch.in` / `time.in`）、
Audio なら高速な FM（`fm.in` / `audio.in`）。

### 知っておくべき振る舞い

**同じ入力に複数本繋げる。値は足される。**
ミキサーを使わなくても `audio.in` に 2 本入れれば混ぜられる。
ただし**クリップに注意**。

**Control だけは 1 ブロックに 1 回しか読まれない。**
Audio / Gate / Trigger / Clock は 1 サンプルごとに処理されるが、
Control はブロック先頭の値を 1 つ取るだけ（ブロックは最大 1024 サンプル）。
だから**ごく短い Attack を VCA に通すと段々に聞こえることがある**。
急な形が欲しいなら Gate を Oscillator の `gate.in` へ直接入れる方が確実。

**ケーブルは 1 つのグラフ全体で 64 本まで。**

**パッチは AudioOutput ごとに組み立てられる。**
AudioOutput から上流へたどって見つかったモジュールだけが動く。
どこにも繋がっていない島は、置いてあっても計算されない。

---

## 定番パッチ

小さいところから順に組んでいく。**各段階で必ず音を確かめてから次へ進む**と、
どこで壊れたかがすぐ分かる。

### 1. まず音を出す（2 モジュール）

```
Oscillator.audio.out → AudioOutput.audio.in
```

これだけで連続音が出る。Oscillator は初期で 220 Hz、Level 0.2、Gate は常時 ON。
出なければこの先を組んでも無駄なので、ここを必ず通す。

### 2. 音量に形をつける（エンベロープの基本形）

```
Oscillator.audio.out → Vca.audio.in
Envelope.control.out → Vca.level.in
Sequencer.gate.out   → Envelope.gate.in      ← これを忘れない
Vca.audio.out        → AudioOutput.audio.in
```

**ポイントは 3 本目**。これがないとエンベロープは開いたままになり、
音量が Sustain の 0.7 で固定されて鳴りっぱなしになる。
Sequencer は何も繋がなくても 120 BPM で自走するので、これだけで拍が出る。

### 3. 音程をつける

```
Sequencer.control.out → Oscillator.pitch.in
```

ステップ値がそのまま音高になる。**`pitch.in` は ±1 の入力を ±2 オクターブに
割り当てる**ので、少しの値で大きく動く。

### 4. テンポを外から与える

```
Lfo.clock.out → Sequencer.clock.in
```

LFO の周波数（初期 1 Hz、範囲 0.01〜40 Hz）がそのままステップ速度になる。
複数の Sequencer を同じ LFO に繋げば拍が揃う。

### 5. 音色に形をつける

```
Vca.audio.out        → Filter.audio.in
Envelope.control.out → Filter.cutoff.in   ← 2 本目の行先
Filter.audio.out     → AudioOutput.audio.in
```

同じエンベロープを音量とカットオフの両方へ繋ぐ。
発音の瞬間だけ明るくなる、いわゆるシンセらしい音になる。

### 6. 一発トリガの打楽器型

```
Sequencer.trigger.out → Envelope.trigger.in
```

2 番の `gate.out → gate.in` をこれに差し替える。ゲート長に関係なく、
Attack→Decay→Release で鳴り切る短い音になる。

### 7. ステップを外部の合図で進める

```
Sequencer.PlaybackMode = StepTrigger   ← 先にモードを変える
（何かの）trigger.out → Sequencer.trigger.in
```

計器の `trigger.out` や操作系のトリガを入れれば、自分の操作で 1 歩ずつ進む。
**モードを変えないと無視される**ので注意。

### 8. LFO で揺らす

| やりたいこと | 繋ぎ方 |
|---|---|
| ビブラート | `Lfo.control.out → Oscillator.pitch.in` |
| トレモロ | `Lfo.control.out → Vca.level.in` |
| ワウワウ | `Lfo.control.out → Filter.cutoff.in` |
| FM（金属的な音） | `Lfo.audio.out → Oscillator.fm.in` |

上 3 つは LFO の周波数を低く（1〜8 Hz）、FM は高くする。

---

## おかしいときの確認順

上から順に見る。上のほどよくある。

### 音が全く出ない

1. **AudioOutput まで繋がっているか**。パッチは AudioOutput から上流をたどって
   組み立てられるので、**途中で切れている島は一切計算されない**。
   途中のモジュールのメーターが振れていても、終端に届いていなければ無音
2. **VCA の level が 0 になっていないか**。`level.in` にケーブルがあれば
   その値が優先され、手元のつまみは無視される。エンベロープが Idle なら 0
3. **Oscillator の Level が 0 でないか**。初期 0.2
4. **Oscillator の `gate.in`**。ケーブルがあるなら、そのゲートが低い間は完全に無音

### 音が鳴りっぱなしになる

**ほぼ `Envelope.gate.in` のケーブル忘れ。**
繋がっていないとゲートは押されたまま扱いになり、Sustain レベルで止まる。

確認: エンベロープの状態が **Sustain のまま動かない**ならこれ。

### エンベロープが伸びない（すぐ消える）

**`trigger.in` だけで駆動している**。トリガは長さを持たないので
Sustain を飛ばして Release へ入る仕様。伸ばしたければ `gate.in` へ変える。

逆に Release を伸ばすのも手（最大 10 秒）。

### ケーブルが繋がらない

**ドメイン違い**がほとんど。よくある間違いはこの 3 つ。

| やろうとしたこと | 正しいポート |
|---|---|
| `gate.out` → `trigger.in` | `trigger.out` を使う |
| `trigger.out` → `clock.in` | `clock.out` を使う |
| `audio.out` → `level.in` / `cutoff.in` | Control 出力（`control.out` 等）を使う |

同じモジュールでも出力ポートを選べば目的のドメインがあることが多い。
LFO は Control / Clock / Gate / Trigger / Audio の 5 つを全部持っている。

### ステップが進まない

1. **`PlaybackMode`** を確認。`trigger.in` で進めたいなら **StepTrigger** にする。
   Clock モードのままだとトリガは無視される
2. 逆に **Clock モードで `clock.in` に繋いだら、内部テンポは使われない**。
   外部クロックが止まっていればシーケンスも止まる

### 変化がカクカクする・段々に聞こえる

**Control は 1 ブロックに 1 値しか読まれない**ため、ブロックより短い変化は
表現できない。

- Attack を少し長くする（1 ms → 5〜10 ms）
- または、急な立ち上がりはゲートを Oscillator の `gate.in` へ直接入れて作る

### 音が歪む・割れる

同じ `audio.in` に複数本入れると**値が足される**。
Oscillator の Level（初期 0.2）や VCA の Gain（初期 1、最大 4）を下げる。
出力は ±1 でクリップされる。
