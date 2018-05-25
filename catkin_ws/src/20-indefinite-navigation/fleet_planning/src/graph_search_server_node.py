#!/usr/bin/env python

import rospy, os, cv2
from fleet_planning.graph_search import GraphSearchProblem
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from fleet_planning.srv import *
from fleet_planning.generate_duckietown_map import graph_creator, MapImageCreator


class graph_search_server():
    def __init__(self):
        print 'Graph Search Service Started'

        # Input: csv file
        map_name = rospy.get_param('/map_name')
        map_dir = rospy.get_param('/map_dir')

        # build and init graphs
        gc = graph_creator()
        self.duckietown_graph = gc.build_graph_from_csv(map_dir=map_dir, csv_filename=map_name)
        self.duckietown_problem = GraphSearchProblem(self.duckietown_graph, None, None)
        self.apriltags_mapping = self.duckietown_graph.get_apriltags_mapping(map_dir=map_dir,csv_filename='autolab_tags_map')
        #apriltags_mapping[tagID] = node
        print "Graph loaded successfully!\n"

    def handle_graph_search(self, req):
        """takes request, calculates path and creates corresponding graph image. returns path"""
        # Checking if nodes exists
        source_node = apriltags_mapping.get(req.source_node)
        target_node = apriltags_mapping.get(req.target_node)
        print 'Tag ID source node: ' + repr(req.source_node) + ' ---> Graph source node: ' +repr(source_node)
        print 'Tag ID target node: ' + repr(req.target_node) + ' ---> Graph target node: ' +repr(target_node)
        if source_node == None or target_node == None:
            print "Source or target node do not exist."
            return GraphSearchResponse([])


        # Running A*
        self.duckietown_problem.start = source_node
        self.duckietown_problem.goal = target_node
        path = self.duckietown_problem.astar_search()
        return GraphSearchResponse(path.actions, path.path)

    def print_all_node_names_and_positions(self):
        for n in range(1,150):
            if n % 2 == 1:
                print 'Node: ' + repr(n)
                print self.duckietown_graph.get_node_pos(str(n))
                print 'Tag ID node: ' + repr(self.apriltags_mapping.get(n))
                print '-----------------'


if __name__ == "__main__":
    rospy.init_node('graph_search_server_node')
    gss = graph_search_server()
    print 'Starting server...\n'
    #debug
    gss.print_all_node_names_and_positions()
    s = rospy.Service('graph_search', GraphSearch, gss.handle_graph_search)
    rospy.spin()
