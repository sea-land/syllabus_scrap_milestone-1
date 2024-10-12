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
CATEGORY = 0
SUBJECT_ID = 1
FACULTY = 2
YEAR = 3
CODE = 4
SUBJECT = 5
SUBJECT_KANA = 6
TEACHER = 7
TEACHER_KANA = 8
SEMESTER = 9
PERIOD = 10
SCHOOL_YEAR = 11
UNITS = 12
ROOM = 13
CAMPUS = 14
SUBJECT_KEY = 15
SUBJECT_CLASS = 16
USED_LANGUAGE = 17
SUBJECT_METHOD = 18
LEVEL = 19
TYPE = 20
DESCRIPTION = 21
URL = 22

#CSVファイルヘッダー項目
HEADER=["科目区分", "授業ID", "学部", "年度", "コースコード", "科目名", "カモクメイ", "担当教員", "フリガナ", "学期", "曜日時限", "学年", "単位数", "教室", "キャンパス", "科目キー", "科目クラス", "使用言語", "授業形式", "レベル", "授業形態", "授業概要", "シラバスURL"]

# 対象学部のリスト
FACULTIES = ["政経", "法学", "教育", "商学", "社学", "国際教養", "文構", "文", "基幹", "創造", "先進", "人科", "スポーツ", "グローバル"]


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
    # options.add_argument("--headless")  # ヘッドレスモードで実行
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
    log("大学シラバスにアクセスします。\n")
    driver.get("https://www.wsl.waseda.jp/syllabus/JAA101.php")

    for faculty in FACULTIES:
        log(f"{faculty} のシラバスにアクセスしています。")
        dest_path = os.path.join(dest_dir, f"{faculty}_raw_syllabus_data.csv")

        select = Select(driver.find_element(By.NAME, "p_gakubu"))
        select.select_by_visible_text(faculty)
        scrape_data(driver, dest_path, faculty)




def scrape_data(driver, dest_path, faculty):
    """
    スクレイピングを実行し、学部のデータをCSVに書き出します。

    Args:
        driver: WebDriverインスタンス。
        writer: CSVライターオブジェクト。
        faculty: 学部名。
    """
    log(f"{faculty} の科目インデックスを取得中です。")
    start_time = time.time()
    total_elements = 0

    # 検索と表示数変更
    driver.execute_script("func_search('JAA103SubCon');")
    driver.execute_script("func_showchg('JAA103SubCon', '1000');")

    with open(dest_path, "w", newline="", encoding="utf-8") as dest:
        writer=csv.writer(dest)
        writer.writerow(HEADER)
        total_elements = save_table(driver,writer,faculty)
        log(f"総科目数: {total_elements} 実行時間: {time.time() - start_time:.6f} 秒\n")
        driver.find_element(By.CLASS_NAME, "ch-back").click()


def save_table(driver,writer,faculty):
    total_elements = 0
    while True:
        try:
            soup = BeautifulSoup(driver.page_source, "html.parser")
            rows = soup.select("#cCommon div div div div div:nth-child(1) div:nth-child(2) table tbody tr")
            for row in rows[1:]:
                cols = row.find_all("td")
                year = cols[0].text.strip()
                code = cols[1].text.strip()
                subject = cols[2].text.strip()
                teacher = cols[3].text.strip()
                semester = cols[5].text.strip()
                period = cols[6].text.strip()
                room = cols[7].text.strip()
                desc = cols[8].text.strip()

                # 科目の詳細ページのリンクを取得
                link_element = cols[2].find("a", onclick=True)
                if link_element:
                    onclick_value = link_element['onclick']
                    # 'post_submit('JAA104DtlSubCon', '1100001010012024110000101011')' から pKey を抽出
                    pkey = onclick_value.split("'")[3]
                    detail_url = f"https://www.wsl.waseda.jp/syllabus/JAA104.php?pKey={pkey}&pLng=jp"
                else:
                    detail_url = ""


                category = ""
                school_year = ""
                units = ""
                campus = ""
                subject_key = ""
                subject_class = ""
                class_lang = ""
                class_method = ""
                level = ""
                class_type = ""

                writer.writerow([
                    category,
                    "",
                    faculty,
                    year,
                    code,
                    subject,
                    "",
                    teacher,
                    "",
                    semester,
                    period,
                    school_year,
                    units,
                    room,
                    campus,
                    subject_key,
                    subject_class,
                    class_lang,
                    class_method,
                    level,
                    class_type,
                    remove_newlines(desc),
                    detail_url,
                ])
                total_elements+=1

            # 次のページへ
            driver.find_element(By.XPATH, "//*[@id='cHonbun']/div[2]/table/tbody/tr/td[3]/div/div/p/a").click()
        except NoSuchElementException:
            break
    return total_elements

def add_details(driver,src_path,dest_path):
    with open(src_path, "r", newline="", encoding="utf-8") as source, \
         open(dest_path, "w", newline="", encoding="utf-8") as dest:
        reader=csv.reader(source)
        writer=csv.writer(dest)
        writer.writerow(HEADER)
        rows=list(reader)
        total_elements = 0
        while True:
            try:
                for row in rows[1:]:
                    if(total_elements%100==0):log(f"{total_elements}/{len(rows)-1}件完了(100件完了ごとに更新されます)")
                    detail_url = row[22]
                    
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
                            log(f"{table_data}の一部の情報が読み取れませんでした。",ERROR)
                            return ""

                    # 各フィールドのデータ取得
                    # year = safe_get(table_data, 0, 1)
                    # faculty = safe_get(table_data, 0, 3)
                    # subject = safe_get(table_data, 1, 1)
                    # teacher = safe_get(table_data, 2, 1)
                    period = safe_get(table_data, 3, 1)
                    category = safe_get(table_data, 4, 1)
                    school_year = safe_get(table_data, 4, 3)
                    units = safe_get(table_data, 4, 5)
                    # room = safe_get(5,1)
                    campus = safe_get(table_data, 5, 3)
                    subject_key = safe_get(table_data, 6, 1)
                    subject_class = safe_get(table_data, 6, 3)
                    class_lang = safe_get(table_data, 7, 1)
                    class_method = safe_get(table_data, 8, 1)
                    level = safe_get(table_data, 13, 1)
                    class_type = safe_get(table_data, 13, 3)

                    writer.writerow([
                        category,
                        "",
                        row[FACULTY],
                        row[YEAR],
                        row[CODE],
                        row[SUBJECT],
                        "",
                        row[TEACHER],
                        "",
                        row[SEMESTER],
                        period,
                        school_year,
                        units,
                        row[ROOM],
                        campus,
                        subject_key,
                        subject_class,
                        class_lang,
                        class_method,
                        level,
                        class_type,
                        row[DESCRIPTION],
                        detail_url,
                    ])
                    total_elements+=1

                # 次のページへ
                driver.find_element(By.XPATH, "//*[@id='cHonbun']/div[2]/table/tbody/tr/td[3]/div/div/p/a").click()
            except NoSuchElementException:
                log(f"{total_elements}/{len(rows)-1}件完了")
                break
    return total_elements



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
            writer.writerow(HEADER)
            rows = list(reader)
        
            for row in rows[1:]:
                try:
                    han_row = [zen_to_han(cell, kana=False) for cell in row]
                    han_row[SUBJECT_KANA] = get_furigana(han_row[SUBJECT])
                    han_row[TEACHER] = format_teacher_name(han_row[TEACHER])
                    han_row[TEACHER_KANA] = get_furigana(han_row[TEACHER])
                    han_row[TYPE] = get_class_type(han_row[CODE])
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
    log("==========スクレイピング開始============")
    start_time = time.time()
    driver = init_driver()
    
    year, month = get_current_date()
    base_dir = f"../data/{year}_{month}"
    row_dir = os.path.join(base_dir, "rowData")
    row_detail_dir = os.path.join(base_dir, "rowData_added_detail")
    mac_dir = os.path.join(base_dir, "forMac")
    win_dir = os.path.join(base_dir, "forWin")

    os.makedirs(row_dir, exist_ok=True)
    os.makedirs(row_detail_dir, exist_ok=True)
    os.makedirs(mac_dir, exist_ok=True)
    os.makedirs(win_dir, exist_ok=True)

    try:
        scrape_syllabus_data(driver, row_dir)
        for faculty in FACULTIES:
            log(f"{faculty} の詳細情報を追加します。")
            row_file = os.path.join(row_dir, f"{faculty}_raw_syllabus_data.csv")
            row_detail_file = os.path.join(row_detail_dir, f"{faculty}_raw_syllabus_data.csv")
            add_details(driver,row_file,row_detail_file)
    finally:
        driver.quit()

    for faculty in FACULTIES:
        log(f"{faculty} をフォーマットしています。")
        row_file = os.path.join(row_detail_dir, f"{faculty}_raw_syllabus_data.csv")
        mac_file = os.path.join(mac_dir, f"{faculty}_科目ノートの素.csv")
        win_file = os.path.join(win_dir, f"{faculty}_科目ノートの素.csv")
        
        format_syllabus_data(row_file, mac_file)
        convert_to_utf8_sig(mac_file, win_file)

    log(f"総実行時間: {time.time() - start_time:.6f} 秒")
    log("==========スクレイピング完了==========")
    

if __name__ == "__main__":
    run()
