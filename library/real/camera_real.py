"""
Copyright Harvey Mudd College
MIT License
Spring 2020

Contains the Camera module of the racecar_core library
"""

from camera import Camera

# General
import cv2 as cv
import numpy as np
from nptyping import NDArray

# ROS2
import rclpy as ros2
from rclpy.qos import (
    QoSDurabilityPolicy,
    QoSHistoryPolicy,
    QoSReliabilityPolicy,
    QoSProfile,
)
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError


class CameraReal(Camera):
    # The ROS topic from which we read camera data
    __COLOR_TOPIC = "/camera/color"
    __DEPTH_TOPIC = "/camera/depth"

    def __init__(self):
        self.__bridge = CvBridge()

        # ROS node
        self.node = ros2.create_node("image_sub")

        qos_profile = QoSProfile(depth=1)
        qos_profile.history = QoSHistoryPolicy.RMW_QOS_POLICY_HISTORY_KEEP_LAST
        qos_profile.reliability = (
            QoSReliabilityPolicy.RMW_QOS_POLICY_RELIABILITY_BEST_EFFORT
        )
        qos_profile.durability = QoSDurabilityPolicy.RMW_QOS_POLICY_DURABILITY_VOLATILE

        # subscribe to the color image topic, which will call
        # __color_callback every time the camera publishes data
        self.__color_image_sub = self.node.create_subscription(
            Image, self.__COLOR_TOPIC, self.__color_callback, qos_profile
        )
        self.__color_image = None
        self.__color_image_new = None

        # subscribe to the depth image topic, which will call
        # __depth_callback every time the camera publishes data
        self.__depth_image_sub = self.node.create_subscription(
            Image, self.__DEPTH_TOPIC, self.__depth_callback, qos_profile
        )
        self.__depth_image = None
        self.__depth_image_new = None

    def __color_callback(self, data):
        try:
            cv_color_image = self.__bridge.imgmsg_to_cv2(data, "bgr8")
        except CvBridgeError as e:
            print(e)

        self.__color_image_new = cv_color_image

    def __depth_callback(self, data):
        try:
            cv_depth_image = self.__bridge.imgmsg_to_cv2(data, "16UC1")
        except CvBridgeError as e:
            print(e)

        self.__depth_image_new = cv_depth_image

    def __update(self):
        self.__depth_image = self.__depth_image_new
        self.__color_image = self.__color_image_new

    def get_color_image_no_copy(self) -> NDArray[(480, 640, 3), np.uint8]:
        return self.__color_image

    def get_depth_image(self) -> NDArray[(480, 640), np.float32]:
        return self.__depth_image

    def get_color_image_async(self) -> NDArray[(480, 640, 3), np.uint8]:
        return self.__color_image_new

    def get_depth_image_async(self) -> NDArray[(480, 640), np.float32]:
        return self.__depth_image_new
