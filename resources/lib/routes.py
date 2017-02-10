# -*- coding: utf-8 -*-
import utils
import requests
import json
from twitch.api import TwitchTV
from twitch.constants import Keys
from exception import managedTwitchExceptions, TwitchException
from converter import JsonListItemConverter, PlaylistConverter
from constants import PLUGIN, LINE_LENGTH, LIVE_PREVIEW_IMAGE, Images
from xbmc import Keyboard

TWITCHTV = TwitchTV(PLUGIN.log)
CONVERTER = JsonListItemConverter(PLUGIN, LINE_LENGTH)
PLAYLIST_CONVERTER = PlaylistConverter()

@PLUGIN.route('/')
def createMainListing():
    context_menu = []
    context_menu.extend(utils.contextClearPreviews())
    items = [
        {'label': PLUGIN.get_string(30008),
         'icon': Images.ICON,
         'thumbnail': Images.THUMB,
         'art': utils.theArt(),
         'context_menu': context_menu,
         'path': PLUGIN.url_for(endpoint='createListOfChannels', index='0')
        },
        {'label': PLUGIN.get_string(30004),
         'icon': Images.ICON,
         'thumbnail': Images.THUMB,
         'art': utils.theArt(),
         'context_menu': context_menu,
         'path': PLUGIN.url_for(endpoint='showSettings')
         }
    ]
    PLUGIN.set_content(utils.getContentType())
    return items

def log(msg):
    f = open("/home/nalle/.kodi/temp/kodi.log", "a")
    f.write(str(msg))
    f.flush()
    f.close()

def getStreams(offset, limit):
    items = []
    url = "http://api.speedrunslive.com/frontend/streams?callback=getCustomStreamsList"
    streams = requests.get(url).content.replace("getCustomStreamsList(","").replace(");","")
    j = json.loads(streams)
    i = 0
    tmp = {}
    for stream in j['_source']['channels']:
        tmp.update({stream['user_name']: stream['current_viewers']})

    for streamer in sorted(tmp, key=tmp.get, reverse=True):
        if len(items) > limit:
            break
        if i < offset:
            i = i+1
            continue
        try:
            items.append(TWITCHTV.getStreamInfo(streamer))
        except Exception:
            pass
        i = i+1
    return items

@PLUGIN.route('/createListOfChannels/<index>/')
@managedTwitchExceptions
def createListOfChannels(index):
    index, offset, limit = utils.calculatePaginationValues(index)
    items = [CONVERTER.convertStreamToListItem(stream) for stream
             in getStreams(offset, limit)]

    items.append(utils.linkToNextPage('createListOfChannels', index))
    utils.refreshPreviews()
    PLUGIN.set_content(utils.getContentType())
    return items


@PLUGIN.route('/channelVideos/<name>/')
@managedTwitchExceptions
def channelVideos(name):
    items = [{'label': PLUGIN.get_string(30078), 'icon': Images.ICON, 'thumbnail': Images.THUMB, 'art': utils.theArt(),
              'path': PLUGIN.url_for(endpoint='channelVideosList', name=name, index=0, broadcast_type='archive')},
             {'label': PLUGIN.get_string(30113), 'icon': Images.ICON, 'thumbnail': Images.THUMB, 'art': utils.theArt(),
              'path': PLUGIN.url_for(endpoint='channelVideosList', name=name, index=0, broadcast_type='upload')},
             {'label': PLUGIN.get_string(30079), 'icon': Images.ICON, 'thumbnail': Images.THUMB, 'art': utils.theArt(),
              'path': PLUGIN.url_for(endpoint='channelVideosList', name=name, index=0, broadcast_type='highlight')}]
    PLUGIN.set_content(utils.getContentType())
    return items


@PLUGIN.route('/channelVideosList/<name>/<index>/<broadcast_type>/')
@managedTwitchExceptions
def channelVideosList(name, index, broadcast_type):
    index = int(index)
    offset = index * 8
    videos = TWITCHTV.getFollowerVideos(name, offset, broadcast_type)
    items = [CONVERTER.convertVideoListToListItem(video) for video in videos[Keys.VIDEOS]]
    if videos[Keys.TOTAL] > (offset + 8):
        items.append(utils.linkToNextPage('channelVideosList', index, name=name, broadcast_type=broadcast_type))
    PLUGIN.set_content(utils.getContentType())
    return items


@PLUGIN.route('/createListForSelectedVideo/')
@managedTwitchExceptions
def createListForSelectedVideo():
    def extractVideoID(url):
        _id = url  # http://twitch.tv/a/v/12345678?t=9m1s
        idx = _id.find('?')
        if idx >= 0:
            _id = _id[:idx]  # https://twitch.tv/a/v/12345678
        idx = _id.rfind('/')
        if idx >= 0:
            _id = _id[:idx] + _id[idx + 1:]  # https://twitch.tv/a/v12345678
        idx = _id.rfind('/')
        if idx >= 0:
            _id = _id[idx + 1:]  # v12345678
        return _id

    items = []
    keyboard = Keyboard('')
    keyboard.doModal()
    if keyboard.isConfirmed():
        _id = extractVideoID(keyboard.getText())
        if _id:
            video = TWITCHTV.getVideo(_id)
            items = [CONVERTER.convertVideoListToListItem(video)]
    return items


@PLUGIN.route('/playVideo/<_id>/<quality>/')
@managedTwitchExceptions
def playVideo(_id, quality):
    """
    :param _id: string: video id
    :param quality: string: qualities[quality]
    0 = Source, 1 = 1080p60, 2 = 1080p30, 3 = 720p60, 4 = 720p30, 5 = 540p30, 6 = 480p30, 7 = 360p30, 8 = 240p30, 9 = 144p30
    -1 = Choose quality dialog
    * any other value for quality will use addon setting
    """
    videoQuality = utils.getVideoQuality(quality)
    oauthtoken = utils.getOauthToken()
    if videoQuality != -1:
        # videoQuality == -1 if quality dialog was cancelled
        videoInfo = CONVERTER.getVideoInfo(TWITCHTV.getVideo(_id))
        simplePlaylist = TWITCHTV.getVideoPlaylist(_id, videoQuality, oauthtoken)
        playlistItems = PLAYLIST_CONVERTER.convertToXBMCPlaylist(simplePlaylist, videoInfo.get('title', ''),
                                                                 videoInfo.get('thumbnail', ''))
        if playlistItems != ():
            (playlist, listItem) = playlistItems
            utils.play(listItem.get('path', ''), listItem)
        else:
            raise TwitchException(TwitchException.NO_PLAYABLE)


@PLUGIN.route('/playVideo/<_id>/')
@managedTwitchExceptions
def oldplayVideo(_id):
    playVideo(_id, -2)


@PLUGIN.route('/search/')
@managedTwitchExceptions
def search():
    query = PLUGIN.keyboard('', PLUGIN.get_string(30007))
    if query:
        target = PLUGIN.url_for(endpoint='searchresults', query=query, index='0')
    else:
        target = PLUGIN.url_for(endpoint='createMainListing')
    PLUGIN.redirect(target)


@PLUGIN.route('/searchresults/<query>/<index>/')
@managedTwitchExceptions
def searchresults(query, index='0'):
    index, offset, limit = utils.calculatePaginationValues(index)
    streams = TWITCHTV.searchStreams(query, offset, limit)
    items = [CONVERTER.convertStreamToListItem(stream) for stream in streams]
    items.append(utils.linkToNextPage('searchresults', index, query=query))
    utils.refreshPreviews()
    PLUGIN.set_content(utils.getContentType())
    return items


@PLUGIN.route('/showSettings/')
def showSettings():
    PLUGIN.open_settings()


@PLUGIN.route('/playLive/<name>/<quality>/')
@managedTwitchExceptions
def playLive(name, quality):
    """
    :param name: string: stream/channel name
    :param quality: string: qualities[quality]
    0 = Source, 1 = 1080p60, 2 = 1080p30, 3 = 720p60, 4 = 720p30, 5 = 540p30, 6 = 480p30, 7 = 360p30, 8 = 240p30, 9 = 144p30
    -1 = Choose quality dialog
    * any other value for quality will use addon setting
    """
    videoQuality = utils.getVideoQuality(quality)
    if videoQuality != -1:
        # videoQuality == -1 if quality dialog was cancelled
        stream = CONVERTER.convertStreamToPlayItem(TWITCHTV.getStreamInfo(name))
        stream['path'] = TWITCHTV.getLiveStream(name, videoQuality)
        utils.play(stream['path'], stream)
        utils.execIrcPlugin(name)


@PLUGIN.route('/playLive/<name>/')
@managedTwitchExceptions
def oldplayLive(name):
    playLive(name, -2)


@PLUGIN.route('/createListOfTeams/<index>/')
@managedTwitchExceptions
def createListOfTeams(index):
    index = int(index)
    teams = TWITCHTV.getTeams(index)
    items = [CONVERTER.convertTeamToListItem(item) for item in teams]
    if len(teams) == 25:
        items.append(utils.linkToNextPage('createListOfTeams', index))
    PLUGIN.set_content(utils.getContentType())
    return items


@PLUGIN.route('/createListOfTeamStreams/<team>/')
@managedTwitchExceptions
def createListOfTeamStreams(team):
    PLUGIN.set_content(utils.getContentType())
    return [CONVERTER.convertTeamChannelToListItem(channel[Keys.CHANNEL])
            for channel in TWITCHTV.getTeamStreams(team)]


@PLUGIN.route('/clearLivePreviews/<notify>/')
def clearLivePreviews(notify):
    do_notify = True
    if notify.lower() == 'false':
        do_notify = False
    utils.TextureCacheCleaner().remove_like(LIVE_PREVIEW_IMAGE, do_notify)
