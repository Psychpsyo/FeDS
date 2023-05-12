import urllib
import requests
import json
import sys
import os
from pathlib import Path
import re
import copy

# Helper Functions
def downloadArchive(folder):
	archiveInfo = {
		"query": None,
		"newestPost": 0,
		"oldestPost": 0
	}
	try:
		with open(folder + ".info.json", "r", encoding="utf-8") as archiveInfoFile:
			newArchiveInfo = json.load(archiveInfoFile)
			for key in newArchiveInfo:
				archiveInfo[key] = newArchiveInfo[key]
	except:
		print(locale["noArchiveInfo"].replace("{{FOLDER}}", folder))
		return
	
	if archiveInfo["query"] == None:
		print(locale["archiveNoQuery"].replace("{{FOLDER}}", folder).replace("{{E621}}", "e926" if config["useE926"] else "e621"))
		return
	
	print(locale["startingDownload"].replace("{{FOLDER}}", folder).replace("{{QUERY}}", archiveInfo["query"]))
	
	posts = getPosts(archiveInfo["query"], archiveInfo["oldestPost"])
	stopAtPost = archiveInfo["newestPost"]
	if archiveInfo["oldestPost"] > 0:
		print(locale["continuingDownload"].replace("{{POST}}", str(archiveInfo["oldestPost"])))
		if archiveInfo["newestPost"] > archiveInfo["oldestPost"]:
			stopAtPost = 0
	elif len(posts) > 0:
		# Picking up from the newest post overall
		archiveInfo["newestPost"] = posts[0]["id"]
	
	postsDownloaded = 0
	bytesDownloaded = 0
	longestPostId = 0
	reachedEnd = False
	try:
		while not reachedEnd:
			if len(posts) == 0:
				if stopAtPost == 0 and archiveInfo["newestPost"] > 0:
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
					fileSize = os.stat(urllib.request.urlretrieve(post["file"]["url"], folder + str(post["id"]) + "." + post["file"]["ext"])[0]).st_size
					longestPostId = max(longestPostId, len(str(post["id"])))
					print(locale["downloaded"].replace("{{POST}}", str(post["id"]).rjust(longestPostId, " ")).replace("{{URL}}", post["file"]["url"].ljust(73, " ")).replace("{{SIZE}}", formatDataAmount(fileSize).rjust(10, " ")))
					postsDownloaded += 1
					bytesDownloaded += fileSize
				
				with open(folder + ".info.json", "w") as archiveInfoFile:
					json.dump(archiveInfo, archiveInfoFile)
				
				if ("maxPosts" in config and postsDownloaded >= config["maxPosts"]) or ("maxBytes" in config and bytesDownloaded >= config["maxBytes"]):
					reachedEnd = True
					break
			
			if not reachedEnd:
				posts = getPosts(archiveInfo["query"], archiveInfo["oldestPost"])
		
		print(locale["finished"].replace("{{COUNT}}", str(postsDownloaded)).replace("{{USER}}", config["adressUserAs"]).replace("{{DATA}}", formatDataAmount(bytesDownloaded)))
	except KeyboardInterrupt:
		print(locale["downloadInterrupted"].replace("{{COUNT}}", str(postsDownloaded)).replace("{{DATA}}", formatDataAmount(bytesDownloaded)))

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
		case "-update":
			# update all existing archives
			for file in os.listdir(config["downloadsFolder"]):
				file = config["downloadsFolder"] + file
				if Path(file).is_dir():
					downloadArchive(file + "/")
					print("\n")
			print(locale["updatedAll"].replace("{{USER}}", config["adressUserAs"]))
			sys.exit()
		case "-search":
			config["defaultQuery"] = " ".join(sorted(params[1:]))
		case _:
			config["defaultQuery"] = " ".join(sorted(params))

def loadLocaleFile(language):
	with open("./locales/" + language + ".json", encoding="utf-8") as localeFile:
		newLocale = json.load(localeFile)
		for key in newLocale:
			locale[key] = newLocale[key]

def getPosts(query, before):
	queryParams = "limit=320"
	if len(query) > 0:
		queryParams += "&tags=" + urllib.parse.quote(query)
	if before > 0:
		queryParams += "&page=b" + str(before)
	if config["e621Username"] != "" and config["e621ApiKey"] != "":
		queryParams += "&login=" + urllib.parse.quote(config["e621Username"])
		queryParams += "&api_key=" + urllib.parse.quote(config["e621ApiKey"])
	posts = requests.get(
		"https://" + ("e926" if config["useE926"] else "e621") + ".net/posts.json?" + queryParams,
		headers={
			"User-Agent": "Funky e621 Download Script! :D"
		}
	)
	return posts.json()["posts"]

def formatDataAmount(bytes):
	unitStrings = ["byte" if bytes == 1 else "bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB", "RB", "QB"]
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

# get/create target folder
targetFolder = config["downloadsFolder"] + re.sub("[" + re.escape("/\:*?\"<>|") + "]", "_", config["defaultQuery"]) + "/"
if not Path(targetFolder).is_dir():
	print(locale["creatingDownloadFolder"].replace("{{FOLDER}}", targetFolder))
	Path(targetFolder).mkdir(parents=True, exist_ok=True)

if not Path(targetFolder + ".info.json").is_file():
	with open(targetFolder + ".info.json", "w") as archiveInfoFile:
		json.dump({
			"query": config["defaultQuery"],
			"newestPost": 0,
			"oldestPost": 0
		}, archiveInfoFile)

# download
downloadArchive(targetFolder)