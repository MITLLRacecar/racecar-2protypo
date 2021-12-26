"""
Copyright Harvey Mudd College
MIT License
Spring 2020

Contains the Racecar class, the top level of the racecar_core library
"""

# General
from datetime import datetime
import threading

# ROS
import rospy
from sensor_msgs.msg import LaserScan

# racecar_core modules
import camera
import controller
import display
import drive
import lidar
import physics


class Racecar:
    """
    The top level racecar module containing several submodules which interface
    with and control the different pieces of the RACECAR hardware
    """

    # Default number of seconds to wait between calls to update_slow
    __DEFAULT_UPDATE_SLOW_TIME = 1

    # Number of frames per second
    __FRAME_RATE = 60

    def __init__(self):
        # Modules
        self.camera = camera.Camera()
        self.controller = controller.Controller(self)
        self.display = display.Display()
        self.drive = drive.Drive()
        self.lidar = lidar.Lidar()
        self.physics = physics.Physics()

        # User provided start and update functions
        self.__user_start = None
        self.__user_update = None
        self.__user_update_slow = None

        # True if the main thread should be running
        self.__running = False

        # Variables relating to the run thread
        self.__run_thread = None
        self.__cur_update = self.__default_update
        self.__cur_update_slow = None
        self.__cur_frame_time = datetime.now()
        self.__last_frame_time = datetime.now()
        self.__cur_update_counter = 0
        self.__max_update_counter = 1
        self.set_update_slow_time(self.__DEFAULT_UPDATE_SLOW_TIME)

        # Start run_thread in default drive mode
        self.__handle_back()
        self.__run_thread = threading.Thread(target=self.__run)
        self.__run_thread.daemon = True
        self.__run_thread.start()

        # Print welcome message
        print(">> Racecar initialization successful")
        print(
            ">> Controlls:\n"
            "     START button = run your program\n"
            "     BACK button = enter default drive mode\n"
            "     BACK + START buttons simultaneously = exit the program\n"
            "     CTRL + Z on keyboard = force quit the program"
        )

    def go(self):
        """
        Starts the RACECAR, beginning in default drive mode.

        Note:
            go idles in the main thread until the car program is exited
            (START + END pressed simultaneously).
        """
        self.__running = True
        while self.__running:
            pass

    def set_start_update(self, start, update, update_slow=None):
        """
        Sets the start and update functions used in user program mode.

        Example:
            # Create a racecar object
            rc = Racecar()
            # Define a start function
            def start():
                print("This function is called once")
            # Define an update function
            def update():
                print("This function is called every frame")
            # Provide the racecar with the start and update functions
            rc.set_start_update(start, update)
            # Tell the racecar to run until the program is exited
            rc.go()

        Args:
            start: (function) The function called once every time we enter user
                program mode.
            update: (function) The function called every frame in user program modes.

        Note:
            The provided start and update functions should not take any parameters.
        """
        self.__user_start = start
        self.__user_update = update
        self.__user_update_slow = update_slow

    def get_delta_time(self):
        """
        Returns the number of seconds elapsed in the previous frame.

        Returns:
            (float) The number of seconds between the start of the previous frame and
            the start of the current frame.

        Example:
            # Increases counter by the number of seconds elapsed in the previous frame
            counter += rc.get_delta_time()
        """
        return (self.__cur_frame_time - self.__last_frame_time).total_seconds()

    def set_update_slow_time(self, time):
        """
        Changes the time between calls to update_slow.

        Args:
            time (float): The time in seconds between calls to update_slow.

        Note:
            The default value is 1 second.

        Example:
            # Sets the time between calls to update_slow to 2 seconds
            rc.set_update_slow_ratio(2)
        """
        self.__max_update_counter = max(1, round(time * self.__FRAME_RATE))

    def __handle_start(self):
        """
        Handles when the START button is pressed by entering user program mode.
        """
        if self.__user_start is None or self.__user_update is None:
            print(
                ">> No user start and update functions found.  "
                "Did you call set_start_update with valid start and "
                "update functions?"
            )
        else:
            print(">> Entering user program mode")
            self.__user_start()
            self.__cur_update = self.__user_update
            self.__cur_update_slow = self.__user_update_slow

    def __handle_back(self):
        """
        Handles when the BACK button is pressed by entering default drive mode.
        """
        print(">> Entering default drive mode")
        self.__default_start()
        self.__cur_update = self.__default_update
        self.__cur_update_slow = None

    def __handle_exit(self):
        """
        Handles when BACK and START are pressed together by exiting the program.
        """
        print(">> Goodbye!")
        self.__running = False

    def __run(self):
        """
        Calls the current update and update_modules once per frame.
        """
        timer = rospy.Rate(self.__FRAME_RATE)
        while True:
            self.__last_frame_time = self.__cur_frame_time
            self.__cur_frame_time = datetime.now()
            self.__cur_update()
            self.__update_modules()

            # Use a counter to decide when we need to call update_slow
            if self.__cur_update_slow is not None:
                self.__cur_update_counter -= 1
                if self.__cur_update_counter <= 0:
                    self.__cur_update_slow()
                    self.__cur_update_counter = self.__max_update_counter

            timer.sleep()

    def __update_modules(self):
        """
        Calls the update function on each module.
        """
        self.drive._Drive__update()
        self.controller._Controller__update()
        self.camera._Camera__update()
        self.physics._Physics__update()

    def __default_start(self):
        """
        The start function for default drive mode.
        """
        self.drive.stop()

    def __default_update(self):
        """
        The update function for default drive mode.

        Controls:
            Left trigger: Accelerate forward
            Right trigger: Accelerate backward
            Left joystick: Turn left and right
            A button: Print "Kachow!" to the terminal
        """
        MAX_SPEED = 1.0  # The speed when the trigger is fully pressed
        MAX_ANGLE = 1.0  # The angle when the joystick is fully moved

        forwardSpeed = self.controller.get_trigger(self.controller.Trigger.RIGHT)
        backSpeed = self.controller.get_trigger(self.controller.Trigger.LEFT)
        speed = (forwardSpeed - backSpeed) * MAX_SPEED

        # If both triggers are pressed, stop for safety
        if forwardSpeed > 0 and backSpeed > 0:
            speed = 0

        angle = (
            self.controller.get_joystick(self.controller.Joystick.LEFT)[0] * MAX_ANGLE
        )

        self.drive.set_speed_angle(speed, angle)

        if self.controller.was_pressed(self.controller.Button.A):
            print("Kachow!")
