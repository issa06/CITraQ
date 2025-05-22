import argparse
import getpass
import json
import os
import time
import unicodedata
from typing import Any, Dict, List, Tuple

try:
    from cit_portal_wrapper.get_grade import get_grades_json
    GRADE_FETCH_AVAILABLE = True
except ImportError:
    GRADE_FETCH_AVAILABLE = False
    print("注意: 成績取得機能を使用するには cit-portal-wrapper をインストールしてください")
    print("pip install -r requirements.txt")
    print("または、以下のコマンドでインストールしてください")
    print("pip install git+https://github.com/issa06/cit-portal-wrapper.git")

# Application information
APP_NAME = "CITraQ"
VERSION = "1.0.1"

# Grades considered as "Pass"
PASS_GRADES = ["S", "A", "B", "C", "認定", "合"]

# ANSI escape codes for colors


class Color:
    GREEN = "\033[92m"  # Green
    RED = "\033[91m"    # Red
    YELLOW = "\033[93m"  # Yellow
    BLUE = "\033[94m"   # Blue
    CYAN = "\033[96m"   # Cyan
    MAGENTA = "\033[95m"  # Magenta
    RESET = "\033[0m"   # Reset


def normalize_subject_name(name: str) -> str:
    """Normalize subject names (full-width to half-width, remove spaces, standardize numbers)"""
    if not name:
        return ""
    # Full-width to half-width, remove spaces, standardize digits
    name = unicodedata.normalize('NFKC', name)
    name = name.replace(' ', '').replace('　', '')
    # Convert full-width digits to half-width
    name = ''.join([str(unicodedata.digit(c)) if unicodedata.name(
        c).startswith('FULLWIDTH DIGIT') else c for c in name])
    return name


def load_requirements(file_path: str, department: str) -> Dict[str, Any]:
    """Load graduation requirements from requirements.json"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "department" not in data:
        raise KeyError("'department' key not found in requirements file.")

    if "requirements" not in data["department"]:
        raise KeyError("'requirements' key not found in department data.")

    return data["department"]["requirements"]


def flatten_subjects(subjects: Any, category: str = None) -> List[Dict[str, Any]]:
    """Flatten all subjects in subjects.json by category"""
    result = []
    if isinstance(subjects, dict):
        for key, value in subjects.items():
            # Inherit the category name
            cat = category if category else key
            result.extend(flatten_subjects(value, cat))
    elif isinstance(subjects, list):
        for subject in subjects:
            if isinstance(subject, dict):
                subject_copy = subject.copy()
                if category:
                    subject_copy["category"] = category
                result.append(subject_copy)
    return result


def load_subjects(file_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """Load subject list from subjects.json (flatten all categories, convert category names)"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    all_subjects = flatten_subjects(data)
    categories = {}
    for subject in all_subjects:
        cat = subject.get("category", "Other")
        # Convert category names to match requirements
        if cat == "基礎科目":
            cat_key = "専門科目_基礎"
        elif cat == "基幹科目":
            cat_key = "専門科目_基幹"
        elif cat == "展開科目":
            cat_key = "専門科目_展開"
        elif cat.startswith("専門科目"):
            cat_key = "専門科目"
        elif cat.startswith("教養科目") or cat == "教養科目":
            cat_key = "教養科目"
        else:
            cat_key = cat
        if cat_key not in categories:
            categories[cat_key] = []
        categories[cat_key].append(subject)
    return categories


def create_patterns(subjects: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    """Return subject lists by category as is"""
    return subjects


def match_subject_to_category(
    subj_name: str,
    patterns: Dict[str, List[Dict[str, Any]]]
) -> Tuple[bool, str]:
    """Match subject name to a category"""
    for category, subject_list in patterns.items():
        for subject_info in subject_list:
            pattern_name = normalize_subject_name(subject_info["科目名"])
            # Exact match or partial match (prefix match)
            if (subj_name == pattern_name or
                pattern_name in subj_name or
                    subj_name in pattern_name):
                return True, category
    return False, ""


def load_grades(
    file_path: str,
    patterns: Dict[str, List[Dict[str, Any]]]
) -> Tuple[float, Dict[str, float]]:
    """Load grades.json and calculate credits for passed subjects"""
    with open(file_path, "r", encoding="utf-8") as f:
        grades = json.load(f)

    # Initialize all required categories
    required_categories = [
        "教養科目", "専門科目", "専門科目_基礎",
        "専門科目_基幹", "専門科目_展開"
    ]
    credits_by_category = {key: 0.0 for key in required_categories}
    for key in patterns.keys():
        if key not in credits_by_category:
            credits_by_category[key] = 0.0
    total_credits = 0.0

    for subject in grades:
        # Skip if subject name is empty
        if not subject.get("subject") or subject["subject"].strip() == "":
            continue

        subj_name = normalize_subject_name(subject["subject"])
        credit = 2.0
        if subject.get("credits") and subject["credits"].strip() != "":
            credit = float(subject["credits"])

        if subject["evaluation"] in PASS_GRADES:
            matched = False
            # First, determine from course_category and classification
            if subject["course_category"] == "専門科目":
                if subject["classification"] == "基礎科目":
                    credits_by_category["専門科目_基礎"] += credit
                    matched = True
                elif subject["classification"] == "基幹科目":
                    credits_by_category["専門科目_基幹"] += credit
                    matched = True
                elif subject["classification"] == "展開科目":
                    credits_by_category["専門科目_展開"] += credit
                    matched = True

            # Pattern matching
            if not matched:
                matched, category = match_subject_to_category(
                    subj_name, patterns)
                if matched:
                    credits_by_category[category] += credit

            total_credits += credit
            if not matched:
                print(
                    f"\n[警告] '{subject['subject']}' は、どのカテゴリにも一致しませんでした。"
                    f"({credit} 単位, grade: {subject['evaluation']})\n"
                )

    # Add up 基礎・基幹・展開 credits to専門科目
    credits_by_category["専門科目"] = (
        credits_by_category["専門科目_基礎"] +
        credits_by_category["専門科目_基幹"] +
        credits_by_category["専門科目_展開"]
    )
    return total_credits, credits_by_category


def check_requirements(
    total_credits: float,
    credits_by_category: Dict[str, float],
    requirements: Dict[str, Any]
) -> None:
    """Check graduation/progression requirements and display remaining credits"""
    print(f"\n{Color.CYAN}【進級・卒業要件チェック】\n{Color.RESET}")

    # Total credits
    total_req = requirements['total_credits']
    total_remainder = max(0, total_req - total_credits)
    print("総単位数: ")
    print(f"  {Color.BLUE}{total_credits}{Color.RESET} / {Color.MAGENTA}{total_req}{Color.RESET}")
    print(f"  残り: {Color.YELLOW}{total_remainder}{Color.RESET}単位")

    # Liberal arts
    print(f"\n{Color.GREEN}【教養科目】\n{Color.RESET}")
    lib_total = requirements['liberal_arts']['total']
    lib_remainder = max(0, lib_total - credits_by_category['教養科目'])
    print(f"{Color.GREEN}教養科目{Color.RESET}: ")
    lib_credits = credits_by_category['教養科目']
    print(f"  {Color.BLUE}{lib_credits}{Color.RESET} / "
          f"{Color.MAGENTA}{lib_total}{Color.RESET}")
    print(f"  残り: {Color.YELLOW}{lib_remainder}{Color.RESET}単位")

    # Specialized subjects
    print(f"\n{Color.BLUE}【専門科目】\n{Color.RESET}")
    spec_total = requirements['specialized']['total']
    spec_remainder = max(0, spec_total - credits_by_category['専門科目'])
    print(f"{Color.BLUE}専門科目{Color.RESET}: ")
    spec_credits = credits_by_category['専門科目']
    print(f"  {Color.BLUE}{spec_credits}{Color.RESET} / "
          f"{Color.MAGENTA}{spec_total}{Color.RESET}")
    print(f"  残り: {Color.YELLOW}{spec_remainder}{Color.RESET}単位")

    # Basic subjects
    basic_total = requirements['specialized']['basic']
    basic_remainder = max(0, basic_total - credits_by_category['専門科目_基礎'])
    print(f"\n  {Color.BLUE}基礎科目{Color.RESET}: ")
    print(f"    {Color.BLUE}{credits_by_category['専門科目_基礎']}{Color.RESET} / "
          f"{Color.MAGENTA}{basic_total}{Color.RESET}")
    print(f"    残り: {Color.YELLOW}{basic_remainder}{Color.RESET}単位")

    # Core subjects
    core_total = requirements['specialized']['core']
    core_remainder = max(0, core_total - credits_by_category['専門科目_基幹'])
    print(f"\n  {Color.BLUE}基幹科目{Color.RESET}: ")
    print(f"    {Color.BLUE}{credits_by_category['専門科目_基幹']}{Color.RESET} / "
          f"{Color.MAGENTA}{core_total}{Color.RESET}")
    print(f"    残り: {Color.YELLOW}{core_remainder}{Color.RESET}単位")

    # Advanced subjects
    adv_total = requirements['specialized']['advanced']
    adv_remainder = max(0, adv_total - credits_by_category['専門科目_展開'])
    print(f"\n  {Color.BLUE}展開科目{Color.RESET}: ")
    print(f"    {Color.BLUE}{credits_by_category['専門科目_展開']}{Color.RESET} / "
          f"{Color.MAGENTA}{adv_total}{Color.RESET}")
    print(f"    残り: {Color.YELLOW}{adv_remainder}{Color.RESET}単位")


def check_specified_subjects(
    subjects: Dict[str, List[Dict[str, Any]]],
    grades: List[Dict[str, Any]],
    requirements: Dict[str, Any]
) -> None:
    """Check the status of specified required subjects"""
    print(f"\n\n{Color.CYAN}【指定科目チェック】\n{Color.RESET}")

    # Create a list of completed subjects
    taken_subjects = {
        subject["subject"]
        for subject in grades
        if subject["evaluation"] in PASS_GRADES
    }

    # Category name mapping
    category_map = {
        "基礎科目": "専門科目_基礎",
        "基幹科目": "専門科目_基幹",
        "展開科目": "専門科目_展開"
    }

    # Create a list of specified subjects
    specified_subjects = []

    # Get required subjects list from subjects.json structure
    for category, req_key in zip(["基礎科目", "基幹科目", "展開科目"], ["basic", "core", "advanced"]):
        key = category_map[category]
        # Get required subjects from subjects file
        subject_list = subjects.get(key, [])
        for subject_info in subject_list:
            if subject_info.get("必修", False):
                specified_subjects.append({
                    "科目名": subject_info["科目名"],
                    "カテゴリー": key,
                    "単位数": subject_info.get("単位数", 2)
                })

    # Display missing required subjects
    missing_specified = [
        subject for subject in specified_subjects
        if subject["科目名"] not in taken_subjects
    ]

    if missing_specified:
        print(f"{Color.YELLOW}未取得の指定科目:{Color.RESET}")
        for subject in missing_specified:
            category_color = Color.GREEN if "教養" in subject["カテゴリー"] else Color.BLUE
            print(
                f"  - {subject['科目名']}\n"
                f"    ({category_color}{subject['カテゴリー']}{Color.RESET}, "
                f"{Color.MAGENTA}{subject['単位数']}{Color.RESET}単位)"
            )
    else:
        print(f"{Color.GREEN}全ての指定科目を修得済みです。{Color.RESET}")


def check_department_specified_subjects(
    grades: List[Dict[str, Any]],
    subjects: Dict[str, List[Dict[str, Any]]]
) -> None:
    """Check the status of department-specified subject groups"""
    print(f"\n\n{Color.CYAN}【学部指定科目群チェック】\n{Color.RESET}")

    # Create a dictionary of completed subjects and their credits
    taken_subjects = {}
    for subject in grades:
        if subject["evaluation"] in PASS_GRADES:
            credit = 2.0
            if subject.get("credits") and subject["credits"].strip() != "":
                credit = float(subject["credits"])
            taken_subjects[subject["subject"]] = credit

    # Extract subjects with "department specified group" attribute from all subjects
    group1_subjects = [s["科目名"]
                       for s in sum(subjects.values(), []) if s.get("学部指定科目群") == 1]
    group2_subjects = [s["科目名"]
                       for s in sum(subjects.values(), []) if s.get("学部指定科目群") == 2]

    # Calculate credits earned for each group
    group1_credits = sum(taken_subjects.get(name, 0)
                         for name in group1_subjects)
    group2_credits = sum(taken_subjects.get(name, 0)
                         for name in group2_subjects)

    print(f"{Color.GREEN}学部指定科目群1:{Color.RESET} {Color.BLUE}{group1_credits}{Color.RESET}単位")
    print(f"{Color.GREEN}学部指定科目群2:{Color.RESET} {Color.BLUE}{group2_credits}{Color.RESET}単位")

    # Display missing subjects
    missing1 = [name for name in group1_subjects if name not in taken_subjects]
    missing2 = [name for name in group2_subjects if name not in taken_subjects]

    if missing1:
        print(f"\n{Color.YELLOW}未取得の群1科目:{Color.RESET}")
        for name in missing1:
            print(f"  - {name}")

    if missing2:
        print(f"\n{Color.YELLOW}未取得の群2科目:{Color.RESET}")
        for name in missing2:
            print(f"  - {name}")


def check_progression_requirements(
    total_credits: float,
    grades: List[Dict[str, Any]]
) -> None:
    """Check progression requirements"""
    print(f"\n\n{Color.CYAN}【進級要件チェック】{Color.RESET}")

    progression_requirements = {
        2: {"years": 1, "credits": 32},
        3: {"years": 2, "credits": 64},
        4: {"years": 3, "credits": 96}
    }

    for year, req in progression_requirements.items():
        print(f"\n第{Color.MAGENTA}{year}{Color.RESET}年次進級要件:")
        print(f"  必要単位数: {Color.MAGENTA}{req['credits']}{Color.RESET}単位")
        print(f"  現在の取得単位数: {Color.BLUE}{total_credits}{Color.RESET}単位")

        is_achieved = total_credits >= req['credits']
        status = status_text(is_achieved)
        message = '満たしています' if is_achieved else '満たしていません'
        print(f"  {status} 進級要件を{message}")

        if not is_achieved:
            remainder = req['credits'] - total_credits
            print(f"    残り必要単位数: {Color.YELLOW}{remainder}{Color.RESET}単位")


def check_graduation_requirements(
    total_credits: float,
    credits_by_category: Dict[str, float],
    grades: List[Dict[str, Any]],
    requirements: Dict[str, Any]
) -> None:
    """Check graduation requirements"""
    print(f"\n\n{Color.CYAN}【卒業要件チェック】{Color.RESET}")

    # Check total credits
    is_total_achieved = total_credits >= requirements['total_credits']
    status = status_text(is_total_achieved)
    message = '満たしています' if is_total_achieved else '満たしていません'
    req_total = requirements['total_credits']

    print("\n総単位数: ")
    print(f"  {Color.BLUE}{total_credits}{Color.RESET} / "
          f"{Color.MAGENTA}{req_total}{Color.RESET}単位")
    print(f"  {status} 総単位数の要件を{message}")

    if not is_total_achieved:
        remainder = req_total - total_credits
        print(f"    残り必要単位数: {Color.YELLOW}{remainder}{Color.RESET}単位")

    # Check liberal arts credits
    print(f"\n{Color.GREEN}教養科目:{Color.RESET}")
    print(f"  取得単位数: {Color.BLUE}{credits_by_category['教養科目']}{Color.RESET}単位")

    # Check communication skills
    comm_credits = sum(
        float(grade['credits']) for grade in grades
        if (grade['course_category'] == '教養科目' and
            grade['classification'] == 'コミュニケーションスキル' and
            grade['subject'] != '日本語表現法' and
            grade['evaluation'] in PASS_GRADES)
    )
    print(f"  {Color.GREEN}コミュニケーションスキル:{Color.RESET} "
          f"{Color.BLUE}{comm_credits}{Color.RESET}単位")

    # Check international understanding
    intl_credits = sum(
        float(grade['credits']) for grade in grades
        if (grade['course_category'] == '教養科目' and
            grade['classification'] == '国際理解' and
            grade['subject'] in ['グローバル時代の法', '国際社会論'] and
            grade['evaluation'] in PASS_GRADES)
    )
    print(
        f"  {Color.GREEN}国際理解:{Color.RESET} {Color.BLUE}{intl_credits}{Color.RESET}単位")

    # Check department specified subject groups
    group1_credits = sum(
        float(grade['credits']) for grade in grades
        if (grade['course_category'] == '教養科目' and
            grade['classification'] == '人間・社会・自然の理解' and
            grade.get('学部指定科目群') == 1 and
            grade['evaluation'] in PASS_GRADES)
    )
    group2_credits = sum(
        float(grade['credits']) for grade in grades
        if (grade['course_category'] == '教養科目' and
            grade['classification'] == '人間・社会・自然の理解' and
            grade.get('学部指定科目群') == 2 and
            grade['evaluation'] in PASS_GRADES)
    )
    print(
        f"  {Color.GREEN}学部指定科目群1:{Color.RESET} {Color.BLUE}{group1_credits}{Color.RESET}単位")
    print(
        f"  {Color.GREEN}学部指定科目群2:{Color.RESET} {Color.BLUE}{group2_credits}{Color.RESET}単位")

    # Check general classification
    total_credits = sum(
        float(grade['credits']) for grade in grades
        if (grade['course_category'] == '教養科目' and
            grade['classification'] == '総合' and
            grade['subject'] in ['課題探究セミナー', '総合学際科目'] and
            grade['evaluation'] in PASS_GRADES)
    )
    print(
        f"  {Color.GREEN}総合分類:{Color.RESET} {Color.BLUE}{total_credits}{Color.RESET}単位")

    # Check specialized subjects
    print(f"\n{Color.BLUE}専門科目:{Color.RESET}")
    print(f"  取得単位数: {Color.BLUE}{credits_by_category['専門科目']}{Color.RESET}単位")

    # Check graduation research related subjects
    has_seminar2 = any(
        grade['subject'] == 'ゼミナール2' and
        grade['evaluation'] in PASS_GRADES for grade in grades
    )
    has_thesis = any(
        grade['subject'] == '卒業研究' and
        grade['evaluation'] in PASS_GRADES for grade in grades
    )
    has_exercise1 = any(
        grade['subject'] == '卒業演習1' and
        grade['evaluation'] in PASS_GRADES for grade in grades
    )
    has_exercise2 = any(
        grade['subject'] == '卒業演習2' and
        grade['evaluation'] in PASS_GRADES for grade in grades
    )

    is_graduation_research_achieved = (has_seminar2 and has_thesis) or (
        has_exercise1 and has_exercise2)
    status = status_text(is_graduation_research_achieved)
    message = '満たしています' if is_graduation_research_achieved else '満たしていません'

    print(f"\n  {status} 卒業研究関連科目の要件を{message}")
    if not is_graduation_research_achieved:
        print("    「ゼミナール2」と「卒業研究」、または")
        print("    「卒業演習1」と「卒業演習2」の取得が必要です")

    # Show enrolled graduation research related subjects
    if not has_seminar2 or not has_thesis or not has_exercise1 or not has_exercise2:
        print("\n  【履修中の卒業研究関連科目】")
        if not has_seminar2:
            print("    - ゼミナール2")
        if not has_thesis:
            print("    - 卒業研究")
        if not has_exercise1:
            print("    - 卒業演習1")
        if not has_exercise2:
            print("    - 卒業演習2")


def get_department_from_code(code: str) -> str:
    """Get department name from department code"""
    with open("catalog/departments.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    for faculty in data["faculties"].values():
        for dept in faculty["departments"].values():
            if dept["code"] == code:
                return dept["name"]
    return ""


def extract_year_and_dept_code(filename: str) -> str:
    """Extract enrollment year and department code from filename (e.g., 2231017 -> 2231)"""
    try:
        filename = os.path.basename(filename)
        if len(filename) >= 4:
            # Extract first 4 characters from filename
            year_dept_code = filename[:4]
            return year_dept_code
        return ""
    except Exception as e:
        print(f"Error: {str(e)}")
        return ""


# Convert year code to actual year
def get_enrollment_year(year_code: str) -> str:
    """Convert year code (e.g., 22) to actual year (e.g., 2022年度)"""
    if len(year_code) >= 2:
        year = "20" + year_code[:2]
        return f"{year}年度"
    return ""


# Display splash screen
def show_splash_screen():
    """Display splash screen at startup"""
    splash = f"""
{Color.CYAN}   ________________           ____ {Color.RESET}
{Color.CYAN}  / ____/  _/_  __/{Color.BLUE}________ {Color.CYAN}_/ __ \\{Color.RESET}
{Color.CYAN} / /    / /  / / {Color.BLUE}/ ___/ __ `{Color.CYAN}/ / / /{Color.RESET}
{Color.CYAN}/ /____/ /  / / {Color.BLUE}/ /  / /_/ {Color.CYAN}/ /_/ / {Color.RESET}
{Color.CYAN}\\____/___/ /_/ {Color.BLUE}/_/   \\__,_/{Color.CYAN}\\___\\_\\ {Color.RESET}

{Color.BLUE}           CITraQ v{VERSION}{Color.RESET}

{Color.YELLOW}   Chiba Institute of Technology{Color.RESET}
{Color.YELLOW}          Progress Checker{Color.RESET}
"""
    print(splash)
    time.sleep(1)  # Display for 1 second


# Function to display status text
def status_text(is_achieved: bool) -> str:
    """Return colored status text based on achievement status"""
    if is_achieved:
        return f"{Color.GREEN}[達成]{Color.RESET}"
    else:
        return f"{Color.RED}[未達成]{Color.RESET}"


def use_existing_file(user_id: str = None) -> str:
    """既存の成績ファイルを探して選択する"""
    # 既存のファイルを探す
    existing_files = [f for f in os.listdir('.') if f.endswith('_grades.json')]

    # ユーザーIDが指定されている場合は、そのユーザーのファイルを優先
    if user_id:
        user_files = [f for f in existing_files if f.startswith(f"{user_id}")]
        if user_files:
            existing_files = user_files

    if existing_files:
        if len(existing_files) == 1:
            grades_file = existing_files[0]
            print(f"{Color.GREEN}ファイル {grades_file} を使用して続行します{Color.RESET}")
            return grades_file
        else:
            print(f"{Color.YELLOW}以下のファイルが見つかりました:{Color.RESET}")
            for i, file in enumerate(existing_files):
                print(f"{i+1}. {file}")
            choice = input(
                f"{Color.YELLOW}使用するファイルの番号を入力してください: {Color.RESET}")
            try:
                grades_file = existing_files[int(choice)-1]
                print(f"{Color.GREEN}ファイル {grades_file} を使用して続行します{Color.RESET}")
                return grades_file
            except (ValueError, IndexError):
                print(f"{Color.RED}無効な選択です。処理を終了します{Color.RESET}")
                sys.exit(1)
    else:
        print(f"{Color.RED}成績ファイルが見つかりません。処理を終了します{Color.RESET}")
        sys.exit(1)
    return None


def check_file_exists(file_path: str, is_grades_file: bool = True) -> str:
    """ファイルの存在確認と代替ファイルの選択"""
    if os.path.exists(file_path):
        return file_path

    # ファイルが存在しない場合
    file_type = "成績ファイル" if is_grades_file else "ファイル"
    print(f"{Color.RED}エラー: 指定された{file_type} {file_path} が見つかりません。{Color.RESET}")

    # 成績ファイルの場合のみ代替ファイルを提案
    if is_grades_file:
        try_existing = input(
            f"{Color.YELLOW}代わりに既存のファイルを使用しますか？(y/n): {Color.RESET}")
        if try_existing.lower() == 'y':
            return use_existing_file()

    print(f"{Color.RED}処理を終了します{Color.RESET}")
    sys.exit(1)


def fetch_grades_from_portal(user_id: str, password: str) -> str:
    """ポータルサイトから成績情報を取得しJSONファイルに保存"""
    if not GRADE_FETCH_AVAILABLE:
        print(
            f"{Color.RED}エラー: 成績取得機能が利用できません。cit-portal-wrapper をインストールしてください。{Color.RESET}")
        print("pip install git+https://github.com/issa06/cit-portal-wrapper.git")
        return None

    try:
        # ユーザーIDからファイル名用の数字部分を抽出（先頭のアルファベットを除去）
        file_id = user_id
        if user_id and user_id[0].isalpha():
            file_id = user_id[1:]  # 先頭の文字（アルファベット）を除去

        # 成績情報を取得（ライブラリ内で保存も行う）
        filename = f"{file_id}_grades.json"
        print(f"{Color.YELLOW}ポータルサイトから成績情報を取得中...{Color.RESET}")
        get_grades_json(user_id, password, filename)

        # ファイルが生成されたかチェック
        if os.path.exists(filename):
            print(f"{Color.GREEN}成績情報を {filename} に保存しました{Color.RESET}")
            return filename
        else:
            print(f"{Color.YELLOW}注意: 成績データファイル {filename} が見つかりません。{Color.RESET}")
            # 現在のディレクトリ内の_grades.jsonファイルを探す
            for file in os.listdir('.'):
                if file.endswith('_grades.json'):
                    print(f"{Color.GREEN}代わりに {file} を使用します{Color.RESET}")
                    return file
            print(f"{Color.RED}成績データファイルが見つかりませんでした{Color.RESET}")
            return None
    except Exception as e:
        print(f"{Color.RED}成績情報の取得に失敗しました: {str(e)}{Color.RESET}")
        # エラー発生後にファイルが生成されていないか確認
        if os.path.exists(filename):
            print(
                f"{Color.GREEN}しかし、成績データファイル {filename} が見つかりました。処理を続行します{Color.RESET}")
            return filename
        # 現在のディレクトリ内の_grades.jsonファイルを探す
        for file in os.listdir('.'):
            if file.endswith('_grades.json') and (file.startswith(f"{file_id}") or file.startswith(f"{user_id}")):
                print(
                    f"{Color.GREEN}成績データファイル {file} が見つかりました。処理を続行します{Color.RESET}")
                return file
        return None


if __name__ == "__main__":
    import sys

    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='CITraQ - 単位計算・進捗チェックツール')
    parser.add_argument('grade_file', nargs='?',
                        help='成績ファイル (例: 2231000_grades.json)')
    parser.add_argument('--get-grades', action='store_true',
                        help='ポータルサイトから成績情報を取得')
    args = parser.parse_args()

    # Display splash screen
    show_splash_screen()

    grades_file = None

    # ポータルサイトから成績情報を取得する場合
    if args.get_grades:
        user_id = input("学籍番号を入力してください: ")
        password = getpass.getpass("パスワードを入力してください: ")

        grades_file = fetch_grades_from_portal(user_id, password)
        if not grades_file:
            print(f"{Color.YELLOW}ポータルからの成績取得に失敗しました。{Color.RESET}")
            sys.exit(1)
    # 成績ファイルが指定されている場合
    elif args.grade_file:
        grades_file = check_file_exists(args.grade_file)
    # 引数が不足している場合
    else:
        parser.print_help()
        print(f"\n{Color.YELLOW}使用例:{Color.RESET}")
        print(
            f"{Color.YELLOW}  python CITraQ.py 2231000_grades.json   # 既存の成績ファイルを使用{Color.RESET}")
        print(
            f"{Color.YELLOW}  python CITraQ.py --get-grades         # ポータルから成績を取得{Color.RESET}")
        sys.exit(1)

    # 成績ファイル名から入学年度と学科コードを取得
    year_dept_code = extract_year_and_dept_code(grades_file)

    if not year_dept_code:
        print(f"{Color.RED}エラー: ファイル名から入学年度と学科コードを抽出できませんでした。{Color.RESET}")
        sys.exit(1)

    # Department code is the last 2 digits
    dept_code = year_dept_code[2:]
    dept_name = get_department_from_code(dept_code)

    # Get enrollment year (e.g., 2022年度)
    enrollment_year = get_enrollment_year(year_dept_code)

    if not dept_name:
        print(f"{Color.RED}エラー: 学科コード {dept_code} に対応する学科が見つかりません。{Color.RESET}")
        sys.exit(1)

    print(f"{Color.CYAN}==== {APP_NAME} - {enrollment_year}入学 {dept_name} ===={Color.RESET}\n")

    # Construct file paths using enrollment year and department code
    requirements_file = f"catalog/{year_dept_code}_requirements.json"
    if not os.path.exists(requirements_file):
        print(f"{Color.RED}エラー: 要件ファイル {requirements_file} が見つかりません。{Color.RESET}")
        sys.exit(1)
    requirements = load_requirements(requirements_file, dept_name)

    # Load subject list
    subjects_file = f"catalog/{year_dept_code}_subjects.json"
    if not os.path.exists(subjects_file):
        print(f"{Color.RED}エラー: 科目ファイル {subjects_file} が見つかりません。{Color.RESET}")
        sys.exit(1)
    subjects = load_subjects(subjects_file)
    patterns = create_patterns(subjects)

    # Load grades
    with open(grades_file, "r", encoding="utf-8") as f:
        grades = json.load(f)

    print(f"{Color.YELLOW}成績データを解析中...{Color.RESET}")
    time.sleep(0.5)  # Wait a bit

    # Calculate total credits
    total_credits, credits_by_category = load_grades(grades_file, patterns)

    # Run various checks
    check_requirements(total_credits, credits_by_category, requirements)
    check_specified_subjects(subjects, grades, requirements)
    check_department_specified_subjects(grades, subjects)
    check_progression_requirements(total_credits, grades)
    check_graduation_requirements(
        total_credits, credits_by_category, grades, requirements
    )

    print(f"\n{Color.CYAN}==== {APP_NAME} 実行完了 ===={Color.RESET}")
