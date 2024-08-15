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

# 定数
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

FACULTIES = ["政経", "法学", "教育", "商学", "社学", "国際教養", "文構", "文", "基幹", "創造", "先進", "人科", "スポーツ", "グローバル"]

CATEGORIES={
    "基幹":[
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
        ],
    "創造":[
        "A群：複合領域",
        "A群：外国語-英語",
        "A群：外国語-初修外国語",
        "B群：数学",
        "B群：自然科学",
        "B群：実験・実習・製作",
        "B群：情報関連科目",
        "建築学科（専門科目）",
        "総合機械工学科（専門科目）",
        "経営システム工学科（専門科目）",
        "社会環境工学科（専門科目）",
        "環境資源工学科（専門科目）",
    ],
    "先進":[
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
    ]
}

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
    # 全体のログ設定
    # ファイルに書き出す。ログが100KB溜まったらバックアップにして新しいファイルを作る。
    logger = getLogger()
    logger.setLevel(DEBUG)
    handler = handlers.RotatingFileHandler("./app.log", maxBytes=100 * 1024, backupCount=3, encoding="utf-8")
    formatter = Formatter("%(asctime)s : %(levelname)s : %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    block_logger = getLogger()
    block_logger.setLevel(ERROR)  # DEBUGやINFOなどのレベルのログを無視
    main_logger = getLogger("__main__")
    main_logger.setLevel(DEBUG)


def log(arg, level=DEBUG):
    logger = getLogger(__name__)
    if level == DEBUG:
        logger.debug(arg)
    elif level == ERROR:
        logger.error(arg)


def get_current_date():
    now = datetime.datetime.now()
    return now.year, now.month


def check_versions():
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


def init_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--verbose")

    return webdriver.Remote(command_executor="http://selenium:4444/wd/hub", options=chrome_options)


def scrape_syllabus_data(driver, dest_dir):
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

            # 基幹、創造、先進の場合、カテゴリを選択
            if faculty in CATEGORIES:
                for category in CATEGORIES[faculty]:
                    select = Select(driver.find_element(By.NAME, "p_keya"))
                    select.select_by_visible_text(category)

                    # 検索を実行(javascriptから直接実行)
                    driver.execute_script("func_search('JAA103SubCon');")#検索ボタン
                    driver.execute_script("func_showchg('JAA103SubCon', '1000');")#表示数を1000に変更

                    log(f"Scraping {faculty} - {category} data.")
                    start_time = time.time()
                    total_elements = 0
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
                                    category,
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
                    log(f"Total Number of Subjects {faculty} - {category}: {total_elements}")
                    log(f"Finished in {time.time() - start_time:.6f} seconds\n")
                    driver.find_element(By.CLASS_NAME, "ch-back").click()
            else:
                # カテゴリがない場合の処理
                driver.execute_script("func_search('JAA103SubCon');")
                driver.execute_script("func_showchg('JAA103SubCon', '1000');")

                log(f"Scraping {faculty} data.")
                start_time = time.time()
                total_elements = 0
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


def process_schedule(row):
    schedule = str(row[PERIOD])
    common_data = row[:PERIOD]
    expanded_rows = []

    if ":" in schedule:
        # ':' が含まれている場合の処理
        for time in schedule.split(":"):
            if len(time) < 4:
                continue
            time = time.replace("　", " ").replace("\n", " ")
            new_schedule = time.split(" ")[0]
            expanded_rows.append(common_data + [new_schedule])
    elif "-" in schedule:
        # '-' が含まれている場合の処理
        schedule = schedule.replace(" ", "")
        day, time_range = schedule[0], schedule[1:]
        try:
            start, end = map(int, time_range.split("-"))
            for time in range(start, end + 1):
                new_schedule = f"{day}{time}時限"
                expanded_rows.append(common_data + [new_schedule])
        except ValueError:
            # 変換エラーをキャッチし、元のデータを追加
            log(f"曜日時限 '{time_range}' の処理中にエラーが発生しました。行: {row}", ERROR)
            expanded_rows.append(list(row))
    else:
        # ':' や '-' が含まれていない場合、そのまま追加
        expanded_rows.append(list(row))

    return expanded_rows



def format_syllabus_data(source_path, dest_path):
    tagger = Tagger()


    def get_furigana(text):
        words = tagger(text)
        furigana = "".join([word.feature.kana if word.feature.kana else word.surface for word in words])
        return furigana

    def get_class_type(code):
        class_type_code = code[-1]
        return CLASS_TYPE_MAP.get(class_type_code, "不明")

    def adjust_teacher_name(teacher_name):
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
                fmt = process_schedule(han_row)
                for sub_row in fmt:
                    writer.writerow(sub_row)
            except Exception as e:
                log(f"Error processing row: {row} - {e}", ERROR)


def run():
    log("==========Scraping started==========")
    set_logger()
    start_time = time.time()
    try:
        check_versions()
        year, month = get_current_date()
        dest_dir = f"../data/{year}_{month}"

        os.makedirs(dest_dir, exist_ok=True)

        driver=init_driver()
    except Exception as e:
        log(f"Error : {e}", ERROR)

    try:
        scrape_syllabus_data(driver, dest_dir)
    finally:
        driver.quit()

    for faculty in FACULTIES:
        log(f"Formatting {faculty} data.")
        source_file = os.path.join(dest_dir, f"raw_syllabus_data_{faculty}.csv")
        dest_file = os.path.join(dest_dir, f"syllabus_data_{faculty}.csv")
        format_syllabus_data(source_file, dest_file)

    log(f"Total Execution Time {time.time() - start_time:.6f} seconds")
    log("==========Scraping completed==========")
    

if __name__ == "__main__":
    run()
