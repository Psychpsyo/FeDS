import urllib
import requests
import json
import sys
import os
from pathlib import Path
import re
import copy

# Functions
def parseParams(params):
	match params[0].lower():
		case "-maxposts":
			try:
				config["maxPosts"] = int(params[1])
			except ValueError:
				sys.exit(locale["errors"]["mustBeWholeNumber"].replace("{{VALUE}}", params[0]))
			parseParams(params[2:])
		case "-maxdata":
			try:
				config["maxBytes"] = int(params[1])
			except ValueError:
				sys.exit(locale["errors"]["mustBeWholeNumber"].replace("{{VALUE}}", params[0]))
			parseParams(params[2:])
		case "-e926":
			config["useE926"] = True
			parseParams(params[1:])
		case "-search":
			config["defaultQuery"] = " ".join(sorted(params[1:]))
		case _:
			config["defaultQuery"] = " ".join(sorted(params))

def loadLocaleFile(language):
	with open("./locales/" + language + ".json", encoding="utf-8") as localeFile:
		newLocale = json.load(localeFile)
		for key in newLocale:
			locale[key] = newLocale[key]

def getPosts(before):
	queryParams = "limit=320"
	if len(config["defaultQuery"]) > 0:
		queryParams += "&tags=" + urllib.parse.quote(config["defaultQuery"])
	if before > 0:
		queryParams += "&page=b" + str(before)
	if config["e621Username"] != "" and config["e621ApiKey"] != "":
		queryParams += "&login=" + urllib.parse.quote(config["e621Username"])
		queryParams += "&api_key=" + urllib.parse.quote(config["e621ApiKey"])
	posts = requests.get(
		targetDomain + "/posts.json?" + queryParams,
		headers={
			"User-Agent": "Funky e621 Download Script! :D"
		}
	)
	return posts.json()["posts"]

def saveArchiveInfo():
	with open(targetFolder + ".info.json", "w") as archiveInfoFile:
		json.dump(archiveInfo, archiveInfoFile)

def formatDataAmount(bytes):
	unitStrings = ["bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB", "RB", "QB"]
	exponent = 0
	while bytes > 1000:
		bytes /= 1000
		exponent += 1
	return str(round(bytes, 2)) + unitStrings[exponent]




# Variables & Setup
# locale
locale = {}
loadLocaleFile("en")

# config
defaultConfig = {
	"language": "en",
	"adressUserAs": "Sir",
	"e621Username": "",
	"e621ApiKey": "",
	"defaultQuery": "",
	"downloadsFolder": "./downloads/",
	"useE926": False
}
config = copy.deepcopy(defaultConfig)
if Path("config.json").is_file():
	with open("config.json", "r", encoding="utf-8") as configFile:
		newConfig = json.load(configFile)
		for key in newConfig:
			config[key] = newConfig[key]

# console parameters
if len(sys.argv) > 1:
	parseParams(sys.argv[1:])

# create default config if it doesn't exist yet
if not Path("config.json").is_file():
	print(locale["configNotFound"])
	with open("config.json", "w", encoding="utf-8") as configFile:
		json.dump(defaultConfig, configFile, indent=4)

# check if query was provided
if config["defaultQuery"] == "":
	print(locale["help"].replace("{{E621}}", "e926" if config["useE926"] else "e621").replace("{{SEARCH}}", "python3 ./feds.py eevee blush" if config["useE926"] else "python3 ./feds.py eevee rating:safe"))
	sys.exit()

# get target folder
targetFolder = config["downloadsFolder"] + re.sub("[" + re.escape("/\:*?\"<>|") + "]", "_", config["defaultQuery"]) + "/"
if not Path(targetFolder).is_dir():
	print(locale["creatingDownloadFolder"].replace("{{FOLDER}}", targetFolder))
	Path(targetFolder).mkdir(parents=True, exist_ok=True)

archiveInfo = {
	"newestPost": 0,
	"oldestPost": 0
}
if Path(targetFolder + ".info.json").is_file():
	with open(targetFolder + ".info.json", "r", encoding="utf-8") as archiveInfoFile:
		archiveInfo = json.load(archiveInfoFile)

targetDomain = "https://" + ("e926" if config["useE926"] else "e621") + ".net"




# Actual Script
posts = getPosts(archiveInfo["oldestPost"])
stopAtPost = archiveInfo["newestPost"]
if archiveInfo["oldestPost"] > 0:
	print(locale["continuingDownload"].replace("{{POST}}", str(posts[0]["id"])))
	if archiveInfo["newestPost"] > archiveInfo["oldestPost"]:
		stopAtPost = 0
else:
	# Picking up from the newest post overall
	archiveInfo["newestPost"] = posts[0]["id"]

postsDownloaded = 0
bytesDownloaded = 0
longestPostId = 0
reachedEnd = False
try:
	while not reachedEnd:
		if len(posts) == 0:
			if stopAtPost == 0:
				archiveInfo["oldestPost"] = 0
				stopAtPost = archiveInfo["newestPost"]
			else:
				reachedEnd = True
		for post in posts:
			archiveInfo["oldestPost"] = post["id"]
			if archiveInfo["oldestPost"] <= stopAtPost:
				# Ran into the old newestPost
				reachedEnd = True
				break
			if post["file"]["url"] == None:
				print(locale["imageUrlNull"].replace("{{POST}}", str(post["id"])))
			else:
				fileSize = os.stat(urllib.request.urlretrieve(post["file"]["url"], targetFolder + str(post["id"]) + ".png")[0]).st_size
				longestPostId = max(longestPostId, len(str(post["id"])))
				print(locale["downloaded"].replace("{{POST}}", str(post["id"]).rjust(longestPostId, " ")).replace("{{URL}}", post["file"]["url"].ljust(73, " ")).replace("{{SIZE}}", formatDataAmount(fileSize).rjust(10, " ")))
				postsDownloaded += 1
				bytesDownloaded += fileSize
			saveArchiveInfo()
			
			if ("maxPosts" in config and postsDownloaded >= config["maxPosts"]) or ("maxBytes" in config and bytesDownloaded >= config["maxBytes"]):
				reachedEnd = True
				break
		
		if not reachedEnd:
			posts = getPosts(archiveInfo["oldestPost"])
	
	print(locale["finished"].replace("{{COUNT}}", str(postsDownloaded)).replace("{{USER}}", config["adressUserAs"]).replace("{{DATA}}", formatDataAmount(bytesDownloaded)))
except KeyboardInterrupt:
	print(locale["downloadInterrupted"].replace("{{COUNT}}", str(postsDownloaded)).replace("{{DATA}}", formatDataAmount(bytesDownloaded)))