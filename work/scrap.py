import os
import csv
import datetime
import time
import subprocess
import re
from fugashi import Tagger
from logging import getLogger, handlers, Formatter, DEBUG, ERROR
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from mojimoji import zen_to_han
from bs4 import BeautifulSoup

# 定数の定義
FACULTY = 0
CODE = 1
CATEGORY = 2
SUBJECT = 3
SUBJECT_KANA = 4
TEACHER = 5
TERM = 6
PERIOD = 7
TYPE = 8
DESCRIPTION = 9

# 対象学部のリスト
# FACULTIES = ["政経", "法学", "教育", "商学", "社学", "国際教養", "文構", "文", "基幹", "創造", "先進", "人科", "スポーツ", "グローバル"]
FACULTIES = ["創造"]

# カテゴリ定義
CATEGORIES = {
    "基幹": [
        "A群：複合領域",
        "A群：外国語-英語",
        "A群：外国語-初修外国語",
        "B群：数学",
        "B群：自然科学",
        "B群：実験・実習・製作",
        "B群：情報関連科目",
        "数学科（専門科目）",
        "応用数理学科（専門科目）",
        "情報理工学科（専門科目）",
        "電子物理システム学科（専門科目）",
        "表現工学科（専門科目）",
        "情報通信学科（専門科目）",
        "機械科学・航空宇宙学科（専門科目）",
        "",
    ],
    "創造": [
        "A群：複合領域",
        "A群：外国語-英語",
        "A群：外国語-初修外国語",
        "B群：数学",
        "B群：自然科学",
        "B群：実験・実習・製作",
        "B群：情報関連科目",
        "C群：創造理工学部共通科目",
        "建築学科（専門科目）",
        "総合機械工学科（専門科目）",
        "経営システム工学科（専門科目）",
        "社会環境工学科（専門科目）",
        "環境資源工学科（専門科目）",
        "",
    ],
    "先進": [
        "A群：複合領域",
        "A群：外国語-英語",
        "A群：外国語-初修外国語",
        "B群：数学",
        "B群：自然科学",
        "B群：実験・実習・製作",
        "B群：情報関連科目",
        "物理学科（専門科目）",
        "応用物理学科（専門科目）",
        "化学・生命化学科（専門科目）",
        "応用化学科（専門科目）",
        "生命医科学科（専門科目）",
        "電気・情報生命工学科（専門科目）",
        "",
    ]
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

# ロガーの設定
def set_logger():
    """
    ログを設定する関数。
    ログをファイルに書き出し、ログが100KB溜まったら新しいファイルを作成。
    """
    log_file = "./app.log"
    # 既存のログファイルがあれば削除
    if os.path.exists(log_file):
        os.remove(log_file)

    logger = getLogger()
    logger.setLevel(DEBUG)
    handler = handlers.RotatingFileHandler(log_file, maxBytes=100 * 1024, backupCount=3, encoding="utf-8")
    formatter = Formatter("%(asctime)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    block_logger = getLogger()
    block_logger.setLevel(ERROR)  # DEBUGやINFOなどのレベルのログを無視
    main_logger = getLogger("__main__")
    main_logger.setLevel(DEBUG)

# ログ出力関数
def log(arg, level=DEBUG):
    """
    ログを出力するための関数。
    
    Args:
        arg: ログメッセージ。
        level: ログレベル。
    """
    logger = getLogger(__name__)
    if level == DEBUG:
        logger.debug(arg)
    elif level == ERROR:
        logger.error(arg)

# 現在の年と月を取得する関数
def get_current_date():
    """
    現在の年と月を取得する関数。
    
    Returns:
        現在の年と月。
    """
    now = datetime.datetime.now()
    return now.year, now.month

# バージョンチェック関数
def check_versions():
    """
    Google ChromeとChromedriverのバージョンをチェックし、ログに出力する関数。
    """
    try:
        chrome_version = subprocess.run(["google-chrome", "--version"], capture_output=True, text=True)
        log("Google Chrome version:"+chrome_version.stdout.strip())
    except FileNotFoundError:
        log("Google Chrome is not installed or not found in the PATH.", ERROR)

    try:
        chromedriver_version = subprocess.run(["chromedriver", "--version"], capture_output=True, text=True)
        log("Chromedriver version:"+chromedriver_version.stdout.strip())
    except FileNotFoundError:
        log("Chromedriver is not installed or not found in the PATH.", ERROR)

# WebDriverの初期化
def init_driver():
    """
    Chrome WebDriverを初期化する関数。
    
    Returns:
        WebDriverインスタンス。
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--verbose")

    return webdriver.Remote(command_executor="http://selenium:4444/wd/hub", options=chrome_options)

# シラバスデータをスクレイピングする関数
def scrape_syllabus_data(driver, dest_dir):
    """
    シラバスデータをスクレイピングしてCSVファイルに保存する関数。

    Args:
        driver: WebDriverインスタンス。
        dest_dir: データ保存先ディレクトリ。
    """
    log("Accessing Waseda's syllabus\n")
    driver.get("https://www.wsl.waseda.jp/syllabus/JAA101.php")

    for faculty in FACULTIES:
        log(f"Accessing {faculty} syllabus")
        faculty_file = f"{dest_dir}/raw_syllabus_data_{faculty}.csv"

        with open(faculty_file, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["学部", "コースコード", "カテゴリ", "科目名","カモクメイ", "担当教員", "学期", "曜日時限", "授業形式", "授業概要"])

            select = Select(driver.find_element(By.NAME, "p_gakubu"))
            select.select_by_visible_text(faculty)

            if faculty in CATEGORIES:
                scrape_data_for_faculty_and_categories(driver, writer, faculty)
            else:
                scrape_data_for_faculty_without_category(driver, writer, faculty)

# カテゴリあり学部のデータをスクレイピングする関数
def scrape_data_for_faculty_and_categories(driver, writer, faculty):
    """
    カテゴリが定義されている学部のデータをスクレイピングする関数。

    Args:
        driver: WebDriverインスタンス。
        writer: CSVライターオブジェクト。
        faculty: 学部名。
    """
    log(f"Scraping {faculty} data.")
    start_time = time.time()
    seen_subjects = set()  # 重複回避のためのセットを用意
    total_elements = 0
    duplicate_count=0

    for category in CATEGORIES[faculty]:
        log(f"Scraping {faculty} - {category} data.")
        start_category_time = time.time()
        select = Select(driver.find_element(By.NAME, "p_keya"))
        select.select_by_visible_text(category)
        total_category_elements = 0

        driver.execute_script("func_search('JAA103SubCon');")  # 検索を実行
        driver.execute_script("func_showchg('JAA103SubCon', '1000');")  # 表示数を1000に変更

        while True:
            try:
                soup = BeautifulSoup(driver.page_source, "html.parser")
                rows = soup.select("#cCommon div div div div div:nth-child(1) div:nth-child(2) table tbody tr")
                for row in rows[1:]:
                    cols = row.find_all("td")
                    course_code = cols[1].text.strip()
                    subject_name = cols[2].text.strip()
                    teacher_name = cols[3].text.strip()
                    semester = cols[5].text.strip()
                    period = cols[6].text.strip()
                    classroom = cols[7].text.strip()
                    description = cols[8].text.strip()


                    if category=="":
                        if (course_code, subject_name, teacher_name, semester, period, classroom) in seen_subjects:
                            log(f"Skipping duplicate subject: {subject_name} - {teacher_name} - {semester}")
                            duplicate_count+=1
                            continue
                    
                    if category!="":    
                        # 重複がなければセットに追加
                        seen_subjects.add((course_code, subject_name, teacher_name, semester, period, classroom))
                    
                    writer.writerow([
                        faculty,
                        course_code,
                        category,
                        subject_name,
                        "",
                        teacher_name,
                        semester,
                        period,
                        "",
                        description,
                    ])
                    total_category_elements += 1
                    total_elements += 1
                # 次のページへ
                driver.find_element(By.XPATH, "//*[@id='cHonbun']/div[2]/table/tbody/tr/td[3]/div/div/p/a").click()
            except NoSuchElementException:
                break
        log(f"Total Number of Subjects {faculty} - {category}: {total_category_elements}")
        log(f"Finished in {time.time() - start_category_time:.6f} seconds\n")
        driver.find_element(By.CLASS_NAME, "ch-back").click()

    log(f"Total Number of Subjects {faculty}: {total_elements}")
    log(f"duplicate_count={duplicate_count}")
    log(f"Finished in {time.time() - start_time:.6f} seconds\n")


# カテゴリなし学部のデータをスクレイピングする関数
def scrape_data_for_faculty_without_category(driver, writer, faculty):
    """
    カテゴリが定義されていない学部のデータをスクレイピングする関数。

    Args:
        driver: WebDriverインスタンス。
        writer: CSVライターオブジェクト。
        faculty: 学部名。
    """
    log(f"Scraping {faculty} data.")
    start_time = time.time()
    total_elements = 0

    driver.execute_script("func_search('JAA103SubCon');")  # 検索を実行
    driver.execute_script("func_showchg('JAA103SubCon', '1000');")  # 表示数を1000に変更

    while True:
        try:
            soup = BeautifulSoup(driver.page_source, "html.parser")
            rows = soup.select("#cCommon div div div div div:nth-child(1) div:nth-child(2) table tbody tr")
            total_elements += len(rows[1:])
            for row in rows[1:]:
                cols = row.find_all("td")
                writer.writerow([
                    faculty,
                    cols[1].text.strip(),
                    "",
                    cols[2].text.strip(),
                    "",
                    cols[3].text.strip(),
                    cols[5].text.strip(),
                    cols[6].text.strip(),
                    "",
                    cols[8].text.strip(),
                ])
            # 次のページへ
            driver.find_element(By.XPATH, "//*[@id='cHonbun']/div[2]/table/tbody/tr/td[3]/div/div/p/a").click()
        except NoSuchElementException:
            break
    log(f"Total Number of Subjects {faculty}: {total_elements}")
    log(f"Finished in {time.time() - start_time:.6f} seconds\n")
    driver.find_element(By.CLASS_NAME, "ch-back").click()

def format_syllabus_data(source_path, dest_path):
    tagger = Tagger()

    def get_furigana(text):
        """
        科目名にふりがなを追加する関数。

        Args:
            subject_name: 科目名。
        
        Returns:
            ふりがな付きの科目名。
        """
        words = tagger(text)
        furigana = "".join([word.feature.kana if word.feature.kana else word.surface for word in words])
        return furigana

    def get_class_type(code):
        class_type_code = code[-1]
        return CLASS_TYPE_MAP.get(class_type_code, "不明")

    def adjust_teacher_name(teacher_name):
        """
        教員名のフォーマット関数。
        
        Args:
            teacher_name: 教員名。
        
        Returns:
            フォーマットされた教員名。
        """
        # スラッシュの数を数えて、2つ以上の場合は「オムニバス」に変更
        if teacher_name.count("/") >= 2:
            return "オムニバス"
        
        # 1つのスラッシュを「･」に置き換える
        if teacher_name.count("/") == 1:
            teacher_name = teacher_name.replace("/", "･")
        
        # 全ての名前がローマ字でスペースが含まれている場合、スペースをピリオドに置き換える
        names = teacher_name.split("･")
        for i, name in enumerate(names):
            if re.search(r'[ァ-ン]', name):
                names[i] = name.replace(" ", ".")
        return "･".join(names)
        
    def remove_newlines(text):
            return text.replace("\n", "").replace("\r", "")    
    
    with open(source_path, "r", newline="", encoding="utf-8") as source, open(dest_path, "w", newline="", encoding="utf-8") as dest:
        reader = csv.reader(source)
        writer = csv.writer(dest)
        writer.writerow(["学部", "コースコード", "カテゴリ", "科目名","カモクメイ", "担当教員", "学期", "曜日時限", "授業形式", "授業概要"])

        rows = list(reader)
        
        for row in rows[1:]:
            try:
                han_row = [zen_to_han(cell, kana=False) for cell in row]
                han_row[SUBJECT_KANA] = get_furigana(han_row[SUBJECT])
                han_row[TEACHER] = adjust_teacher_name(han_row[TEACHER])
                han_row[TYPE] = get_class_type(han_row[CODE])
                han_row[DESCRIPTION] = remove_newlines(han_row[DESCRIPTION])
                writer.writerow(han_row)
            except Exception as e:
                log(f"Error processing row: {row} - {e}", ERROR)


def convert_to_utf8_with_bom(source_file, dest_file):
    with open(source_file, "r", newline="", encoding="utf-8") as source:
        content = source.read()
    
    with open(dest_file, "w", newline="", encoding="utf-8-sig") as dest:
        dest.write(content)


def run():
    set_logger()
    log("==========Scraping started============")
    start_time = time.time()
    
    try:
        check_versions()
        year, month = get_current_date()
        base_dir = f"../data/{year}_{month}"
        mac_dir = os.path.join(base_dir, "forMac")
        windows_dir = os.path.join(base_dir, "forWindows")

        os.makedirs(mac_dir, exist_ok=True)
        os.makedirs(windows_dir, exist_ok=True)

        driver = init_driver()
    except Exception as e:
        log(f"Error : {e}", ERROR)
        return

    try:
        scrape_syllabus_data(driver, base_dir)
    finally:
        driver.quit()

    for faculty in FACULTIES:
        log(f"Formatting {faculty} data.")
        source_file = os.path.join(base_dir, f"raw_syllabus_data_{faculty}.csv")
        mac_file = os.path.join(mac_dir, f"syllabus_data_{faculty}.csv")
        windows_file = os.path.join(windows_dir, f"syllabus_data_{faculty}.csv")
        
        format_syllabus_data(source_file, mac_file)
        convert_to_utf8_with_bom(mac_file, windows_file)

    log(f"Total Execution Time {time.time() - start_time:.6f} seconds")
    log("==========Scraping completed==========")
    

if __name__ == "__main__":
    run()
