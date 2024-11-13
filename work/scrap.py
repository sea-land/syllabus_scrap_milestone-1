import os
import csv
import datetime
import time
import shutil
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

def set_logger():
    """
    ログを設定する関数。
    ログをファイルに書き出し、ログが100KB溜まったら新しいファイルを作成。
    """
    log_file = "./log/app.txt"

    logger = getLogger()
    logger.setLevel(DEBUG)
    handler = handlers.RotatingFileHandler(log_file, maxBytes=100 * 1024, backupCount=3, encoding="utf-8-sig")
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
    # options.add_argument("--headless")  # ヘッドレスモードで実行
    options.add_argument("--disable-gpu")  # GPUの無効化
    options.add_argument("--no-sandbox")  # サンドボックスを無効化
    options.add_argument("--disable-dev-shm-usage")  # /dev/shmの使用を無効化
    options.add_argument("--verbose")  # 詳細なログを出力
    return webdriver.Remote(command_executor="http://selenium:4444/wd/hub", options=options)

def scrape_syllabus_data(driver, faculty, dest_dir):
    """
    シラバスデータをスクレイピングしてCSVファイルに保存する関数。

    Args:
        driver: WebDriverインスタンス。
        dest_dir: データ保存先ディレクトリ。
    """
    log(f"{FACULTIES_MAP[faculty]} のシラバスにアクセスしています。")
    dest_path = os.path.join(dest_dir, f"{FACULTIES_MAP[faculty]}_raw_syllabus_data.csv")

    driver.get("https://www.wsl.waseda.jp/syllabus/JAA101.php")
    select = Select(driver.find_element(By.NAME, "p_gakubu"))
    select.select_by_visible_text(faculty)

    # 表示数変更
    driver.execute_script("func_search('JAA103SubCon');")
    # driver.execute_script("page_turning('JAA103SubCon',167);")
    driver.execute_script("func_showchg('JAA103SubCon', '2000');")
    log(f"{faculty} の科目インデックスを取得中です。")
    start_time = time.time()
    total_elements = 0

    with open(dest_path, "w", newline="", encoding="utf-8-sig") as dest:
        writer=csv.writer(dest)
        writer.writerow(HEADER)
        total_elements = 0
        while True:
            try:
                soup = BeautifulSoup(driver.page_source, "html.parser")
                rows = soup.select("#cCommon div div div div div:nth-child(1) div:nth-child(2) table tbody tr")
                for row in rows[1:]:
                    read_row = [""] * 25

                    cols = row.find_all("td")
                    read_row[FACULTY] = faculty
                    read_row[YEAR] = cols[0].text.strip()
                    read_row[COURSE_CODE] = cols[1].text.strip()
                    read_row[SUBJECT] = cols[2].text.strip()
                    read_row[TEACHER] = cols[3].text.strip()
                    read_row[SEMESTER] = cols[5].text.strip()
                    read_row[TIMETABLE] = cols[6].text.strip()
                    read_row[ROOM] = cols[7].text.strip()
                    read_row[DESCRIPTION] = remove_newlines(cols[8].text.strip())

                    # 科目の詳細ページのリンクを取得
                    link_element = cols[2].find("a", onclick=True)
                    if link_element:
                        onclick_value = link_element['onclick']
                        # 'post_submit('JAA104DtlSubCon', '1100001010012024110000101011')' から pKey を抽出
                        pkey = onclick_value.split("'")[3]
                        read_row[URL] = f"https://www.wsl.waseda.jp/syllabus/JAA104.php?pKey={pkey}&pLng=jp"
                    else:
                        read_row[URL] = ""
                    writer.writerow(read_row)
                    total_elements+=1

                # 次のページへ
                driver.find_element(By.XPATH, "//*[@id='cHonbun']/div[2]/table/tbody/tr/td[3]/div/div/p/a").click()
            except NoSuchElementException:
                break

        log(f"総科目数: {total_elements} 実行時間: {time.time() - start_time:.6f} 秒\n")


def add_details(driver, faculty, row_dir, row_detail_dir):
    log(f"{FACULTIES_MAP[faculty]} の詳細情報を追加します。")
    src_path = os.path.join(row_dir, f"{FACULTIES_MAP[faculty]}_raw_syllabus_data.csv")
    dest_path = os.path.join(row_detail_dir, f"{FACULTIES_MAP[faculty]}_raw_syllabus_data.csv")

    with open(src_path, "r", newline="", encoding="utf-8-sig") as source, \
         open(dest_path, "w", newline="", encoding="utf-8-sig") as dest:
        reader=csv.reader(source)
        writer=csv.writer(dest)
        writer.writerow(HEADER)
        rows=list(reader)
        total_elements = 0
        for row in rows[1:]:
            if(total_elements%100==0):log(f"{total_elements}/{len(rows)-1}件完了(100件完了ごとに更新されます)")
            detail_url = row[URL]
            
            driver.get(detail_url)
            detail_page = BeautifulSoup(driver.page_source, "html.parser")

            # テーブルのすべての行とセルを2次元リストに変換
            table_data = [
                [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
                for row in detail_page.select("#cEdit > div:nth-child(1) > div > div > div > div > div.ctable-main > table > tbody > tr")
            ]

            # 項目が存在しない場合は空欄をデフォルトにする
            def safe_get(data, row_idx, col_idx):
                try:
                    return data[row_idx][col_idx]
                except IndexError:
                    return ""
            read_row = row
            # 各フィールドのデータ取得
            # read_row[YEAR] = safe_get(table_data, 0, 1)
            # read_row[FACULTY] = faculty
            # read_row[SUBJECT] = safe_get(table_data, 1, 1)
            # read_row[TEACHER] = safe_get(table_data, 2, 1)
            # read_row[TIMETABLE] = safe_get(table_data, 3, 1)
            read_row[CATEGORY] = safe_get(table_data, 4, 1)
            read_row[SCHOOL_YEAR] = safe_get(table_data, 4, 3)
            read_row[UNITS] = safe_get(table_data, 4, 5)
            # room = safe_get(5,1)
            read_row[CAMPUS] = safe_get(table_data, 5, 3)
            read_row[SUBJECT_KEY] = safe_get(table_data, 6, 1)
            read_row[SUBJECT_CLASS] = safe_get(table_data, 6, 3)
            read_row[LANGUAGE] = safe_get(table_data, 7, 1)
            read_row[MODALITY_CATEGORIES] = safe_get(table_data, 8, 1)
            read_row[LEVEL] = safe_get(table_data, 13, 1)
            read_row[TYPE] = safe_get(table_data, 13, 3)

            writer.writerow(read_row)
            total_elements+=1

        log(f"{total_elements}/{len(rows)-1}件完了\n")



def get_furigana(text):
    """
    テキストにふりがなを追加する関数。

    Args:
        text: テキスト。
    
    Returns:
        ふりがな付きのテキスト。
    """
    tagger = Tagger()
    furigana = " ".join(word.feature.kana or word.surface for word in tagger(text))
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

def split_clss_date(date):
    if re.search(r'[:]', date):
        return date, "", ""
    else:
        return date, date[0], date[1]


def remove_newlines(text):
    return text.replace("\n", "/").replace("\r", "/")


def format_syllabus_data(faculty, row_detail_dir, formatted_data):
    """
    Format the syllabus data by converting it to half-width characters, 
    generating furigana, adjusting teacher names, and more.

    :param src_path: Path to the source CSV file.
    :param dest_path: Path to the destination CSV file.
    """
    log(f"{FACULTIES_MAP[faculty]} をフォーマットしています。")
    src_path = os.path.join(row_detail_dir, f"{FACULTIES_MAP[faculty]}_raw_syllabus_data.csv")
    dest_path = os.path.join(formatted_data, f"{FACULTIES_MAP[faculty]}_科目ノートの素.csv")

    try:
        with open(src_path, "r", newline="", encoding="utf-8-sig") as source, \
             open(dest_path, "w", newline="", encoding="utf-8-sig") as dest:
            reader = csv.reader(source)
            writer = csv.writer(dest)
            writer.writerow(HEADER)
            rows = list(reader)
        
            for row in rows[1:]:
                try:
                    han_row = [zen_to_han(cell, kana=False) if cell else "" for cell in row]
                    han_row[SUBJECT_KANA] = get_furigana(han_row[SUBJECT]) if han_row[SUBJECT] else ""
                    han_row[TEACHER] = format_teacher_name(han_row[TEACHER]) if han_row[TEACHER] else ""
                    han_row[TEACHER_KANA] = get_furigana(han_row[TEACHER]) if han_row[TEACHER] else ""
                    han_row[TIMETABLE], han_row[WEEK], han_row[PERIOD] = split_clss_date(han_row[TIMETABLE]) if han_row[TIMETABLE] else "" "" ""
                    han_row[TYPE] = get_class_type(han_row[COURSE_CODE]) if han_row[COURSE_CODE] else ""
                    writer.writerow(han_row)
                except Exception as e:
                    log(f"{row}行目でエラー: {e}", ERROR)
    except IOError as e:
        log(f"File I/O error: {e}", ERROR)
    except Exception as e:
        log(f"Unexpected error: {e}", ERROR)


def expand_timetable(row):
    timetable = row[TIMETABLE]
    common_data1 = row[:TIMETABLE]
    common_data2 = row[MODALITY_CATEGORIES:]
    time_data = []
    expanded_rows = []

    if ":" in timetable:
        time = timetable.split(":")
        for timetable in time[1:]:
            timetable, week, period = split_clss_date(timetable)
            time_data=[timetable, week, period]
            expanded_rows.append(common_data1 + time_data + common_data2)
    else:
        time_data=[timetable, timetable[0], timetable[1]]
        expanded_rows.append(common_data1 + time_data + common_data2)
    return expanded_rows


def create_subject_data(faculty, row_detail_dir, formatted_data):
    """
    Format the syllabus data by converting it to half-width characters, 
    generating furigana, adjusting teacher names, and more.

    :param src_path: Path to the source CSV file.
    :param dest_path: Path to the destination CSV file.
    """
    log(f"{FACULTIES_MAP[faculty]} の科目データを作成しています。")
    src_path = os.path.join(row_detail_dir, f"{FACULTIES_MAP[faculty]}_科目ノートの素.csv")
    dest_path = os.path.join(formatted_data, f"{FACULTIES_MAP[faculty]}_科目データ.csv")

    try:
        with open(src_path, "r", newline="", encoding="utf-8-sig") as source, \
             open(dest_path, "w", newline="", encoding="utf-8-sig") as dest:
            reader = csv.reader(source)
            writer = csv.writer(dest)
            writer.writerow(HEADER)
            rows = list(reader)
            for row in rows[1:]:
                try:
                    expanded_row = expand_timetable(row)
                    for final_row in expanded_row:
                        writer.writerow(final_row)
                except Exception as e:
                    log(f"Error processing row: {row} - {e}", ERROR)
    except IOError as e:
        log(f"File I/O error: {e}", ERROR)
    except Exception as e:
        log(f"Unexpected error: {e}", ERROR)


def run():
    log_dir = f"./log"
    if os.path.exists(log_dir):
        shutil.rmtree(log_dir)
    os.makedirs(log_dir, exist_ok=True)
    set_logger()
    log("==========スクレイピング開始============")
    start_time = time.time()
    driver = init_driver()

    year, month = get_current_date()
    base_dir = f"../data/{year}_{month}"
    row_dir = os.path.join(base_dir, "rowData")
    row_detail_dir = os.path.join(base_dir, "rowData_added_detail")
    formatted_dir = os.path.join(base_dir, "科目ノートの素")
    subject_data_dir =os.path.join(base_dir, "科目データ")

    # フォルダの中身を削除
    if os.path.exists(row_dir):
        shutil.rmtree(row_dir)
    if os.path.exists(row_detail_dir):
        shutil.rmtree(row_detail_dir)
    if os.path.exists(formatted_dir):
        shutil.rmtree(formatted_dir)
    if os.path.exists(subject_data_dir):
        shutil.rmtree(subject_data_dir)

    # 必要なフォルダを再作成
    os.makedirs(row_dir, exist_ok=True)
    os.makedirs(row_detail_dir, exist_ok=True)
    os.makedirs(formatted_dir, exist_ok=True)
    os.makedirs(subject_data_dir, exist_ok=True)

    try:
        for faculty in FACULTIES:
            scrape_syllabus_data(driver, faculty, row_dir)
            add_details(driver, faculty, row_dir, row_detail_dir)
            format_syllabus_data(faculty, row_detail_dir, formatted_dir)
            create_subject_data(faculty, formatted_dir, subject_data_dir)
    finally:
        driver.quit()

    # 処理が終了した後にフォルダを削除
    shutil.rmtree(row_dir)
    shutil.rmtree(row_detail_dir)

    log(f"総実行時間: {time.time() - start_time:.6f} 秒")
    log("==========スクレイピング完了==========")
    

if __name__ == "__main__":
    run()
