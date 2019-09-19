from .messages import Query # to get type of special message


class Reader:
    '''
    Outputs a message as reader command pulses. 
    Pulses are durations in us, toggling power level, first low.
    '''
    def __init__(self, tariUs=12, blfKHz=320):
        '''
        :param tariUs: reader data-0 symbol length in us
        :param blfKHz: tag backscatter frequency in KHz
        '''
        self.tari = tariUs
        self.blf = blfKHz
    

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
        trCal = [dr/(self.blf*1e-3)-self.pw, self.pw] # tag -> reader calibration symbol
        return self.frameSync+trCal
    

    def toPulses(self, msg, ints=False):
        '''
        Outputs a message as reader pulses

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
    

    def toSamples(self, pulses, samplerate=1e6):
        '''
        Outputs list of pulses as sample magnitudes

        :param pulses: list of durations in us
        :param samplerate: sample rate in Hz
        :returns: list of sample magnitudes between 0...1
        '''
        level = 0.
        samples = []
        for pulse in pulses:
            # add samples with magnitude
            nSamples = int(pulse*1e-6*samplerate)
            samples.extend(nSamples*[level])
            # switch level
            level = abs(1.-level)
        
        return samples
