#!/usr/bin/env python

import rospy, csv
from geometry_msgs.msg import Twist
from turtlesim.srv import TeleportAbsolute
from turtlesim.msg import Pose
from std_srvs.srv import Empty as EmptyServiceCall
from math import atan2, sqrt, pow

PI = 3.1415926535897

class turtle_robot:

    def __init__(self):

	#Create node, publisher and subscriber
	
	rospy.init_node('turtle_robot', anonymous=True)
    
	self.velocity_publisher = rospy.Publisher('/turtle1/cmd_vel', Twist, queue_size=10)
	self.vel_msg = Twist()

	self.pose_subscriber = rospy.Subscriber('/turtle1/pose', Pose, self.pose_callback)
	self.pose_data = Pose()

    #Define callback function to retrieve pose data from robot 
    def pose_callback(self, data):

	self.pose_data = data

    #Define function to draw a figure
    def draw_figure(self):

	#Get the speed in the x axis as a ROS parameter stored in the launch file 
	#The ~ is because it was defined as a private parameter inside the node
    	xspeed = rospy.get_param('~xspeed')

    	#Set the angular speed (here it is arbitrary, as there is no specification on controlling it)
    	angular_speed = PI/2

	#Get the coordinates to draw the figure
	self.get_figure()

    	#Place the turtle in the start point
    	self.moveto_startpoint()
    	   
	#Wait for the node to start receiving the pose data (I had trouble with this, since it had a delay at the beginning.
	#I don't like this solution but it was the best I could come up with to wait for the data)
        while(self.pose_data.x==0):
		pass       

	#Counter used to go over the points in the figure list
	target_id = 1

    	while(target_id<len(self.target_points)):	
	

    		#First rotate the turtle so that the TCP axis is alligned with the vector to the target
    		#self.setOrientation(target_id, angular_speed)

		#Calculate the target angle (absolute)
		desired_angle_abs= atan2(self.target_points[target_id][1]-self.pose_data.y, self.target_points[target_id][0] - self.pose_data.x)

		#Place the turtle in the starting point and then clear the first trace
    		rospy.wait_for_service('turtle1/teleport_absolute')
    		turtle1_teleport = rospy.ServiceProxy('turtle1/teleport_absolute', TeleportAbsolute)
    		turtle1_teleport(self.pose_data.x, self.pose_data.y, desired_angle_abs)

		#Then move the robot along the TCP x axis, towards the target

    		self.moveToXY(target_id, xspeed)
		
    		#Increase the target ID to get to the next point
    		target_id+=1
		
    	rospy.spin()

    #Get the target points for the turtle to draw the figure
    def get_figure(self):

	#(When creating a new figure, make sure to add the first point at the end to draw a closed surface)

	coordinates_file = rospy.get_param('~figure_file')

	with open(coordinates_file) as csvfile:

     		self.target_points=[(float(x), float(y)) for x, y in csv.reader(csvfile, delimiter=',')] 
   

    def moveto_startpoint(self):

    	#Reset the simulator in case it was already open, to delete any previous trace 
    	rospy.wait_for_service('reset')
    	turtle1_reset = rospy.ServiceProxy('reset', EmptyServiceCall)
    	turtle1_reset()

    	#Place the turtle in the starting point with theta = 0
    	rospy.wait_for_service('turtle1/teleport_absolute')
    	turtle1_teleport = rospy.ServiceProxy('turtle1/teleport_absolute', TeleportAbsolute)
    	turtle1_teleport(self.target_points[0][0], self.target_points[0][1], 0)

    	#Erase the first trace
    	rospy.wait_for_service('clear')
    	turtle1_clear = rospy.ServiceProxy('clear', EmptyServiceCall)
    	turtle1_clear()

    def moveToXY(self,index, linSpeed):
	
	#Calculate the target distance
	target_distance = sqrt(pow(self.target_points[index][0]-self.pose_data.x, 2)+ pow(self.target_points[index][1]-self.pose_data.y, 2))
	
	#Set the speed for the x axis
        self.vel_msg.linear.x = linSpeed

	#Since we are moving in x, make velocity in other dimensions zero
    	self.vel_msg.linear.y = 0
    	self.vel_msg.linear.z = 0
	self.vel_msg.angular.x = 0
	self.vel_msg.angular.y = 0
	self.vel_msg.angular.z = 0

	#Loop to move the turtle a specified distance
	self.rate = rospy.Rate(100)

    	while(current_distance < target_distance):

		#Publish the velocity
		self.velocity_publisher.publish(self.vel_msg)
        	#Calculate the distance already travelled by the robot
		current_distance = sqrt(pow(self.target_points[index-1][0]-self.pose_data.x, 2)+ pow(self.target_points[index-1][1]-self.pose_data.y, 2))
		self.rate.sleep()

        #After the loop, stop the robot
        self.vel_msg.linear.x = 0
        self.velocity_publisher.publish(self.vel_msg)

    def setOrientation(self, index, angSpeed):

	#Calculate the target angle (absolute)
	desired_angle_abs= atan2(self.target_points[index][1]-self.pose_data.y, self.target_points[index][0] - self.pose_data.x)

	theta0 = self.pose_data.theta
		
	#Make both angles, the target and the current one, be between 0 and 2*PI
	if (desired_angle_abs<0):
		desired_angle_abs = desired_angle_abs +2*PI
		
	if (self.pose_data.theta<0):
		theta0 = theta0 + 2*PI

	#Now calculate the value of the angle between the target and the current point
	desired_angle_rel = desired_angle_abs - theta0

	#Make sure that the robot takes the shortest path (no angles bigger than PI)
		
	if(desired_angle_rel> PI):
		desired_angle_rel = desired_angle_rel -2*PI

	if(desired_angle_rel<-PI):
		desired_angle_rel = 2*PI + desired_angle_rel
	
	#Set the clockwise or counterclockwise motion, according to the shortest path
						
	if(desired_angle_rel<0):

		self.vel_msg.angular.z = -abs(angSpeed)
	else:
		self.vel_msg.angular.z = abs(angSpeed)

	self.rotateZ(desired_angle_rel, angSpeed)
	

    def rotateZ(self, desired_angle, ang_zspeed):

	#Since we are rotating in z, make velocity in other dimensions zero
	self.vel_msg.linear.x = 0
    	self.vel_msg.linear.y = 0
    	self.vel_msg.linear.z = 0
	self.vel_msg.angular.y = 0
	
	current_angle_rel=0

	t0_r = rospy.Time.now().to_sec()
		
	self.rate = rospy.Rate(100)

    	while(abs(current_angle_rel) < abs(desired_angle)):

            	self.velocity_publisher.publish(self.vel_msg)

           	t1_r = rospy.Time.now().to_sec()
           	current_angle_rel = ang_zspeed*(t1_r-t0_r)
				
		self.rate.sleep()
	
    	#Force the robot to stop once the orientation is reached
    	self.vel_msg.angular.z = 0
    	self.velocity_publisher.publish(self.vel_msg)


if __name__ == '__main__':

    try:
        #Testing our function
	tr = turtle_robot()
        tr.draw_figure()

    except rospy.ROSInterruptException: pass
