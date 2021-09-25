#!/usr/bin/env python
# pylint: disable=line-too-long
# pylint: disable=W0702, W0703, C0103, C0410
# encoding=utf8
'''
# HardKinks (IAFD)
                                                  Version History
                                                  ---------------
    Date            Version                         Modification
    22 Dec 2019   2019.12.22.1     Corrected scrapping of collections
    14 Aug 2020   2019.08.12.21    Change to regex matching code - site titles which had studio name in them were failing to match to 
                                   file titles as regex was different between the two
    22 Sep 2020   2019.08.12.22    correction to summary xpath to cater for different layouts
    07 Oct 2020   2019.08.12.23    IAFD - change to https
    28 Feb 2021   2019.08.12.25    Moved IAFD and general functions to other py files
                                   Enhancements to IAFD search routine, including Levenshtein Matching on Cast names
                                   Added iafd legend to summary
    27 Mar 2021   2019.08.12.26    Site Title had spaces removed before normalisation - caused matching failure
                                   Site Studio was been set to [-1] rather than the last element of the site entry split, so Studio always matched
    21 Apr 2021   2019.08.12.27    Posters with url extention .webp - renamed to .jpg
    25 Apr 2021   2019.08.12.28    removed regex pref, search string length only has full words, json unicode issues, added to title/studio matching
    25 Apr 2021   2019.08.12.29    Issue #96 - changed title sort so that 'title 21' sorts differently to 'title 12'
                                   duration matching with iafd entries as iafd has scene titles that match with film titles
                                   use of ast module to avoid unicode issues in some libraries
                                   Removal of REGEX preference
                                   code reorganisation like moving logging fuction out of class so it can be used by all imports
    11 May 2021   2019.08.12.30    Further code reorganisation
    29 Jul 2021   2019.08.12.31    Further code reorganisation

---------------------------------------------------------------------------------------------------------------
'''
import datetime, platform, os, re, sys, json
from unidecode import unidecode

# Version / Log Title
VERSION_NO = '2019.12.22.31'
PLUGIN_LOG_TITLE = 'HardKinks'
LOG_BIGLINE = '------------------------------------------------------------------------------'
LOG_SUBLINE = '      ------------------------------------------------------------------------'

# Preferences
DELAY = 0                         # Delay used when requesting HTML, may be good to have to prevent being banned from the site
MATCHSITEDURATION = int(Prefs['matchsiteduration']) # Acceptable difference between actual duration of video file and that on agent website
DURATIONDX = int(Prefs['durationdx'])               # Acceptable difference between actual duration of video file and that on agent website
DETECT = Prefs['detect']                            # detect the language the summary appears in on the web page
PREFIXLEGEND = Prefs['prefixlegend']                # place cast legend at start of summary or end
COLCLEAR = Prefs['clearcollections']                # clear previously set collections
COLSTUDIO = Prefs['studiocollection']               # add studio name to collection
COLTITLE = Prefs['titlecollection']                 # add title [parts] to collection
COLGENRE = Prefs['genrecollection']                 # add genres to collection
COLDIRECTOR = Prefs['directorcollection']           # add director to collection
COLCAST = Prefs['castcollection']                   # add cast to collection
COLCOUNTRY = Prefs['countrycollection']             # add country to collection

# PLEX API /CROP Script/online image cropper
load_file = Core.storage.load
CROPPER = r'CScript.exe "{0}/Plex Media Server/Plug-ins/HardKinks.bundle/Contents/Code/ImageCropper.vbs" "{1}" "{2}" "{3}" "{4}"'
THUMBOR = Prefs['thumbor'] + "/0x0:{0}x{1}/{2}"

XML_PATHS = {
        'Search': '//*[@id="search"]//*[@class="g"]/div/div/div/a',
        'SearchTitle': '//h3/text()',
        'SearchUrl': './@href',
        'SiteTitle': '//h1[@class="h4"]/text()',
        'SiteSummary': '//h2', #not the text but the XML element
        'ReleaseDate' : '',
        'SiteArts': '//img[contains(@class,"border-light")]/@src',
        'CastMembers': '//a[contains(@class,"btn-outline-dark") and contains(@href,"modeles")]',
        'CastMembersName': '//a[contains(@class,"btn-outline-dark") and contains(@href,"modeles")]/h3/text()[normalize-space()]',
        'CastName': './h3/text()',
        'CastUrl': './@href',
        'CastPhoto': '//*[contains(@class,"obj-cover")]/@src',
        'SiteTags': '//a[contains(@class,"btn-outline-dark") and not(descendant::i)]/h3/text()',
        'Studio': ''
}

# URLS
BASE_URL = 'https://www.hardkinks.com'
BASE_SEARCH_URL = 'https://www.google.com/search?q=site%3Ahardkinks.com/videos/detail+{0}'
BASE_VIDEO = 'https://www.hardkinks.com/en/videos/detail/{0}'
# dictionary holding film variables
FILMDICT = {}   

# Date Formats used by website
DATEFORMAT = '%B %d, %Y'

# Website Language
SITE_LANGUAGE = 'en'

# ----------------------------------------------------------------------------------------------------------------------------------
def Start():
    ''' initialise process '''
    HTTP.CacheTime = CACHE_1WEEK
    HTTP.Headers['User-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.113 Safari/537.36'
    HTTP.Headers['Cookie'] = 'CONSENT=Y' #Bypasses the age verification screen
# ----------------------------------------------------------------------------------------------------------------------------------
def ValidatePrefs():
    ''' validate changed user preferences '''
    pass

# ----------------------------------------------------------------------------------------------------------------------------------
def anyOf(iterable):
    '''  used for matching strings in lists '''
    for element in iterable:
        if element:
            return element
    return None

# ----------------------------------------------------------------------------------------------------------------------------------
def log(message, *args):
    ''' log messages '''
    if re.search('ERROR', message, re.IGNORECASE):
        Log.Error(PLUGIN_LOG_TITLE + ' - ' + message, *args)
    else:
        Log.Info(PLUGIN_LOG_TITLE + '  - ' + message, *args)

# ----------------------------------------------------------------------------------------------------------------------------------
# imports placed here to use previously declared variables
import utils

# ----------------------------------------------------------------------------------------------------------------------------------
class HardKinks(Agent.Movies):
    ''' define Agent class '''
    name = 'HardKinks (IAFD)'
    languages = [Locale.Language.English]
    primary_provider = False
    preference = True
    media_types = ['Movie']
    contributes_to = ['com.plexapp.agents.GayAdult', 'com.plexapp.agents.GayAdultScenes']    
    # -------------------------------------------------------------------------------------------------------------------------------
    def CleanSearchString(self, myString):
        '''  clean search string before searching on EricVideos '''
        log('AGNT  :: Original Search Query        : {0}'.format(myString))

        myString = myString.lower().strip()

        # for titles with " - " replace with ":"
        myString = myString.replace(' - ', ': ')

        # replace curly apostrophes with straight as strip diacritics will remove these
        quoteChars = [ur'‘', ur'’', ur'\u2018', ur'\u2019']
        pattern = u'({0})'.format('|'.join(quoteChars))
        matched = re.search(pattern, myString)  # match against whole string
        if matched:
            log('AGNT  :: Search Query:: Replacing characters in string. Found one of these {0}'.format(quoteChars))
            myString = re.sub(pattern, "'", myString)
            myString = ' '.join(myString.split())   # remove continous white space
            log('AGNT  :: Amended Search Query [{0}]'.format(myString))
        else:
            log('AGNT  :: Search Query:: String has none of these {0}'.format(quoteChars))

        # string can not be longer than 50 characters
        if len(myString) > 50:
            lastSpace = myString[:50].rfind(' ')
            myString = myString[:lastSpace]

        myString = String.StripDiacritics(myString)
        myString = String.URLEncode(myString.strip())

        # sort out double encoding: & html code %26 for example is encoded as %2526; on MAC OS '*' sometimes appear in the encoded string
        myString = myString.replace('%25', '%').replace('*', '')

        log('AGNT  :: Returned Search Query        : {0}'.format(myString))
        log(LOG_BIGLINE)

        return myString

    # -------------------------------------------------------------------------------------------------------------------------------
    def search(self, results, media, lang, manual):
        ''' Search For Media Entry '''
        if not media.items[0].parts[0].file:
            return

        utils.logHeaders('SEARCH', media, lang)

        # Check filename format
        try:
            FILMDICT = utils.matchFilename(media.items[0].parts[0].file)
        except Exception as e:
            log('SEARCH:: Error: %s', e)
            return

        log(LOG_BIGLINE)

        # Search Query - for use to search the internet, remove all non alphabetic characters as GEVI site returns no results if apostrophes or commas exist etc..
        # if title is in a series the search string will be composed of the Film Title minus Series Name and No.
        searchTitle = self.CleanSearchString(FILMDICT['SearchTitle'])
        searchQuery = BASE_SEARCH_URL.format(searchTitle)

        # strip studio name from title to use in comparison
        log('SEARCH:: Search Title: %s', searchTitle)
        regex = ur'^{0} |at {0}$'.format(re.escape(FILMDICT['CompareStudio']))
        pattern = re.compile(regex, re.IGNORECASE)
        compareTitle = re.sub(pattern, '', searchTitle)
        compareTitle = utils.NormaliseComparisonString(compareTitle)

        log('SEARCH:: Search Title: %s', searchTitle)

        log('SEARCH:: Search Title: %s', searchTitle)
        if FILMDICT['ClipNo']:
            siteUrl = BASE_VIDEO.format(FILMDICT['ClipNo'])
            log('SEARCH:: Looking for video: %s, URL %s', FILMDICT['ClipNo'], siteUrl)
            try:
                html = HTML.ElementFromURL(siteUrl, timeout=20, sleep=DELAY)
            except Exception as e:
                log('SEARCH:: Error: Search Video Query did not pull any results: %s', e)
                return
            siteStudio = 'HardKinks'
            # Studio Name
            try:
                utils.matchStudio(siteStudio, FILMDICT)
                log(LOG_BIGLINE)
                FILMDICT['SiteURL'] = siteUrl
                FILMDICT['Title'] = html.xpath(XML_PATHS['SiteTitle'])[0].strip()
                log('SEARCH:: Video matched with ID %s', FILMDICT['ClipNo'])
                results.Append(MetadataSearchResult(id=json.dumps(FILMDICT), name=FILMDICT['Title'], score=100, lang=lang))
                return
            except Exception as e:
                log('SEARCH:: Error getting Site Studio from url %s: %s', siteUrl, e)
                log(LOG_SUBLINE)

        morePages = True
        while morePages:
            log('SEARCH:: Search Query: %s', searchQuery)
            try:
                html = HTML.ElementFromURL(searchQuery, timeout=20, sleep=DELAY)
            except Exception as e:
                log('SEARCH:: Error: Search Query did not pull any results: %s', e)
                return

            try:
                pageNumber = 1
                morePages = False
            except:
                searchQuery = ''
                log('SEARCH:: No More Pages Found')
                pageNumber = 1
                morePages = False

            titleList = html.xpath(XML_PATHS['Search'])
            log('SEARCH:: Result Page No: %s, Titles Found %s', pageNumber, len(titleList))
            log(LOG_BIGLINE)

            for title in titleList:
                # Site Entry
                try:
                    siteEntry = title.xpath(XML_PATHS['SearchTitle'])[0].strip()
                    log('SEARCH:: Site Entry:                   %s', siteEntry)
                    # prepare the Site Entry
                    singleQuotes = ["`", "‘", "’"]
                    pattern = ur'[{0}]'.format(''.join(singleQuotes))
                    siteEntry = re.sub(pattern, "'", siteEntry)

                    # the siteEntry usual has the format Studio: Title
                    siteEntry = siteEntry.lower()
                    if ' - ' in siteEntry:
                        siteTitle, siteStudio = siteEntry.split(' - ', 1)
                    elif '? ' in siteEntry:
                        siteStudio, siteTitle = siteEntry.split('? ', 1)
                    elif ', ' in siteEntry:
                        siteStudio, siteTitle = siteEntry.split(', ', 1)
                    elif FILMDICT['Studio'].lower() in siteEntry:       # in case the film title is mssing a separator between the studio and clip name
                        log('SEARCH:: Warning: Site Entry did not have a clear separator to separate Studio from Title')
                        siteStudio = FILMDICT['Studio'].lower()
                        siteTitle = FILMDICT['Title'].lower() if FILMDICT['Title'].lower() in siteEntry else ''
                    else:
                        log('SEARCH:: Error determining Site Studio and Title from Site Entry')
                        log(LOG_SUBLINE)
                        continue

                    log(LOG_BIGLINE)

                except Exception as e:
                    log('SEARCH:: Error getting Site Entry: %s', e)
                    log(LOG_SUBLINE)
                    continue
       
                try:
                    utils.matchTitle(siteTitle, FILMDICT)
                    titleMatche = True
                    log(LOG_BIGLINE)
                except Exception as e:
                    log('SEARCH:: Error getting Site Title: %s', e)
                    log(LOG_SUBLINE)
                    continue

                # Studio Name
                try:
                    utils.matchStudio(siteStudio, FILMDICT)
                    log(LOG_BIGLINE)
                except Exception as e:
                    log('SEARCH:: Error getting Site Studio: %s', e)
                    log(LOG_SUBLINE)
                    continue

                # Site Title URL
                try:
                    siteURL = title.xpath(XML_PATHS['SearchUrl'])[0]
                    siteURL = ('' if BASE_URL in siteURL else BASE_URL) + siteURL
                    FILMDICT['SiteURL'] = siteURL
                    log('SEARCH:: Site Title url                %s', siteURL)
                    log(LOG_BIGLINE)
                except Exception as e:
                    log('SEARCH:: Error getting Site Title Url: %s', e)
                    log(LOG_SUBLINE)
                    continue

                # we should have a match on studio, title and year now
                log('SEARCH:: Finished Search Routine')
                log(LOG_BIGLINE)
                results.Append(MetadataSearchResult(id=json.dumps(FILMDICT), name=FILMDICT['Title'], score=100, lang=lang))
                return

    # -------------------------------------------------------------------------------------------------------------------------------
    def update(self, metadata, media, lang, force=True):
        ''' Update Media Entry '''
        utils.logHeaders('UPDATE', media, lang)

        # Fetch HTML.
        FILMDICT = json.loads(metadata.id)
        log('UPDATE:: Film Dictionary Variables:')
        for key in sorted(FILMDICT.keys()):
            log('UPDATE:: {0: <29}: {1}'.format(key, FILMDICT[key]))
        log(LOG_BIGLINE)

        html = HTML.ElementFromURL(FILMDICT['SiteURL'], timeout=60, errors='ignore', sleep=1)

        #  The following bits of metadata need to be established and used to update the movie on plex
        #    1.  Metadata that is set by Agent as default
        #        a. Studio               : From studio group of filename - no need to process this as above
        #        b. Title                : From title group of filename - no need to process this as is used to find it on website
        #        c. Tag line             : Corresponds to the url of movie
        #        d. Originally Available : set from metadata.id (search result)
        #        e. Content Rating       : Always X
        #        f. Content Rating Age   : Always 18
        #        g. Collection Info      : From title group of filename 

        # 1a.   Set Studio
        metadata.studio = FILMDICT['Studio']
        log('UPDATE:: Studio: %s' , metadata.studio)

        # 1b.   Set Title
        metadata.title = FILMDICT['Title']
        log('UPDATE:: Title: %s' , metadata.title)

        # 1c/d. Set Tagline/Originally Available from metadata.id
        metadata.tagline = FILMDICT['SiteURL']

        # 1e/f. Set Content Rating to Adult/18 years
        metadata.content_rating = 'X'
        metadata.content_rating_age = 18
        log('UPDATE:: Content Rating - Content Rating Age: X - 18')

        # 1g. Collection
        if COLCLEAR:
            metadata.collections.clear()

        collections = FILMDICT['Collection']
        for collection in collections:
            metadata.collections.add(collection)

        log('UPDATE:: Collection Set From filename: %s', collections)

        #    2.  Metadata retrieved from website
        #        a.   Genres
        #        b.   Posters/Art
        #        c.   Summary

        # 2a. Tags - Fagalicious stores the cast and genres as tags
        log(LOG_BIGLINE)
        genreList = []
        try:
            testStudio = FILMDICT['Studio'].lower().replace(' ', '')
            ignoreGenres = []
            htmltags = html.xpath(XML_PATHS['SiteTags'])
            log('UPDATE:: %s Genres/Cast Tags Found: "%s"', len(htmltags), htmltags)
            for tag in htmltags:
                if '(' in tag:
                    tag = tag.split('(')[0].strip()
                if 'AKA' in tag:
                    tag = tag.split('AKA')[0].strip()
                if anyOf(x.lower() in tag.lower() for x in ignoreGenres):
                    continue
                # do not process studio names in tags
                if 'Movie' in tag or 'Series' in tag or '.com' in tag:
                    continue
                if tag.lower().replace(' ', '') in testStudio:
                    continue
                genreList.append(tag)
        except Exception as e:
            log('UPDATE:: Error getting Cast/Genres: %s', e)

        # Process Genres
        log(LOG_SUBLINE)
        log('UPDATE:: %s Genres Found: %s', len(genreList), genreList)
        metadata.genres.clear()
        genreList.sort()
        for genre in genreList:
            metadata.genres.add(genre)
            # add genres to collection
            if COLGENRE:
                metadata.collections.add(genre)
                                            
        # 2a    Cast
        #       QueerClick stores the cast as links in the article
        castList = {}
        log(LOG_BIGLINE)
        try:
            if XML_PATHS["CastMembersName"]:
                if html.xpath(XML_PATHS["CastMembers"]):
                    htmlcasstsite = html.xpath(XML_PATHS["CastMembers"])
                    for cast in htmlcasstsite:
                        castname = cast.xpath(XML_PATHS["CastName"])[0].strip(", ")
                        castname = String.StripDiacritics(castname)
                        if XML_PATHS["CastUrl"]:
                            casturl = cast.xpath(XML_PATHS["CastUrl"])[0]
                            if casturl.startswith('/'):
                                casturl = BASE_URL + casturl
                            castList[castname] = { 'Url': casturl }

                htmlcast = html.xpath(XML_PATHS["CastMembersName"])
                log('UPDATE:: %s fetched from site', len(htmlcast))

                # standardise apostrophe's then remove duplicates
                htmlcast = [x.replace("’", "'") for x in htmlcast]
                htmlcast = [x.strip(", ") for x in htmlcast]
                htmlcast = list(set(htmlcast))

                # remove File Studio Name
                htmlcast = [x for x in htmlcast if not '.tv' in x.lower()]
                htmlcast = [x for x in htmlcast if not '.com' in x.lower()]
                htmlcast = [x for x in htmlcast if not '.net' in x.lower()]
                htmlcast = [x for x in htmlcast if not FILMDICT['Studio'].replace(' ', '').lower() in x.replace(' ', '').lower()]

                # as cast is found in summary text and actors can be referred to by their first names only; remove these
                htmlcast = [l for i, l in enumerate(htmlcast) if True not in [l in x for x in htmlcast[0:i]]]

                castDict = utils.getCast(htmlcast, FILMDICT)
                # sort the dictionary and add key(Name)- value(Photo, Role) to metadata
                metadata.roles.clear()
                log('UPDATE:: Number of cast to be added: %s', len(castDict))
                for key in sorted(castDict):
                    newRole = metadata.roles.new()
                    newRole.name = key
                    if castDict[key]['Photo']:
                        newRole.photo = castDict[key]['Photo']
                    else:
                        if key in castList:
                            if castList[key]['Url'] and XML_PATHS["CastPhoto"]:
                                log('UPDATE:: Fetching photo for %s: %s',key, castList[key]['Url'])
                                castdetailhtml = HTML.ElementFromURL(castList[key]['Url'], timeout=60, errors='ignore', sleep=1)
                                photo = castdetailhtml.xpath(XML_PATHS["CastPhoto"])[0]
                                if photo.startswith('/'):
                                    photo = BASE_URL + photo
                                newRole.photo = photo
                    newRole.role = castDict[key]['Role']
                    # add cast name to collection
                    if COLCAST:
                        metadata.collections.add(key)
        except Exception as e:
            log('UPDATE:: Error getting Cast: %s', e)

        # 2c.   Posters/Art - First Image set to Poster, next to Art
        log(LOG_BIGLINE)
        imageType = 'Poster & Art'
        try:
            if XML_PATHS['SiteArts']:
                htmlimages = html.xpath(XML_PATHS['SiteArts'])
                if len(htmlimages) == 1:
                    htmlimages.append(htmlimages[0])
                log('UPDATE:: %s Images Found: %s', len(htmlimages), htmlimages)
                posterIndex = ((len(htmlimages) % 2) +1)
                if len(htmlimages) < posterIndex:
                    posterIndex = 0
                for index, image in enumerate(htmlimages):
                    if image.startswith("/"):
                        image = BASE_URL + image
                    image = image.replace('.webp', '.jpg')      # change extension of url image
                    if index > 1:
                        break
                    whRatio = 1.5 if index == posterIndex else 0.5625
                    imageType = 'Poster' if index == posterIndex else 'Art'
                    pic, picContent = utils.getFilmImages(imageType, image, whRatio)    # height is 1.5 times the width for posters
                    if index == posterIndex:     # processing posters
                        #  clean up and only keep the posters we have added
                        metadata.posters[pic] = Proxy.Media(picContent, sort_order=1)
                        metadata.posters.validate_keys([pic])
                        log(LOG_SUBLINE)
                    elif (metadata.art) == 0:               # processing art
                        metadata.art[pic] = Proxy.Media(picContent, sort_order=1)
                        metadata.art.validate_keys([pic])

        except Exception as e:
            log('UPDATE:: Error getting %s: %s', imageType, e)

        # 2a.   Summary = IAFD Legend + Synopsis
        # synopsis
        synopsis = ''
        try:
            htmlsynopsis = html.xpath(XML_PATHS['SiteSummary'])
            for item in htmlsynopsis:
                synopsis = '{0}{1}\n'.format(synopsis, item.text_content())
            log('UPDATE:: Synopsis Found: %s', synopsis)
            pattern = re.compile(r'Watch.*at.*', re.IGNORECASE)
            synopsis = re.sub(pattern, '', synopsis)
        except Exception as e:
            log('UPDATE:: Error getting Synopsis: %s', e)

        # combine and update
        log(LOG_SUBLINE)
        summary = ('{0}\n{1}' if PREFIXLEGEND else '{1}\n{0}').format(FILMDICT['CastLegend'], synopsis.strip())
        summary = summary.replace('\n\n', '\n')
        metadata.summary = summary
        log('UPDATE:: Summary updated %s', metadata.summary)

        log(LOG_BIGLINE)
        log('UPDATE:: Finished Update Routine')
        log(LOG_BIGLINE)