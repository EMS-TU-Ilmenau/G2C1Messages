from .messages import Query # to get type of special message


class Reader:
    '''
    Outputs a message as reader command pulses. 
    Pulses are durations in us, toggling power level, first low.
    '''
    def __init__(self, tariUs=12, blfMHz=0.32, port=None):
        '''
        :param tariUs: reader data-0 symbol length in us
        :param blfMHz: tag backscatter frequency in MHz
        :param port: can be set to a string containing a serial port to send commands
        '''
        self.tari = tariUs
        self.blf = blfMHz
        self.dev = None
        if port:
            try:
                import serial # for RS232/UART/COM port
            except ImportError:
                print('Install pyserial package to use this feature')
            else:
                self.dev = serial.Serial(port, 250000, timeout=2)
    

    def __del__(self):
        if self.dev:
            self.dev.close()
    

    @property
    def pw(self):
        '''
        Width of a low-pulse

        :returns: duration in us
        '''
        return 0.5*self.tari
    

    @property
    def data0(self):
        '''
        Symbol for a reader data-0

        :returns: list of durations in us
        '''
        return [self.pw, self.pw]
    

    @property
    def data1(self):
        '''
        Symbol for a reader data-1

        :returns: list of durations in us
        '''
        return [1.5*self.tari, self.pw]
    

    @property
    def frameSync(self):
        '''
        Pulses for a R->T frame-sync which preceedes all reader messages

        :returns: list of durations in us
        '''
        delim = [12.5]
        rtCal = [3*self.tari-self.pw, self.pw] # reader -> tag calibration symbol
        return delim+self.data0+rtCal
    

    def preamble(self, dr):
        '''
        Pulses for a R->T preamble which preceedes the query message

        :param dr: divide ratio
        :returns: list of durations in us
        '''
        trCal = [dr/self.blf-self.pw, self.pw] # tag -> reader calibration symbol
        return self.frameSync+trCal
    

    def toPulses(self, msg, ints=False):
        '''
        Outputs a message as reader pulses

        :param msg: message object
        :param ints: when set to True, converts the ouput to integers
        :returns: list of durations in us
        '''
        # select start
        if isinstance(msg, Query):
            pulses = self.preamble(msg.dr.value)
        else:
            pulses = self.frameSync
        
        # append data bits as symbols
        for bit in msg.toBits():
            pulses.extend(self.data1 if bit == 1 else self.data0)
        
        # convert to ints for microcontroller compatibility
        if ints:
            pulses = [int(p) for p in pulses]
        
        return pulses
    

    def sendBytes(self, msgBytes):
        '''
        Sends bytes via serial port and awaits confirmation

        :param msgBytes: message bytes to send
        '''
        if not self.dev:
            raise AttributeError('Serial port not given upon instantiation')

        for _ in range(2):
            self.dev.write(msgBytes+b'\0') # send
            resp = self.dev.read_until(b'\0') # receive
            if b'1' in resp:
                break
        
        if b'1' not in resp:
            print('sending {} was not successful'.format(msgBytes))

    def sendMsg(self, msg):
        '''
        Starts transmission of message pulses via serial port

        :param msg: message object
        '''
        pulses = self.toPulses(msg, True)
        self.sendBytes(b'TX '+bytes(pulses))
    

    def enablePower(self, enable=True):
        '''
        Enables or disables cw power via serial port

        :param enable: True sets output power on, False disables it
        '''
        state = 'ON' if enable else 'OFF'
        self.sendBytes(bytes('POW '+state, 'ascii'))
