'''
To Do: 

!!!!!!monochromator is incorrect lmao how did you even do that
-add video mode
-add actual raman mode lol
-add spectrum time calc
-initialize values
-error handling for wrong inputs
-fix ROI bug to remove stupid for loops
-add update loop for ccd temp
-add calibration 
-add save button on camera control
-save spectrums as csv

known issue: mono control freq loses communication. needs current pos in file to match current positon 
usually fails if commercial softaware is used

'''

'''
Questions and Notes and Such:

What is a picture vs a Raman spectrum?

Does monochromator require 999.9 style input or can this be relaxed?
Is it possible to automatically fill 0's after decimal if not input?



'''
# REQUIRED PACKAGES:  pylablib, ???


# mono imports
import sys
sys.path.append('C:/Users/nickp/anaconda3/')
import logging, configparser, time, serial
import datetime as dt
from PyQt5 import QtGui, QtCore, QtWidgets
import PyQt5.QtWidgets as QWidgets

from tkinter import Tk
from tkinter.filedialog import askdirectory
from datetime import date
import os
# camera import
# from picam import *
import pylablib as pll
pll.par["devices/dlls/picam"] = "path/to/dlls"
from pylablib.devices import PrincetonInstruments

import matplotlib.pyplot as plt
import numpy as np

import ctypes
myappid = 'reznik.ramanControl.steve.01' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

plt.ion()

# first, do some house keeping
# prompt the user for parent directory, then make folder with todays date
try: 
    parentDir = askdirectory(title='Select project folder') # shows dialog box and return the path
    dataDir = str(date.today())
    path = os.path.join(parentDir, dataDir)
    os.mkdir(path)
except FileExistsError:
    print('Using folder from earlier today')


laser = 532# hard coded bullshit, fix

# def wavNumToNM(wav):
#     #for a relative shift, not absolute
#     wav = float(wav)
#     nm = 1/(wav + 1/(laser))
#     return nm

def takeSnapShot(fname, pos):
    # pos is spectrometer position
    img = cam.snap()

    signal = []
    pixel = range(len(img[0]))
    # it would be so much better to use the ROI binning. something weird need to fix
    for i in range(len(img[0])):
        signal.append(sum(img[:, i]))

    plt.plot(pixel, signal)
    plt.show()

    # now save this spec
    # this is clunky, you should be able to separate this later
    fpath = os.path.join(path, fname)
    file = open(fpath, 'w')
    file.write('wavelength(nm), raman shift(cm^-1), intensity(arb) \n')
    wavelen =[]
    wavNum = []
    data = []
    px1 = 799 #center wavelength position
    px2 = 426 # high edge (7nm below)
    deltaL = 22
    pixel = range(0,1340)
    for i in range(400,1340):
        wav = pos+ ((deltaL/(px2-px1))*(pixel[i]-px1))
        waveNum = 1/laser - 1/(wav*10**(-7))
        signal = sum(img[:, i])
        wavelen.append(wav)
        wavNum.append(waveNum)
        data.append(signal)
        stringToWrite = str(wav) + ','+str(waveNum) + ','+str(signal)+'\n' 
        file.write(stringToWrite)    

    return signal

def takeSpectrum(start, stop, fname): 
    #HARD CODED CONVERSION FOR NOW
    #FIX THIS DUMBASS
    '''
        start and stop input in nm bc my brain is tired and i keep fucking up the conversion. 
        output saves both nm and cm^-1 so its fine
    '''
    fpath = os.path.join(path, fname)
    file = open(fpath, 'w')
    file.write('wavelength(nm), raman shift(cm^-1), intensity(arb) \n')
    # assumes start and stop input in cm^-1 shift, since thats how we normally talk about it
    # start by converting start and stop to nm
    # nmStart = wavNumToNM(float(start))
    # nmStop = wavNumToNM(float(stop))

    #now we move the spec to the start 
    #note - this will overshoot! personally, i don't care
    #i'd rather take more data & am writing this so it just takes a fuckload of data
    #can be rewritten in future
    wavelen =[]
    wavNum = []
    data = []
    #sleep for 1 minute to give time to leave the room
    time.sleep(60)
    for pos in np.arange(float(start), float(stop), 7):
        # Mono1.approachWL(pos)
        img = cam.snap()
        #now figure out what the axis was 
        #yikes
        #remember pos is the detector center, not edge
        #all of this is hard coded but should be switched with a calibration process to do at the start f the day
        px1 = 799 #center wavelength position
        px2 = 426 # high edge (7nm below)
        deltaL = 22
        pixel = range(0,1340)
        for i in range(400,1340):
            wav = pos+ ((deltaL/(px2-px1))*(pixel[i]-px1))
            waveNum = 1/laser - 1/(wav*10**(-7))
            signal = sum(img[:, i])
            wavelen.append(wav)
            wavNum.append(waveNum)
            data.append(signal)
            stringToWrite = str(wav) + ','+str(waveNum) + ','+str(signal)+'\n' 
            file.write(stringToWrite)
    file.close()
    fpath_csv=os.path.join(path,fname+'.csv')
    os.rename(fpath,fpath_csv)
    plt.plot(wavNum, data)

class Monochromator(object):
    ### Initialises a serial port
    def __init__(self):
	
        self.config = configparser.RawConfigParser()
        self.config.read('mono.cfg')
        self.comport = self.config.get('Mono_settings', 'com_port')
        self.mono = serial.Serial(self.comport, timeout=1, baudrate=9600, xonxoff=1, stopbits=1)

        self.current_wavelength = self.config.get('Mono_settings', 'current_wavelength')
        self.current_laser_wavelength = self.config.get('Settings', 'laser_wavelength')
        self.speed = self.config.get('Mono_settings', 'speed')
        self.approach_speed = self.config.get('Mono_settings', 'approach_speed')
        self.offset = self.config.get('Mono_settings', 'offset')
        self.nm_per_revolution = self.config.get('Mono_settings', 'nm_per_revolution')
        self.steps_per_revolution = self.config.get('Mono_settings', 'steps_per_revolution')

    ### sends ascii commands to the serial port and pauses for half a second afterwards
    def sendcommand(self,command):
        self.mono.flushInput()
        self.mono.flushOutput()
        if (command != "^"):
            print('Send command: ' + command)
        #logging.debug('Send command: ' + command)
        self.mono.write(bytearray(command + '\r\n','ascii'))
        time.sleep(0.5) 
        
    ### reads ascii text from serial port + formatting
    def readout(self):
        #time.sleep(0.5)
        #self.mono.flushInput()
        value = self.mono.readline().decode("utf-8")
        return str(value.rstrip().lstrip())
    
    ### sets the ramp speed
    def setRampspeed(self, rampspeed):
        self.sendcommand('K ' + str(rampspeed))
    
    ### sets the initial velocity
    def setInitialVelocity(self,initspeed): 
        self.sendcommand('I ' + str(initspeed))
    
    ### sets the velocity   
    def setVelocity(self,velocity):
        self.sendcommand('V ' + str(velocity))
        
    ### checks if the Monochromator is moving (returns True or False) 
    def moving(self):
        self.sendcommand('^')
        a = self.readout()
        if a[3:].lstrip() == "0":
            print("Mono is not moving \r")
            return False
        else:
            print("Mono is moving \r")
            return True
			
    def checkfortimeout(self):
        try:
            self.sendcommand('X')
            if self.readout() == None:
                print('Timeout occurred')
        except:
            print('Timeout occurred')
            
    def checkLimitSwitches(self):
        self.sendcommand("]")
        a = self.readout()
        if a[3:].lstrip() == "64":
            return "Upper"
        if a[3:].lstrip() == "128":
            return "Lower"
        else:
            return False
        
    def checkHOMEstatus(self):
        self.sendcommand("]")
        value = self.mono.readline().decode("utf-8")
        print("HOME Status complete: " + value)
        print("HOME Status: " + value[3:])
        return str(value[3:].rstrip().lstrip())
		
    def getHomePosition(self): 

        ### This function performs the homing procedure of the monochromator. See
        ### the mono manual for information about the seperate parameters

        ### move to 510 nm before starting the homing procedure

        self.approachWL(510.0)

        while(self.moving()):
            self.moving()

        ### begin homing procedure

        self.sendcommand("A8")
        self.checkHOMEstatus()
        if(self.checkHOMEstatus() == "32"):
            self.sendcommand("M+23000")
            while(self.checkHOMEstatus() != "2"):
                time.sleep(0.8)
                self.checkHOMEstatus()

            self.sendcommand("@")
            self.sendcommand("-108000")
		
            while(self.moving()):
                self.moving()
				
            self.sendcommand("+72000")

            while(self.moving()):
                self.moving()
				
            self.sendcommand("A24")
	            
            while(self.moving()):
                self.moving()
            
            n1=dt.datetime.now()
			
            self.sendcommand("F1000,0")

            while(self.moving()):
                self.moving()
                n2=dt.datetime.now()
                if (((n2.microsecond-n1.microsecond)/1e6) >= 300):
                    self.sendcommand("@")
                    print("timeout, stopping")
                    break
				
            self.sendcommand("A0")
            self.config.set('Mono_settings', 'current_wavelength', '524.9')
            print("Homing done, setting current wavelength now to 524.9 nm according to mono manual")
            f = open('mono.cfg',"w")
            self.config.write(f)
            Interface.currentMonoWavelengthLabel.setText("524.9 nm")
		
    def approachWL(self, approach_wavelength):		
        Interface.approachButton.setEnabled(False)
        if isinstance(approach_wavelength, float):
            print("Wavelength to approach: " + str(approach_wavelength) + " nm")
            nm_difference = float(approach_wavelength) - float(self.current_wavelength)
            print("Difference in nm: " + str(nm_difference))
            step_difference = round(((float(nm_difference) / float(self.nm_per_revolution)) * float(self.steps_per_revolution))+ float(self.offset))
            print("Difference in steps: " + str(step_difference))  
            time_needed_sec = abs(step_difference / int(self.speed)) + abs(int(self.offset)/int(self.approach_speed))
            print("Time needed for operation: " + str(time_needed_sec) + " s")
            time_delay_for_progressbar = time_needed_sec / 100
            self.sendcommand("V" + str(self.speed))
            self.sendcommand(str(format(step_difference, '+')))
            self.sendcommand("V" + str(self.approach_speed))
            self.sendcommand("-" + str(self.offset))
            while True:
                time.sleep(time_delay_for_progressbar)
                value = Interface.progressBar.value() + 1
                Interface.progressBar.setValue(value)
                QtWidgets.qApp.processEvents()
                if (value >= Interface.progressBar.maximum()):
                    Interface.approachButton.setEnabled(True)
                    Interface.progressBar.setValue(0)
                    self.config.set('Mono_settings', 'current_wavelength', approach_wavelength)
                    self.config.set('Settings', 'laser_wavelength', self.current_laser_wavelength)
                    self.current_wavelength = approach_wavelength
                    Interface.currentMonoWavelengthLabel.setText(str(self.current_wavelength) + " nm")
                    f = open('mono.cfg',"w")
                    self.config.write(f)
                    break
        else:
            print("Input is not numeric")
            MessageBox = QtGui.QMessageBox.warning(Interface,"Error:","Input is not numeric") 
            Interface.approachButton.setEnabled(True)
        
class Ui_Form(QWidgets.QWidget):
    ### All UI elements go here
    def __init__(self,cam):
        # self.upate_timer = QTimer(self)
        # self.upate_timer.setInterval(100) # milliseconds i believe
        # self.upate_timer.setSingleShot(False)
        # self.upate_timer.timeout.connect(self.update_label)

        ### create main window

        QWidgets.QWidget.__init__(self)
        self.setWindowTitle('Steve control')
        self.setWindowIcon(QtGui.QIcon('icon.png'))
        

        ## create status bar
        #def createStatusBar(self):
        #    statusBar().showMessage(tr("Ready"))
        #statusbar=QWidgets.QStatusBar()
        #statusbar.addWidget(QtWidgets.QLabel("Test status"))
        #QWidgets.QStatusBar.showMessage('test status',30)

        ### create tabbed interface

        tab_widget = QtWidgets.QTabWidget()
        tab1 = QWidgets.QWidget()
        tab2 = QWidgets.QWidget()
        tab3 = QWidgets.QWidget()
        p1_vertical = QtWidgets.QFormLayout(tab1)
        p2_vertical = QtWidgets.QFormLayout(tab2)
        p3_vertical = QtWidgets.QFormLayout(tab3)
        tab_widget.addTab(tab1, "Spectrometer Control")
        tab_widget.addTab(tab2, "Camera Control") 
        tab_widget.addTab(tab3, "Raman") 

        # ### create label for current mono wavelength
		
        # self.currentMonoWavelengthLabel = QtWidgets.QLabel(self)
        # self.currentMonoWavelengthLabel.setAlignment(QtCore.Qt.AlignRight)
        # self.currentMonoWavelengthLabel.setText(Mono1.current_wavelength + " nm")

        # ### create input field for current laser wavelength for Raman peak calculations
        
        # self.currentLaserWavelengthInput = QtWidgets.QLineEdit(self)
        # self.currentLaserWavelengthInput.setMaxLength(5)
        # self.currentLaserWavelengthInput.setInputMask("999.9")
        # self.currentLaserWavelengthInput.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        # self.currentLaserWavelengthInput.setText(Mono1.current_laser_wavelength + " nm")

        # ### create input field for wavelength to approach

        # self.approachWavelengthInput = QtWidgets.QLineEdit(self)
        # self.approachWavelengthInput.setMaxLength(5)
        # self.approachWavelengthInput.setInputMask("999.9")
        # self.approachWavelengthInput.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        # # self.approachWavelengthInput.textChanged.connect(self.check_state)
        # self.approachWavelengthInput.textChanged.emit(self.approachWavelengthInput.text())

        # ### create button to start the mono movement

        # self.approachButton = QtWidgets.QPushButton(self)
        # self.approachButton.setObjectName("approachButton")
        # self.approachButton.clicked.connect(lambda: Mono1.approachWL(float(self.approachWavelengthInput.text())))
        # self.approachButton.setText("Approach")

		# ### create progress bar for mono movement progress indication
		
        # self.progressBar = QtWidgets.QProgressBar(self)
        # self.progressBar.setProperty("value", 0)
        # self.progressBar.setMaximum(101)
		
        # ### create button for mono homing procedure

        # self.homeButton = QtWidgets.QPushButton(self)
        # self.homeButton.setObjectName("homeButton")
        # self.homeButton.clicked.connect(lambda: Mono1.getHomePosition())
        # self.homeButton.setText("HOME Monochromator")

        ### create exposure time input
        self.exposureTimeInput = QtWidgets.QLineEdit(self)
        self.exposureTimeInput.setMaxLength(5)
        self.exposureTimeInput.setInputMask("999.9")
        self.exposureTimeInput.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.exposureTimeInput.textChanged.emit(self.exposureTimeInput.text())

        ### create button to change exposure time
        self.expButton = QtWidgets.QPushButton(self)
        self.expButton.setObjectName("expButton")
        self.expButton.clicked.connect(lambda: cam.set_attribute_value("Exposure Time", float(self.exposureTimeInput.text())))
        self.expButton.setText("Send exposure time (s)")


        
        
        ### create picture button
        self.camButton = QtWidgets.QPushButton(self)
        self.camButton.setObjectName("camButton")
        self.camButton.clicked.connect(lambda: takeSnapShot(self.fname, self.pos))
        self.camButton.setText("Take a picture")

        ### create input for mono position
        self.pos = QtWidgets.QLineEdit(self)
        self.pos.setMaxLength(5)
        self.pos.setInputMask("999.9")
        self.pos.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.pos.textChanged.emit(self.pos.text())

        ### create label for current camera temp
        self.camTempLabel = QtWidgets.QLabel(self)
        self.camTempLabel.setAlignment(QtCore.Qt.AlignRight)
        self.camTempLabel.setText(str(cam.get_attribute_value('Sensor Temperature Reading')) + " C")

        ### create start input
        self.startInput = QtWidgets.QLineEdit(self)
        self.startInput.setMaxLength(5)
        self.startInput.setInputMask("999.9")
        self.startInput.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.startInput.textChanged.emit(self.startInput.text())

        ### create stop input
        self.stopInput = QtWidgets.QLineEdit(self)
        self.stopInput.setMaxLength(5)
        self.stopInput.setInputMask("999.9")
        self.stopInput.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.stopInput.textChanged.emit(self.stopInput.text())

        ### create file name input
        self.fname = QtWidgets.QLineEdit(self)
        self.fname.setMaxLength(50)
        #self.fname.setInputMask("Nxxxxxxxxxxxxxxxxxxxxxx")
        self.fname.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.fname.textChanged.emit(self.fname.text())

        ### create take spectrum button
        self.ramanButton = QtWidgets.QPushButton(self)
        self.ramanButton.setObjectName("ramanButton")
        self.ramanButton.clicked.connect(lambda: takeSpectrum(self.startInput.text(), self.stopInput.text(), self.fname.text()))
        self.ramanButton.setText("Take Raman spectrum")
      
        ### put widgets into the QFormLayout of tab1

        # # p1_vertical.addRow("Solvent:", self.combo)
        # p1_vertical.addRow("Current Laser Wavelength:", self.currentLaserWavelengthInput)
        # p1_vertical.addRow("Current Mono Wavelength:", self.currentMonoWavelengthLabel)
        # p1_vertical.addRow("Approach Mono Wavelength:", self.approachWavelengthInput)
        # p1_vertical.addRow(self.progressBar, self.approachButton)
        # p1_vertical.addRow("Move to 524.9 nm:", self.homeButton)

        ### put widgets into the QFormLayout of tab2
		
        # p2_vertical.addRow("Move to 524.9 nm:", self.homeButton)
        p2_vertical.addRow("Current temp", self.camTempLabel)
        p2_vertical.addRow("Exposure time (s)", self.exposureTimeInput)
        p2_vertical.addRow(self.expButton)
        p2_vertical.addRow('File name', self.fname)
        p2_vertical.addRow("Mono position", self.pos)
        p2_vertical.addRow("Take and save current frame", self.camButton)

        ### put widgets into the QFormLayout of tab3 
        #p3_vertical.addRow("file name", self.fname)
        p3_vertical.addRow("Scan Start (cm^-1)", self.startInput)
        p3_vertical.addRow("Scan Stop (cm^-1)", self.stopInput)
        p3_vertical.addRow(self.ramanButton)
        ### set window title and add tab widget to main window

        self.setWindowTitle("Raman control")
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(tab_widget)
        self.setLayout(vbox) 

    def getWavenumber(self, laserWL, monoWL):
        if(monoWL != "."):
            wavenumber = abs((1/float(laserWL)) - (1/float(monoWL)))*10000000
            return int(round(wavenumber,0))
        
def main(): 
    app = QtWidgets.QApplication(sys.argv)
    pixmap = QtGui.QPixmap('icon.png')
    splash = QtWidgets.QSplashScreen(pixmap)
    splash.show()
    # Mono1 = Monochromator()
    # print("Initializing communication with Monochromator controller...")
    PrincetonInstruments.list_cameras()
    cam = PrincetonInstruments.PicamCamera()
    # Mono1.sendcommand(' ')  
    app.processEvents()
    Interface = Ui_Form(cam)
    Interface.show()
    Interface.setFixedSize(Interface.size())
    splash.finish(Interface)
    app.setWindowIcon(QtGui.QIcon('icon.png'))
    app.exec_()

if __name__ == "__main__":
    main()
