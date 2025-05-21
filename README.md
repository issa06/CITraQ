# CITraQ - 単位計算・進捗チェックツール

CITraQ は、千葉工大生の修得済単位を分析し、進級/卒業要件と照合して進捗状況を表示するコマンドラインツールです。

## 特徴

- 学科ごとの卒業要件に基づく単位チェック
- 必修科目の修得状況確認
- 学部指定科目群の取得状況確認
- 進級要件チェック
- 卒業要件チェック
- ポータルサイトから直接成績データを取得（オプション）

## インストール方法

```bash
# リポジトリをクローン
git clone https://github.com/issa06/CITraQ.git
cd CITraQ

# 依存パッケージのインストール（成績取得機能を使用する場合）
pip install -r requirements.txt


## 使用方法

### 既存の成績ファイルを使用する場合
```bash
python CITraQ.py <成績ファイル>
```

例：
```bash
python CITraQ.py 2231000_grades.json
```

### ポータルサイトから成績を取得する場合
```bash
python CITraQ.py --get-grades
```
※実行時に学籍番号とパスワードの入力を求められます

## データ形式

### 成績データ (grades.json)

成績データは以下の形式のJSONファイルです：

```json
[
  {
    "subject": "科目名",
    "credits": "単位数",
    "evaluation": "評価（S/A/B/C/認定/合）",
    "course_category": "授業区分（教養科目/専門科目）",
    "classification": "分類（基礎科目/基幹科目/展開科目など）"
  },
  ...
]
```

ファイル名は `学籍番号_grades.json` 形式にしてください。

例：`2231000_grades.json` = 2022年度入学・情報工学科の学生
※2231000: 20 ''22'' 31 ''情報工学科'' 000 ''学生番号''を表しています

### 必要なデータファイル

`scoredata` ディレクトリに以下のファイルが必要です：

1. `departments.json` - 学部・学科の情報 (リポジトリ内にあります)
2. `YYNN_requirements.json` - 卒業要件情報
3. `YYNN_subjects.json` - 科目リスト

YYNN は入学年度と学科コードを表しています。

