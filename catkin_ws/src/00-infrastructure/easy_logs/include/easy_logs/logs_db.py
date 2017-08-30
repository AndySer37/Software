from collections import OrderedDict
from contracts.utils import check_isinstance
import os
import re

from duckietown_utils import logger
from duckietown_utils.bag_info import rosbag_info_cached
from duckietown_utils.caching import get_cached
from duckietown_utils.dates import format_time_as_YYYY_MM_DD
from duckietown_utils.friendly_path_imp import friendly_path
from duckietown_utils.fuzzy import fuzzy_match, filters0
from duckietown_utils.path_utils import get_ros_package_path
from duckietown_utils.yaml_wrap import look_everywhere_for_bag_files, yaml_load_file,\
    yaml_write_to_file
from easy_logs.logs_structure import PhysicalLog
from easy_logs.time_slice import filters_slice
from duckietown_utils.constants import get_duckietown_root
import copy


def get_urls_path():
    d = get_ros_package_path('easy_logs')
    f = os.path.join(d, 'dropbox.urls.yaml')
    return f

def get_easy_logs_db():
    return get_easy_logs_db_cached_if_possible()

def get_easy_logs_db_cached_if_possible():
    if EasyLogsDB._singleton is None:
        f = EasyLogsDB
#         use_cache = DuckietownConstants.use_cache_for_logs
        EasyLogsDB._singleton = get_cached('EasyLogsDB', f) #if use_cache else f()
        
        fn = os.path.join(get_duckietown_root(),'caches','candidate_cloud.yaml')
        
        if not os.path.exists(fn):
            logs = copy.deepcopy(EasyLogsDB._singleton.logs)
            # remove the field "filename"
            for k, v in logs.items():
                logs[k]=v._replace(filename=None)
            yaml_write_to_file(logs, fn)

    return EasyLogsDB._singleton

def get_easy_logs_db_fresh():
    if EasyLogsDB._singleton is None:
        f = EasyLogsDB
        EasyLogsDB._singleton = f()
    return EasyLogsDB._singleton

def get_easy_logs_db_cloud():
    cloud_file = os.path.join(get_ros_package_path('easy_logs'), 'cloud.yaml')
    if not os.path.exists(cloud_file):
        url = "https://www.dropbox.com/s/vdl1ej8fihggide/duckietown-cloud.yaml?dl=1"
        from easy_logs.cli.require import download_url_to_file
        download_url_to_file(url, cloud_file)
    
    logger.info('Loading cloud DB %s' % friendly_path(cloud_file))
    
    logs = yaml_load_file(cloud_file)
    
    logs = OrderedDict(logs)
    logger.info('Loaded cloud DB with %d entries.' % len(logs))
    
    return EasyLogsDB(logs)
    

class EasyLogsDB():
    _singleton = None

    def __init__(self, logs=None):
        # ordereddict str -> PhysicalLog
        if logs is None:
            logs  = load_all_logs()
        else:
            check_isinstance(logs, OrderedDict)
        self.logs = logs
         
    def query(self, query, raise_if_no_matches=True):
        """
            query: a string

            Returns an OrderedDict str -> PhysicalLog.
        """
        check_isinstance(query, str)
        filters = OrderedDict()
        filters.update(filters_slice)
        filters.update(filters0)
        result = fuzzy_match(query, self.logs, filters=filters,
                             raise_if_no_matches=raise_if_no_matches)
        return result

def read_stats(pl):
    assert isinstance(pl, PhysicalLog)

    info = rosbag_info_cached(pl.filename)
    if info is None:
        return pl._replace(valid=False, error_if_invalid='Not indexed')

    # print yaml.dump(info)
    length = info['duration']
    if length is None:
        return pl._replace(valid=False, error_if_invalid='Empty bag.')

    date_ms = info['start']
    if date_ms < 156600713:
        return pl._replace(valid=False, error_if_invalid='Date not set.')

    date = format_time_as_YYYY_MM_DD(date_ms)

    pl = pl._replace(date=date, length=length, t0=0, t1=length, bag_info=info)

    try:
        vehicle = which_robot(info)
        pl =pl._replace(vehicle=vehicle, has_camera=True)
    except ValueError:
        vehicle = None
        pl = pl._replace(valid=False, error_if_invalid='No camera data.')

#     camera_topic = '/%s/camera_node/image/compressed' % vehicle
#
#     found = False
#     for _ in info['topics']:
#         if _['topic'] == camera_topic:
#             found = True
#
#     if not found:
#

    return pl

def which_robot(info):
    pattern  = r'/(\w+)/camera_node/image/compressed'
    for topic in info['topics']:
        m = re.match(pattern, topic['topic'])
        if m:
            vehicle = m.group(1)
            return vehicle
    msg = 'Could not find a topic matching %s' % pattern
    raise ValueError(msg)

def is_valid_name(basename):
    forbidden = [',','(','conflicted', ' ']
    for f in forbidden:
        if f in basename:
            return False
    return True
        
def load_all_logs(which='*'):
    pattern = which + '.bag'
    basename2filename = look_everywhere_for_bag_files(pattern=pattern)
    logs = OrderedDict()
    for basename, filename in basename2filename.items():
        log_name = basename
       
        if not is_valid_name(basename):
            msg = 'Ignoring Bag file with invalid file name "%r".' % (basename)
            msg += '\n Full path: %s' % filename
            logger.warn(msg)
            continue

        date = None
        size =  os.stat(filename).st_size

        l = PhysicalLog(log_name=log_name,
                        map_name=None,
                        description=None,
                        length=None,
                        t0=None,t1=None,
                        date=date,
                        size=size,
                        has_camera=None,
                        vehicle = None,
                        filename=filename,
                        bag_info=None,
                        valid=True,
                        error_if_invalid=None)
        l = read_stats(l)
        logs[l.log_name]= l

    return logs
