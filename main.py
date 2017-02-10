import requests
import json
	
class GetStreams():
	def __init__(self, url):
		self.streams = requests.get(url).content.replace("getCustomStreamsList(","").replace(");","")
		self.json = json.loads(self.streams)

if __name__ == '__main__':
	s = GetStreams("http://api.speedrunslive.com/frontend/streams?callback=getCustomStreamsList")
	print s.streams
