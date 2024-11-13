# 定数の定義
CATEGORY = 0
SUBJECT_ID = 1
FACULTY = 2
YEAR = 3
COURSE_CODE = 4
SUBJECT = 5
SUBJECT_KANA = 6
TEACHER = 7
TEACHER_KANA = 8
SEMESTER = 9
TIMETABLE = 10
WEEK = 11
PERIOD = 12
SCHOOL_YEAR = 13
UNITS = 14
ROOM = 15
CAMPUS = 16
SUBJECT_KEY = 17
SUBJECT_CLASS = 18
LANGUAGE = 19
MODALITY_CATEGORIES = 20
LEVEL = 21
TYPE = 22
DESCRIPTION = 23
URL = 24

SYLLABUS_URL="https://www.wsl.waseda.jp/syllabus/JAA101.php"

#CSVファイルヘッダー項目
HEADER=["科目区分", "授業ID", "学部", "年度", "コースコード", "科目名", "カモクメイ", "教員名", "フリガナ", "学期", "曜日時限", "曜日", "時限", "学年", "単位数", "教室", "キャンパス", "科目キー", "科目クラス", "使用言語", "授業形式", "レベル", "授業形態", "授業概要", "シラバスURL"]

# 対象学部のリスト
FACULTIES = ["政経", "法学", "教育", "商学", "社学", "人科", "スポーツ", "国際教養", "文構", "文", "基幹", "創造", "先進", "グローバル"]

FACULTIES_MAP={
    "政経":"A_政治経済学部",
    "法学":"B_法学部",
    "教育":"E_教育学部",
    "商学":"F_商学部",
    "社学":"H_社会科学部",
    "人科":"J_人間科学部",
    "スポーツ":"K_スポーツ科学部",
    "国際教養":"M_国際教養学部",
    "文構":"T_文化構想学部",
    "文":"U_文学部",
    "基幹":"W_基幹理工学部",
    "創造":"X_創造理工学部",
    "先進":"Y_先進理工学部",
    "グローバル":"G_GEC"
}

# コースコードの末尾に基づく授業形式のマッピング
CLASS_TYPE_MAP = {
    "L": "講義",
    "S": "演習/ゼミ",
    "W": "実習/実験/実技",
    "F": "外国語",
    "P": "実践/フィールドワーク",
    "G": "研究",
    "T": "論文",
    "B": "対面+オンデマンド",
    "O": "オンデマンド",
    "X": "その他"
}
