# -*- coding: utf-8 -*-
"""
Package Observatory module instruments

Monitor and control of commercial instruments
"""
from Electronics.Interfaces.GPIB import Gpib
from Electronics.Interfaces.GPIB.devices import pm

import re
from time import sleep, ctime, time
import numpy as NP
import logging

module_logger = logging.getLogger(__name__)


class SG(Gpib):
  """  
  GPIB controlled signal generator SG8673G
  
  This class defines the signal generator functions as follows::
   1. Initialises signal generator- Reset it to default; clear event registers
   2. Reports status- IDN, FRQ, RF status, AMPL
   3. Switch RF power ON/OFF
   4. Set Frequency
   5. Set Amplitude 
  
  Public Attributes
  =================
  ID - identification
"""
  def __init__(self, ID):
    Gpib.__init__(self, ID)
    self.ID = ID
    #self.init()
    
  def init(self):
    """
    Initialize the sig gen to default settings:
     - Reset the signal generator to a default state
     - Clear status and event registers
    """
    self.clear()
    #self.write("*RST")
    #Wait for 2 sec before passing next command
    #sleep(2)
    #self.write("*CLS")
    print "Signal Generator has been reset"

  # Turn RF ON
  def power_on(self):
    self.write(":RF1")
    print "RF turned ON"
  
  #Turn RF OFF
  def power_off(self):
    self.write(":RF0")
    print "RF turned OFF"

  # Set Frequency
  def set_freq(self,freq):
    # Frequency between 2.0 to 26.0 GHz in either MHz, KHz or Hz
    self.write("FREQ:CW "+ str(freq) +" HZ")
    print "Frequency set to ", freq     
 
  #Set Amplitude
  def set_ampl(self,num):
    #WARNING: Enter Amplitude in dBm only and not more that "0dBm" !!!
    self.write("POW:AMPL "+ str(num) +" DBM")
    print "Amplitude set to ", num, "dBm" 

  #Get the device identification, FRQ, RF status, AMPL
  def get_status(self):
    try:
      #Wait 1 sec between each command
      sleep(1)
      # Query commands in this section are not functioning.
      # Need to look for the right GPIB commands.
      self.write("*IDN?")
      print "SigGen", self.read(), "identified" 
    except:
      print "SigGen",self.ID,"identification failed"
      return None
    
    try:
      sleep(1)
      self.write("OUTP:STAT?")
      print "RF is", self.read()
    except:
      print "RF status request failed"
      return None
    
    try:
      sleep(1)
      self.write("FREQ:CW?")
      print "Sig Gen frequency is set to", self.read()
    except:
      print "Sig Gen frequency request failed"
      return None
    
    try:
      sleep(1)
      self.write("POW:AMPL?")
      print "Amplitude is set to", self.read()
    except:
      print "Sig Gen amplitude request failed"
      return None
    
 
