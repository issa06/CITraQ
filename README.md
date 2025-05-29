# CITraQ - 進級/卒業判定ツール

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

### 必要なデータファイル

`catalog` ディレクトリに以下のファイルが必要です：

1. `departments.json` - 学部・学科の情報 (リポジトリ内にあります)
2. `YYNN_requirements.json` - 進級/卒業要件情報
3. `YYNN_subjects.json` - 科目リスト

YYNN は入学年度と学科コードを表しています。  

### 各jsonファイルのフォーマット

#### 成績データ (XXXXXXX_grades.json)

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

#### 学部・学科情報 (departments.json)

```json
[
"faculties": {
        "engineering": { // 学部名省略形
            "name": "工学部", // 学部名
            "name_en": "Faculty of Engineering", // 学部英語名
            "departments": {
                "A1": { // 学科コード
                    "name": "機械工学科", // 学科名
                    "name_en": "Department of Mechanical Engineering",  // 学科英語名
                    "code": "A1" // 学科コード
                },
                ...
            }
        }
    }
]
```

#### 進級/卒業要件情報 (XXXXNN_requirements.json)

```json
{
    "department": {
        "requirements": {
            "total_credits": 124, // 卒業に必要な単位数
            "liberal_arts": {
                "total": 24, // 教養科目の単位数
                "communication": 8, // 言語
                "human_social_natural": {
                    "group1": 4, // 学科指定科目群1の単位数
                    "group2": 4 // 学科指定科目群2の単位数
                }
            },
            "specialized": { // 専門科目
                "basic": 20, // 基礎科目の単位数
                "core": 40, // 基幹科目の単位数
                "advanced": 40 // 展開科目の単位数
            }
        },
        "subjects": { // 科目リスト
            "liberal_arts": { // 教養科目
                "department_specified": { // 学科指定科目群
                    "human_social_natural_1": { // 学科指定科目群1
                        "subjects": [
                            "科目名",
                            ...
                        ]
                    },
                    "human_social_natural_2": { // 学科指定科目群2
                        "subjects": [
                            "科目名",
                            ...
                        ]
                    }
                },
                "other_liberal_arts": { // その他の教養科目
                    "subjects": [
                        "科目名",
                        ...
                    ]
                }
            },
            "specialized": { // 専門科目
                "basic": { // 基礎科目
                    "required_subjects": [
                        "科目名",
                        ...
                    ]
                },
                "core": { // 基幹科目
                    "required_subjects": [
                        "科目名",
                        ...
                    ]
                },
                "advanced": { // 展開科目
                    "required_subjects": [
                        "科目名",
                        ...
                    ]
                }
            },
            "graduation_research": { // 卒業研究
                "required_subjects": [
                    "科目名",
                    ...
                ]
            }
        }
    }
}
```

#### 科目リスト (XXXXNN_subjects.json)

```json
{
    "教養科目": {
        "教養基礎科目": {
            "コミュニケーションスキル": [
                {
                    "科目名": "科目名",
                    "単位数": 2,
                    "必修": true (or false)
                },
                ...
            ],
            ...
        },
        ...
    },
    "専門科目": {
        "基礎科目": [
            {
                "科目名": "科目名",
                "単位数": 2,
                "必修": true (or false)
            },
            ...
        ],
        ...
    }
}
