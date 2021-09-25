#!/usr/bin/env python
# encoding=utf8
'''
# AEBNiii - (IAFD)
                                                  Version History
                                                  ---------------
    Date            Version                         Modification
    21 May 2020   2020.05.21.01    Creation: using current AdultEntertainmentBroadcastNetwork website - added scene breakdown to summary
    01 Jun 2020   2020.05.21.02    Implemented translation of summary
                                   improved getIAFDActor search
    27 Jun 2020   2020.05.21.03    Improvement to Summary Translation: Translate into Plex Library Language
                                   stripping of intenet domain suffixes from studio names when matching
                                   handling of unicode characters in film titles and comparision string normalisation
    01 Jul 2020   2020.05.21.03	   Renamed to AEBNiii
    14 Jul 2020   2020.05.21.04    Enhanced seach to also look through the exact matches, as AEBN does not always put these
                                   in the general search results
    07 Oct 2020   2020.05.21.05    IAFD - change to https
    09 Jan 2021   2020.05.21.06    IAFD - New Search Routine + Auto Collection setting
    19 Feb 2021   2020.05.21.08    Moved IAFD and general functions to other py files
                                   Enhancements to IAFD search routine, including LevenShtein Matching on Cast names
                                   set content_rating age to 18
                                   Set collections from filename + countries, cast and directors
                                   Added directors photos
                                   included studio on iafd processing of filename
                                   Added iafd legend to summary
                                   improved logging
    31 Jul 2021   2020.05.21.09    Code reorganisation, use of review area for scene info

-----------------------------------------------------------------------------------------------------------------------------------
'''
import json, re
from datetime import datetime

# Version / Log Title
VERSION_NO = '2020.05.21.08'
PLUGIN_LOG_TITLE = 'AEBN iii'

# log section separators
LOG_BIGLINE = '--------------------------------------------------------------------------------'
LOG_SUBLINE = '      --------------------------------------------------------------------------'

# Preferences
DELAY = int(Prefs['delay'])                         # Delay used when requesting HTML, may be good to have to prevent being banned from the site
MATCHSITEDURATION = Prefs['matchsiteduration']      # Match against Site Duration value
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

# URLS
BASE_URL = 'https://gay.aebn.com'
BASE_SEARCH_URL = [BASE_URL + '/gay/search/?sysQuery={0}', BASE_URL + '/gay/search/movies/page/1?sysQuery={0}&criteria=%7B%22sort%22%3A%22Relevance%22%7D']

IGNORE_STUDIOS_GENRES = ['rawfuckclub','darkalleymedia', 'menatplay', 'kink', 'boundgods', 'boundinpublic']
ALTERNATE_STUDIOS = {
    "Dark Alley Media": ["Raw Fuck Club"],
    "Bound Gods": ["Kink", "Kink Men"],
    "Bound in Public": ["Kink", "Kink Men"],
    "Men On Edge": ["Kink", "Kink Men"],
    "30 Minutes Of Torment": ["Kink", "Kink Men"],
    "KinkMen" : ["Kink", "Bound Gods", "Bound in Public", "Men On Edge", "30 Minutes Of Torment"],
    "Kink" : ["KinkMen", "Bound Gods", "Bound in Public", "Men On Edge", "30 Minutes Of Torment"]
}
STUDIOS_SKIP_STEPS=["rawfuckclub", "darkalleymedia", "boundgods", "boundinpublic", "menonedge", "30minutesoftorment", "menatplay"]
# dictionary holding film variables
FILMDICT = {}

# Date Formats used by website
DATEFORMAT = '%b %d, %Y'

# Website Language
SITE_LANGUAGE = 'en'

XML_PATHS = {
        'Search': '',
        'SearchTitle': '',
        'SearchStudio': '',
        'SearchUrl': '',
        'SiteTitle': '',
        'SiteSummary': '', #not the text but the XML element
        'ReleaseDate' : '',
        'SiteArts': '',
        'CastMembers': '',
        'CastMembersName': '',
        'CastName': '',
        'CastUrl': '',
        'CastPhoto': '',
        'SiteTags': '',
        'Studio': '',
        'Scenes': '//*[contains(@class,"dts-movie")]/*[contains(@class,"dts-panel")]',
        'SceneNo': './/*[@class="dts-panel-header-title"]//*[@class="dts-panel-header-title-no-link"]/text()',
        'SceneCastNames': './/*[@class="dts-scene-star-wrapper"]/*/text()',
        'SceneGenres': './/*[contains(@class,"dts-scene-info")]/*/*[2]/*[@class="dts-text-link"]/text()',
}

# ----------------------------------------------------------------------------------------------------------------------------------
def Start():
    ''' initialise process '''
    HTTP.CacheTime = CACHE_1WEEK
    HTTP.Headers['User-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.113 Safari/537.36'

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
import utilsGenres

# ----------------------------------------------------------------------------------------------------------------------------------
class AEBNiii(Agent.Movies):
    ''' define Agent class '''
    name = 'AEBN iii (IAFD)'
    languages = [Locale.Language.English]
    primary_provider = False
    preference = True
    media_types = ['Movie']
    contributes_to = ['com.plexapp.agents.GayAdult', 'com.plexapp.agents.GayAdultFilms']

    # -------------------------------------------------------------------------------------------------------------------------------
    def matchFilmTitle(self, ExactMatches, title, FILMDICT):
        ''' match Film in list returned by running the query '''
        matched = True

        # Site Title
        try:
            siteTitle = title.xpath('./section//h1/a/text()')[0] if ExactMatches else title.xpath('./a//img/@title')[0]
            utils.matchTitle(siteTitle, FILMDICT)
            log(LOG_BIGLINE)
        except Exception as e:
            log('AGNT  :: Error getting Site Title: %s', e)
            log(LOG_SUBLINE)
            matched = False

        # Site Title URL
        if matched:
            try:
                siteURL = title.xpath('./section//h1/a/@href')[0] if ExactMatches else title.xpath('./a/@href')[0]
                siteURL = ('' if BASE_URL in siteURL else BASE_URL) + siteURL
                FILMDICT['SiteURL'] = siteURL
                log('AGNT  :: Site Title URL                %s', siteURL)
                log(LOG_BIGLINE)
            except:
                log('AGNT  :: Error getting Site Title Url')
                log(LOG_SUBLINE)
                matched = False

        # Access Site URL for Studio and Release Date information only when looking at non exact match titles
        if matched:
            if not ExactMatches:
                try:
                    log('AGNT  :: Reading Site URL page         %s', siteURL)
                    html = HTML.ElementFromURL(FILMDICT['SiteURL'], sleep=DELAY)
                except Exception as e:
                    log('AGNT  :: Error reading Site URL page: %s', e)
                    log(LOG_SUBLINE)
                    matched = False

        # Site Studio
        if matched:
            foundStudio = False
            try:
                htmlSiteStudio = title.xpath('./section//li[contains(@class,"item-studio")]/a/text()') if ExactMatches else html.xpath('//div[@class="dts-studio-name-wrapper"]/a/text()')
                siteStudios = []
                for siteStudio in htmlSiteStudio:
                    if siteStudio not in siteStudios:
                        siteStudios.append(siteStudio)
                    if siteStudio in ALTERNATE_STUDIOS:
                        for alternateStudio in ALTERNATE_STUDIOS[siteStudio]:
                            if alternateStudio not in siteStudios:
                                siteStudios.append(alternateStudio)
                log('AGNT  :: %s Site URL Studios             %s', len(htmlSiteStudio), htmlSiteStudio)
                log('AGNT  :: %s Site URL Studios w/alternate %s', len(siteStudios), siteStudios)
                for siteStudio in siteStudios:
                    try:
                        utils.matchStudio(siteStudio, FILMDICT)
                        foundStudio = True
                    except Exception as e:
                        log('AGNT  :: Error: %s', e)
                        log(LOG_SUBLINE)

                    if foundStudio:
                        log(LOG_BIGLINE)
                        break
            except Exception as e:
                log('AGNT  :: Error getting Site Studio %s', e)
                log(LOG_SUBLINE)
                matched = False

            if not foundStudio:
                log('AGNT  :: Error No Matching Site Studio')
                log(LOG_SUBLINE)
                matched = False

        # Site Release Date
        if matched:
            try:
                siteReleaseDate = title.xpath('./section//li[contains(@class,"item-release-date")]/text()')[0].strip() if ExactMatches else html.xpath('//li[contains(@class,"item-release-date")]/text()')[0].strip()
                log('AGNT  :: Site URL Release Date         %s', siteReleaseDate)
                try:
                    siteReleaseDate = utils.matchReleaseDate(siteReleaseDate, FILMDICT)
                    log(LOG_BIGLINE)
                except Exception as e:
                    log('AGNT  :: Error getting Site URL Release Date: %s', e)
                    log(LOG_SUBLINE)
                    matched = False
            except:
                log('AGNT  :: Error getting Site URL Release Date: Default to Filename Date')
                log(LOG_SUBLINE)

        # Site Film Duration
        if matched:
            try:
                siteDuration = title.xpath('./section//li[contains(@class,"list-item-duration")]/text()')[0].strip() if ExactMatches else html.xpath('//li[contains(@class,"list-item-duration")]/text()')[0].strip()
                log('SEARCH:: Site Film Duration            %s', siteDuration)
                try:
                    utils.matchDuration(siteDuration, FILMDICT, MATCHSITEDURATION)
                    log(LOG_BIGLINE)
                except Exception as e:
                    log('SEARCH:: Error getting Site Film Duration: %s', e)
                    log(LOG_SUBLINE)
                    matched = False
            except:
                log('AGNT  :: Error getting Site Film Duration')
                log(LOG_SUBLINE)

        return matched

    # -------------------------------------------------------------------------------------------------------------------------------
    def CleanSearchString(self, myString):
        ''' Prepare Title for search query '''
        log('AGNT  :: Original Search Query        : {0}'.format(myString))

        # convert to lower case and trim and strip diacritics, fullstops, enquote
        myString = myString.replace('.', '').replace('-', '')
        myString = myString.lower().strip()
        myString = String.StripDiacritics(myString)

        # sort out double encoding: & html code %26 for example is encoded as %2526; on MAC OS '*' sometimes appear in the encoded string
        myNormalString = String.URLEncode(myString).replace('%25', '%').replace('*', '')
        myQuotedString = String.URLEncode('"{0}"'.format(myString)).replace('%25', '%').replace('*', '')
        myString = [myQuotedString, myNormalString]
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
        searchTitleList = []
        if FILMDICT['SearchMovie']:
            searchTitleList.extend(self.CleanSearchString(FILMDICT['SearchMovie']))    
        searchTitleList.extend(self.CleanSearchString(FILMDICT['SearchTitle']))
        for count, searchTitle in enumerate(searchTitleList, start=1):
            searchQuery = BASE_SEARCH_URL[0].format(searchTitle)
            log('SEARCH:: %s. Exact Match Search Query: %s', count, searchQuery)

            # first check exact matches
            try:
                html = HTML.ElementFromURL(searchQuery, timeout=20, sleep=DELAY)
                titleList = html.xpath('//section[contains(@class,"dts-panel-exact-match")]/div[@class="dts-panel-content"]')
                for title in titleList:
                    matchedTitle = self.matchFilmTitle(True, title, FILMDICT)

                    # we should have a match on studio, title and year now
                    if matchedTitle:
                        log('SEARCH:: Finished Search Routine')
                        log(LOG_BIGLINE)
                        results.Append(MetadataSearchResult(id=json.dumps(FILMDICT, ensure_ascii=True, separators=(',', ':')), name=FILMDICT['Title'], score=100, lang=lang))
                        return
            except Exception as e:
                log('SEARCH:: Error: Search Query did find any Exact Movie Matches: %s', e)

            # if we get here there were no exact matches returned by the search query, so search through the rest
            searchQuery = BASE_SEARCH_URL[1].format(searchTitle)
            log('SEARCH:: %s. General Search Query: %s', count, searchQuery)
            morePages = True
            while morePages:
                log('SEARCH:: Search Query: %s', searchQuery)
                try:
                    html = HTML.ElementFromURL(searchQuery, timeout=20, sleep=DELAY)
                    # Finds the entire media enclosure
                    titleList = html.xpath('//div[@class="dts-image-overlay-container"]')
                    if not titleList:
                        break   # out of WHILE loop to the FOR loop
                except Exception as e:
                    log('SEARCH:: Error: Search Query did not pull any results: %s', e)
                    return

                try:
                    searchQuery = html.xpath('//ul[@class="dts-pagination"]/li[@class="active" and text()!="..."]/following::li/a[@class="dts-paginator-tagging"]/@href')[0]
                    searchQuery = (BASE_URL if BASE_URL not in searchQuery else '') + searchQuery
                    log('SEARCH:: Next Page Search Query: %s', searchQuery)
                    pageNumber = int(html.xpath('//ul[@class="dts-pagination"]/li[@class="active" and text()!="..."]/text()')[0])
                    morePages = True if pageNumber <= 1 else False
                except:
                    searchQuery = ''
                    log('SEARCH:: No More Pages Found')
                    pageNumber = 1
                    morePages = False

                log('SEARCH:: Result Page No: %s, Titles Found %s', pageNumber, len(titleList))
                log(LOG_BIGLINE)
                for title in titleList:
                    # get film variables in dictionary format: if dict is filled we have a match
                    matchedTitle = self.matchFilmTitle(False, title, FILMDICT)
                    if matchedTitle:
                        # we should have a match on studio, title and year now
                        log('SEARCH:: Finished Search Routine')
                        log(LOG_BIGLINE)
                        results.Append(MetadataSearchResult(id=json.dumps(FILMDICT, ensure_ascii=True, separators=(',', ':')), name=FILMDICT['Title'], score=100, lang=lang))
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

        html = HTML.ElementFromURL(FILMDICT['SiteURL'], timeout=60, errors='ignore', sleep=DELAY)
        htmlScene = None

        isMovie = FILMDICT['Movie'] != ""
        hasScene = FILMDICT['Title'] != ""
        runDetailStep = not (isMovie and FILMDICT['Studio'].lower().replace(' ','') in STUDIOS_SKIP_STEPS)

        #  The following bits of metadata need to be established and used to update the movie on plex
        #    1.  Metadata that is set by Agent as default
        #        a. Studio               : From studio group of filename - no need to process this as above
        #        b. Title                : From title group of filename - no need to process this as is used to find it on website
        #        c. Tag line             : Corresponds to the url of movie
        #        d. Originally Available : set from metadata.id (search result)
        #        e. Content Rating       : Always X
        #        f. Content Rating Age   : Always 18
        #        g. Collection Info      : From title group of filename 
        if FILMDICT['Movie']:
            if not 'Scenes' in XML_PATHS:
                raise Exception('<Scenes XML Path not defined>')
            if not 'SceneNo' in XML_PATHS:
                raise Exception('<SceneNo XML Path not defined>')
            agentSceneNo = FILMDICT['SceneNo'].lower().replace(' ','')
            scenes = html.xpath(XML_PATHS['Scenes'])
            foundScene = False
            for siteScene in scenes:
                if foundScene == True:
                    continue
                if len(siteScene.xpath(XML_PATHS['SceneNo'])) > 0:
                    sceneNo = siteScene.xpath(XML_PATHS['SceneNo'])[0].lower().replace(' ','').replace('scene','')
                    if (sceneNo == agentSceneNo):
                        foundScene = True
                        htmlScene = siteScene
                        log('UPDATE:: Matched Scene for Movie %s' , FILMDICT['Movie'])
                        log('                     Agent Scene %s' , FILMDICT['SceneNo'])
                        log('                      Site Scene %s' , sceneNo)
            if foundScene == False:
                log('UPDATE:: Scene %s not found for Movie %s' , FILMDICT['SceneNo'], FILMDICT['Movie'])
                log('UPDATE:: Updating title and poster')
        
        # 1a.   Set Studio
        metadata.studio = FILMDICT['Studio']
        log('UPDATE:: Studio: %s' , metadata.studio)

        # 1b.   Set Title
        if FILMDICT['Movie']:
            if FILMDICT['SceneNo']:
                metadata.title = '%s (Scene %s) - %s' % (FILMDICT['Movie'], FILMDICT['SceneNo'], FILMDICT['Title']) if FILMDICT['Title'] else '%s (Scene %s)' % (FILMDICT['Movie'], FILMDICT['SceneNo'])            
            else:
                metadata.title = '%s - %s' % (FILMDICT['Movie'],  FILMDICT['Title']) if FILMDICT['Title'] else FILMDICT['Movie']
        else:
            metadata.title = FILMDICT['Title']
        log('UPDATE:: Title: %s' , metadata.title)

        # 1c/d. Set Tagline/Originally Available from metadata.id
        if runDetailStep:
            metadata.tagline = FILMDICT['SiteURL']

        if FILMDICT['CompareDate']:
            metadata.originally_available_at = datetime.strptime(FILMDICT['CompareDate'], DATEFORMAT)
            metadata.year = metadata.originally_available_at.year
            log('UPDATE:: Tagline: %s', metadata.tagline)
            log('UPDATE:: Default Originally Available Date: %s', metadata.originally_available_at)

        # 1e/f. Set Content Rating to Adult/18 years
        metadata.content_rating = 'X'
        metadata.content_rating_age = 18
        log('UPDATE:: Content Rating - Content Rating Age: X - 18')

        # 1g. Collection
        if COLCLEAR:
            metadata.collections.clear()

        if COLTITLE:
            collections = FILMDICT['Collection']
            for collection in collections:
                metadata.collections.add(collection)
            log('UPDATE:: Collection Set From filename: %s', collections)

        #    2.  Metadata retrieved from website
        #        a. Genres
        #        b. Collections
        #        c. Directors            : List of Drectors (alphabetic order)
        #        d. Cast                 : List of Actors and Photos (alphabetic order) - Photos sourced from IAFD
        #        e. Posters/Background
        #        f. Reviews              : Scene Breakdowns
        #        f. Summary              : Synopsis

        # 2a.   Genres
        log(LOG_BIGLINE)
        try:
            ignoreGenres = ['feature', 'exclusive', 'new release', 'hd', 'high definition']
            genres = []
            if runDetailStep:
                #if FILMDICT['Match'] == 'Movie':
                #    htmlgenres = htmlScene.xpath(XML_PATHS['SceneGenres'])
                #else:
                htmlgenres = html.xpath('//span[@class="dts-image-display-name"]/text()')

                htmlgenres = [x.strip() for x in htmlgenres if x.strip()]
                htmlgenres.sort()
                log('UPDATE:: %s Genres Found: %s', len(htmlgenres), htmlgenres)
                for genre in htmlgenres:
                    if anyOf(x in genre.lower() for x in ignoreGenres):
                        continue
                    genres.append(genre)
                    if 'compilation' in genre.lower():
                        FILMDICT['Compilation'] = 'Compilation'

                metadata.genres.clear()
                genres = utilsGenres.getGenres(genres)
                for genre in genres:
                    metadata.genres.add(genre)
                    # add genres to collection
                    if COLGENRE:
                        metadata.collections.add(genre)
        except Exception as e:
            log('UPDATE:: Error getting Genres: %s', e)

        # 2b.   Collections
        if runDetailStep and COLTITLE:
            log(LOG_BIGLINE)
            try:
                htmlcollections = html.xpath('//li[@class="section-detail-list-item-series"]/span/a/span/text()')
                htmlcollections = [x for x in htmlcollections if x.strip()]
                log('UPDATE:: %s Collections Found: %s', len(htmlcollections), htmlcollections)
                uniqueCollections = [x for x in htmlcollections if x.lower() not in (y.lower() for y in FILMDICT['Collection'])]
                for collection in uniqueCollections:
                    metadata.collections.add(collection)
                    log('UPDATE:: %s Collection Added: %s', collection)
            except Exception as e:
                log('UPDATE:: Error getting Collections: %s', e)

        # 2c.   Directors
        log(LOG_BIGLINE)
        try:
            htmldirectors = html.xpath('//li[@class="section-detail-list-item-director"]/span/a/span/text()')
            htmldirectors = ['{0}'.format(x.strip()) for x in htmldirectors if x.strip()]
            log('UPDATE:: Director List %s', htmldirectors)
            directorDict = utils.getDirectors(htmldirectors, FILMDICT)
            metadata.directors.clear()
            for key in sorted(directorDict):
                newDirector = metadata.directors.new()
                newDirector.name = key
                newDirector.photo = directorDict[key]
                # add director to collection
                if COLDIRECTOR:
                    metadata.collections.add(key)

        except Exception as e:
            log('UPDATE:: Error getting Director(s): %s', e)

        # 2d.   Cast: get thumbnails from IAFD as they are right dimensions for plex cast list and have more actor photos than AdultEntertainmentBroadcastNetwork
        if runDetailStep:
            log(LOG_BIGLINE)
            try:
                if FILMDICT['SceneNo']:
                    htmlcast = htmlScene.xpath(XML_PATHS['SceneCastNames'])
                else:
                    htmlcast = html.xpath('//div[@class="dts-star-name-overlay"]/text()')
                castDict = utils.getCast(htmlcast, FILMDICT)

                # sort the dictionary and add key(Name)- value(Photo, Role) to metadata
                metadata.roles.clear()
                atLeatOneCastPhoto = False
                for key in sorted(castDict):
                    newRole = metadata.roles.new()
                    newRole.name = key
                    newRole.photo = castDict[key]['Photo']
                    if castDict[key]['Photo']:
                        atLeatOneCastPhoto = True
                    newRole.role = castDict[key]['Role']
                    # add cast name to collection
                    if COLCAST:
                        metadata.collections.add(key)
                #When no cast member have a photos, don't fetch, they will be fetched by a lower priority agent
                if atLeatOneCastPhoto == False:
                    log('UPDATE:: No cast photo photo found')
                    metadata.roles.clear()

            except Exception as e:
                log('UPDATE:: Error getting Cast: %s', e)

        # 2e.   Posters/Art - Front Cover set to poster, Back Cover to art
        log(LOG_BIGLINE)
        try:
            htmlimages = html.xpath('//*[contains(@class,"dts-movie-boxcover")]//img/@src')
            image = htmlimages[0].split('?')[0]
            image = ('http:' if 'http:' not in image else '') + image
            log('UPDATE:: Poster Image Found: %s', image)
            #  clean up and only keep the poster we have added
            metadata.posters[image] = Proxy.Media(HTTP.Request(image).content, sort_order=1)
            metadata.posters.validate_keys([image])

            if runDetailStep:
                log(LOG_SUBLINE)
                image = htmlimages[1].split('?')[0]
                image = ('http:' if 'http:' not in image else '') + image
                log('UPDATE:: Art Image Found: %s', image)
                #  clean up and only keep the Art we have added
                metadata.art[image] = Proxy.Media(HTTP.Request(image).content, sort_order=1)
                metadata.art.validate_keys([image])
        except Exception as e:
            log('UPDATE:: Error getting Poster/Art: %s', e)

        # 2f.   Reviews - Put all Scene Information here
        try:
            if isMovie and not hasScene:
                htmlscenes = html.xpath('//div[@class="col-sm-6 m-b-1"]')
                log(LOG_BIGLINE)
                log('UPDATE:: Possible Number of Scenes [%s]', len(htmlscenes))

                metadata.reviews.clear()
                count = 0
                sceneCount = 0 # avoid enumerating the number of scenes as some films have empty scenes
                htmlheadings = html.xpath('//header[@class="dts-panel-header"]/div/h1[contains(text(),"Scene")]/text()')
                htmlscenes = html.xpath('//div[@class="dts-scene-info dts-list-attributes"]')
                log('UPDATE:: %s Scenes Found', len(htmlscenes))
                for (heading, htmlscene) in zip(htmlheadings, htmlscenes):
                    try:
                        count += 1
                        castList = htmlscene.xpath('./ul/li[descendant::span[text()="Stars:"]]/a/text()')
                        if castList:
                            castList = [x.split('(')[0] for x in castList]
                            title = ', '.join(castList)
                            log('UPDATE:: Title: Cast List [%s]', title)
                        else:
                            title = ''

                        actsList = htmlscene.xpath('./ul/li[descendant::span[text()="Sex acts:"]]/a/text()')
                        if actsList:
                            actsList = [x for x in actsList if x]
                            writing = ', '.join(actsList)
                            log('UPDATE:: Writing: Sex Acts [%s]', writing)
                        else:
                            writing = ''

                        # if no title and no scene write up
                        if not title and not writing:
                            continue
                        sceneCount += 1

                        settingsList = htmlscene.xpath('./ul/li[descendant::span[text()="Settings:"]]/a/text()')
                        if settingsList:
                            settingsList = [x for x in settingsList if x]
                            author = ', '.join(settingsList)
                            log('UPDATE:: Author: Setting List [%s]', author)
                            settings = ('[{0}] Setting: {1}').format(heading.strip(), author)
                        else:
                            author = '[{0}]'.format(heading.strip())

                        newReview = metadata.reviews.new()
                        newReview.author = author
                        newReview.link  = FILMDICT['SiteURL']
                        if len(title) > 40:
                            for i in range(40, -1, -1):
                                if title[i] == ' ':
                                    title = title[0:i]
                                    break
                        newReview.source = '{0}. {1}...'.format(sceneCount, title if title else FILMDICT['Title'])
                        if len(writing) > 275:
                            for i in range(275, -1, -1):
                                if writing[i] in ['.', '!', '?']:
                                    writing = writing[0:i + 1]
                                    break
                        newReview.text = utils.TranslateString(writing, lang)
                        log(LOG_SUBLINE)
                    except Exception as e:
                        log('UPDATE:: Error getting Scene No. %s: %s', count, e)
        except Exception as e:
            log('UPDATE:: Error getting Scenes: %s', e)

        # 2g.   Summary = IAFD Legend + Synopsis
        # synopsis
        if runDetailStep:
            try:
                synopsis = html.xpath('//div[@class="dts-section-page-detail-description-body"]/text()')[0].strip()
                log('UPDATE:: Synopsis Found: %s', synopsis)
                synopsis = utils.TranslateString(synopsis, lang)
            except Exception as e:
                synopsis = ''
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