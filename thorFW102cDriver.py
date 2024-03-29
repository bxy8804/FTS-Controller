#Following script from:
#https://github.com/mgraupe/acq4/blob/filterwheel/acq4/drivers/ThorlabsFW102C/thorFW102cDriver.py
#Because we organize this script into our own FTS package in Python, we updated the original
#import lines that came with this script

import serial, struct, time, collections, threading, re, pdb
from FTS.SerialDevice import SerialDevice, TimeoutError, DataError

errorMessages = {
    'CMD_NOT_DEFINED': 0xEA,
    'time out':0xEB,
    'time out':0xEC,
    'invalid string buffer':0XED
    }

class FilterWheelDriver(SerialDevice):
    """
    Class for communicating with ThorLabs FW 102C Motorized Filter Wheel
    
    """
    def __init__(self, p, baud=115200):
        #self.fws = {}
        #self.paramTable = OrderedDict()
        
        SerialDevice.__init__(self, port=p, baudrate=baud)
        
    def getPos(self):
        """Reads and returns the current filterwheel position """
        pos = self['pos?']
        return int(pos)
    
    def setPos(self, newPos):
        """Sets filterwheel position to n """
        self['pos'] = int(newPos)
    
    def getPosCount(self):
        """Position count query."""
        pcount = self['pcount?']
        return int(pcount)
    
    def getTriggerMode(self):
        """ trigger mode query : 
            (0) - input (response to an ative low pulse advancing postion by 1
            (1) - output (generate an active high pulse when selected position arrive)
        """
        trigger = self['trig?']
        return int(trigger)
    
    def setTriggerMode(self, newMode):
        """tirgger modes : 
            (0) - input (response to an ative low pulse advancing postion by 1
            (1) - output (generate an active high pulse when selected position arrive)
        """
        if int(newMode) in [0,1]:
            self['trig'] = int(newMode)
        else:
            raise Exception("FilterWheel trigger mode has to be '0' or '1'", newMode)
    
    def getSpeed(self):
        """ filterwheel movement speed query : 
            (0) - slow
            (1) - fast
        """
        speed = self['speed?']
        return int(speed)
    
    def setSpeed(self, newSpeed):
        """tirgger modes : 
            (0) - slow
            (1) - fast
        """
        if int(newSpeed) in [0,1]:
            self['speed'] = int(newSpeed)
        else:
            raise Exception("FilterWheel speed has to be '0' or '1'", newMode)
    
    def getSensorMode(self):
        """ returns sensor behavior when wheel is idle : 
            (0) - Sensors turn off when wheel is idle to eliminiate stray light
            (1) - Sensors remain active
        """
        sensor = self['sensors?']
        return int(sensor)
    
    def setSensorMode(self, newSensorMode):
        """sensor modes : 
            (0) - Sensors turn off when wheel is idle to eliminiate stray light
            (1) - Sensors remain active
        """
        if int(newSensorMode) in [0,1]:
            self['sensors'] = int(newSensorMode)
        else:
            raise Exception("FilterWheel speed has to be '0' or '1'", newMode)
    
    def getIdentification(self):
        """ identification query """
        idn = self['*idn?']
        return idn
        
    def __getitem__(self, arg):  ## request a single value from the laser
        #print "write", arg
        self.write("%s\r" % arg)
        ret = self.readPacket()
        #print "   return:", ret
        if '\n' in ret[0]:
            err =  re.search('%s(.*)%s' % ('\r', '\n'), ret[0]).group(1)
            raise Exception("FilterWheel error:", err)
        if ret[0].count('\r')==2:
            result = re.search('%s(.*)%s' % ('\r', '\r'), ret[0]).group(1)
        elif ret[0].count('\r')==1:
            result = re.search('%s(.*)%s' % ('=', '\r'), ret[0]).group(1)
        #print "   result:", result
        return result
        
    def __setitem__(self, arg, val):  ## set a single value on the laser
        #print "write", arg, val
        self.write("%s=%s\r" % (arg,str(val)))
        ret = self.readPacket()
        #print "   return:", ret
        #return ret

    def readPacket(self, expect=0, timeout=10, block=True):
        ## Read until a '>' is encountered (or timeout).
        ## If expect is >0, then try to get a packet of that length, ignoring '>' within that data
        ## if block is False, then return immediately if no data is available.
        start = time.time()
        s = ''
        errors = []
        packets = []
        while True:
            n = self.serial.inWaiting()
            s += self.read(n)
            #print "read:", repr(s)
            if not block and len(s) == 0:
                return
            
            while len(s) > 0:  ## pull packets out of s one at a time
                if '>' in s[expect:]:
                    i = expect + s[expect:].index('>')
                    packets.append(s[:i])
                    expect = 0
                    s = s[i+2:]
                else:
                    break
            if len(s) == 0:
                if len(packets) == 1:
                    if 'Error' in packets[0]:
                        raise Exception(packets[0])
                    return packets   ## success
                if len(packets) > 1:
                    raise Exception("Too many packets read.", packets)
            
            time.sleep(0.01)
            if time.time() - start > timeout:
                raise TimeoutError("Timeout while waiting for response. (Data so far: %s)" % (repr(s)), s)