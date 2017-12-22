from collections import OrderedDict

import cv2

from anti_instagram import AntiInstagram
from duckietown_segmaps.draw_map_on_images import plot_map
from duckietown_segmaps.maps import FRAME_AXLE, FRAME_TILE,\
    plot_map_and_segments
from duckietown_segmaps.template_lane_straight import \
    TemplateStraightLane
from duckietown_segmaps.transformations import TransformationsInfo
import duckietown_utils as dtu
from duckietown_utils.coords import SE2_from_xyth
from easy_algo import get_easy_algo_db
from ground_projection import GroundProjection
from ground_projection.segment import rectify_segments
from lane_filter import FAMILY_LANE_FILTER
from line_detector.line_detector_interface import FAMILY_LINE_DETECTOR
from line_detector.visual_state_fancy_display import vs_fancy_display
from line_detector2.run_programmatically import FakeContext
import numpy as np

from .fuzzing import fuzzy_segment_list_image_space


@dtu.contract(gp=GroundProjection)
def run_pipeline(image, gp, line_detector_name, image_prep_name, lane_filter_name,
                 all_details=False):
    """ 
        Image: numpy (H,W,3) == BGR
        Returns a dictionary, res with the following fields:
            
            res['input_image']
    """
    
    res = OrderedDict()
    res['image_input'] = image
    algo_db = get_easy_algo_db()
    line_detector = algo_db.create_instance(FAMILY_LINE_DETECTOR, line_detector_name)
    lane_filter = algo_db.create_instance(FAMILY_LANE_FILTER, lane_filter_name)
    image_prep = algo_db.create_instance('image_prep', image_prep_name)

    context = FakeContext()
    
    if all_details:
        segment_list = image_prep.process(context, image, line_detector, transform = None)
     
        res['segments_on_image_input'] = vs_fancy_display(image_prep.image_cv, segment_list)    
        res['segments_on_image_resized'] = vs_fancy_display(image_prep.image_resized, segment_list)
    
    ai = AntiInstagram()
    ai.calculateTransform(image)
    
    transform = ai.applyTransform 
    
    transformed = transform(image)
    if all_details:
        res['image_input_transformed'] = transformed
        
    transformed_clipped = cv2.convertScaleAbs(transformed)
    
    if all_details:
        res['image_input_transformed_then_convertScaleAbs'] = transformed_clipped

    segment_list2 = image_prep.process(context, transformed_clipped, line_detector, transform=transform)
    
    if all_details:
        res['segments_on_image_input_transformed'] = \
            vs_fancy_display(image_prep.image_cv, segment_list2)
        
    res['segments_on_image_input_transformed_resized'] = \
        vs_fancy_display(image_prep.image_resized, segment_list2)

    grid = get_grid(image.shape[:2])
    
    if all_details:
        res['grid'] = grid

        res['grid_remapped'] = gp.rectify(grid)
        
    rectified = gp.rectify(res['image_input'])
    
    if all_details:
        res['image_input_rect'] = rectified
    
#     res['difference between the two'] = res['image_input']*0.5 + res['image_input_rect']*0.5
#     
    segment_list2 = fuzzy_segment_list_image_space(segment_list2, n=100, intensity=0.0015)
#     segment_list2 = fuzzy_color(segment_list2)
    
    segment_list2_rect = rectify_segments(gp, segment_list2)
    res['segments rectified on image rectified'] = \
        vs_fancy_display(rectified, segment_list2_rect)

    # Project to ground
    sg = gp.find_ground_coordinates(segment_list2_rect)
    
    lane_filter.initialize()
    if all_details:
        res['prior'] = lane_filter.get_plot_phi_d()
    
    lane_filter.update(sg.segments)

    res['belief'] = lane_filter.get_plot_phi_d()  
    
    lm = TemplateStraightLane()
    
    gpg = gp.gpc # XXX
    
    est = lane_filter.get_estimate()
    
    # Coordinates in TILE frame
    xytheta_tile = lm.xytheta_from_coords(est)

#     camera_xy = np.array([0, -lane_filter.lanewidth/2+est['d'], 0])
#     camera_theta = est['phi'] 
#     
    tinfo = TransformationsInfo()
    g = SE2_from_xyth(xytheta_tile)
    tinfo.add_transformation(frame1=FRAME_TILE, frame2=FRAME_AXLE, g=g) 
        
    sm_orig = lm.get_map()
    sm_axle = tinfo.transform_map_to_frame(sm_orig, FRAME_AXLE)
    
    res['world'] = plot_map_and_segments(sm_orig, tinfo, sg.segments, dpi=120)
    
    res['reprojected'] = plot_map(rectified, sm_axle, gpg)
    
    
    
    return res

def get_grid(shape, L=32, col={0: (255,0,0), 1: (0,255,0)}):
    """ Creates a grid of given shape """
    H, W = shape
    res = np.zeros((H, W, 3), 'uint8')
    for i in range(H):
        for j in range(W):
            cx = int(i / L) 
            cy = int(j / L)
            coli = (cx + cy) % 2
            res[i,j,:] = col[coli]
    return res

