# 定数の定義
SUBJECT_ID = 0
CATEGORY = 1
FACULTY = 2
YEAR = 3
SUBJECT = 4
SUBJECT_KANA = 5
TEACHER = 6
TEACHER_KANA = 7
SEMESTER = 8
TIMETABLE = 9
WEEK = 10
PERIOD = 11
SCHOOL_YEAR = 12
UNITS = 13
CAMPUS = 14
LANGUAGE = 15
MODALITY_CATEGORIES = 16
TYPE = 17
DESCRIPTION = 18
URL = 19

SYLLABUS_URL = "https://www.wsl.waseda.jp/syllabus/JAA101.php"

#CSVファイルヘッダー項目
HEADER = [
    "授業ID", "科目区分", "学部", "年度", "科目名", "カモクメイ", "教員名", "フリガナ", "学期", "曜日時限",
    "曜日", "時限", "学年", "単位数", "キャンパス", "使用言語", "授業形式", "授業形態", "授業概要", "シラバスURL"
]
SUBJECT_DATA_HEADER = ["授業ID", "学部", "科目名", "教員名", "曜日時限", "学期", "曜日", "時限"]

# 対象学部のリスト
FACULTIES = [
    "政経", "法学", "教育", "商学", "社学", "人科", "スポーツ", "国際教養", "文構", "文", "基幹", "創造",
    "先進", "グローバル"
]

FACULTIES_MAP = {
    "政経": "A_政治経済学部",
    "法学": "B_法学部",
    "教育": "E_教育学部",
    "商学": "F_商学部",
    "社学": "H_社会科学部",
    "人科": "J_人間科学部",
    "スポーツ": "K_スポーツ科学部",
    "国際教養": "M_国際教養学部",
    "文構": "T_文化構想学部",
    "文": "U_文学部",
    "基幹": "W_基幹理工学部",
    "創造": "X_創造理工学部",
    "先進": "Y_先進理工学部",
    "グローバル": "G_GEC"
}
