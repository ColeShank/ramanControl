'''
To Do: 

!!!!!!monochromator is incorrect lmao how did you even do that
-add actual raman mode lol
-add video mode
-add spectrum time calc
-error handling for wrong inputs
-fix ROI bug to remove stupid for loops
-make it so files don't overwrite, rather append _2, _3, ...
-add 2D camera mode
-Add fine calibration mode (popup: warning only perform with laser attenuated by ND wheel)
-Add sections ideally




Known Issues:

-mono control freq loses communication. needs current pos in file to match current position 
-usually fails if commercial softaware is used


Questions and Notes and Such:



'''

# imports
import sys
sys.path.append('C:/Users/nickp/anaconda3/')
import os
from datetime import date
import logging, configparser, time, serial
import datetime as dt
from PyQt5 import QtGui, QtCore, QtWidgets
import PyQt5.QtWidgets as QWidgets
#from tkinter import Tk
from tkinter.filedialog import askdirectory
# from picam import *
import pylablib as pll
pll.par["devices/dlls/picam"] = "path/to/dlls"
from pylablib.devices import PrincetonInstruments
#PrincetonInstruments.list_cameras()
cam = PrincetonInstruments.PicamCamera()   
import matplotlib.pyplot as plt
import numpy as np
import ctypes
myappid = 'reznik.ramanControl.steve.01' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

# global Mono1
# Mono1 = Monochromator()
# Mono1.sendcommand(' ')  

plt.ion()

# first, do some house keeping
# prompt the user for parent directory, then make folder with todays date
''' Deprecated
try: 
    parentDir = askdirectory(title='Select project folder') # shows dialog box and return the path
    dataDir = str(date.today())
    path = os.path.join(parentDir, dataDir)
    os.mkdir(path)
except FileExistsError:
    print('Using folder from earlier today')
'''

laser = 532# hard coded bullshit, fix

def wavNumToNM(wav):
    # converts shift "wav" [1/cm] to nm
    nm = 1/(1/float(laser) - float(wav)/float(1e+7))
    return nm

def nmToWav(laserWL, monoWL):
    # calculates shift "wav" [1/cm] 
    wav=(1/float(laserWL) - 1/float(monoWL))*float(1e+7)
    return wav

def takeSnapShot(fname, pos):
    # pos is spectrometer position
    img = cam.snap()
    
    global signal
    signal = []
    pixel = range(len(img[0]))
    # it would be so much better to use the ROI binning. something weird need to fix
    for i in range(len(img[0])):
        signal.append(sum(img[:, i]))

    plt.plot(pixel, signal)
    plt.show()
    
    global data
    global wavelen
    global wavNum
    wavelen =[]
    wavNum = []
    data = []
    px1 = 799 # center wavelength position
    px2 = 426 # high edge (7nm below)
    deltaL = 22
    pixel = range(0,1340)
    for i in range(400,1340): #SHOULD BE (0,1340)?
        wav = pos+ ((deltaL/(px2-px1))*(pixel[i]-px1))
        waveNum = 1/laser - 1/(wav*10**(-7))
        signal = sum(img[:, i])
        wavelen.append(wav)
        wavNum.append(waveNum)
        data.append(signal)
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
    file.write('Wavelength(nm), Raman shift(cm^-1), Intensity(arb) \n')
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
    for pos in np.arange(float(start), float(stop), 7):     # SPURIOUS 7
        # Mono1.approachWL(pos)
        img = cam.snap()
        #now figure out what the axis was 
        #yikes
        #remember pos is the detector center, not edge
        #all of this is hard coded but should be switched with a calibration process to do at the start of the day
        px1 = 799 # center wavelength position
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
            stringToWrite = str(wav)+','+str(waveNum)+','+str(signal)+'\n' 
            file.write(stringToWrite)
    file.close()
    fpath_txt=os.path.join(path,fname+'.txt')
    os.rename(fpath,fpath_txt)
    plt.plot(wavNum, data)
    plt.show()
    return signal

def saveData(fname):
    fpath = os.path.join(path,fname)
    file = open(fpath,'w')
    file.write('Wavelength(nm), Raman shift(cm^-1), Intensity(arb) \n')
    for line in np.arange(len(data)):
        stringToWrite = str(wavelen[line])+','+str(wavNum[line])+','+str(data[line])+'\n' 
        file.write(stringToWrite)    
    file.close()
    fpath_txt=os.path.join(path,fname+'.txt')
    os.rename(fpath,fpath_txt)
    

    

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
            print("Mono is moving \r")  #AWFUL SPAMMY
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
        print("HOME Status: " + value[3:])
        return str(value[3:].rstrip().lstrip())
		
    def getHomePosition(self): 

        ### This function performs the homing procedure of the monochromator
        ### See the mono manual for information about the separate parameters
        
        self.approachWL(float(435))
        
        
        while(self.moving()):
            self.moving()

        ### begin homing procedure

        self.sendcommand("A8")
        #self.checkHOMEstatus()
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
            self.config.set('Mono_settings', 'current_wavelength', '440.067')
            print("Homing done, setting current wavelength now to 440.067 nm (verify counter: 660.1)")
            f = open('mono.cfg',"w")
            self.config.write(f)
            Window.currentMonoWavelengthLabel.setText("440.067 nm")
		
    def approachWL(self, approach_wavelength):
        Window.approachButton.setEnabled(False)
        if isinstance(approach_wavelength, float):
            print("Wavelength to approach: " + str(approach_wavelength) + " nm")
            nm_difference = float(approach_wavelength) - float(self.current_wavelength)
            print("Difference in nm: " + str(nm_difference))
            step_difference = round(((float(nm_difference) / float(self.nm_per_revolution)) * float(self.steps_per_revolution))+ float(self.offset))
            print("Difference in steps: " + str(step_difference))  
            time_needed_sec = abs(step_difference / int(self.speed)) + abs(int(self.offset)/int(self.approach_speed))
            print("Time needed for operation: " + str(time_needed_sec) + " s")
            Window.statusBar().showMessage("Moving monochromator . . .  (est. "+str(time_needed_sec)+" seconds)",2000)
            #Window.timeNeeded = time_needed_sec
            time_delay_for_progressbar = time_needed_sec / 100
            self.sendcommand("V" + str(self.speed))
            self.sendcommand(str(format(step_difference, '+')))
            self.sendcommand("V" + str(self.approach_speed))
            self.sendcommand("-" + str(self.offset))
            while True:
                time.sleep(time_delay_for_progressbar)
                value = Window.progressBar.value() + 1
                Window.progressBar.setValue(value)
                QtWidgets.qApp.processEvents()
                if (value >= Window.progressBar.maximum()):
                    Window.approachButton.setEnabled(True)
                    Window.progressBar.setValue(0)
                    self.config.set('Mono_settings', 'current_wavelength', approach_wavelength)
                    self.config.set('Settings', 'laser_wavelength', self.current_laser_wavelength)
                    self.current_wavelength = approach_wavelength
                    Window.currentMonoWavelengthLabel.setText(str(self.current_wavelength) + " nm")
                    f = open('mono.cfg',"w")
                    self.config.write(f)
                    break
        else:
            print("Input is not numeric")
            MessageBox = QtGui.QMessageBox.warning(Window,"Error:","Input is not numeric") 
            Window.approachButton.setEnabled(True)
    
    ### Does this go here???? Unclear why it is here, maybe can be replaced/deleted/combined with the other function which does the same thing
    def getWavenumber(laserWL, monoWL):
        if(monoWL != "."):
            wavenumber = abs((1/float(laserWL)) - (1/float(monoWL)))*float(1e+7)
        return int(round(wavenumber,0))
        
    def disconnect(self):
        self.mono.flushInput()
        self.mono.flushOutput()
        self.mono.close()
   
 
        
class MainWindow(QWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        tab_widget = QWidgets.QTabWidget()
        tab1 = QWidgets.QWidget()
        tab2 = QWidgets.QWidget()
        tab3 = QWidgets.QWidget()
        tab4 = QWidgets.QWidget()
        p1_vertical = QWidgets.QFormLayout(tab1)
        p2_vertical = QWidgets.QFormLayout(tab2)
        p3_vertical = QWidgets.QFormLayout(tab3)
        p4_vertical = QWidgets.QFormLayout(tab4)
        tab_widget.addTab(tab1, "Spectrometer Control")
        tab_widget.addTab(tab2, "CCD Control") 
        tab_widget.addTab(tab3, "File Saving")
        tab_widget.addTab(tab4, "Shift Calculator")
        
        
        
        self.update_timer = QtCore.QTimer(self)
        self.update_timer.start()
        self.update_timer.setInterval(1000) # milliseconds
        self.update_timer.setSingleShot(False)
        self.update_timer.timeout.connect(lambda: self.camTempLabel.setText(str(cam.get_attribute_value('Sensor Temperature Reading')) + " C"))
        
        
        
        ### create input field for current laser wavelength for Raman peak calculations
        self.currentLaserWavelengthInput = QWidgets.QLineEdit(self)
        self.currentLaserWavelengthInput.setMaxLength(3)
        self.currentLaserWavelengthInput.setInputMask("999")
        self.currentLaserWavelengthInput.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        #self.currentLaserWavelengthInput.setText(Mono1.current_laser_wavelength + " nm")

        ### create header for calibration
        self.calHeader = QWidgets.QLabel(self)
        self.calHeader.setText("Calibrate Monochromator Position")
        self.calHeader.setStyleSheet("font-weight: bold")

        ### create input field for counter
        self.currentCounterInput = QWidgets.QLineEdit(self)
        #calWL = round((2/3)*float(self.currentCounterInput.text()),1)
        self.currentCounterInput.setMaxLength(6)
        self.currentCounterInput.setInputMask("9999.9")
        self.currentCounterInput.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        
        ### create button to calibrate mono
        self.calButton = QWidgets.QPushButton(self)
        self.calButton.setObjectName("calButton")
        self.calButton.clicked.connect(lambda: self.calibrate()) #ADD ERROR HANDLING FOR NULL INPUT
        self.calButton.clicked.connect(lambda: self.currentMonoWavelengthLabel.setText(str(round((2/3)*float(self.currentCounterInput.text()),1))))
        self.calButton.clicked.connect(lambda: self.currentCounterInput.clear())
        self.calButton.setText("Calibrate monochromator position")

        ### create header for moving mono
        self.moveHeader = QWidgets.QLabel(self)
        self.moveHeader.setText("Move Monochromator Position")
        self.moveHeader.setStyleSheet("font-weight: bold")
        
        ### create label for current mono wavelength
        self.currentMonoWavelengthLabel = QWidgets.QLabel(self)
        self.currentMonoWavelengthLabel.setAlignment(QtCore.Qt.AlignRight)
        #self.currentMonoWavelengthLabel.setText(Mono1.current_wavelength + " nm")

        ### create input field for wavelength to approach
        self.approachWavelengthInput = QWidgets.QLineEdit(self)
        self.approachWavelengthInput.setMaxLength(5)
        self.approachWavelengthInput.setInputMask("999.9")
        self.approachWavelengthInput.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        #self.approachWavelengthInput.textChanged.connect(self.check_state)
        self.approachWavelengthInput.textChanged.emit(self.approachWavelengthInput.text())

        ### create button to start the mono movement
        self.approachButton = QWidgets.QPushButton(self)
        self.approachButton.setObjectName("approachButton")
        self.approachButton.clicked.connect(lambda: Mono1.approachWL(float(self.approachWavelengthInput.text())))
        #self.approachButton.clicked.connect(lambda: self.statusBar().showMessage("Moving monochromator . . .  (est. "+str(self.timeNeeded)+" seconds)",2000))
        self.approachButton.setText("Approach")

		### create progress bar for mono movement progress indication
        self.progressBar = QWidgets.QProgressBar(self)
        self.progressBar.setProperty("value", 0)
        self.progressBar.setMaximum(101)
		
        ### create button for mono homing procedure
        self.homeButton = QWidgets.QPushButton(self)
        self.homeButton.setObjectName("homeButton")
        self.homeButton.clicked.connect(lambda: Mono1.getHomePosition())
        self.homeButton.clicked.connect(lambda: self.statusBar().showMessage("Homing monochromator . . .  (est. TIME minutes)",2000))
        self.homeButton.setText("HOME Monochromator")



        ### create header for CCD settings
        self.ccdHeader = QWidgets.QLabel(self)
        self.ccdHeader.setText("CCD Settings")
        self.ccdHeader.setStyleSheet("font-weight: bold")

        ### create label for current camera temp
        self.camTempLabel = QWidgets.QLabel(self)
        self.camTempLabel.setAlignment(QtCore.Qt.AlignRight)
        self.camTempLabel.setText(str(cam.get_attribute_value('Sensor Temperature Reading')) + " C")

        ### create exposure time input
        self.exposureTimeInput = QWidgets.QLineEdit(self)
        self.exposureTimeInput.setMaxLength(6)
        self.exposureTimeInput.setInputMask("999.99")
        self.exposureTimeInput.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.exposureTimeInput.textChanged.emit(self.exposureTimeInput.text())

        ### create button to change exposure time
        self.expButton = QWidgets.QPushButton(self)
        self.expButton.setObjectName("expButton")
        self.expButton.clicked.connect(lambda: cam.set_attribute_value("Exposure Time", float(self.exposureTimeInput.text())))
        self.expButton.clicked.connect(lambda: self.statusBar().showMessage("Exposure time set to "+str(float(self.exposureTimeInput.text()))+" seconds.",2000))
        self.expButton.setText("Send exposure time (s)")

        ### create header for snapshot
        self.snapshotHeader = QWidgets.QLabel(self)
        self.snapshotHeader.setText("Snapshot (does not save automatically)")
        self.snapshotHeader.setStyleSheet("font-weight: bold")


        ### create picture button
        self.camButton = QWidgets.QPushButton(self)
        self.camButton.setObjectName("camButton")
        self.camButton.clicked.connect(lambda: takeSnapShot(str(self.fname.text()), float(self.currentMonoWavelengthLabel.text())))
        self.camButton.clicked.connect(lambda: self.statusBar().showMessage("Picture taken",2000))
        self.camButton.setText("Take a picture")

        ''' Deprecated
        ### create input for mono position
        self.pos = QWidgets.QLineEdit(self)
        self.pos.setMaxLength(5)
        self.pos.setInputMask("999.9")
        self.pos.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.pos.textChanged.emit(self.pos.text())
        '''
        
        ### create header for Raman
        self.ramanHeader = QWidgets.QLabel(self)
        self.ramanHeader.setText("Raman Spectrum (saves automatically)")
        self.ramanHeader.setStyleSheet("font-weight: bold")
        
        ### create start input
        self.startInput = QWidgets.QLineEdit(self)
        self.startInput.setMaxLength(5)
        self.startInput.setInputMask("999.9")
        self.startInput.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.startInput.textChanged.emit(self.startInput.text())

        ### create stop input
        self.stopInput = QWidgets.QLineEdit(self)
        self.stopInput.setMaxLength(5)
        self.stopInput.setInputMask("999.9")
        self.stopInput.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.stopInput.textChanged.emit(self.stopInput.text())

        ### create take spectrum button
        self.ramanButton = QWidgets.QPushButton(self)
        self.ramanButton.setObjectName("ramanButton")
        self.ramanButton.clicked.connect(lambda: takeSpectrum(self.startInput.text(), self.stopInput.text(), self.fname.text()))
        self.ramanButton.clicked.connect(lambda: self.statusBar().showMessage("Pausing for 60 seconds before collection . . . ",60000))
        self.ramanButton.setText("Take Raman spectrum")
      
      
      
        ### create label for current directory
        self.currentDir = QWidgets.QLabel(self)
        self.currentDir.setAlignment(QtCore.Qt.AlignRight)
        
        ### create directory button
        self.dirButton = QWidgets.QPushButton(self)
        self.dirButton.setObjectName("dirButton")
        self.dirButton.clicked.connect(lambda: self.currentDir.setText(askdirectory(title='Select folder')))
        self.dirButton.clicked.connect(lambda: self.pathUpdate())
        #self.dirButton.clicked.connect(lambda: self.currentDir.show())
        #self.dirButton.clicked.connect(lambda: print(path))
        self.dirButton.setText("...")
     
        ### create file name input
        self.fname = QWidgets.QLineEdit(self)
        self.fname.setMaxLength(50)
        self.fname.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.fname.textChanged.emit(self.fname.text())

        ### create save file button
        self.saveButton = QWidgets.QPushButton(self)
        self.saveButton.setObjectName("saveButton")
        self.saveButton.clicked.connect(lambda: saveData(self.fname.text()))
        self.saveButton.setText("Save most recent data")
        
     
     
        ### create excitation wavelength input
        self.shiftExcitationInput = QWidgets.QLineEdit(self)
        self.shiftExcitationInput.setMaxLength(3)
        self.shiftExcitationInput.setInputMask("999")
        self.shiftExcitationInput.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)

        ### create response wavelength input
        self.shiftResponseInput = QWidgets.QLineEdit(self)
        self.shiftResponseInput.setMaxLength(3)
        self.shiftResponseInput.setInputMask("999")
        self.shiftResponseInput.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        
        ### create shift wavenumber label
        self.shiftWN = QWidgets.QLabel(self)
        self.shiftWN.setText("0")
        
        ### create shift calculation button
        self.shiftButton = QWidgets.QPushButton(self)
        self.shiftButton.setObjectName("shiftButton")
        self.shiftButton.clicked.connect(lambda: self.calculateShift())
        self.shiftButton.setText("Calculate Raman Shift")
        
        
        
        ### put widgets into the QFormLayout of tab1
        # # p1_vertical.addRow("Solvent:", self.combo)
        p1_vertical.addRow("Current Laser Wavelength:", self.currentLaserWavelengthInput)
        p1_vertical.addRow(self.calHeader)
        p1_vertical.addRow("Calibration, enter current counter setting", self.currentCounterInput)
        p1_vertical.addRow(self.calButton)
        p1_vertical.addRow(self.moveHeader)
        p1_vertical.addRow("Current Mono Wavelength:", self.currentMonoWavelengthLabel)
        p1_vertical.addRow("Approach Mono Wavelength:", self.approachWavelengthInput)
        p1_vertical.addRow(self.progressBar, self.approachButton)
        p1_vertical.addRow("Home counter location: 660.1", self.homeButton)

        ### put widgets into the QFormLayout of tab2
        p2_vertical.addRow(self.ccdHeader)
        p2_vertical.addRow("Current temp", self.camTempLabel)
        p2_vertical.addRow("Exposure time (s)", self.exposureTimeInput)
        p2_vertical.addRow(self.expButton)
        p2_vertical.addRow(self.snapshotHeader)
        p2_vertical.addRow("Take and save current frame", self.camButton)
        p2_vertical.addRow(self.ramanHeader)
        p2_vertical.addRow("Scan Start (1/cm)", self.startInput)
        p2_vertical.addRow("Scan Stop (1/cm)", self.stopInput)
        p2_vertical.addRow(self.ramanButton)

        ### put widgets into the QFormLayout of tab3
        p3_vertical.addRow("Active folder:", self.currentDir)
        p3_vertical.addRow("Select new folder:", self.dirButton)
        p3_vertical.addRow("File name", self.fname)
        p3_vertical.addRow(self.saveButton)
        
        ### put widgets into the QFormLayout of tab4
        p4_vertical.addRow("Excitation Wavelength (nm):", self.shiftExcitationInput)
        p4_vertical.addRow("Response Wavelength (nm):", self.shiftResponseInput)
        p4_vertical.addRow(self.shiftButton)
        p4_vertical.addRow("Raman Shift (1/cm):", self.shiftWN)

        ### set window title and add tab widget to main window
        self.setWindowTitle("Raman control")
        self.setCentralWidget(tab_widget)
     

    def calibrate(self):
        self.config = configparser.RawConfigParser()
        self.config.read('mono.cfg')
        self.config.set('Mono_settings', 'current_wavelength', str(round((2/3)*float(self.currentCounterInput.text()),1)))
        f = open('mono.cfg',"w")
        self.config.write(f)
        Mono1.current_wavelength = str(round((2/3)*float(self.currentCounterInput.text()),1))
    
    def closeEvent(self,event):
        Mono1.disconnect()
        print("Terminated connection with monochromator.")
        event.accept()
        sys.exit(0)
        
    def initialize(self):
        self.currentLaserWavelengthInput.setText("532")
        self.currentDir.setText('C:/')
        global path
        path = os.path.join(self.currentDir.text())
        
    def pathUpdate(self):
        global path
        path = os.path.join(self.currentDir.text())

    
def main():        
    app = QWidgets.QApplication(sys.argv)
    pixmap = QtGui.QPixmap('icon.png')
    splash = QWidgets.QSplashScreen(pixmap)
    splash.show()
    print("Connecting to monochromator ...")
    global Mono1
    Mono1 = Monochromator()
    Mono1.sendcommand(' ')  
    #PrincetonInstruments.list_cameras()
    #cam = PrincetonInstruments.PicamCamera()
    app.processEvents()
    global Window
    Window = MainWindow()
    Window.resize(400,400)
    Window.show()
    Window.initialize()
    app.setWindowIcon(QtGui.QIcon('icon.png'))
    splash.finish(Window)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
