#!/usr/bin/env python
# encoding=utf8
'''
General Functions found in all agents
'''
# ----------------------------------------------------------------------------------------------------------------------------------
REQUEST_DELAY = 3

SCRAPER_PATHS = {
        'Search': '//*[@id="search"]//*[@class="g"]/div/div/div/a',
        'SearchVideoTitle': '//h3/text()',
        'SearchVideoUrl': './@href',
        'VideoTitle' : '//*[@class="episode-description"]/h1/text()',
        'VideoSummary': 'substring-after(//*[@class="episode-description"]/p/text(), " - ")',
        'ReleaseDate' : 'substring-before(//*[@class="episode-description"]/p/text(), " - ")',
        'Poster': '//*[@class="episode--gallery"]//img/@src',
        'Art': '//*[@class="episode--gallery"]//img/@src',
        'CastMembers': '',
        'CastName': '',
        'CastUrl': '',
        'CastPhoto': '',
        'Genres': '',
        'Studio': ''
}

STUDIO_MAP = {}

URL = {
        "Base": "https://fraternityx.com%s",
        "Search": "https://www.google.com/search?q=site%%3Afraternityx.com+%s",
        "Video": "https://fraternityx.com/episode/%s",
        "AddReferrer" : False
}