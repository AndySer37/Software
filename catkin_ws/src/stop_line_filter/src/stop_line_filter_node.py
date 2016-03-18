#!/usr/bin/env python
import rospy
import numpy as np
from duckietown_msgs.msg import SegmentList, Segment, BoolStamped, StopLineReading
from std_msgs.msg import Float32
import time

# Lane Filter Node
# Author: Liam Paull
# Inputs: SegmentList from line detector
# Outputs: LanePose - the d (lateral displacement) and phi (relative angle) of the car in the lane
# For more info on algorithm and parameters please refer to the google doc: https://drive.google.com/open?id=0B49dGT7ubfmSX1k5ZVN1dEU4M2M


class StopLineFilterNode(object):
    def __init__(self):
        self.node_name = "Stop Line Filter"

        self.stop_distance = self.setupParam("~stop_distance", 0.02) # distance from the stop line that we should stop 
        self.min_segs      = self.setupParam("~min_segs", 2) # minimum number of red segments that we should detect to estimate a stop
        self.sub = rospy.Subscriber("~segment_list", SegmentList, self.processSegments)
        # self.pub_stop_line_detect  = rospy.Publisher("~stop_line_detected", BoolStamped, queue_size=1)
        # self.pub_at_stop_line      = rospy.Publisher("~at_stop_line", BoolStamped, queue_size=1)
        # self.pub_stop_line_dist    = rospy.Publisher("~stop_line_dist", Float32, queue_size=1)
        self.pub_stop_line_reading = rospy.Publisher("~stop_line_reading", StopLineReading, queue_size=1)


    def setupParam(self,param_name,default_value):
        value = rospy.get_param(param_name,default_value)
        rospy.set_param(param_name,value) #Write to parameter server for transparancy
        rospy.loginfo("[%s] %s = %s " %(self.node_name,param_name,value))
        return value

    def processSegments(self,segment_list_msg):
        good_seg_count=0
        stop_line_distance_accumulator=0.0
        for segment in segment_list_msg.segments:
            if segment.color != segment.RED:
                continue
            if segment.points[0].x < 0 or segment.points[1].x < 0: # the point is behind us 
                continue

            p1 = np.array([segment.points[0].x, segment.points[0].y])
            p2 = np.array([segment.points[1].x, segment.points[1].y])
            dist1 = np.linalg.norm(p1)
            dist2 = np.linalg.norm(p2)
            avg_dist = 0.5*(dist1+dist2)
            stop_line_distance_accumulator += avg_dist
            good_seg_count += 1.0

        if (good_seg_count < self.min_segs):
            stop_line_reading_msg = StopLineReading()
            stop_line_reading_msg.header.stamp = segment_list_msg.header.stamp
            stop_line_reading_msg.stop_line_detected = False
            stop_line_reading_msg.at_stop_line = False
            stop_line_reading_msg.stop_line_dist = -1.0
            self.pub_stop_line_reading.publish(stop_line_reading_msg)
            return
        
        stop_line_reading_msg = StopLineReading()
        stop_line_reading_msg.header.stamp = segment_list_msg.header.stamp
        stop_line_reading_msg.stop_line_detected = True
        stop_line_reading_msg.stop_line_dist = stop_line_distance_accumulator/good_seg_count
        if stop_line_reading_msg.stop_line_dist < self.stop_distance:
            stop_line_reading_msg.at_stop_line = True
        else:
            stop_line_reading_msg.at_stop_line = False
        self.pub_stop_line_reading.publish(stop_line_reading_msg)    
    
    def onShutdown(self):
        rospy.loginfo("[StopLineFilterNode] Shutdown.")

if __name__ == '__main__': 
    rospy.init_node('lane_filter',anonymous=False)
    lane_filter_node = StopLineFilterNode()
    rospy.on_shutdown(lane_filter_node.onShutdown)
    rospy.spin()

