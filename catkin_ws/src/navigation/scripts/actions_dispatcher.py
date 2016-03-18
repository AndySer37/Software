#!/usr/bin/env python

import sys
import rospy
from navigation.srv import *
from navigation.msg import SourceTargetNodes
from duckietown_msgs.msg import FSMState
from std_msgs.msg import Int16

actions = []
pub = 0

def dispatcher(data):
    global actions
    global pub
    if data.state == data.COORDINATION and actions:
        action = actions.pop(0)
        print 'Dispatched:', action
        if action == 's':
            pub.publish(Int16(1))
        elif action == 'r':
            pub.publish(Int16(0))
        elif action == 'l':
            pub.publish(Int16(2))
        elif action == 'w':
            pub.publish(Int16(-1))    

def graph_search(data):
    global actions
    rospy.wait_for_service('graph_search')
    try:
        graph_search = rospy.ServiceProxy('graph_search', GraphSearch)
        resp = graph_search(data.source_node, data.target_node)
        actions = resp.actions
        if actions:
            # remove 'f' (follow line) from actions and add wait action in the end of queue
            actions = [x for x in actions if x != 'f']
            actions.append('w')
            print 'Actions to be executed:', actions
    except rospy.ServiceException, e:
        print "Service call failed: %s"%e

if __name__ == "__main__":
    rospy.init_node('action_dispatcher')
    rospy.Subscriber("~mode", FSMState, dispatcher)
    rospy.Subscriber("~plan_request", SourceTargetNodes, graph_search)
    pub = rospy.Publisher("~turn_type", Int16, queue_size=1)
    
    rospy.spin()
