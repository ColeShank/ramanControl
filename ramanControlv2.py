'''

To Do: 
-add spectrum time calc (maybe just a rough: number of chunks * (10s + exposure time))
-live data collection
-error handling for wrong inputs
-make it so files don't overwrite, rather append _2, _3, ...
    - currently crashes if file already exists
-Clean up when core functions are solid
-Add button to display python code (and any other relevant files, e.g. 'mono.cfg') (?)
-Package exe with the necessary files (there's only a couple)
-


Known Issues:
-Homing doesn't always work, idk why :(



For the next editor:
-Paths are specific to nickp user and the raman system in the corner
-




'''

## imports
import sys
#sys.path.append('C:/Users/nickp/anaconda3/') #maybe unnecessary?
import os
from datetime import date
import logging, configparser, time, serial
import datetime as dt
from PyQt5 import QtGui, QtCore, QtWidgets
import PyQt5.QtWidgets as QWidgets
from tkinter.filedialog import askdirectory
import pylablib as pll
pll.par["devices/dlls/picam"] = "path/to/dlls"
from pylablib.devices import PrincetonInstruments
#PrincetonInstruments.list_cameras()
cam = PrincetonInstruments.PicamCamera()   
import matplotlib.pyplot as plt
import numpy as np
import ctypes
myappid = 'reznik.ramanControl.tony.01' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
plt.ion()

'''
## Does this work????
'''
global laser
laser = 1

def laserUpdate(wavl):
    laser = float(wavl)

'''
These conversion functions show up like 3-4 times in different ways
It would be good to condense to use common variables (from GUI) and remove redundancy
'''

def wavToNM(wavn):
    # converts shift "wavn" [1/cm] to nm
    nm = 1/(1/float(laser) - float(wavn)/float(1e+7))
    return nm

def nmToWav(wavl):
    # calculates shift "wav" [1/cm] 
    wav = (1/float(laser) - 1/float(wavl))*float(1e+7)
    return wav

def takeSnapShot(fname, pos):
    img = cam.snap()
    
    global signal
    signal = []
    pixel = range(len(img[0]))
    '''
    Are the next two lines redundant with the for loop later?
    '''
    for i in range(len(img[0])):
        signal.append(sum(img[:, i]))

    global data
    global wavelen
    global wavenum
    wavelen =[]
    wavenum = []
    data = []
    
    pxc = 670.5 # center pixel
    deltaL = 16.708 # nm range over the 1340 pixel wide detector
    pixel = range(0,1340)
    for i in range(0,1340):
        wav = pos - (deltaL/1340)*(pixel[i]-pxc)
        wavNum = nmToWav(wav)
        signal = sum(img[:, i])
        wavelen.append(wav)
        wavenum.append(wavNum)
        data.append(signal)
        
    plt.plot(wavenum, data)
    plt.show()
    autoSave()    
    return signal


def takeSnapShot2D(fname, pos):
    # pos is spectrometer position
    img = cam.snap()
    plt.imshow(img,aspect='auto')
    
    global signal
    signal = []
    
    global data
    ## this may or may not be the most sensible way to package the data into a 1D array
    ## in MATLAB, this requires a reshape and a rotate to display the proper orientation
    ## which doesn't seem the most ideal
    img1D = img.reshape(-1)
    data = img1D.tolist()

    pixel = range(len(img[0]))
    '''
    Are the next two lines redundant with the for loop later?
    '''
    for i in range(len(img[0])):
        signal.append(sum(img[:, i]))

    global wavelen
    global wavenum
    wavelen =[]
    wavenum = []
    pxc = 670.5 # center pixel
    deltaL = 16.708 # nm range over the 1340 pixel wide detector
    pixel = range(0,1340)
    for i in range(0,1340):
        wav = pos - (deltaL/1340)*(pixel[i]-pxc)
        wavNum = nmToWav(wav)
        signal = sum(img[:, i])
        wavelen.append(wav)
        wavenum.append(wavNum)
    wavelen = wavelen * 100
    wavenum = wavenum * 100
    autoSave()
    return signal

def takeSpectrum(start, stop, fname):
    ## file handling
    #fpath = os.path.join(path, fname)
    #global file
    #file = open(fpath, 'w')
    #file.write('Wavelength(nm), Raman shift(cm^-1), Intensity(arb) \n')
    
    ## start by converting start and stop to nm
    nmStart = wavToNM(float(start))
    nmStop = wavToNM(float(stop))
    numSnaps = int(np.ceil(abs(nmStart - nmStop)/(15.8))) #number of detector width spectra required
    
    Window.statusBar().showMessage("Estimated time needed: "+str(0.5*float(stop)/1000 + 0.5*numSnaps)+" minutes.",10000)
    
    ## sleep for 1 minute to give time to leave the room
    time.sleep(60)

    global signal
    signal = []

    global data
    global wavelen
    global wavenum
    wavelen =[]
    wavenum = []
    data = []

    for pos in np.linspace(float(nmStart - 8.3 + 15.8*numSnaps), float(nmStart), numSnaps):  #this is giving weird gaps again (moving 17 nm/step)
        
        ## position is detector center
        pos = pos + 8.3
        Mono1.approachWL(float(pos))

        ## let detector discharge between measurements
        #time.sleep(20)
        img = cam.snap()

        pxc = 670.5 # center pixel
        deltaL = 16.708 # nm range over the 1340 pixel wide detector
        pixel = range(0,1340)
        for i in range(0,1340):
            wav = pos - (deltaL/1340)*(pixel[i]-pxc)
            wavNum = nmToWav(wav)
            signal = sum(img[:, i])
            wavelen.append(wav)
            wavenum.append(wavNum)
            data.append(signal)

    #for line in np.arange(len(data)):
    #    stringToWrite = str(wavelen[line])+','+str(wavenum[line])+','+str(data[line])+'\n'
    #    file.write(stringToWrite)  
    
    #file.close()
    #fpath_txt = os.path.join(path,fname+'.txt')
    #os.rename(fpath,fpath_txt)
    autoSave()
    print('Spectrum complete.')
    plt.plot(wavenum, data)
    plt.show()

def autoSave():
    now = dt.datetime.now()
    now_str = now.strftime('%y%m%d%H%M%S')
    tempname = 'Raman_'+now_str
    autopath = os.path.join('C:/Users/nickp/Documents/Raman data files',str(tempname))
    file = open(autopath,'w')
    for line in np.arange(len(data)):
        stringToWrite = str(wavelen[line])+','+str(wavenum[line])+','+str(data[line])+'\n' 
        file.write(stringToWrite)    
    file.close()
    autopath_txt = os.path.join(autopath+'.txt')
    os.rename(autopath,autopath_txt)

def saveData(fname):
    fpath = os.path.join(path,fname)
    file = open(fpath,'w')
    file.write('Wavelength(nm), Raman shift(cm^-1), Intensity(arb) \n')
    for line in np.arange(len(data)):
        stringToWrite = str(wavelen[line])+','+str(wavenum[line])+','+str(data[line])+'\n' 
        file.write(stringToWrite)    
    file.close()
    fpath_txt = os.path.join(path,fname+'.txt')
    os.rename(fpath,fpath_txt)

class Monochromator(object):
    ## Initializes a serial port
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

    ## sends ascii commands to the serial port and pauses for half a second afterwards
    def sendcommand(self,command):
        self.mono.flushInput()
        self.mono.flushOutput()
        if (command != "^"):
            print('Send command: ' + command)
        #logging.debug('Send command: ' + command)
        self.mono.write(bytearray(command + '\r\n','ascii'))
        time.sleep(0.5) 
        
    ## reads ascii text from serial port + formatting
    def readout(self):
        #time.sleep(0.5)
        #self.mono.flushInput()
        value = self.mono.readline().decode("utf-8")
        return str(value.rstrip().lstrip())
        
    ## sets the ramp speed
    def setRampspeed(self, rampspeed):
        self.sendcommand('K ' + str(rampspeed))
        
    ## sets the initial velocity
    def setInitialVelocity(self,initspeed): 
        self.sendcommand('I ' + str(initspeed))
        
    ## sets the velocity   
    def setVelocity(self,velocity):
        self.sendcommand('V ' + str(velocity))
        
    ## checks if the Monochromator is moving (returns True or False) 
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
        print("HOME Status: " + value[3:])
        return str(value[3:].rstrip().lstrip())
		
    def getHomePosition(self): 

        ## This function performs the homing procedure of the monochromator
        ## See the mono manual for information about the separate parameters
        
        ## This doesn't work reliably for some reason
        
        self.approachWL(float(435))
        
        
        while(self.moving()):
            self.moving()

        ## begin homing procedure

        self.sendcommand("A8")
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
        #Window.approachButton.setEnabled(False)
        if isinstance(approach_wavelength, float):
            print("Wavelength to approach: " + str(approach_wavelength) + " nm")
            nm_difference = float(approach_wavelength) - float(self.current_wavelength)
            print("Difference in nm: " + str(nm_difference))
            step_difference = round(((float(nm_difference) / float(self.nm_per_revolution)) * float(self.steps_per_revolution))+ float(self.offset))
            print("Difference in steps: " + str(step_difference))
            time_needed_sec = abs(step_difference / int(self.speed)) + abs(int(self.offset)/int(self.approach_speed))
            print("Time needed for operation: " + str(time_needed_sec) + " s")
            Window.statusBar().showMessage("Moving monochromator . . .  (est. "+str(time_needed_sec)+" seconds)",3000)
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
                    Window.currentMonoWavelengthLabel.setText(str(round(self.current_wavelength,2)) + " nm")
                    f = open('mono.cfg',"w")
                    self.config.write(f)
                    break
        else:
            print("Input is not numeric")
            MessageBox = QtGui.QMessageBox.warning(Window,"Error:","Input is not numeric") 
            #Window.approachButton.setEnabled(True)
    ''' Deprecated
    ## Does this go here???? Unclear why it is here, maybe can be replaced/deleted/combined with the other function which does the same thing
    def getWavenumber(laserWL, monoWL):
        if(monoWL != "."):
            wavenumber = abs((1/float(laserWL)) - (1/float(monoWL)))*float(1e+7)
        return int(round(wavenumber,0))
    '''    
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
        
        
        ## update loop for CCD temperature
        self.update_timer = QtCore.QTimer(self)
        self.update_timer.start()
        self.update_timer.setInterval(1000) # milliseconds
        self.update_timer.setSingleShot(False)
        self.update_timer.timeout.connect(lambda: self.camTempLabel.setText(str(cam.get_attribute_value('Sensor Temperature Reading')) + " C"))
        
        
        ## create input field for current laser wavelength for Raman peak calculations
        self.currentLaserWavelengthInput = QWidgets.QLineEdit(self)
        self.currentLaserWavelengthInput.setMaxLength(3)
        self.currentLaserWavelengthInput.setInputMask("999")
        self.currentLaserWavelengthInput.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.currentLaserWavelengthInput.textChanged.connect(lambda: laserUpdate(self.currentLaserWavelengthInput.text()))

        ## create header for calibration
        self.calHeader = QWidgets.QLabel(self)
        self.calHeader.setText("Calibrate Monochromator Position")
        self.calHeader.setStyleSheet("font-weight: bold")

        ## create input field for counter
        self.currentCounterInput = QWidgets.QLineEdit(self)
        self.currentCounterInput.setMaxLength(7)
        self.currentCounterInput.setInputMask("99999.9")
        self.currentCounterInput.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        
        ## create button to calibrate mono
        self.calButton = QWidgets.QPushButton(self)
        self.calButton.setObjectName("calButton")
        self.calButton.clicked.connect(lambda: self.calibrateMono())
        self.calButton.setText("Calibrate monochromator position")

        ## create label for current mono wavelength
        self.currentMonoWavelengthLabel = QWidgets.QLabel(self)
        self.currentMonoWavelengthLabel.setAlignment(QtCore.Qt.AlignRight)

        ## create header for moving mono
        self.moveHeader = QWidgets.QLabel(self)
        self.moveHeader.setText("Move Monochromator Position")
        self.moveHeader.setStyleSheet("font-weight: bold")

        ## create input field for wavelength to approach
        self.approachWavelengthInput = QWidgets.QLineEdit(self)
        self.approachWavelengthInput.setMaxLength(5)
        self.approachWavelengthInput.setInputMask("999.9")
        self.approachWavelengthInput.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.approachWavelengthInput.textChanged.emit(self.approachWavelengthInput.text())

        ## create button to start the mono movement
        self.approachButton = QWidgets.QPushButton(self)
        self.approachButton.setObjectName("approachButton")
        self.approachButton.clicked.connect(lambda: Mono1.approachWL(float(self.approachWavelengthInput.text())))
        self.approachButton.setText("Approach")

		## create progress bar for mono movement progress indication
        self.progressBar = QWidgets.QProgressBar(self)
        self.progressBar.setProperty("value", 0)
        self.progressBar.setMaximum(101)
		
        ## create button for mono homing procedure
        self.homeButton = QWidgets.QPushButton(self)
        self.homeButton.setObjectName("homeButton")
        self.homeButton.clicked.connect(lambda: Mono1.getHomePosition())
        self.homeButton.clicked.connect(lambda: self.statusBar().showMessage("Homing monochromator . . . ",10000))
        self.homeButton.setText("HOME Monochromator")


        ## create header for CCD settings
        self.ccdHeader = QWidgets.QLabel(self)
        self.ccdHeader.setText("CCD Settings")
        self.ccdHeader.setStyleSheet("font-weight: bold")

        ## create label for current camera temp
        self.camTempLabel = QWidgets.QLabel(self)
        self.camTempLabel.setAlignment(QtCore.Qt.AlignRight)
        self.camTempLabel.setText(str(cam.get_attribute_value('Sensor Temperature Reading')) + " C")
        
        ## create button for CCD calibration
        self.ccdCalButton = QWidgets.QPushButton(self)
        self.ccdCalButton.setObjectName("ccdCalButton")
        self.ccdCalButton.clicked.connect(lambda: self.calibrateCCD())
        self.ccdCalButton.setText("Calibrate")

        ## create exposure time input
        self.exposureTimeInput = QWidgets.QLineEdit(self)
        self.exposureTimeInput.setMaxLength(7)
        self.exposureTimeInput.setInputMask("9999.99")
        self.exposureTimeInput.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.exposureTimeInput.textChanged.emit(self.exposureTimeInput.text())
        self.exposureTimeInput.textChanged.connect(lambda: cam.set_attribute_value("Exposure Time", float(self.exposureTimeInput.text())))

        ''' Deprecated
        ## create button to change exposure time
        self.expButton = QWidgets.QPushButton(self)
        self.expButton.setObjectName("expButton")
        self.expButton.clicked.connect(lambda: cam.set_attribute_value("Exposure Time", float(self.exposureTimeInput.text())))
        self.expButton.clicked.connect(lambda: self.statusBar().showMessage("Exposure time set to "+str(float(self.exposureTimeInput.text()))+" seconds.",3000))
        self.expButton.setText("Send exposure time (s)")
        '''

        ## create header for snapshot
        self.snapshotHeader = QWidgets.QLabel(self)
        self.snapshotHeader.setText("Snapshot (does not save automatically)")
        self.snapshotHeader.setStyleSheet("font-weight: bold")


        ## create picture button
        self.camButton = QWidgets.QPushButton(self)
        self.camButton.setObjectName("camButton")
        self.camButton.clicked.connect(lambda: takeSnapShot(str(self.fname.text()), float(Mono1.current_wavelength)))
        self.camButton.clicked.connect(lambda: self.statusBar().showMessage("Picture taken",3000))
        self.camButton.setText("Take 1D spectrum")

        ## create 2D button
        self.camButton2D = QWidgets.QPushButton(self)
        self.camButton2D.setObjectName("camButton2D")
        self.camButton2D.clicked.connect(lambda: takeSnapShot2D(str(self.fname.text()), float(Mono1.current_wavelength)))
        self.camButton2D.setText("Take 2D image")
        
        ## create header for Raman
        self.ramanHeader = QWidgets.QLabel(self)
        self.ramanHeader.setText("Raman Spectrum (saves automatically)")
        self.ramanHeader.setStyleSheet("font-weight: bold")
        
        ## create start input
        self.startInput = QWidgets.QLineEdit(self)
        self.startInput.setMaxLength(4)
        self.startInput.setInputMask("9999")
        self.startInput.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.startInput.textChanged.emit(self.startInput.text())

        ## create stop input
        self.stopInput = QWidgets.QLineEdit(self)
        self.stopInput.setMaxLength(4)
        self.stopInput.setInputMask("9999")
        self.stopInput.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.stopInput.textChanged.emit(self.stopInput.text())

        ## create take spectrum button
        self.ramanButton = QWidgets.QPushButton(self)
        self.ramanButton.setObjectName("ramanButton")
        self.ramanButton.clicked.connect(lambda: self.statusBar().showMessage("Pausing for 60 seconds before collection . . . ",50000))
        self.ramanButton.clicked.connect(lambda: takeSpectrum(self.startInput.text(), self.stopInput.text(), self.fname.text()))
        self.ramanButton.setText("Take Raman spectrum")
      
        
        ## create label for current directory
        self.currentDir = QWidgets.QLabel(self)
        self.currentDir.setAlignment(QtCore.Qt.AlignRight)
        
        ## create directory button
        self.dirButton = QWidgets.QPushButton(self)
        self.dirButton.setObjectName("dirButton")
        self.dirButton.clicked.connect(lambda: self.currentDir.setText(askdirectory(title='Select folder')))
        self.dirButton.clicked.connect(lambda: self.pathUpdate())
        self.dirButton.setText("...")
     
        ## create file name input
        self.fname = QWidgets.QLineEdit(self)
        self.fname.setMaxLength(50)
        self.fname.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.fname.textChanged.emit(self.fname.text())

        ## create save file button
        self.saveButton = QWidgets.QPushButton(self)
        self.saveButton.setObjectName("saveButton")
        self.saveButton.clicked.connect(lambda: saveData(self.fname.text()))
        self.saveButton.setText("Save most recent data")
        
     
        ## create excitation wavelength input
        self.shiftExcitationInput = QWidgets.QLineEdit(self)
        self.shiftExcitationInput.setMaxLength(3)
        self.shiftExcitationInput.setInputMask("999")
        self.shiftExcitationInput.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        
        ## create header for wavenumber shift
        self.shiftWNHeader = QWidgets.QLabel(self)
        self.shiftWNHeader.setText("Enter Wavelength")
        self.shiftWNHeader.setStyleSheet("font-weight: bold")
        
        ## create response wavelength input
        self.shiftResponseInput = QWidgets.QLineEdit(self)
        self.shiftResponseInput.setMaxLength(6)
        self.shiftResponseInput.setInputMask("999.99")
        self.shiftResponseInput.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.shiftResponseInput.textChanged.connect(lambda: self.calculateShift())

        
        ## create shift wavenumber label
        self.shiftWN = QWidgets.QLabel(self)
        self.shiftWN.setText("0")     

        ## create header for wavelength shift
        self.shiftNMHeader = QWidgets.QLabel(self)
        self.shiftNMHeader.setText("Or, Enter Shift")
        self.shiftNMHeader.setStyleSheet("font-weight: bold")
        
        ## create shift input
        self.shiftInputWN = QWidgets.QLineEdit(self)
        self.shiftInputWN.setObjectName("shiftInputWN")
        self.shiftInputWN.setMaxLength(4)
        self.shiftInputWN.setInputMask("9999")
        self.shiftInputWN.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.shiftInputWN.textChanged.connect(lambda: self.calculateShift())

        
        ## create absolute nm label
        self.absoluteShift = QWidgets.QLabel(self)
        self.absoluteShift.setObjectName("absoluteShift")
        
        ## create relative nm label
        self.relativeShift = QWidgets.QLabel(self)
        self.relativeShift.setObjectName("relativeShift")
        
        ''' Deprecated
        ## create shift calculation button
        self.shiftButton = QWidgets.QPushButton(self)
        self.shiftButton.setObjectName("shiftButton")
        self.shiftButton.clicked.connect(lambda: self.calculateShift())
        self.shiftButton.setText("Calculate Shift")
        '''
        
        ## put widgets into the QFormLayout of tab1
        p1_vertical.addRow("Current Laser Wavelength (nm):", self.currentLaserWavelengthInput)
        p1_vertical.addRow(self.calHeader)
        p1_vertical.addRow("Calibration, enter current counter setting", self.currentCounterInput)
        p1_vertical.addRow(self.calButton)
        p1_vertical.addRow("Current Mono Wavelength:", self.currentMonoWavelengthLabel)
        p1_vertical.addRow(self.moveHeader)
        p1_vertical.addRow("Approach Mono Wavelength:", self.approachWavelengthInput)
        p1_vertical.addRow(self.progressBar, self.approachButton)
        #p1_vertical.addRow("Home counter location: 660.1", self.homeButton) # Doesnt work RIP

        ## put widgets into the QFormLayout of tab2
        p2_vertical.addRow(self.ccdHeader)
        p2_vertical.addRow("Current temp", self.camTempLabel)
        p2_vertical.addRow("Calibrate CCD", self.ccdCalButton)
        p2_vertical.addRow("Exposure time (s)", self.exposureTimeInput)
        #p2_vertical.addRow(self.expButton)
        p2_vertical.addRow(self.snapshotHeader)
        p2_vertical.addRow("Take 1D snapshot", self.camButton)
        p2_vertical.addRow("Take 2D snapshot", self.camButton2D)
        p2_vertical.addRow(self.ramanHeader)
        p2_vertical.addRow("Scan Start (1/cm)", self.startInput)
        p2_vertical.addRow("Scan Stop (1/cm)", self.stopInput)
        p2_vertical.addRow(self.ramanButton)
        #p2_vertical.addRow(self.testButton)

        ## put widgets into the QFormLayout of tab3
        p3_vertical.addRow("Active folder:", self.currentDir)
        p3_vertical.addRow("Select new folder:", self.dirButton)
        p3_vertical.addRow("File name", self.fname)
        p3_vertical.addRow(self.saveButton)
        
        ## put widgets into the QFormLayout of tab4
        p4_vertical.addRow("Excitation Wavelength (nm):", self.shiftExcitationInput)
        p4_vertical.addRow(self.shiftWNHeader)
        p4_vertical.addRow("Response Wavelength (nm):", self.shiftResponseInput)
        p4_vertical.addRow("Raman Shift (1/cm):", self.shiftWN)
        p4_vertical.addRow(self.shiftNMHeader)
        p4_vertical.addRow("Raman shift (1/cm):", self.shiftInputWN)
        p4_vertical.addRow("Absolute wavelength (nm):", self.absoluteShift)
        p4_vertical.addRow("Relative wavelength (nm):", self.relativeShift)
        #p4_vertical.addRow(self.shiftButton)
        

        ## set window title and add tab widget to main window
        self.setWindowTitle("Raman control")
        self.setCentralWidget(tab_widget)
      
      
    def calibrateMono(self):
        if self.currentCounterInput.text() == '.':
            self.statusBar().showMessage("Error: no counter value input",3000)
        else:
            calWL = round((0.1)*(2/3)*float(self.currentCounterInput.text()),1)
            self.config = configparser.RawConfigParser()
            self.config.read('mono.cfg')
            self.config.set('Mono_settings', 'current_wavelength', str(calWL))
            f = open('mono.cfg',"w")
            self.config.write(f)
            self.currentMonoWavelengthLabel.setText(str(calWL))
            Mono1.current_wavelength = str(calWL)
            self.currentCounterInput.clear()
            
    def calibrateCCD(self):
        ## set a very short exposure time to ensure CCD isnt blown out
        cam.set_attribute_value("Exposure Time", float(0.01))
        
        ## place laser on high end of detector range and take image
        Mono1.approachWL(float(537))
        img1 = cam.snap()
        signal1 = []
        pixel = range(1340)
        for i in range(1340):
            signal1.append(sum(img1[:, i]))
        max1 = max(signal1)
        px1 = signal1.index(max1)
        
        ## place laser on low end of detector range and take image
        Mono1.approachWL(float(527))
        img2 = cam.snap()
        signal2 = []
        pixel = range(1340)
        for i in range(1340):
            signal2.append(sum(img2[:,i]))
        max2 = max(signal2)
        px2 = signal2.index(max2)
        
        ## calculate nm/px and center detector at laser line
        global nm_per_px
        nm_per_px = 10/(px1 - px2)
        print("nm per px: "+str(nm_per_px))

        px_offset = 670.5 - px2
        nm_offset = px_offset*nm_per_px
        calWL = float(527 + nm_offset)
        print(px_offset)
        print(nm_offset)
        Mono1.approachWL(calWL)

        self.config = configparser.RawConfigParser()
        self.config.read('mono.cfg')
        self.config.set('Mono_settings', 'current_wavelength', '532')
        f = open('mono.cfg',"w")
        self.config.write(f)
        self.currentMonoWavelengthLabel.setText('532.0')
        Mono1.current_wavelength = "532"
        
        ## take and save image to verify calibration
        takeSnapShot('cal_temp',532)
        
        now = dt.datetime.now()
        now_str = now.strftime('%y%m%d%H%M%S')
        tempname = 'Cal_'+now_str
        autopath = os.path.join('C:/Users/nickp/Documents/Raman calibration files',str(tempname))
        file = open(autopath,'w')
        for line in np.arange(len(data)):
            stringToWrite = str(wavelen[line])+','+str(wavenum[line])+','+str(data[line])+'\n' 
            file.write(stringToWrite)    
        file.close()
        autopath_txt = os.path.join(autopath+'.txt')
        os.rename(autopath,autopath_txt)
        
    def closeEvent(self,event):
        ## disconnects from instruments when X button is clicked
        Mono1.disconnect()
        print("Terminated connection with monochromator.")
        cam.close()
        print("Disconnected from camera.")
        event.accept()
        sys.exit(0)
        
    def initialize(self):
        ## pre-fills some data with standard values
        laserUpdate(532)
        self.currentLaserWavelengthInput.setText("532")
        self.exposureTimeInput.setText("0.1")
        cam.set_attribute_value("Exposure Time", float(self.exposureTimeInput.text()))
        self.currentDir.setText('C:/')
        global path
        path = os.path.join(self.currentDir.text())
        self.shiftExcitationInput.setText("532")
        
    def pathUpdate(self):
        global path
        path = os.path.join(self.currentDir.text())
        
    def calculateShift(self):
        if self.shiftResponseInput.text()+self.shiftInputWN.text() == '.':
            self.statusBar().showMessage("Error: must enter at least one input",2000)
            
        elif self.shiftResponseInput.text() == '.':
            nm = round(1/(1/float(self.shiftExcitationInput.text()) - float(self.shiftInputWN.text())/float(1e+7)),2)
            self.absoluteShift.setText(str(nm))
            self.relativeShift.setText(str(round(nm - float(self.shiftExcitationInput.text()),2)))
            
        elif self.shiftInputWN.text() == '':
            wav=round(((1/float(self.shiftExcitationInput.text()) - 1/float(self.shiftResponseInput.text()))*float(1e+7)),2)
            self.shiftWN.setText(str(wav))
            
        else:       
            wav=round(((1/float(self.shiftExcitationInput.text()) - 1/float(self.shiftResponseInput.text()))*float(1e+7)),2)
            self.shiftWN.setText(str(wav))
            nm = round(1/(1/float(self.shiftExcitationInput.text()) - float(self.shiftInputWN.text())/float(1e+7)),2)
            self.absoluteShift.setText(str(nm))
            self.relativeShift.setText(str(round(nm - float(self.shiftExcitationInput.text()),2)))


def main():        
    app = QWidgets.QApplication(sys.argv)
    pixmap = QtGui.QPixmap('icon.png')
    splash = QWidgets.QSplashScreen(pixmap)
    splash.show()
    print("Connecting to monochromator ...")
    global Mono1
    Mono1 = Monochromator()
    Mono1.sendcommand(' ')  
    app.processEvents()
    global Window
    Window = MainWindow()
    Window.resize(400,400)
    Window.show()
    Window.initialize()
    app.setWindowIcon(QtGui.QIcon('icon.png'))
    splash.finish(Window)
    #global laser
    #laser = float(Window.currentLaserWavelengthInput.text())
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()