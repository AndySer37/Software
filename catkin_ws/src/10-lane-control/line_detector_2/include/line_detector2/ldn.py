import numpy as np
import cv2

from anti_instagram.AntiInstagram import AntiInstagram
from cv_bridge import CvBridge
from duckietown_msgs.msg import (Segment, SegmentList)
from duckietown_utils.instantiate_utils import instantiate
from duckietown_utils.jpg import image_cv_from_jpg
from duckietown_utils.text_utils import indent
from easier_node.easy_node import EasyNode 
from line_detector.line_detector_plot import drawLines, color_segment


class LineDetectorNode2(EasyNode):
    def __init__(self):
        EasyNode.__init__(self, 'line_detector2', 'line_detector_node2')
        
        self.detector = None 
        self.bridge = CvBridge()
        self.ai = AntiInstagram()
        self.active = True

        # Only be verbose every 10 cycles
        self.intermittent_interval = 100
        self.intermittent_counter = 0

    def on_parameters_changed(self, _first_time, updated):
        if 'verbose' in updated:
            self.info('Verbose is now %r' % self.config.verbose)

        if 'detector' in updated:
            c = self.config.detector
            self.info('detector config: %s' % str(c))
            assert isinstance(c, list) and len(c) == 2, c
 
            self.detector = instantiate(c[0], c[1])

    def on_received_switch(self, context, switch_msg):  # @UnusedVariable
        self.active = switch_msg.data
 
    def on_received_transform(self, context, transform_msg):  # @UnusedVariable
        self.ai.shift = transform_msg.s[0:3]
        self.ai.scale = transform_msg.s[3:6]

        self.info("AntiInstagram transform received")
 
    def on_received_image(self, context, image_msg):
        if not self.active:
            return 

        self.intermittent_counter += 1

        with context.phase('decoding'):
            # Decode from compressed image with OpenCV
            try:
                image_cv = image_cv_from_jpg(image_msg.data)
            except ValueError as e:
                self.loginfo('Could not decode image: %s' % e)
                return
 

        with context.phase('resizing'):
            # Resize and crop image
            hei_original, wid_original = image_cv.shape[0:2]
    
            if  self.config.img_size[0] != hei_original or  self.config.img_size[1] != wid_original:
                # image_cv = cv2.GaussianBlur(image_cv, (5,5), 2)
                image_cv = cv2.resize(image_cv, (self.config.img_size[1],  self.config.img_size[0]),
                                       interpolation=cv2.INTER_NEAREST)
            image_cv = image_cv[self.config.top_cutoff:,:,:]
 

        with context.phase('correcting'):
            # apply color correction: AntiInstagram
            image_cv_corr = self.ai.applyTransform(image_cv)
            image_cv_corr = cv2.convertScaleAbs(image_cv_corr)
 
        with context.phase('detection'):
            # Set the image to be detected
            self.detector.setImage(image_cv_corr)
    
            # Detect lines and normals    
            white = self.detector.detectLines('white')
            yellow = self.detector.detectLines('yellow')
            red = self.detector.detectLines('red')
 

        with context.phase('preparing-images'):
            # SegmentList constructor
            segmentList = SegmentList()
            segmentList.header.stamp = image_msg.header.stamp
    
            # Convert to normalized pixel coordinates, and add segments to segmentList
            arr_cutoff = np.array((0, self.config.top_cutoff, 0, self.config.top_cutoff))
            arr_ratio = np.array((1./ self.config.img_size[1], 1./ self.config.img_size[0], 1./ self.config.img_size[1], 1./ self.config.img_size[0]))
            if len(white.lines) > 0:
                lines_normalized_white = ((white.lines + arr_cutoff) * arr_ratio)
                segmentList.segments.extend(toSegmentMsg(lines_normalized_white, white.normals, Segment.WHITE))
            if len(yellow.lines) > 0:
                lines_normalized_yellow = ((yellow.lines + arr_cutoff) * arr_ratio)
                segmentList.segments.extend(toSegmentMsg(lines_normalized_yellow, yellow.normals, Segment.YELLOW))
            if len(red.lines) > 0:
                lines_normalized_red = ((red.lines + arr_cutoff) * arr_ratio)
                segmentList.segments.extend(toSegmentMsg(lines_normalized_red, red.normals, Segment.RED))
    
            self.intermittent_log('# segments: white %3d yellow %3d red %3d' % (len(white.lines),
                    len(yellow.lines), len(red.lines)))
 

        # Publish segmentList
        with context.phase('publishing'):
            self.publishers.segment_list.publish(segmentList) 

        # VISUALIZATION only below

        if self.config.verbose:

            with context.phase('draw-lines'):
                # Draw lines and normals
                image_with_lines = np.copy(image_cv_corr)
                drawLines(image_with_lines, white.lines, (0, 0, 0))
                drawLines(image_with_lines, yellow.lines, (255, 0, 0))
                drawLines(image_with_lines, red.lines, (0, 255, 0))
 
            with context.phase('published-images'):
                # Publish the frame with lines
                image_msg_out = self.bridge.cv2_to_imgmsg(image_with_lines, "bgr8")
                image_msg_out.header.stamp = image_msg.header.stamp
                self.publishers.image_with_lines.publish(image_msg_out) 

            with context.phase('pub_edge/pub_segment'):
                colorSegment = color_segment(white.area, red.area, yellow.area)
                edge_msg_out = self.bridge.cv2_to_imgmsg(self.detector.edges, "mono8")
                colorSegment_msg_out = self.bridge.cv2_to_imgmsg(colorSegment, "bgr8")
                self.publishers.edge.publish(edge_msg_out)
                self.publishers.color_segment.publish(colorSegment_msg_out)

        
        if self.intermittent_log_now():
            self.info('stats from easy_node\n' + indent(context.get_stats(), '> '))
    
    def intermittent_log_now(self):
        return self.intermittent_counter % self.intermittent_interval == 1
    def intermittent_log(self, s):
        if not self.intermittent_log_now():
            return
        self.info('%3d:%s' % (self.intermittent_counter, s))



def toSegmentMsg(lines, normals, color):
    segmentMsgList = []
    for x1,y1,x2,y2,norm_x,norm_y in np.hstack((lines,normals)):
        segment = Segment()
        segment.color = color
        segment.pixels_normalized[0].x = x1
        segment.pixels_normalized[0].y = y1
        segment.pixels_normalized[1].x = x2
        segment.pixels_normalized[1].y = y2
        segment.normal.x = norm_x
        segment.normal.y = norm_y
        segmentMsgList.append(segment)
    return segmentMsgList

