# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from logging.handlers import TimedRotatingFileHandler
import traceback
from datetime import datetime
import time
import json
import re
from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

logger = logging.getLogger()
logger.setLevel('INFO')
formatter = logging.Formatter('%(asctime)s %(process)d %(levelname)1.1s %(lineno)3s:%(funcName)-16.16s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

current_dir = os.path.dirname(os.path.abspath(__file__))
current_filename = os.path.splitext(os.path.basename(__file__))[0]
filename = current_dir + os.sep + "log" + os.sep + current_filename + ".log"
handler = TimedRotatingFileHandler(filename=filename, when='midnight', backupCount=7, encoding='utf8')
handler.suffix = '%Y%m%d'
handler.setFormatter(formatter)
logger.addHandler(handler)

chrome_options = Options()
chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--ignore-certificate-errors')
chrome_options.add_argument('--headless')
chrome_options.add_argument('--window-size=1920,9720')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36')

driver = webdriver.Chrome(chrome_options=chrome_options, executable_path='/Users/ktj/Documents/github/selenium_crawler/driver/chromedriver')
driver.implicitly_wait(3)


def naver_map_crawler(keyword, address, keyword_index, last):
    result = ''
    next_keyword = 'false'
    start = datetime.now()

    try:
        logger.info('=' * 80)
        logger.info(f'[{keyword_index} / {last}] {keyword}')
        logger.info('=' * 80)

        # 해당 키워드로 검색
        city = address.split(' ')[1]
        logger.info(f'[{city} {keyword}]를 검색창에 입력합니다.')
        driver.get(f'https://map.naver.com/v5/search/{city} {keyword}')

        # 완전한 로드를 위해 3초 대기
        time.sleep(3)

        # 키워드로 검색 [1]
        if next_keyword == 'false':

            # 검색 프레임으로 이동
            driver.switch_to.frame(driver.find_element_by_tag_name('#searchIframe'))

            # 조건에 맞는 업체 유무 확인
            check_load = driver.find_elements_by_css_selector('#_pcmap_list_scroll_container + div > a:last-child')
            if len(check_load) > 0:
                next_keyword = 'false'
            else:
                search_failed = driver.find_element_by_css_selector('#app-root > div > div > div > div')
                search_failed = search_failed.text
                if search_failed == '조건에 맞는 업체가 없습니다.':
                    next_keyword = 'true'

        # 더 포괄적인 키워드로 검색이 필요한 경우 [2]
        if next_keyword == 'true':

            # 더 포괄적인 키워드로 검색
            logger.info(f' - 조건에 맞는 업체가 없습니다. 더 포괄적인 키워드인 [{keyword}]를 검색창에 입력합니다.')
            driver.get(f'https://map.naver.com/v5/search/{keyword}')

            # 완전한 로드를 위해 3초 대기
            time.sleep(3)

            # 검색 프레임으로 이동
            driver.switch_to.frame(driver.find_element_by_tag_name('#searchIframe'))

            # 조건에 맞는 업체 유무 확인
            check_load = driver.find_elements_by_css_selector('#_pcmap_list_scroll_container + div > a:last-child')
            if len(check_load) > 0:
                next_keyword = 'false'
            else:
                search_failed = driver.find_element_by_css_selector('#app-root > div > div > div > div')
                search_failed = search_failed.text
                if search_failed == '조건에 맞는 업체가 없습니다.':
                    next_keyword = 'true'

        # 더 포괄적인 키워드로 검색이 필요한 경우 [3]
        if next_keyword == 'true':

            # ~점 삭제
            short_keyword = re.split('( \w+점$)', keyword)
            short_keyword = short_keyword[0]

            # 더 포괄적인 키워드로 검색
            logger.info(f' - 조건에 맞는 업체가 없습니다. 더 포괄적인 키워드인 [{short_keyword}]를 검색창에 입력합니다.')
            driver.get(f'https://map.naver.com/v5/search/{short_keyword}')

            # 완전한 로드를 위해 3초 대기
            time.sleep(3)

            # 검색 프레임으로 이동
            driver.switch_to.frame(driver.find_element_by_tag_name('#searchIframe'))

            # 조건에 맞는 업체 유무 확인
            check_load = driver.find_elements_by_css_selector('#_pcmap_list_scroll_container + div > a:last-child')
            if len(check_load) > 0:
                pass
            else:
                search_failed = driver.find_element_by_css_selector('#app-root > div > div > div > div')
                search_failed = search_failed.text
                if search_failed == '조건에 맞는 업체가 없습니다.':
                    logger.info('- 조건에 맞는 업체가 없습니다. 다음 키워드를 검색합니다.')
                    result = '검색결과 없음'
                    return result

        # 리스트 개수 확인
        li_lists_len = len(driver.find_elements_by_css_selector('#_pcmap_list_scroll_container > ul > li'))
        logger.info(f' - {li_lists_len}개의 리스트가 존재합니다.')

        for i in range(1, li_lists_len + 1):

            # 검색결과가 20개보다 많을 경우 중단
            if i == 21:
                logger.info('- 데이터가 너무 많습니다. 다음 키워드를 검색합니다.')
                result = '항목 많음'
                return result

            # 결과 프레임이 검색 프레임을 덮고 있는 경우
            try:
                # 기본 프레임으로 이동
                driver.switch_to.default_content()

                # 결과 프레임이 검색 프레임을 가리는지 확인
                driver.find_element_by_css_selector('#container > shrinkable-layout > div > app-base > search-layout > div.sub.ng-star-inserted.-covered')
                logger.info(f'[1/{li_lists_len}]번째 리스트를 클릭합니다.')

            # 결과 프레임이 검색 프레임을 덮고 있지 않은 경우
            except NoSuchElementException as e:

                # 검색 프레임으로 이동
                driver.switch_to.frame(driver.find_element_by_tag_name('#searchIframe'))

                # 리스트 클릭
                logger.info(f'[{i}/{li_lists_len}]번째 리스트를 클릭합니다.')
                main_list_divs = driver.find_element_by_css_selector(f'#_pcmap_list_scroll_container > ul > li:nth-child({i}) > div > a > div > div > span')
                main_list_divs.click()

                # 기본 프레임으로 이동
                driver.switch_to.default_content()

            # 결과 프레임으로 이동
            driver.switch_to.frame(driver.find_element_by_tag_name('#entryIframe'))

            # 완전한 이동을 위해 3초 대기
            time.sleep(3)

            # 미용실일 경우 다음 리스트로 넘어가기
            if driver.find_element_by_css_selector('#_title > span:nth-child(2)').text == '미용실':
                logger.info(' - 미용실입니다. 다음 리스트를 검색합니다')
                continue

            # 전화번호가없을 때의 주소 가져오기
            if driver.find_element_by_css_selector('#app-root div.place_detail_wrapper > div:nth-child(4) > div > div > div > ul > li:nth-child(1) > strong').text == '주소':

                # 검색 된 결과의 도로명 주소 다듬기
                real_address_01 = ''
                address_01 = driver.find_element_by_css_selector('#app-root div.place_detail_wrapper > div:nth-child(4) > div > div > div > ul > li:nth-child(1) > div span:nth-child(1)').text
                address_01_split = address_01.split(' ')
                for index, address_01 in enumerate(address_01_split):
                    if index == 0:
                        continue
                    elif index == 1:
                        real_address_01 = address_01
                    else:
                        real_address_01 = real_address_01 + ' ' + address_01

                real_address_01 = re.split('(\w+[시|구|동|읍|리|가|로|길] \d+-?\d*)', real_address_01)
                if len(real_address_01) != 1:
                    real_address_01 = real_address_01[0] + real_address_01[1]
                else:
                    real_address_01 = real_address_01[0]
                real_address_01.strip()

                # 지번 변경 버튼클릭
                logger.info(' - 지번 변경 버튼을 클릭합니다.')
                change_button = driver.find_element_by_css_selector('#app-root div.place_detail_wrapper > div:nth-child(4) > div > div > div > ul > li:nth-child(1) > div span:nth-child(2)')
                change_button.click()

                # 검색 된 결과의 지번 주소 다듬기
                real_address_02 = ''
                address_02 = driver.find_element_by_css_selector('#app-root div.place_detail_wrapper > div:nth-child(4) > div > div > div > ul > li:nth-child(1) > div span:nth-child(1)').text
                address_02_split = address_02.split(' ')
                for index, address_02 in enumerate(address_02_split):
                    if index == 0:
                        continue
                    elif index == 1:
                        real_address_02 = address_02
                    else:
                        real_address_02 = real_address_02 + ' ' + address_02

                real_address_02 = re.split('(\w+[시|구|동|읍|리|가|로|길] \d+-?\d*)', real_address_02)
                if len(real_address_02) != 1:
                    real_address_02 = real_address_02[0] + real_address_02[1]
                else:
                    real_address_02 = real_address_02[0]
                real_address_02.strip()

            # 전화번호가 있을 때의 주소 가져오기
            else:

                # 검색 된 결과의 도로명 주소 다듬기
                real_address_01 = ''
                address_01 = driver.find_element_by_css_selector('#app-root div.place_detail_wrapper > div:nth-child(4) > div > div > div > ul > li:nth-child(2) > div span:nth-child(1)').text
                address_01_split = address_01.split(' ')
                for index, address_01 in enumerate(address_01_split):
                    if index == 0:
                        continue
                    elif index == 1:
                        real_address_01 = address_01
                    else:
                        real_address_01 = real_address_01 + ' ' + address_01

                real_address_01 = re.split('(\w+[시|구|동|읍|리|가|로|길] \d+-?\d*)', real_address_01)
                if len(real_address_01) != 1:
                    real_address_01 = real_address_01[0] + real_address_01[1]
                else:
                    real_address_01 = real_address_01[0]
                real_address_01.strip()

                # 지번 변경 버튼클릭
                logger.info(' - 지번 변경 버튼을 클릭합니다.')
                change_button = driver.find_element_by_css_selector('#app-root div.place_detail_wrapper > div:nth-child(4) > div > div > div > ul > li:nth-child(2) > div span:nth-child(2)')
                change_button.click()

                # 검색 된 결과의 지번 주소 다듬기
                real_address_02 = ''
                address_02 = driver.find_element_by_css_selector('#app-root div.place_detail_wrapper > div:nth-child(4) > div > div > div > ul > li:nth-child(2) > div > div > div:nth-child(2)').text
                address_02 = address_02.split(' 복사')[0]
                address_02_split = address_02.split(' ')
                for index, address_02 in enumerate(address_02_split):
                    if index == 0:
                        continue
                    elif index == 1:
                        real_address_02 = address_02
                    else:
                        real_address_02 = real_address_02 + ' ' + address_02

                real_address_02 = re.split('(\w+[시|구|동|읍|리|가|로|길] \d+-?\d*)', real_address_02)
                if len(real_address_02) != 1:
                    real_address_02 = real_address_02[0] + real_address_02[1]
                else:
                    real_address_02 = real_address_02[0]
                real_address_02.strip()

            # 주소 비교하기
            logger.info(' - 검색 된 결과의 주소와 JSON의 주소를 비교합니다.')
            logger.info(f'    - 검색 된 결과의 도로명 주소 : {real_address_01}')
            logger.info(f'    - 검색 된 결과의 지번 주소 : {real_address_02}')
            logger.info(f'    - JSON의 주소 : {address}')

            regexp_01 = re.compile(rf'{real_address_01}')
            regexp_02 = re.compile(rf'{real_address_02}')
            if regexp_01.search(address) or regexp_02.search(address):
                logger.info('    - 검색 된 결과 주소와 JSON의 주소가 일치합니다.')
            else:
                logger.info('    - 검색 된 결과 주소와 JSON의 주소가 일치하지 않습니다.')

                # 검색 결과가 1개일 경우
                if li_lists_len == 1:
                    result = '주소 불일치'
                    return result

                # 검색 결과가 1개보다 많을 경우
                else:

                    # 기본 프레임으로 이동
                    driver.switch_to.default_content()

                    # 결과 프레임 닫기
                    close_button = driver.find_element_by_css_selector('.sub > entry-layout > entry-close-button > button')
                    close_button.click()

                    # 검색 프레임으로 이동
                    driver.switch_to.frame(driver.find_element_by_tag_name('#searchIframe'))

                    # 해당 페이지에서 끝까지 검색했을 경우
                    if i == li_lists_len:
                        logger.info('1')
                        result = '주소 불일치'
                        return result

                    # 해당 페이지에서 아직 끝까지 검색하지 않았을 경우
                    else:
                        result = '주소 불일치'
                        continue

            # 전화번호
            if driver.find_element_by_css_selector('#app-root div.place_detail_wrapper > div:nth-child(4) > div > div > div > ul > li:nth-child(1) > strong').text == '주소':
                phone = ''
                logger.info(f' - 전화번호 : {phone}')
            else:
                phone = driver.find_element_by_css_selector('#app-root div.place_detail_wrapper > div:nth-child(4) > div > div > div > ul > li:nth-child(1)').text.replace('안내', '').replace('복사', '')
                phone = phone.strip()
                logger.info(f' - 전화번호 : {phone}')

            # 리뷰 수
            if len(driver.find_elements_by_css_selector('#_title + div > span')) == 3:
                visitant_review = driver.find_element_by_css_selector('#_title + div > span:nth-child(2) em').text.replace(',', '')
                blog_review = driver.find_element_by_css_selector('#_title + div > span:nth-child(3) em').text.replace(',', '')
                logger.info(f' - 방문자 리뷰 개수 : {visitant_review}')
                logger.info(f' - 블로그 리뷰 개수 : {blog_review}')
            elif len(driver.find_elements_by_css_selector('#_title + div > span')) == 2:
                if driver.find_element_by_css_selector('#_title + div > span:nth-child(1)').text.find('방문자리뷰') != -1:
                    visitant_review = driver.find_element_by_css_selector('#_title + div > span:nth-child(1) em').text.replace(',', '')
                    blog_review = driver.find_element_by_css_selector('#_title + div > span:nth-child(2) em').text.replace(',', '')
                    logger.info(f' - 방문자 리뷰 개수 : {visitant_review}')
                    logger.info(f' - 블로그 리뷰 개수 : {blog_review}')
                else:
                    visitant_review = driver.find_element_by_css_selector('#_title + div > span:nth-child(2) em').text.replace(',', '')
                    blog_review = 0
                    logger.info(f' - 방문자 리뷰 개수 : {visitant_review}')
                    logger.info(f' - 블로그 리뷰 개수 : {blog_review}')
            elif len(driver.find_elements_by_css_selector('#_title + div > span')) == 1:
                if driver.find_element_by_css_selector('#_title + div > span:nth-child(1)').text.find('방문자리뷰') != -1:
                    visitant_review = driver.find_element_by_css_selector('#_title + div > span:nth-child(1) em').text.replace(',', '')
                    blog_review = 0
                    logger.info(f' - 방문자 리뷰 개수 : {visitant_review}')
                    logger.info(f' - 블로그 리뷰 개수 : {blog_review}')
                else:
                    visitant_review = 0
                    blog_review = driver.find_element_by_css_selector('#_title + div > span:nth-child(1) em').text.replace(',', '')
                    logger.info(f' - 방문자 리뷰 개수 : {visitant_review}')
                    logger.info(f' - 블로그 리뷰 개수 : {blog_review}')
            elif len(driver.find_elements_by_css_selector('#_title + div > span')) == 0:
                visitant_review = 0
                blog_review = 0
                logger.info(f' - 방문자 리뷰 개수 : {visitant_review}')
                logger.info(f' - 블로그 리뷰 개수 : {blog_review}')

            # 성공
            result = '성공'
            break

    except Exception as e:
        logger.error(traceback.format_exc())

    finally:
        elapsed_time = (datetime.now() - start).total_seconds()
        logger.info("소요시간  {:5.2f}".format(elapsed_time))

    return result


if __name__ == '__main__':
    success = 0
    no_result = 0
    no_match = 0
    lots_of_items = 0
    start = datetime.now()
    db = None

    try:
        # JSON파일 읽어오기
        with open('/Users/ktj/Documents/github/selenium_crawler/json/store.jsonㄴㄴ', 'r', encoding='UTF-8') as f:
            json_data = json.load(f)

        # 크롤링 시작
        for row in json_data:

            keyword = row['title'].strip()
            address = row['com_addr']
            index = row['idx']

            result = naver_map_crawler(keyword, address, index, len(json_data))
            # result = naver_map_crawler('준식당', '경기도 수원시 권선구 호매실동 1402 105호', 8, 8478)
            logger.info(f"[{keyword}] 의 크롤링 결과 : {result}")

            if result == '성공':
                success = success + 1
            elif result == '주소 불일치':
                no_match = no_match + 1
            elif result == '검색결과 없음':
                no_result = no_result + 1
            elif result == '항목 많음':
                lots_of_items = lots_of_items + 1

            logger.info(f'성공 : {success} / 주소 불일치 : {no_match} / 검색결과 없음 : {no_result} / 항목 많음 : {lots_of_items}')

    except Exception as e:
        logger.error(traceback.format_exc())

    finally:
        driver.quit()
        db.close()
        elapsed_time = (datetime.now() - start).total_seconds()
        logger.info("총 소요시간  {:5.2f}".format(elapsed_time))
