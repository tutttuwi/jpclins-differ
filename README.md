# jpclins-differ
hl7fhir の日本国内規格である jpclins の更新箇所を特定するためのアプリです

## 環境構築

- python3系DL

## セットアップ

- 仮想環境アクティベート

```zsh
python3 -m venv venv
source venv/bin/activate
```

## 実行

```zsh
python3 compare_structure_definition_elements.py jp-eCSCLINS.r4-1.9.0-snap jp-eCSCLINS.r4-1.10.0-snap
```

## 結果確認

- Vscode,cursorなどで `LiveServer` などのプラグインをインストールしておく
- 以下ファイルを`LiveServer`で開く
  - `public/structure_definition_elements_diff.html`

