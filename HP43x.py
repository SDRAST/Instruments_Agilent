"""
provides a class for HP436, HP437 and HP438 power meters

This needs to be subclassed to Electronics.Instruments.PowerMeter
"""

import logging
import re
import numpy as NP

from Electronics.Interfaces.GPIB import Gpib
from Electronics.Interfaces.GPIB.devices import pm

module_logger = logging.getLogger(__name__)


class PM(Gpib):
  """
  GPIB controlled power meter

  Public Attributes
  =================
  - ID -      name of power meter as in /etc/gpib.conf
  - pm_type - power meter model
  - mode -    data mode ( W | dBm | ? [rel] )

  If the power meter reports a filter in the 10-19 range, it means that the
  filter was auto-selected according to the power range.
  """
  # These are for the HP438
  response_time = {0:0.10, 1:0.15, 2:0.25, 3:1.00, 4:1.40, 5:2.20,
                   6:3.70, 7:6.90, 8:14.0, 9:27.0} # keyed on filter code
  trigger_mode = {0: "hold; take no data",
                  1: "one reading now",
                  2: "one reading after settling time",
                  3: "read continuously"}
  power_range = {1:"min -- min+10",
                 2:"min+10 -- min+20",
                 3:"min+20 -- min+30",
                 4:"min+30 -- min+40",
                 5:"min+40 -- max",
                 "AUTO":"set automatically"}
  max_settling_time = {1:3.0, 2:1.0, 3:0.15, 4:0.10, 5:0.10} # seconds vs range
  sampling_rate = {1:20, 2:2} # samples/sec for 1 or 2 channels
  power_range_filter = {1:7, 2:3, 3:1, 4:0, 5:0}
  def __init__(self, name, pm_type=None, timeout=10000):
    """
    @type name : str
    @param name : as it appears in /etc/gpib.conf

    @type pm_type : str
    @param pm_type : model number (436, 437, 438, E4418, etc.)
    """
    Gpib.__init__(self, name)
    self.tmo(500)
    module_logger.debug("PM.__init__: opened session %d", self.instrument)
    if pm_type == None:
      (devtype,devID) = name.split()
      pm_type = pm[devID]['type']
    self.name = name
    self.pm_type = pm_type
    self.init()

  def init(self):
    """
    Initialize the power meter to default settings:
     - disable limits checking
     - linear mode (W)
     - sensor A only
     - trigger-free run
     - auto-ranging
     - manual filter 5
     - resolution 0.01% of full scale
    """
    if re.search("437", self.pm_type) or \
       re.search("438", self.pm_type):
      #           |||--------------------- disable limits checking
      #           |  ||------------------- linear
      #           |  | ||------------------sensor A
      #           |  | | |||-------------- trigger-free run
      #           |  | | |  ||**---------- auto ranging
      #           |  | | |  |   |||**----- manual filter
      #           |  | | |  |   |    |||** REF cal factor
      #           |  | | |  |   |    |     res. .01% of full scale
      self.write("LM0LNAPTR3RAENFM5ENRE3EN\r\n")
      self.filtercode = 5
      self.num_averages = self._n_avgs_()
      self.mode = 'LN'
    else:
      self.logger.error("Type %s power meter not implemented", self.pm_type)

  def _n_avgs_(self):
    return 2**self.filtercode
    
  def get_readings(self,num):
    """
    Get a number of readings

    @param num : number of readings
    @type num : int

    @return: a list of loats
    """
    self.clear()

    self.mode = self.get_mode()
    readings = []
    for i in range(0,num):
      try:
        readings.append( float(self.read().strip()) )
      except:
        module_logger.error("PM.get_readings: Invalid reading #%d from PM", i)
        readings.append(0)
      if i < num-1:
        sleep(0.5)
    return readings,self.mode

  def get_average(self,num):
    """
    Get an average of N readings

    @param num : number of readings
    @type num : int

    @return: float
    """
    readings = self.get_readings(num)[0]
    return NP.mean(NP.array(readings))

  def get_mode(self):
    """
    Get the reading mode, W or dBm

    @return: str
    """
    module_logger.debug("PM.get_mode: entered")
    if re.search('437', self.pm_type) or \
       re.search('438', self.pm_type) or \
       re.search('E4418', self.pm_type):
      try:
        self.write("SM")
      except:
        module_logger.error("PM.get_mode: sending PM%d mode request failed",
                            self.name)
        return None
      try:
        response = self.read()
      except Exception, details:
        module_logger.error("PM.get_mode: reading PM %s failed", self.name)
        module_logger.error("PM.get_mode: "+str(details))
        return None
    else:
      module_logger.error("PM.get_mode: Unknown power meter type %s",self.pm_type)
      return None
    # This returns a string something like this: 000000151105170A0002000
    if len(response) >= 15:
      units = int(response[14])
    else:
      units = -1
    if units == 0:
      mode = 'W'
    elif units == 1:
      mode = 'dBm'
    else:
      mode = '?'
    if len(response) >= 18:
      rel_mode = response[17]
    else:
      rel_mode = -1
    if rel_mode > 0:
      mode += " rel"
    return mode

  def set_mode(self,mode):
    """
    Set the power meter mode

    @param mode : "W" or 'dBm"
    @type mode : string

    @return: None
    """
    if mode == "W":
      if re.search("436", self.pm_type):
        self.write("9A+V")
      elif re.search("437", self.pm_type) or \
          re.search("438", self.pm_type) or \
          re.search("E4418", self.pm_type):
        self.write("LN")
      self.mode = "W"
    else:
      # must be dBm mode instead
      if re.search("436", self.pm_type):
        self.write("9D+V")
      elif re.search("437", self.pm_type) or \
          re.search("438", self.pm_type) or \
          re.search("E4418", self.pm_type):
        self.write("LG")
      self.mode = "dBm"

  def configure(self):
    """
    The HP 437 and 438 are programmed with a code like this::
      PR ZE CL100 EN OC1 LG TR2
    The spaces are there for readability and not included. Codes::
      PR      - preset
      ZE      - zero
      CL100   - cal adjust at 100%
      EN      - terminates a parameter entry, equivalent to pressing Enter
      OC1     - reference oscillator on
      LG      - logarithmic mode (dBm)
      TR2     -
    All frequency entries must be terminated with HZ, KZ, MZ, GZ.
    For duty cycle (DY), calibration factor (KB) and CAL (CL) the percent
    sign ("%") may be used instead of EN.  These are the commands::
      RL0 - relative mode off, RL1 - relative mode on
      OC0 - reference oscilator off, OC1 - reference oscillator on
      RH - range hold, switch auto-ranging off if it is on
      FH - filter hold, switch auto filter mode off
      LLvalueEN - return this value for readings less than it
      LHvalueEN - return this value for readings greater than it
      LM1 - enable limit checking, LM0 - disable
      TR0 - trigger hold, send no data
      TR1 - trigger immediate, take one measurement quickly
      TR2 - trigger with settling time; send no commands until done
      TR3 - free run (no triggering)
    """
    pass

  def zero(self,FE):
    """
    This requires that the input signal be zeroed, for example by turning
    the pre-amp bias off.

    @param FE : front-end with amplifier to be turned off
    @type FE : front end instance
    """
    if re.search('436', self.pm_type):
      # see below for the configuration codes
      self.write("LM0LNTR3RM1ENFM5EN")
      # send the zero command
      self.write("ZEEN")
      # wait for done
      status = "06"
      while status == "06":
        self.write("SM")
        status = self.read()[4:6]
      # restore configuration; this only changes the ranging
      self.write("LM0LNTR3RM4ENFM5EN")
    elif re.search('437', self.pm_type) or \
       re.search('438', self.pm_type):
      # configure for zeroing:
      #  LM0 -disable limit checking
      #  LN - linear mode
      #  AP - sensor A measurement
      #  TR3 - free run
      #  RM1EN - manual ranging 1
      #  FM5EN - manual filter 5
      self.write("LM0LNAPTR3RM1ENFM5EN")
      # send the zero command
      self.write("ZEEN")
      # wait for done
      status = "06"
      while status == "06":
        self.write("SM")
        status = self.read()[4:6]
      # restore configuration
      self.write("LM0LNAPTR3RM4ENFM5EN")
    else:
      pass
