#!/usr/bin/env python
# encoding=utf8
# FraternityX
import re, os, platform, cgi, datetime, pprint, sys
import urllib
import urlparse

AGENT_NAME             = 'FraternityX'
AGENT_VERSION          = '2021.08.25.0'
AGENT_LANGUAGES        = [Locale.Language.NoLanguage, Locale.Language.English]
AGENT_FALLBACK_AGENT   = False
AGENT_PRIMARY_PROVIDER = False
AGENT_CONTRIBUTES_TO   = ['com.plexapp.agents.cockporn']
AGENT_CACHE_TIME       = CACHE_1HOUR * 24
AGENT_MATCH_VIDEO_NAME = False

META_ID_SEPARATOR = "|||-|||"

LOG_BIGLINE = '------------------------------------------------------------------------------'
LOG_SUBLINE = '---------------------'
LOG_STARLINE ='******************************************************************************'

def Start():
	Log.Info(LOG_BIGLINE)
	Log.Info('[' + AGENT_NAME + '] ' + 'Starting Metadata Agent ' + AGENT_VERSION)
	HTTP.CacheTime = 0	
	HTTP.Headers['Cookie'] = 'pp-accepted=true' #Bypasses the age verification screen
	HTTP.Headers['User-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36'

def ValidatePrefs():
	Log.Info('[' + AGENT_NAME + '] ' + 'Validating Preferences')
	Log.Debug('[' + AGENT_NAME + '] ' + 'Folder(s) where these items might be found: ' + str(Prefs['folders']))
	Log.Debug('[' + AGENT_NAME + '] ' + 'Regular expression - ' + str(Prefs['regex']))
	Log.Debug('[' + AGENT_NAME + '] ' + 'Cover Images to download - ' + str(Prefs['cover']))
	Log.Debug('[' + AGENT_NAME + '] ' + 'Ouput debugging info in logs - ' + str(Prefs['debug']))
	Log.Info('[' + AGENT_NAME + '] ' + 'Validation Complete')

def log(state, message, *args):
	if state == 'info':
		Log.Info('[' + AGENT_NAME + '] ' + ' - ' + message, *args)
	elif state == 'error':
		Log.Error('[' + AGENT_NAME + '] ' + ' - ' + message, *args)
	elif Prefs['debug'] and state == 'debug':
		Log.Debug('[' + AGENT_NAME + '] ' + ' - ' + message, *args)

import utils
from studioVars import SCRAPER_PATHS, STUDIO_MAP, URL, REQUEST_DELAY

class FraternityX(Agent.Movies):
	name = AGENT_NAME
	languages = AGENT_LANGUAGES
	media_types = ['Movie']
	primary_provider = AGENT_PRIMARY_PROVIDER
	fallback_agent = AGENT_FALLBACK_AGENT
	contributes_to = AGENT_CONTRIBUTES_TO

	def search(self, results, media, lang):
		log('info', LOG_BIGLINE)
		log('info', '%s> search::init:%s', LOG_SUBLINE, media.title)
		log('info', LOG_BIGLINE)
		log('debug', 'search::%s | Platform: %s %s', media.title, platform.system(), platform.release())
		log('debug', 'search::%s | results - %s', media.title, results)
		log('debug', 'search::%s | media.items[0].parts[0].file - %s', media.title, media.items[0].parts[0].file)
		log('debug', 'search::%s | media.filename - %s', media.title, media.filename)
		log('debug', 'search::%s | %s', media.title, results)

		if not media.items[0].parts[0].file:
			return

		path_and_file = media.items[0].parts[0].file
		log('debug', 'search::%s | Filepath - %s', media.title, path_and_file)

		path_and_file = os.path.splitext(path_and_file)[0]
		enclosing_directory, file_name = os.path.split(os.path.splitext(path_and_file)[0])
		enclosing_directory, enclosing_folder = os.path.split(enclosing_directory)
		log('debug', 'search::%s | Enclosing Folder - %s', media.title, enclosing_folder)
		log('debug', 'search::%s | Enclosing Directory - %s', media.title, enclosing_directory)
		log('debug', 'search::%s | File Name - %s', media.title, file_name)

		if Prefs['folders'] != "*":
			folder_list = re.split(',\s*', Prefs['folders'])
			file_folders = utils.splitall(path_and_file)
			log('debug', 'search::%s | Looking for folder matched - Folders enabled: [%s] ', media.title, ','.join(folder_list))
			log('debug', 'search::%s | Item folder - Folders enabled: [%s] ', media.title, ','.join(file_folders))
			folder_matched = False
			for folder in file_folders:
				if folder in folder_list:
					folder_matched = True
					log('info', 'search::%s | Folder matched - %s', media.title, folder)
			if folder_matched == False:
				log('info', 'search::%s | No folder match found - Skipping media', media.title)
				log('debug', LOG_BIGLINE)
				return

		# File names to match for this agent
		log('debug', 'search::%s | Regular expression: %s', media.title, str(Prefs['regex']))
		try:
			file_name_pattern = re.compile(Prefs['regex'], re.IGNORECASE)
		except Exception as e:
			log('error', LOG_STARLINE)
			log('error', 'search::%s | Error with regex - %s | %s', media.title, path_and_file, e)
			log('error', LOG_STARLINE)
			return

		m = file_name_pattern.search(file_name)
		if not m:
			log('debug', 'search::%s | File %s not in expected format - Skipping...', media.title, file_name)
			log('debug', LOG_BIGLINE)
			return

		groups = m.groupdict()
		clip_number = file_studio = clip_name = None
		file_studio = groups['studio']
		if 'file_studio' in groups:
			file_studio = groups['file_studio']
		if 'clip_number' in groups:
			clip_number = groups['clip_number']
		clip_name = groups['clip_name']

		log('debug', 'search::%s | Studio - %s', media.title, file_studio)
		log('debug', 'search::%s | Clip Number - %s', media.title, clip_number)
		log('debug', 'search::%s | Clip Name - %s', media.title, clip_name)

		if file_studio is not None and AGENT_MATCH_VIDEO_NAME==True and file_studio.lower() != AGENT_NAME.lower():
			log('debug', 'search::%s | Skipping %s because does not match: %s', media.title, file_name, AGENT_NAME)
			return

		if clip_number is not None:
			url = URL["Video"] % clip_number
			title = self.fetch_title_search(url, media.title)
			log('info', 'search::%s | Clipnumber match [%s]', media.title, clip_number)
			log('info', 'search::%s |        Clip name [%s]', media.title, clip_name)
			log('info', 'search::%s |              URL [%s]', media.title, url)
			log('info', LOG_BIGLINE)
			results.Append(MetadataSearchResult(id = url, name = title, score = 98, lang = lang))
			return

		search_query_raw = list()
		for piece in clip_name.split(' '):
			search_query_raw.append(cgi.escape(piece))

		search_query="+".join(search_query_raw)
		log('debug', 'search::%s | Search query - %s', media.title, search_query)
		htmlElement=HTML.ElementFromURL(URL["Search"] % search_query, sleep=REQUEST_DELAY)
		search_results=htmlElement.xpath(SCRAPER_PATHS['Search'])
		log('debug', 'search::%s | Browsing results - %s', media.title, SCRAPER_PATHS['Search'])
		search_results_videos = []
		log('debug', 'search::%s | (%s) movies found', media.title, len(search_results))
		if len(search_results) > 0:
			for result in search_results:
				video_title = result.xpath(SCRAPER_PATHS['SearchVideoTitle'])[0].strip()
				log('debug', 'search::%s | Search results for "%s": - "%s"', media.title, clip_name, video_title)
				video_title = video_title.replace(AGENT_NAME, "").replace(AGENT_NAME.replace(" ",""),"")
				log('debug', 'search::%s | Trimmed result "%s"', media.title, video_title)
				url = result.xpath(SCRAPER_PATHS['SearchVideoUrl'])[0]
				if url.startswith("/url?"):
					log('debug', 'search::%s | Parsing URL"', media.title)
					video_url = urlparse.parse_qs(urlparse.urlparse(url).query)['url'][0]
					log('debug', 'search::%s | Parsed URL %s', media.title, video_url)
				elif url.startswith("http"):
					video_url = url
				else:
					video_url = URL["Base"] % url
				log('debug', 'search::%s | Video url - %s', media.title, video_url)
				video_title = self.fetch_title_search(video_url, media.title)
				if video_title.strip().lower() == clip_name.strip().lower():
					log('info', 'search::%s |     MATCH: TITLE [%s]', media.title, clip_name)
					log('info', 'search::%s |            Title [%s]', media.title, video_title)
					log('info', 'search::%s |              URL [%s]', media.title, video_url)
					results.Append(MetadataSearchResult(id = video_url, name = video_title, score = 90, lang = lang))
					log('info', LOG_BIGLINE)
					return
				else:
					search_results_videos.append({"title": video_title, "url": video_url})
					log('info', 'search::%s |   Match: CLOSEST [%s]', media.title, clip_name)
					log('info', 'search::%s |            Title [%s]', media.title, video_title)
					log('info', 'search::%s |              URL [%s]', media.title, video_url)
			log('info', 'search::%s | Returning closest match for "%s" - [site''s title: "%s", url: "%s"]', media.title, clip_name, search_results_videos[0]['title'],  search_results_videos[0]['url'])
			results.Append(MetadataSearchResult(id = search_results_videos[0]['url'], name = search_results_videos[0]['title'], score = 80, lang = lang))
			log('info', LOG_BIGLINE)
			return
		else:
			log('info', 'search::%s | No results for clip: %s', media.title, clip_name)
			log('info', LOG_BIGLINE)
			return

	def fetch_title_search(self, url, id):
		log('debug', 'fetch_title_search::init::%s', id)
		htmlElement=HTML.ElementFromURL(url, sleep=REQUEST_DELAY)
		name=self.fetch_title(htmlElement, id)
		log('debug', 'fetch_title_search::%s | Video Title for search : %s', id, name)
		return name

	def fetch_title(self, html, id):
		if not SCRAPER_PATHS['VideoTitle']:
			return
		log('debug', 'fecth_title::%s init', id)
		title = [0, 1]
		log('debug', 'fetch_title::%s | Video_title search: "%s"', id, SCRAPER_PATHS['VideoTitle'])
		xpathTitle=html.xpath(SCRAPER_PATHS['VideoTitle'])
		if len(xpathTitle) > 0:
			title[0] = xpathTitle[0]
			log('debug', 'fetch_title::%s | Video_title found: "%s"', id, title[0])
		else:
			title[0] = "TITLE_NOT_FOUND"
			log('debug', 'fetch_title::%s | No title found', id)
		return title[0]

	def fetch_title_meta(self, html, metadata):
		metadata.title = self.fetch_title(html, metadata.id)

	def fetch_date(self, html, metadata):
		if not SCRAPER_PATHS['ReleaseDate']:
			return
		log('debug', 'fetch_date::init::%s', metadata.id)
		xpath = html.xpath(SCRAPER_PATHS['ReleaseDate'])
		log('debug', 'fetch_date::init::%s - XPATH result', xpath)
		if xpath:
			if isinstance(xpath, list):
				release_date=xpath[0].strip()
			else:
				release_date=xpath.strip()
			if (release_date):
				release_date = html.xpath(SCRAPER_PATHS['ReleaseDate'])[0].replace("Published on","").strip()
				log('debug', 'fetch_date::%s | %s', metadata.id, release_date)
				date_original = Datetime.ParseDate(release_date).date()
				metadata.originally_available_at = date_original
				metadata.year = metadata.originally_available_at.year
			else:
				log('debug', 'fetch_date::%s | No Date to fetch for this studio')

	def fetch_summary(self, html, metadata):
		if not SCRAPER_PATHS['VideoSummary']:
			return
		log('debug', 'fetch_summary::init::%s', metadata.id)
		try:
			xpath = html.xpath(SCRAPER_PATHS['VideoSummary'])
			if isinstance(xpath, list):
				video_summary=xpath[0].strip()
			else:
				video_summary=xpath.strip()
			
			log('debug', 'fetch_summary::%s | Fetched summary %s', metadata.id, video_summary)
			metadata.summary = video_summary
		except Exception as e:
			log('error', LOG_STARLINE)
			log('error', 'Error in fetch_summary::%s || %s', metadata.id, e)
			log('error', LOG_STARLINE)
			pass

	def fetch_cast(self, html, metadata):
		if not SCRAPER_PATHS['CastMembers']:
			return
		log('debug', 'fetch_cast::init::%s', metadata.id)
		try:
			video_cast=html.xpath(SCRAPER_PATHS['CastMembers'])
			log('debug', 'fetch_cast::%s | %s Cast members found', metadata.id, len(video_cast))
			metadata.roles.clear()
			for cast in video_cast:
				log('debug', 'fetch_cast::%s | xpath result name %s', metadata.id, cast.xpath(SCRAPER_PATHS['CastName']))
				cname = cast.xpath(SCRAPER_PATHS['CastName'])[0].strip(', ')
				log('debug', 'fetch_cast::%s | Cast Member %s', metadata.id, cname)
				log('debug', 'fetch_cast::%s | xpath result url %s', metadata.id, cast.xpath(SCRAPER_PATHS['CastUrl']))
				
				# Extracting cast members photo
				castUrlPath = cast.xpath(SCRAPER_PATHS['CastUrl'])
				if len(castUrlPath) > 0:
					castUrl = castUrlPath[0].strip()
					castUrl = castUrl = URL["Base"] % castUrl if castUrl.startswith("/") else castUrl
					log('debug', 'fetch_cast::%s | Cash Url %s', metadata.id, castUrl)
					castHtml = HTML.ElementFromURL(castUrl, sleep=REQUEST_DELAY)
					castPhotos = castHtml.xpath(SCRAPER_PATHS['CastPhoto'])
					log('debug', 'fetch_cast::%s | xpath result cast photos %s', metadata.id, castPhotos)
					if len(castPhotos) > 0 :
						castPhoto = castHtml.xpath(SCRAPER_PATHS['CastPhoto'])[0].strip()
						castPhoto = castPhoto = URL["Base"] % castPhoto if castPhoto.startswith("/") else castPhoto
						log('debug', 'fetch_cast::%s | Cash Photo %s', metadata.id, castPhoto)
						if (len(cname) > 0):
							role = metadata.roles.new()
							role.name = cname
							role.photo = castPhoto
		except Exception as e:
			log('error', LOG_STARLINE)
			log('error', 'Error in fetch_cast::%s || %s', metadata.id, e)
			log('error', LOG_STARLINE)
			pass

	def fetch_genres(self, html, metadata):
		if not SCRAPER_PATHS['Genres']:
			return
		log('debug', 'fetch_genres::init::%s', metadata.id)
		metadata.genres.clear()
		log('debug', 'fetch_genres::%s | xpath %s', metadata.id, SCRAPER_PATHS['Genres'])
		genres=html.xpath(SCRAPER_PATHS['Genres'])
		log('debug', 'fetch_cast::%s | Genres extracted %s', metadata.id, genres)
		for genre in genres:
			genre = genre.strip()
			if (len(genre) > 0):
				metadata.genres.add(genre)

	def fetch_studio(self, html, metadata):
		log('debug', 'fetch_studio::init::%s', metadata.id)
		metadata.studio = AGENT_NAME
		if SCRAPER_PATHS['Studio'].strip():
			log('debug', 'fetch_studio::%s | xpath %s', metadata.id, SCRAPER_PATHS['Studio'])
			xpath_result = html.xpath(SCRAPER_PATHS['Studio'])
			if len(xpath_result) > 0:
				studio=xpath_result[0].strip()
				metadata.studio = studio
				log('debug', 'fetch_studio::%s | Studio extracted - "%s"', metadata.id, studio)
				if STUDIO_MAP is not None:
					if studio.lower() in STUDIO_MAP:
						metadata.studio = STUDIO_MAP[studio.lower()]

		log('debug', 'fetch_studio::%s | Studio %s', metadata.id, metadata.studio)
		if not metadata.studio in metadata.collections:
			log('debug', 'fetch_studio::%s | Adding to collection %s', metadata.id, metadata.studio)
			metadata.collections.add(metadata.studio)
		return
		
	def fetch_images(self, html, metadata):
		log('debug', 'fetch_images::init::%s', metadata.id)
		i = 0
		try:
			coverPrefs = int(Prefs['cover'])
		except ValueError:
			# an absurdly high number means "download all the things"
			coverPrefs = 10000
		imageType = 'Poster & Art'
		try:
			log('debug', LOG_SUBLINE)
			htmlimages = []
			posterIndex = -1
			if SCRAPER_PATHS['Poster']:
				log('debug', 'fetch_images::%s | poster xpath - %s', metadata.id, SCRAPER_PATHS['Poster'])
				fetched_posters = html.xpath(SCRAPER_PATHS['Poster'])
				if len(fetched_posters) > 0:
					log('debug', 'fetch_images::%s | poster found - %s', metadata.id, fetched_posters[0])
					htmlimages.append(fetched_posters[0])
					posterIndex = 0
			if SCRAPER_PATHS['Art']:
				log('debug', 'fetch_images::%s | art xpath - %s', metadata.id, SCRAPER_PATHS['Art'])
				htmlimages = htmlimages + html.xpath(SCRAPER_PATHS['Art'])
			log('debug', 'fetch_images::%s | (%s) images found - %s', metadata.id, len(htmlimages), htmlimages)
			if posterIndex == -1:
				posterIndex = len(htmlimages) // 2
				if posterIndex < len(htmlimages):
					posterIndex = posterIndex + 1
				log('debug', 'fetch_images::%s | poster index to be used - %s', metadata.id, posterIndex)
			log('debug', 'fetch_images::%s | current posters - %s', metadata.id, len(metadata.posters))
			log('debug', 'fetch_images::%s | current arts - %s', metadata.id, len(metadata.art))
			referrer = URL["AddReferrer"]
			for index, image in enumerate(htmlimages):
				if image.startswith("/") :
					image = URL['Base'] % image
				if index < 4 or index == posterIndex :
					image = image.replace('.webp', '.jpg')      # change extension of url image
					whRatio = 1.5 if index == 0 else 0.5625
					imageType = 'Poster' if (index == 0 or index == posterIndex) else 'Art'
					pic, picContent = utils.getFilmImages(imageType, image, whRatio)    # height is 1.5 times the width for posters					
				if (index == 0 or posterIndex == index):      # processing posters
					#  clean up and only keep the posters we have added
					log('debug', 'fetch_images::%s | Adding poster - %s', metadata.id, image)
					if referrer == True:
						metadata.posters[pic] = Proxy.Media(picContent, sort_order=index + 1)
					else:
						metadata.posters[pic] = Proxy.Preview(picContent, sort_order=index + 1)
				if index < 4 or len(metadata.art) < 4: # processing art
					log('debug', 'fetch_images::%s | Adding art - %s', metadata.id, pic)
					if referrer == True:
						metadata.art[pic] = Proxy.Media(picContent, sort_order=index)
					else:
						metadata.art[pic] = Proxy.Preview(picContent, sort_order=index)
			log('debug', 'fetch_images::%s | posters after - %s', metadata.id, len(metadata.posters))
			log('debug', 'fetch_images::%s | arts after - %s', metadata.id, len(metadata.art))
		except Exception as e:
			log('error', LOG_STARLINE)
			log('error', 'Error in fetch_images::%s || %s', metadata.id, e)
			log('error', LOG_STARLINE)


	def update(self, metadata, media, lang):
		log('info', LOG_BIGLINE)
		log('info', '%s> update::init:%s', LOG_SUBLINE, metadata.id)
		log('info', LOG_BIGLINE)

		if metadata.tagline:
			log('debug', 'update::%s | Contains tagline, url set to - %s', metadata.id, metadata.tagline)
			url = metadata.tagline
			metadata.id = metadata.tagline
		else:
			log('debug', 'update::%s | No tagline set for this metadata (%s)', metadata.id, metadata.tagline)
			# Set tagline to URL
			url = metadata.id
			metadata.tagline = url

		enclosing_directory, file_name = os.path.split(os.path.splitext(media.items[0].parts[0].file)[0])
		file_name = file_name.lower()
		log('debug', 'update::%s | File Name - %s', metadata.id, file_name)
		if not media.items[0].parts[0].file:
			return

		file_path = media.items[0].parts[0].file
		log('debug', 'update::%s | File Path - %s', metadata.id, file_path)
		log('debug', 'update::%s | Fetching HTML from %s', metadata.id, url)
		# Fetch HTML
		log('debug', 'update::%s | Fetching HTML from %s', metadata.id, url)
		html = HTML.ElementFromURL(url)
		log('debug', 'update::%s | HTML fecthed', metadata.id)
		
		# Set additional metadata
		metadata.content_rating = 'X'
		try:
			self.fetch_studio(html, metadata)
		except Exception as e:
			log('error', LOG_STARLINE)
			log('error', 'update::exception::%s | Error in fetch_studio:: %s', metadata.id, e)
			log('error', LOG_STARLINE)
			pass

		# Try to get the title
		try:
			self.fetch_title_meta(html, metadata)
		except Exception as e:
			log('error', LOG_STARLINE)
			log('error', 'update::exception::%s | Error in fetch_title::fetch_title %s', metadata.id, e)
			log('error', LOG_STARLINE)
			pass


		# Try to get the release date
		try:
			self.fetch_date(html, metadata)
		except Exception as e:
			log('error', LOG_STARLINE)
			log('error', 'update::exception::%s | Error in fetch_date:: %s', metadata.id, e)
			log('error', LOG_STARLINE)
			pass

		# Try to get the summary
		try:
			self.fetch_summary(html, metadata)
		except Exception as e:
			log('error', LOG_STARLINE)
			log('error', 'update::exception::%s | Error in fetch_summary:: %s', metadata.id, e)
			log('error', LOG_STARLINE)
			pass

		# Try to get the cast
		try:
			self.fetch_cast(html, metadata)
		except Exception as e:
			log('error', LOG_STARLINE)
			log('error', 'update::exception::%s | Error in fetch_cast:: %s', metadata.id, e)
			log('error', LOG_STARLINE)
			pass
			
		# Try to get the genres
		try:
			self.fetch_genres(html, metadata)
		except Exception as e:
			log('error', LOG_STARLINE)
			log('error', 'update::exception::%s | Exception in fetch_genres:: %s', metadata.id, e)
			log('error', LOG_STARLINE)
			pass

		# Try to get the video images
		try:
			self.fetch_images(html, metadata)
		except Exception as e:
			log('error', LOG_STARLINE)
			log('error', 'UPDATE - Exception in fetch_images:: %s', metadata.id)
			log('error', LOG_STARLINE)
			pass
		log('info', '%s> update::%s - Success :) :) :)', LOG_SUBLINE, metadata.id)
		log('info', LOG_BIGLINE)