import os
import csv
import datetime
import time
import re
from fugashi import Tagger # type: ignore
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
TEACHER_KANA = 6
TERM = 7
PERIOD = 8
TYPE = 9
DESCRIPTION = 10

# 対象学部のリスト
FACULTIES = ["政経", "法学", "教育", "商学", "社学", "国際教養", "文構", "文", "基幹", "創造", "先進", "人科", "スポーツ", "グローバル"]

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

def get_current_date():
    """
    現在の年と月を取得する関数。
    
    Returns:
        現在の年と月。
    """
    now = datetime.datetime.now()
    return now.year, now.month


def init_driver():
    """
    Chrome WebDriverを初期化する関数。
    
    Returns:
        WebDriverインスタンス。
    """
    options = Options()
    options.add_argument("--headless")  # ヘッドレスモードで実行
    options.add_argument("--disable-gpu")  # GPUの無効化
    options.add_argument("--no-sandbox")  # サンドボックスを無効化
    options.add_argument("--disable-dev-shm-usage")  # /dev/shmの使用を無効化
    options.add_argument("--verbose")  # 詳細なログを出力
    return webdriver.Remote(command_executor="http://selenium:4444/wd/hub", options=options)

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
            writer.writerow(["学部", "コースコード", "カテゴリ", "科目名", "カモクメイ", "担当教員", "フリガナ", "学期", "曜日時限", "授業形式", "授業概要"])

            select = Select(driver.find_element(By.NAME, "p_gakubu"))
            select.select_by_visible_text(faculty)

            if faculty in CATEGORIES:
                scrape_data_categories(driver, writer, faculty)
            else:
                scrape_data_without_category(driver, writer, faculty)


def scrape_data_categories(driver, writer, faculty):
    """
    スクレイピングを実行し、カテゴリが定義されている学部のデータをCSVに書き出します。

    Args:
        driver: WebDriverインスタンス。
        writer: CSVライターオブジェクト。
        faculty: 学部名。
    """
    start_time = time.time()
    seen_subjects = set()
    total_elements = 0
    duplicate_count=0
    for category in CATEGORIES.get(faculty, []):
        log(f"Scraping {faculty} - {category} data.")
        start_category_time = time.time()
        total_category_elements = 0

        # カテゴリ選択
        select = Select(driver.find_element(By.NAME, "p_keya"))
        select.select_by_visible_text(category)

        # 検索と表示数変更
        driver.execute_script("func_search('JAA103SubCon');")
        driver.execute_script("func_showchg('JAA103SubCon', '1000');")

        while True:
            try:
                soup = BeautifulSoup(driver.page_source, "html.parser")
                rows = soup.select("#cCommon div div div div div:nth-child(1) div:nth-child(2) table tbody tr")

                for row in rows[1:]:
                    cols = row.find_all("td")
                    code = cols[1].text.strip()
                    subject = cols[2].text.strip()
                    teacher = cols[3].text.strip()
                    semester = cols[5].text.strip()
                    period = cols[6].text.strip()
                    room = cols[7].text.strip()
                    desc = cols[8].text.strip()

                    if category == "" and (code, subject, teacher, semester, period, room) in seen_subjects:
                        duplicate_count += 1
                        continue
                    
                    if category!="":    
                        # 重複がなければセットに追加
                        seen_subjects.add((code, subject, teacher, semester, period, room))
                    
                    writer.writerow([
                        faculty,
                        code,
                        category,
                        subject,
                        "",
                        teacher,
                        "",
                        semester,
                        period,
                        "",
                        desc,
                    ])
                    total_category_elements += 1
                    total_elements += 1

                # 次のページへ
                driver.find_element(By.XPATH, "//*[@id='cHonbun']/div[2]/table/tbody/tr/td[3]/div/div/p/a").click()
            except NoSuchElementException:
                break

        log(f"Subjects: {total_category_elements} Time: {time.time() - start_category_time:.6f} seconds\n")
        driver.find_element(By.CLASS_NAME, "ch-back").click()

    log(f"All {faculty} Subjects: {total_elements} Time: {time.time() - start_time:.6f} seconds\n")


def scrape_data_without_category(driver, writer, faculty):
    """
    スクレイピングを実行し、カテゴリが定義されていない学部のデータをCSVに書き出します。

    Args:
        driver: WebDriverインスタンス。
        writer: CSVライターオブジェクト。
        faculty: 学部名。
    """
    log(f"Scraping {faculty} data.")
    start_time = time.time()
    total_elements = 0

    # 検索と表示数変更
    driver.execute_script("func_search('JAA103SubCon');")
    driver.execute_script("func_showchg('JAA103SubCon', '1000');")

    while True:
        try:
            soup = BeautifulSoup(driver.page_source, "html.parser")
            rows = soup.select("#cCommon div div div div div:nth-child(1) div:nth-child(2) table tbody tr")

            for row in rows[1:]:
                cols = row.find_all("td")
                writer.writerow([
                    faculty,
                    cols[1].text.strip(),
                    "",
                    cols[2].text.strip(),
                    "",
                    cols[3].text.strip(),
                    "",
                    cols[5].text.strip(),
                    cols[6].text.strip(),
                    "",
                    cols[8].text.strip(),
                ])
                total_elements += 1

            # 次のページへ
            driver.find_element(By.XPATH, "//*[@id='cHonbun']/div[2]/table/tbody/tr/td[3]/div/div/p/a").click()
        except NoSuchElementException:
            break

    log(f"Subjects: {total_elements} Time: {time.time() - start_time:.6f} seconds\n")
    driver.find_element(By.CLASS_NAME, "ch-back").click()


def get_furigana(text):
    """
    テキストにふりがなを追加する関数。

    Args:
        text: テキスト。
    
    Returns:
        ふりがな付きのテキスト。
    """
    tagger = Tagger()
    furigana = "".join(word.feature.kana or word.surface for word in tagger(text))
    return furigana

def get_class_type(code):
    """
    コードに基づいて授業形式を取得する関数。

    Args:
        code: 授業コード。
    
    Returns:
        授業形式の文字列。

    Raises:
        ValueError: コードが空の場合に発生。
    """
    if not code:
        raise ValueError("授業コードが空です。")

    return CLASS_TYPE_MAP.get(code[-1], "不明")


def format_teacher_name(name):
    """
    教員名のフォーマット関数。
    
    Args:
        name: 教員名。
    
    Returns:
        フォーマットされた教員名。
    """
    # スラッシュの数を数えて、2つ以上の場合は「オムニバス」に変更
    if name.count("/") >= 2:
        return "オムニバス"
    
    # スラッシュの数を数えて、1つの場合は「/」を「･」に置き換える
    if name.count("/") == 1:
        name = name.replace("/", "･")
    
    # 全ての名前がカタカナでスペースが含まれている場合、スペースをピリオドに置き換える
    names = name.split("･")
    for i, name in enumerate(names):
        if re.search(r'[ァ-ン]', name):
            names[i] = name.replace(" ", ".")
    return "･".join(names)


def remove_newlines(text):
    return text.replace("\n", "").replace("\r", "")    


def format_syllabus_data(src_path, dest_path):
    """
    Format the syllabus data by converting it to half-width characters, 
    generating furigana, adjusting teacher names, and more.

    :param src_path: Path to the source CSV file.
    :param dest_path: Path to the destination CSV file.
    """
    try:
        with open(src_path, "r", newline="", encoding="utf-8") as source, \
             open(dest_path, "w", newline="", encoding="utf-8") as dest:
            reader = csv.reader(source)
            writer = csv.writer(dest)
            writer.writerow(["学部", "コースコード", "カテゴリ", "科目名", "カモクメイ", "担当教員", "フリガナ", "学期", "曜日時限", "授業形式", "授業概要"])
            rows = list(reader)
        
            for row in rows[1:]:
                try:
                    han_row = [zen_to_han(cell, kana=False) for cell in row]
                    han_row[SUBJECT_KANA] = get_furigana(han_row[SUBJECT])
                    han_row[TEACHER] = format_teacher_name(han_row[TEACHER])
                    han_row[TEACHER_KANA] = get_furigana(han_row[TEACHER])
                    han_row[TYPE] = get_class_type(han_row[CODE])
                    han_row[DESCRIPTION] = remove_newlines(han_row[DESCRIPTION])
                    writer.writerow(han_row)
                except Exception as e:
                    log(f"Error processing row {row}: {e}", ERROR)
    except IOError as e:
        log(f"File I/O error: {e}", ERROR)
    except Exception as e:
        log(f"Unexpected error: {e}", ERROR)

def convert_to_utf8_sig(src_file, dest_file):
    """
    Convert the content of a file from UTF-8 to UTF-8 with BOM (UTF-8-SIG).

    :param src_file: Path to the source file.
    :param dest_file: Path to the destination file.
    """
    with open(src_file, "r", encoding="utf-8") as src,\
          open(dest_file, "w", encoding="utf-8-sig") as dest:
        dest.write(src.read())



def run():
    set_logger()
    log("==========Scraping started============")
    start_time = time.time()
    driver = init_driver()
    
    year, month = get_current_date()
    base_dir = f"../data/{year}_{month}"
    row_dir = os.path.join(base_dir, "rowData")
    mac_dir = os.path.join(base_dir, "forMac")
    win_dir = os.path.join(base_dir, "forWin")

    os.makedirs(row_dir, exist_ok=True)
    os.makedirs(mac_dir, exist_ok=True)
    os.makedirs(win_dir, exist_ok=True)

    try:
        scrape_syllabus_data(driver, row_dir)
    finally:
        driver.quit()

    for faculty in FACULTIES:
        log(f"Formatting {faculty} data.")
        row_file = os.path.join(row_dir, f"raw_syllabus_data_{faculty}.csv")
        mac_file = os.path.join(mac_dir, f"syllabus_data_{faculty}.csv")
        win_file = os.path.join(win_dir, f"syllabus_data_{faculty}.csv")
        
        format_syllabus_data(row_file, mac_file)
        convert_to_utf8_sig(mac_file, win_file)

    log(f"Total Execution Time {time.time() - start_time:.6f} seconds")
    log("==========Scraping completed==========")
    

if __name__ == "__main__":
    run()
