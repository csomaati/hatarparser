
import requests
from lxml import html
from lxml.cssselect import CSSSelector
from hashlib import blake2b
import json
from datetime import datetime
from collections import defaultdict

UTF8_HTML_PARSER = html.HTMLParser(encoding="utf-8")
HH_KEY = "<SECRET_RANDOM_KEY>"
HH_STORAGE = "<HH_PHP_PAGE_URL>"
HH_SOURCE_URL = "http://www.police.hu/hu/hirek-es-informaciok/hatarinfo?field_hat_rszakasz_value=All"
HEADERS = {}

def generate_user_agent(requested_user_agent="chrome"):
    ua_string = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.2 (KHTML, like Gecko) Chrome/22.0.1216.0 Safari/537.2"
    return ua_string

def scrape(url):
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()

    return r.content.decode("utf-8")

def scrape_html(url):
    response = scrape(url)
    html_response = html.fromstring(response, parser=UTF8_HTML_PARSER)
    return html_response


def crawl_hatarhelyzet():
    result = {}
    HEADERS["User-Agent"] = generate_user_agent("chrome")
    parse_time = datetime.now().replace(microsecond=0).isoformat(sep=" ")
    hh_page = scrape_html(HH_SOURCE_URL)
    countries_div = hh_page.cssselect(".crossing-point")
    for country_div in countries_div:
        country = country_div.text.split(":")[1].strip()[:-13]
        result[country] = {}
        accordion_box = country_div.getnext()
        panels = accordion_box.cssselect(".panel")
        for panel in panels:
            headers = panel.cssselect(".panel-title span")
            city_hu, city_other = headers[0].text_content().strip().split("-")[:2]
            panel_name = f"{city_hu}-{city_other}"
            openings = headers[1].text_content()
            result[country][panel_name] = defaultdict(lambda: "-")
            result[country][panel_name].update({
                "hu": city_hu.strip(),
                "other": city_other.strip(),
                "openings": openings.strip()
            })
            result[country][panel_name]["seen"] = parse_time

            szgk, tgk, busz = 0, 0, 0
            labels = panel.cssselect(".panel-body .label")
            for label in labels:
                attr = label.text_content().strip()
                value_element = label.getnext()
                if "(ki)" in attr or "(be)" in attr:
                    szgk_element = value_element.cssselect(".szgk")
                    if szgk_element: szgk = szgk_element[0].text_content()

                    busz_element = value_element.cssselect(".busz")
                    if busz_element: busz = busz_element[0].text_content()
                    tgk_element = value_element.cssselect(".tgk")
                    if tgk_element: tgk = tgk_element[0].text_content()
                    if not szgk_element and not tgk_element and not busz_element:
                        result[country][panel_name][attr] = {"all": value_element.text_content()}
                    else:
                        result[country][panel_name][attr] = {
                            "szgk": szgk,
                            "busz": busz,
                            "tgk": tgk
                        }
                else:
                    value = value_element.text_content().strip()
                    result[country][panel_name][attr] = value

    return result

def create_records(hatarhelyzet):
    record_borders = {}
    record_info = {}
    record_border_info = []

    for country, borders in hatarhelyzet.items():
        for border, details in borders.items():
            b = [country, details["hu"], details["other"], details["openings"], details["Forgalom típusa:"], details["Alternatív határátkelőhely:"]]
            b_id = blake2b(repr(b).encode('utf-8'), digest_size=10).hexdigest()
            record_borders[b_id] = [b_id, ] + b + [details["seen"], ]
            for dir_key, dir_value in [["Várakozási idő Magyarország felé (be):", "be"], ["Várakozási idő Magyarország felől (ki):", "ki"]]:
                for t, count in details[dir_key].items():
                    i = [dir_value, t, count]
                    i_id = blake2b(repr(i).encode('utf-8'), digest_size=20).hexdigest()
                    record_info[i_id] = [i_id, ] + i
                    record_border_info.append([b_id, i_id, details['seen']])

    record_borders_result = list(record_borders.values())
    record_info_result = list(record_info.values())
    return record_borders_result, record_border_info, record_info_result

def upload(border_results, info_results, border_info_results):
    payload = {
        "key": HH_KEY,
        "payload": {
            "borders": border_results,
            "info": info_results,
            "border_info": border_info_results,
        }
    }
    r = requests.post(HH_STORAGE, json=payload)
    print(r.text)
    r.raise_for_status();

def main():
    hatarhelyzet = crawl_hatarhelyzet()
    r_border, r_border_info, r_info = create_records(hatarhelyzet)
    upload(r_border, r_info, r_border_info)

if __name__ == "__main__":
    main()
