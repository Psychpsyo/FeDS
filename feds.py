import urllib
import requests
import json
import sys
from pathlib import Path
import re

# Variables & Setup
locale = None
with open("./locales/en.json", encoding="utf-8") as localeFile:
	locale = json.load(localeFile)

config = {
	"language": "en",
	"adressUserAs": "Sir",
	"e621Username": "",
	"e621ApiKey": "",
	"defaultQuery": "",
	"downloadsFolder": "./downloads/",
	"useE926": False
}
if Path("config.json").is_file():
	with open("config.json", "r", encoding="utf-8") as configFile:
		newConfig = json.load(configFile)
		for key in newConfig:
			config[key] = newConfig[key]
else:
	print(locale["configNotFound"])
	with open("config.json", "w", encoding="utf-8") as configFile:
		json.dump(config, configFile, indent=4)

with open("./locales/" + config["language"] + ".json", encoding="utf-8") as localeFile:
	newLocale = json.load(localeFile)
	for key in newLocale:
		locale[key] = newLocale[key]

searchQuery = config["defaultQuery"]
if len(sys.argv) > 1:
	searchQuery = " ".join(sorted(sys.argv[1:]))

if searchQuery == "":
	print(locale["help"].replace("{{E621}}", "e926" if config["useE926"] else "e621").replace("{{SEARCH}}", "python3 ./feds.py eevee blush" if config["useE926"] else "python3 ./feds.py eevee rating:safe"))
	sys.exit()

targetFolder = config["downloadsFolder"] + re.sub("[" + re.escape("/\:*?\"<>|") + "]", "_", searchQuery) + "/"
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

# Functions
def getPosts(before):
	queryParams = "limit=320"
	if len(searchQuery) > 0:
		queryParams += "&tags=" + urllib.parse.quote(searchQuery)
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

newPostCount = 0
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
				print(locale["downloading"].replace("{{POST}}", str(post["id"])).replace("{{URL}}", post["file"]["url"]))
				urllib.request.urlretrieve(post["file"]["url"], targetFolder + str(post["id"]) + ".png")
				newPostCount += 1
			saveArchiveInfo()
		
		if not reachedEnd:
			posts = getPosts(archiveInfo["oldestPost"])
	
	print(locale["finished"].replace("{{COUNT}}", str(newPostCount)).replace("{{USER}}", config["adressUserAs"]))
except KeyboardInterrupt:
	print(locale["downloadInterrupted"])