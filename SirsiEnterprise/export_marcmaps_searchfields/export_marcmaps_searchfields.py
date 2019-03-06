#! /usr/bin/env python3

import json
import getpass
import logging
import http.client as http_client

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bs4 import BeautifulSoup as soup

ROOT_URL = 'https://lsu.ent.sirsi.net/client/en_US/'

"""required imports"""
# pip install bs4 requests lxml

"""Utility functions"""


def make_soup(page_name, slug):
    base_url = requests.compat.urljoin(ROOT_URL, 'admin/search/')
    urls = {
        'managemarcsubfields.edit': '{}managemarcsubfields.edit/{}',
        'managemarctags.edit': '{}managemarctags.edit/{}',
        'managemarctags.configuresubfields': '{}managemarctags.configuresubfields/{}',
        'managefields.grid.pager': '{}managefields.grid.pager/{}',
        'managefields.edit': '{}managefields.edit/{}',
        'managefields.configmarcmap': '{}managefields.confmarcmap/{}',
        'managemarcmaps.grid.pager': '{}managemarcmaps.grid.pager/{}',
        'managemarcmaps.edit': '{}managemarcmaps.edit/{}',
        'managemarcmaps.confmarc21tags': '{}managemarcmaps.confmarc21tags/{}/false',
    }
    if isinstance(slug, str):
        slug = slug.replace('/', '$002f').replace(' ', '$0020')
    full_url = urls[page_name].format(base_url, slug)
    print(full_url)
    page = requests_retry_session(session=s).get(full_url)
    return soup(page.content, 'lxml')


def get_max_page_count(kind):
    url = {
        'searchfields': requests.compat.urljoin(ROOT_URL, 'admin/search/managefields'),
        'marcmaps': requests.compat.urljoin(ROOT_URL, 'admin/search/managemarcmaps'),
    }
    page = requests_retry_session(session=s).get(url[kind])
    pagesoup = soup(page.content, 'lxml')
    counts = pagesoup.select('.t-data-grid-pager a')
    max_count = max(int(i.text) for i in counts)
    return max_count


def get_max_marc_maps_subfields(subfields_soup):
    return len(subfields_soup.select('.t-data-grid tbody tr'))


"""functions for parsing field types"""


def parse_checkbox(css_id, my_soup):
    try:
        css_code = '#{}'.format(css_id)
        my_soup.select(css_code)[0]['checked']
        return True
    except KeyError:
        return False
    except IndexError:
        return "Unknown"


def parse_dropdown(css_id, my_soup):
    try:
        css_code = '#{}'.format(css_id)
        return my_soup.select(css_code)[0].select('[selected]')[0].string
    except KeyError:
        return "None"
    except IndexError:
        return "None"


def parse_textbox(css_id, my_soup):
    try:
        css_code = '#{}'.format(css_id)
        return my_soup.select(css_code)[0]['value']
    except KeyError:
        return "None"
    except IndexError:
        return "None"


"""Parsing Searchfield info"""


def do_searchfields():
    searchfields_dict = build_basic_search_dict()
    searchfields_dict = add_searchfield_editfield_dict(searchfields_dict)
    searchfields_dict = add_searchfield_configuremarcmap_dict(searchfields_dict)
    with open('Enterprise_searchfields.json', 'w') as f:
        f.write(json.dumps(searchfields_dict, indent=2, sort_keys=True))


def build_basic_search_dict():
    searchfields_dict = None
    max_page = get_max_page_count('searchfields')
    for page_num in range(1, max_page + 1):
        searchfields_dict = get_searchfields_items(page_num, searchfields_dict)
    return searchfields_dict


def get_searchfields_items(pagenum, searchfields_dict):
    search_soup = make_soup('managefields.grid.pager', pagenum)
    if not searchfields_dict:
        searchfields_dict = dict()
    for row in search_soup.tbody:
        searchfield_code, searchfield_name, searchfield_hierarchy, links = row.contents
        searchfields_dict[searchfield_code.string] = {
            'code': searchfield_code.string,
            'name': searchfield_name.string,
            'hierarchy': searchfield_hierarchy.string.strip(),
        }
    return searchfields_dict


def add_searchfield_editfield_dict(searchfields_dict):
    for searchfield_code in searchfields_dict:
        editfield_soup = make_soup('managefields.edit', searchfield_code)
        if not searchfields_dict[searchfield_code].get('Details'):
            searchfields_dict[searchfield_code]['Details'] = dict()
        editfield_dict = {
            'descripton': editfield_soup.select('#description')[0].string,
            'hierarchy': parse_dropdown('hierarchy', editfield_soup),
            'fieldCodeType': parse_dropdown('fieldCodeType', editfield_soup),
            'indexed': parse_checkbox('indexed', editfield_soup),
            'normalizer': parse_dropdown('normalizer', editfield_soup),
            'dataType': parse_dropdown('dataType', editfield_soup),
            'sort': parse_dropdown('sort', editfield_soup),
            'repeatable': parse_checkbox('repeatable', editfield_soup),
            'splitonspace': parse_checkbox('splitonspace', editfield_soup),
            'facet': parse_checkbox('facet', editfield_soup),
            'exclusiveFacet': parse_checkbox('exclusiveFacet', editfield_soup),
            'displayFieldType': parse_dropdown('displayFieldType', editfield_soup),
            'hitlistAvail': parse_checkbox('hitlistAvail', editfield_soup),
            'detailAvail': parse_checkbox('detailAvail', editfield_soup),
            'detailTab': parse_dropdown('detailTab', editfield_soup),
            'specialProcessing': parse_dropdown('specialProcessing', editfield_soup),
        }
        searchfields_dict[searchfield_code]['Details'].update(editfield_dict)
    return searchfields_dict


def add_searchfield_configuremarcmap_dict(searchfields_dict):
    for searchfield_code in searchfields_dict:
        configuremarcmap_soup = make_soup('managefields.configmarcmap', searchfield_code)
        searchfields_dict[searchfield_code]['Marc Code'] = parse_dropdown('marcMap', configuremarcmap_soup)
    return searchfields_dict


"""Parsing MarcMap info"""


def do_marcmaps():
    all_marc_codes = get_all_marc_codes()
    all_marc_details_dict = {
        i: get_marc_info(i) for i in all_marc_codes
    }
    with open('Enterprise_marc_fields.json', 'w') as f:
        f.write(json.dumps(all_marc_details_dict, indent=2, sort_keys=True))


def get_all_marc_codes():
    count_of_marc_results_pages = get_max_page_count('marcmaps')
    marc_codes = set()
    for index in range(1, count_of_marc_results_pages + 1):
        marc_results_page_soup = make_soup('managemarcmaps.grid.pager', index)
        marc_item_rows = marc_results_page_soup.select('#marcMapTable tbody tr')
        for marc_item_row in marc_item_rows:
            marc_code = marc_item_row.select('td')[0].string
            marc_codes.add(marc_code)
    return list(sorted(marc_codes))


def get_marc_info(marc_code):
    marcmap_item_dict = parse_marcmap_item_details(marc_code)
    fields_soup = make_soup('managemarcmaps.confmarc21tags', marc_code)
    fields = fields_soup.select('#tagsTable tbody tr')
    if not marcmap_item_dict.get('Tags'):
        marcmap_item_dict['Tags'] = list()
    for index, _ in enumerate(fields):
        tag, field_marc_dict = parse_marcmap_item_tags_details(index)
        field_marc_dict['subfields'] = parse_subfields(index)
        marcmap_item_dict['Tags'].append(field_marc_dict)
    return marcmap_item_dict


def parse_marcmap_item_details(marc_code):
    marcmap_item_details_soup = make_soup('managemarcmaps.edit', marc_code)
    marc_item_details_dict = {
        'name': parse_textbox('mltf_2', marcmap_item_details_soup),
        'description': parse_textbox('description', marcmap_item_details_soup),
        'marc21Cond': parse_textbox('marc21Cond', marcmap_item_details_soup),
        'unimarcCond': parse_textbox('unimarcCond', marcmap_item_details_soup),
        'exclusiveValue': parse_checkbox('exclusiveValue', marcmap_item_details_soup),
    }
    return marc_item_details_dict


def parse_marcmap_item_tags_details(index):
    tag_details_soup = make_soup('managemarctags.edit', index)
    tag_name = parse_textbox('tag', tag_details_soup)
    field_marc_dict = {
        'tag': tag_name,
        'marcCond': parse_textbox('marcCond', tag_details_soup),
        'firstPrefix': parse_textbox('firstPrefix', tag_details_soup),
        'firstSuffix': parse_textbox('firstSuffix', tag_details_soup),
        'otherPrefix': parse_textbox('otherPrefix', tag_details_soup),
        'otherSuffix': parse_textbox('otherSuffix', tag_details_soup),
        'concatSubfields': parse_checkbox('concatSubfields', tag_details_soup),
        'concatTags': parse_checkbox('concatTags', tag_details_soup),
        'fixedField': parse_checkbox('fixedField', tag_details_soup),
        'offset': parse_textbox('offset', tag_details_soup),
        'length': parse_textbox('length', tag_details_soup),
    }
    return tag_name, field_marc_dict


def parse_subfields(marc_item_index):
    subfields_soup = make_soup('managemarctags.configuresubfields', marc_item_index)
    subfields_count = get_max_marc_maps_subfields(subfields_soup)
    subfields_dict = dict()
    for subfield_index in range(subfields_count):
        subfield_page_soup = make_soup('managemarcsubfields.edit', subfield_index)
        subfield = parse_textbox('subfield', subfield_page_soup)
        subfield_marc_dict = {
            'subfield': subfield,
            'beginningPunct': parse_textbox('beginningPunct', subfield_page_soup),
            'endingPunct': parse_textbox('endingPunct', subfield_page_soup),
            'marcCond': parse_textbox('marcCond', subfield_page_soup),
        }
        subfields_dict[subfield] = subfield_marc_dict
    return subfields_dict


def login():
    admin_frontpage = requests_retry_session(session=s).get(requests.compat.urljoin(ROOT_URL, 'admin/admin'))
    admin_frontpage_soup = soup(admin_frontpage.content, 'lxml')
    formdata = admin_frontpage_soup.select('input[name="t:formdata"]')[0]['value']
    admin_login_url = requests.compat.urljoin(ROOT_URL, 'login.loginform')
    for i in range(3):
        admin_login_data = {
            'j_username': input('what is your Enterprise username? '),
            'j_password': getpass.getpass('what is your Enterprise password? '),
            't:formdata': formdata,
        }
        login_response = s.post(admin_login_url, data=admin_login_data)
        if 'login failed' in login_response.text.lower():
            print('Login failed.  Please try again')
        else:
            break


def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def do_verbose_logging():
    http_client.HTTPConnection.debuglevel = 1
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


if __name__ == '__main__':
    # do_verbose_logging()

    s = requests.Session()

    login()

    print('scraping your searchfields')
    do_searchfields()
    print('scraping your marcmaps')
    do_marcmaps()
