# Dataclass for API endpoints in Joule
from dataclasses import dataclass

@dataclass
class EndPoints:
    root = '/'

    db_connection = '/db/connection.json'
    db_info = '/dbinfo'
    
    version = '/version'
    version_json  = '/version.json'

    event = '/event.json'
    event_move = '/event/move.json'
    event_data = '/event/data.json'
    event_data_count = '/event/data/count.json'
    
    stream = '/stream.json'
    stream_move = '/stream/move.json'
    stream_annotations = '/stream/annotations.json'
    
    folder = '/folder.json'
    folders = '/folders.json'
    folder_move = '/folder/move.json'
    
    data = '/data'
    data_json = '/data.json'
    data_intervals = '/data/intervals.json'
    data_decimate = '/data/decimate.json'
    data_consolidate = '/data/consolidate.json'
    
    module = '/module.json'
    modules = '/modules.json'
    module_logs = '/module/logs.json'
    
    app_auth = '/app/auth'
    app_json = '/app.json'
    
    proxy = '/proxy.json'
    proxies = '/proxies.json'
    
    master = '/master.json'
    masters = '/masters.json'
    
    follower = '/follower.json'
    followers = '/followers.json'

    annotation = '/annotation.json'
    annotations = '/annotations.json'
    annotations_info = '/annotations/info.json'

@dataclass
class ConfigFiles:
    default_node='default_node.txt'
    nodes = 'nodes.json'

