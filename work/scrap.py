import os
import csv
import datetime
import time
import subprocess
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

faculties = ["政経", "法学", "教育", "商学", "社学", "国際教養", "文構", "文", "基幹", "創造", "先進", "人科", "スポーツ", "グローバル"]


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


set_logger()


def log(arg, level=DEBUG):
    logger = getLogger(__name__)
    if level == DEBUG:
        logger.debug(arg)
    elif level == ERROR:
        logger.error(arg)


def get_current():
    now = datetime.datetime.now()
    return now.year, now.month


def scrape_syllabus_data(driver, dest_dir):
    log("Accessing Waseda's syllabus\n")
    driver.get("https://www.wsl.waseda.jp/syllabus/JAA101.php")
    for faculty in faculties:
        log(f"Accessing {faculty} syllabus")
        faculty_file = f"{dest_dir}/raw_syllabus_data_{faculty}.csv"
        with open(faculty_file, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["学部", "コースコード", "科目名", "担当教員", "学期", "曜日時限", "授業概要"])
            select = Select(driver.find_element(By.NAME, "p_gakubu"))
            select.select_by_visible_text(faculty)
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
                            cols[2].text.strip(),
                            cols[3].text.strip(),
                            cols[5].text.strip(),
                            cols[6].text.strip(),
                            cols[8].text.strip(),
                        ])
                    driver.find_element(By.XPATH, "//*[@id='cHonbun']/div[2]/table/tbody/tr/td[3]/div/div/p/a").click()
                except NoSuchElementException:
                    break
            log(f"Total Number of Subjects {faculty}: {total_elements}")
            log(f"Finished in {time.time() - start_time:.6f} seconds\n")
            driver.find_element(By.CLASS_NAME, "ch-back").click()


def convert_zen_to_han(source_path, output_path):
    with open(source_path, "r", newline="", encoding="utf-8") as infile, open(output_path, "w", newline="", encoding="utf-8") as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        for row in reader:
            writer.writerow([zen_to_han(cell, kana=False) for cell in row])


def process_schedule(row):
    schedule = str(row[5])
    common_data = row[:5]
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
            log(f"スケジュール範囲 '{time_range}' の処理中にエラーが発生しました。行: {row}", ERROR)
            expanded_rows.append(list(row))
    else:
        # ':' や '-' が含まれていない場合、そのまま追加
        expanded_rows.append(list(row))

    return expanded_rows


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


def format_syllabus_data(source_path, dest_path):
    tagger = Tagger()

    class_type_map = {
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

    def get_furigana(text):
        words = tagger(text)
        furigana = "".join([word.feature.kana if word.feature.kana else word.surface for word in words])
        return furigana

    def get_class_type(code):
        class_type_code = code[-1]
        return class_type_map.get(class_type_code, "不明")

    with open(source_path, "r", newline="", encoding="utf-8") as source, open(dest_path, "w", newline="", encoding="utf-8") as dest:
        csvreader = csv.reader(source)
        csvwriter = csv.writer(dest)
        rows = list(csvreader)
        # ヘッダーの書き込み
        csvwriter.writerow(rows[0][:3] + ["かもくめい"] + rows[0][3:6] + ["授業形態"] + rows[0][6:])
        
        for row in rows[1:]:
            try:
                han_row = [zen_to_han(cell, kana=False) for cell in row]
                subject_name = han_row[2]
                furigana = get_furigana(subject_name)
                course_code = han_row[1]
                class_type = get_class_type(course_code)
                han_row.insert(3, furigana)
                han_row.insert(6, class_type)
                fmt = process_schedule(han_row)
                for sub_row in fmt:
                    csvwriter.writerow(sub_row)
            except Exception as e:
                log(f"Error processing row: {row} - {e}", ERROR)


def main():
    log("==========Scraping started==========")
    start_time = time.time()
    try:
        check_versions()
        year, month = get_current()
        dest_dir = f"../data/{year}_{month}"

        os.makedirs(dest_dir, exist_ok=True)

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--verbose")

        driver = webdriver.Remote(command_executor="http://selenium:4444/wd/hub", options=chrome_options)
    except Exception as e:
        log(f"Error : {e}", ERROR)

    try:
        scrape_syllabus_data(driver, dest_dir)
    finally:
        driver.quit()

    for faculty in faculties:
        log(f"Formatting {faculty} data.")
        source_file = os.path.join(dest_dir, f"raw_syllabus_data_{faculty}.csv")
        dest_file = os.path.join(dest_dir, f"syllabus_data_{faculty}.csv")
        format_syllabus_data(source_file, dest_file)

    log(f"Total Execution Time {time.time() - start_time:.6f} seconds")
    log("==========Scraping completed==========")
    

if __name__ == "__main__":
    main()
