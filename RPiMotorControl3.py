#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# RPiMotorcontrol.py adapted to run from python3

""" Control of 2 motors 
    through 4 GPIO pins 11,12,15,16 (changeable) on Raspberry Pi,
    e.g. to drive and steer buggy. 
    
    Run program from laptop via wifi to onboard (headless) Raspberry Pi 
      from laptop command line: gksudo python3 RPiMotorControl3.py

    Ian R Williams 2016 Nov 12, amended for speed control from 2015 Oct 10
"""

# FURTHER TESTING STILL NEEDED
# adapted from k8055motorcontrol.py 2015 May 8 to run under python3
#
# ***** This program works but needs some tidying up'
#        Running remotely (using gksudo python3 RPiMotorControl3.py) generates warning in cli:
#            Xlib:  extension "RANDR" missing on display ":1.0".
#            (gksudo:2918): GLib-GObject-WARNING **: Attempt to add property 
#                   GtkSettings::gtk-label-select-on-focus after class was initialised
#            (gksudo:2918): GLib-GObject-WARNING **: Attempt to add property 
#                    GtkSettings::gtk-button-images after class was initialised
# ***** Different speed motors means, 
#        e.g., "forwards" is a gentle curve rather than a straight line!

# 2 motors are each driven through dual DPDT relay boards,
#   each relay being controlled by 2 RPi GPIO pins
# One high output makes the motor move forwards (FWD) or backwards (REV).
# The motor is stopped if both outputs are low or if both are high.

# The program presents 4 panels.
# A CONTROL panel activates one of the three other panels.
# The TEST panel activates (makes high) any one of the 4 digital outputs
#   so that the effect on the motors can be seen, e.g. left motor drives forward.
# The ASSIGN panel assigns GPIO pins Pin A, B, C, D to LEFT FWD, etc
# These assigned connections set the DRIVE controls as follows
#     STOP          LT STOP     RT STOP
#     FORWARD       LT FWD      RT FWD
#     REVERSE       LT REV      RT REV
#     TURN LEFT     LT STOP     RT FWD
#     TURN RIGHT    LT FWD      RT STOP
#     REVERSE LEFT  LT STOP     RT REV
#     REVERSE RIGHT LT REV      RT STOP
#     ROTATE LEFT   LT REV      RT FWD
#     ROTATE RIGHT  LT FWD      RT REV
# The DRIVE panel can now be used to drive the 2 motors and the attached platform

import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import time
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BOARD)    # Call pins by their positions on the BOARD

class MotorControl():

    """ Tests Digital Outputs to see effect on one or other motor, e.g., LEFT FWD
        Assigns Outputs for their effects on motors, e.g FORWARD 
        Drives both motors:
            layout is      Left Motor          Right Motor
                                   Trailing Caster
    """
    
    # This callback quits the program
    def delete_event(self, widget, event, data=None):
        GPIO.cleanup()
        Gtk.main_quit()
        return 0
        
    # This method sets/resets the voltages on the 4 GPIO (Output) Pins
    def write_GPIO(self, widget, data):
        print("write_GPIO: data = ",data)
        if True: #widget_get_active():
            time.sleep(1.0)
            print("widget active when data = ",data)
            x = int(data)        
            if x & 1:
                self.PWM_A.ChangeDutyCycle(100)
                #GPIO.output(self.PinA, GPIO.HIGH)
            else:
                self.PWM_A.ChangeDutyCycle(0)
                GPIO.output(self.PinA, GPIO.LOW)
            if x & 2:
                self.PWM_B.ChangeDutyCycle(100)
                #GPIO.output(self.PinB, GPIO.HIGH)
            else:
                self.PWM_B.ChangeDutyCycle(0)
                #GPIO.output(self.PinB, GPIO.LOW)
            if x & 4:
                self.PWM_C.ChangeDutyCycle(100)
                #GPIO.output(self.PinC, GPIO.HIGH)
            else:
                self.PWM_C.ChangeDutyCycle(0)
                #GPIO.output(self.PinC, GPIO.LOW)
            if x & 8:
                self.PWM_D.ChangeDutyCycle(100)
                #GPIO.output(self.PinD, GPIO.HIGH)
            else:
                self.PWM_D.ChangeDutyCycle(0)
                #GPIO.output(self.PinD, GPIO.LOW)

    # This callback responds to a change in the CONTROL box (TEST/ASSIGN/DRIVE)
    def control_changed(self, widget, data=None):        
        self.tbutton[0].set_active(True)   # set TEST buttons to STOP
        self.dbutton[0].set_active(True)   # set DRIVE buttons to STOP
        self.write_GPIO(self, 0)           # set all GPIO outputs low -> both motors off

        # If TEST panel is active find effect of each pin on motors:
        #   left or right motor, forward or backward:-           
        if self.cbutton_t.get_active():
            for i in range(self.np + 1):     
                self.tbutton[i].set_sensitive(True)
            for i in range(self.np):
                for j in range(self.np):
                    self.abutton[self.np*i+j].set_sensitive(False)
            for i in range(self.ns):
                self.dbutton[i].set_sensitive(False)
            print('TEST buttons enabled (DRIVE & ASSIGN disabled)')
        else:
            for i in range(self.np + 1):
                self.tbutton[i].set_sensitive(False)

        # If ASSIGN panel is active, set inputs to both motors from TEST run
        #   to give correct driving/steering behaviour:-        
        if self.cbutton_a.get_active():
            for i in range(self.np):
                for j in range(self.np):                                                  
                    self.abutton[self.np*i + j].set_sensitive(True) 
            for i in range(self.ns):
                self.dbutton[i].set_sensitive(False)                   
            print('ASSIGN buttons enabled (TEST & DRIVE disabled)')

        # If DRIVE panel is active use ASSIGNed settings to drive both motors
        if self.cbutton_d.get_active():
            for i in range(self.np + 1):
                self.tbutton[i].set_sensitive(False)
            for i in range(self.np):
                for j in range(self.np):
                    self.abutton[self.np*i + j].set_sensitive(False)    
            for i in range(self.ns):
                self.dbutton[i].set_sensitive(True)
                self.kd[i] = 0
                for j in range(self.np):
                    x = 1<<j                    
                    if self.dp[i] & x > 0:
                        self.kd[i] = self.kd[i] | self.ka[j]     
            print('DRIVE is enabled (TEST & ASSIGN disabled)')
                    
    # This callback responds to a button being clicked in the TEST box
    #   if the TEST button in the CONTROL BOX is active      
    def test_output_called(self, widget, data):
        if self.cbutton_t.get_active():    
            self.dbutton[0].set_active(True)
            if data == "STOP":
                x = 0            
            else:
                x = 1 << (int(data))              
            self.write_GPIO(self, x)                                           
            if x == 0:
                print('Pins all now turned OFF')
            else:                
                print('Pin {} only is now turned ON: (x = {})'.format(self.pin[data],x))

    # This callback responds to a button being clicked in the ASSIGN box
    #   if the ASSIGN button in the CONTROL BOX is active       
    def assign_output_called(self, widget, data):
        if self.cbutton_a.get_active():
            i = data % self.np
            j = data // self.np
            print('Button P{} pressed in ASSIGN box {}, data = {}'.format(self.pin[i],self.drive[j],data))

            # toggle bit i in drive bit control ka[j]
            x = 1 << i

            # Bit setting/unsetting in keepers ka of digital assignments for steering/driving
            self.ka[j] = (self.ka[j] & ~x, self.ka[j] | x)[widget.get_active()]
            print('Pin {} and {}:' .format(self.pin[i], self.drive[j])),
            print( '%s' ("detached","attached")[widget.get_active()])
            #print( "ka[%s] is now %s" % (j,self.ka[j]))
            
        
    # This callback responds to a button being clicked in the DRIVE box
    #   if the DRIVE button in the CONTROL BOX is active     
    def drive_output_called(self, widget, data):
        if self.cbutton_d.get_active():
            print(data)
            if data == "STOP":
              print("button pressed in drive box: STOP")
              x = 0
            else:
              print("button pressed in drive box: data = %s, kd = %s" % (data, self.kd[int(data)]))
              x = self.kd[int(data)]
            self.write_GPIO(self, x)           
                           
    def __init__(self, readtime):

        # GPIO pins to be used for output, set LOW _quickly_ at start of program
        ##GPIO.setwarnings(False)
        self.PinA = 11  
        self.PinB = 12
        self.PinC = 15
        self.PinD = 16
        try:        
            GPIO.setup(self.PinA, GPIO.OUT, initial=0)  
        except RuntimeError:
            print("You need to run as root: gksudo  python3 RPiMotorControl3.py")  
        GPIO.setup(self.PinB, GPIO.OUT, initial=0)
        GPIO.setup(self.PinC, GPIO.OUT, initial=0)
        GPIO.setup(self.PinD, GPIO.OUT, initial=0)
        
        # Set PWM frequency, and create PWM for pins A to D, initially all OFF
        self.freq = 100
        self.PWM_A = GPIO.PWM(self.PinA, self.freq)
        self.PWM_B = GPIO.PWM(self.PinB, self.freq)
        self.PWM_C = GPIO.PWM(self.PinC, self.freq)
        self.PWM_D = GPIO.PWM(self.PinD, self.freq)
        self.PWM_A.start(0)
        self.PWM_B.start(0)
        self.PWM_C.start(0)
        self.PWM_D.start(0)

        # Create a new window
        self.window = Gtk.Window()
        self.window.set_title("RPi Motor Control")
        self.window.set_border_width(20)
               
        # Set a handler for delete_event that immediately exits GTK.
        self.window.connect("delete_event", self.delete_event)

        # Create a Box within the window to contain everything
        box0 = Gtk.VBox(False, 0)
        self.window.add(box0)

        # Add a frame to switch CONTROL between TEST, ASSIGN and DRIVE modes
        frame_c = Gtk.Frame(label="MAIN CONTROL PANEL  --  select mode")
        box0.pack_start(frame_c, False, False, 0)

        # Create a box to contain the CONTROL buttons
        box_c = Gtk.HBox(True, 120)
        frame_c.add(box_c)

        # Create another box to contain TEST, ASSIGN and DRIVE boxes the rest of the boxes)
        box1 = Gtk.HBox(False, 0)
        box0.pack_start(box1, False, False, 0)
           
        # Create radiobutton CONTROL box to activate TEST or ASSIGN or DRIVE button sets     
        self.cbutton_t = Gtk.RadioButton.new_with_label_from_widget(None, "TEST")
        self.cbutton_t.connect("toggled", self.control_changed, "Test")
        self.cbutton_t.set_active(True)
        box_c.pack_start(self.cbutton_t, True, True, 0)

        self.cbutton_a = Gtk.RadioButton.new_from_widget(self.cbutton_t)
        self.cbutton_a.set_label("ASSIGN")
        self.cbutton_a.connect("toggled", self.control_changed, "Assign")
        box_c.pack_start(self.cbutton_a, True, True, 0)

        self.cbutton_d = Gtk.RadioButton.new_with_mnemonic_from_widget(self.cbutton_t, "DRIVE")
        self.cbutton_d.connect("toggled", self.control_changed, None)
        box_c.pack_start(self.cbutton_d, True, True, 0)

        # Align the label in the middle of the frame    
        frame_c.set_label_align(0.5, 0.0)                           
           
        # Create a Box to contain the Digital Display to TEST output to motors
        box_t = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box1.pack_start(box_t, False, False, 0)


        # Create a Frame for Digital Outputs and attach to the box
        frame_t = Gtk.Frame() 
        box_t.pack_start(frame_t, False, False, 0)
        # Create a Box within the Frame to pack the Buttons
        box_t1 = Gtk.VBox(False, 0)
        frame_t.add(box_t1)       

        # Create a Box to contain the Display ASSIGNing Digital Outputs to Motor Controls
        box_a =  Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box1.pack_start(box_a, False, False, 0)
        
        # Create a Frame for Motor Controls
        frame_d = Gtk.Frame()      
        box1.pack_start(frame_d, False, False, 0)
        
        # Create a Frame to ASSIGN Digital Outputs to Motor Driving Controls
        frame_a = Gtk.Frame()
        box_a.pack_start(frame_a, False, False, 0)        

        # Create a Box within the Frame to pack the Buttons
        box_a1 = Gtk.VBox(False, 0)
        frame_a.add(box_a1)       

        # Create a Box to contain the Display to control/steer/DRIVE the motors
        box_d = Gtk.VBox(False, 0)
        frame_d.add(box_d)

        # Motor connection links for ASSIGN
        self.drive =("L  FWD","L  REV ","R  FWD","R  REV ")

        # np is the number of digital lines (GPIO pins) used for controlling the motors
        self.np = len(self.drive)

        # pin are the names of the pins on the RPi given earlier in the program
        self.pin = ("A", "B", "C", "D")
              
        # Steering and direction controls for DRIVE
        #   as assigned in the ASSIGN panel      
        steer = ("STOP","FORWARD","REVERSE","TURN LEFT","TURN RIGHT","REVERSE LEFT","REVERSE RIGHT","ROTATE LEFT","ROTATE RIGHT")

        # ns is the number of different ways of driving the 2-motor system
        # The drive parameters dp store the info as bits (MSB first): 
        #    R REV, R FWD, L REV, L FWD
        self.ns = len(steer)
        self.dp = (0b0000, 0b0101, 0b1010, 0b0100, 0b0001, 0b1000, 0b0010, 0b0110, 0b1001)
              
        # Put the widgets into the TEST box
        
        # Create list of buttons for TESTing digital outputs
        self.tbutton = []
        for i in range(self.np + 1):
            self.tbutton.append(False)
            
        # Create STOP button in TEST frame
        self.tbutton[0] = Gtk.RadioButton.new_with_label_from_widget(None, "STOP")

        # When the STOP button is pressed, call the callback method
        self.tbutton[0].connect("toggled", self.test_output_called, "STOP")           
        box_t1.pack_start(self.tbutton[0], True, True, 0)
        
        # Create buttons to control and display Digital Outputs to motors in TEST frame
        for i in range(self.np):

            # Create button
            s = str(self.pin[i])
            j = i+1
            self.tbutton[j] = Gtk.RadioButton.new_from_widget(self.tbutton[0],)
            self.tbutton[j].set_label("P" + s)      

            # When the button is pressed, call the callback method
            self.tbutton[j].connect("toggled", self.test_output_called, i)
            # Insert button
            box_t1.pack_start(self.tbutton[j], True, True, 4)       
            
        # Initialize the settings ka for use in the ASSIGN box 
        #   These will be copied from drive parameters dp (in 4-bit format)
        self.ka = []
        for i in range(self.np):
            self.ka.append(0)
            #self.ka[i] = 0
            
        # Initialize the settings kd for the ns DRIVE modes
        self.kd = []
        for i in range(self.ns):
            self.kd.append(0)
            #self.kd[i] = 0 

        # Create buttons to ASSIGN Digital Outputs to Steering Controls
        self.abutton = []

        # i is the row in the ASSIGN box: i=0 L FWD as in drive tuple
        for i in range(self.np):

            # j is the column in the ASSIGN box
            for j in range(self.np): 
                self.abutton.append(False)                

        for i in range(self.np):

            # Create box to contain label and buttons
            label = Gtk.Label(self.drive[i] + ": || ")          
            box_a2 = Gtk.HBox(False, 0)
            box_a1.pack_start(box_a2, False, False, 2) 
            frame_a2 = Gtk.Frame()
            box_a2.pack_start(frame_a2, False, False, 3)
            box_a3 = Gtk.HBox(False, 0)
            frame_a2.add(box_a3)
            
            box_a3.pack_start(label, False, False, 0)          
            for j in range(self.np): 
                n = self.np*i + j      
                self.abutton[n] = Gtk.CheckButton("P" + self.pin[j] + " || ")
                self.abutton[n].set_sensitive(False)
                self.abutton[n].connect("toggled",self.assign_output_called, n)

                # Insert button
                box_a3.pack_start(self.abutton[n], False, False, 0) 
      
        # Create DRIVE buttons to steer platform
        self.dbutton = []

        for i in range(self.ns):
            self.dbutton.append(False)
        self.dbutton[0] = Gtk.RadioButton.new_with_label_from_widget(None, steer[0])
        self.dbutton[0].set_sensitive(False)
        self.dbutton[0].connect("toggled", self.drive_output_called, "STOP")    
        box_d.pack_start(self.dbutton[0], False, False, 3)        

        for i in range(1,self.ns):
            self.dbutton[i] = Gtk.RadioButton.new_from_widget(self.dbutton[0])
            self.dbutton[i].set_sensitive(False)
            self.dbutton[i].set_label(steer[i])    
            self.dbutton[i].connect("toggled", self.drive_output_called, i)       
            # Insert button
            box_d.pack_start(self.dbutton[i], False, False, 3)

        self.dbutton[0].set_active(True)

        # Create "Quit" button
        button = Gtk.Button("Quit")
 
        # When the QUIT button is clicked, call the function to exit the program
        button.connect("clicked", self.delete_event, None)
        
        # Insert the QUIT button under the ASSIGN buttons
        box_a.pack_start(button, False, False, 15)
        #button.set_flags(Gtk.CAN_DEFAULT) 
        button.grab_default()

        # Make everything visible
        self.window.show_all()       
              
def main():
    Gtk.main()
    return 0            

if __name__ == "__main__":
        MotorControl(readtime=50)
        main()
        
