from .messages import Query, fromBits # to get type of special message


class Tag:
    '''
    Parses pulses from commander and respond 
    with tag pulses
    '''
    MIN_TARI = 6.25
    MAX_TARI = 25
    EDGE_SPLIT_THRESH = 250

    def __init__(self):
        self.reset()
        self.command = None
        self.blf = None
    

    @property
    def blfMHz(self):
        '''
        :returns: tag backscatter frequency configured by last reader Query
        '''
        return self.blf
    

    def reset(self):
        '''
        Resets all parsed values from last reader command
        '''
        self.rtCal = None
        self.trCal = None
        self.bits = []
    

    def samplesToEdges(self, samples, samplerate=1e6, synth=False):
        '''
        Converts sample magnitudes to raising edge durations

        :param samples: list of sample magnitudes
        :param samplerate: sample rate in Hz
        :param synth: when set to True, extends the samples by artifical start and end
        :returns: list of durations in us
        '''
        sMin = min(samples)
        sMax = max(samples)
        
        if synth:
            # insert sythetic start
            start = [sMin]+int(100*samplerate*1e-6)*[sMax]
            samples = start+samples
            # insert synthetic end
            samples += [sMax]
        
        # prepare schmitt trigger
        delta = sMax-sMin
        hyst = 0.1
        mid = 0.3*(sMin+sMax)
        threshHigh = mid+hyst*delta
        threshLow = mid-hyst*delta
        raised = False

        # get raising edges
        edges = []
        iOldRaising = 0
        for iSample, level in enumerate(samples):
            if level > threshHigh and not raised:
                # raising edge occured
                raised = True
                edge = 1e6*(iSample-iOldRaising)/samplerate
                iOldRaising = iSample
                edges.append(edge)
            if level < threshLow and raised:
                raised = False
        
        return edges
    

    def splitEdges(self, edges):
        '''
        :param edges: list of durations in us
        :returns: list of valid reader command edges
        '''
        arrs = []
        subArr = []
        for edge in edges:
            if edge > self.EDGE_SPLIT_THRESH:
                # split and get collected
                if subArr:
                    arrs.append(subArr)
                    subArr = [] # reset
            else:
                # collect
                subArr.append(edge)
        
        if subArr:
            # get remaining collected
            arrs.append(subArr)
        
        return arrs
    

    def fromEdges(self, edges):
        '''
        Converts durations between raising edges from reader pulses 
        to reader command bits of exactly one reader command (!). 
        To parse more than one command, use the splitEdges method 
        before to separate the commands.

        :param edges: list of durations in us
        '''
        self.reset()

        dNew = 0
        for edge in edges:
            dOld = dNew
            dNew = edge
            if not self.rtCal:
                # wait for reader -> tag calibration symbol
                if self.MIN_TARI <= dOld <= self.MAX_TARI:
                    self.rtCal = dNew # valid rtCal duration
            else:
                # wait either for tag -> reader calibration symbol OR data
                if not self.trCal and self.rtCal <= dNew <= 3*self.rtCal:
                    self.trCal = dNew # full reader -> tag preamble (query command)
                else:
                    if dNew > self.rtCal:
                        break # end of command
                    self.bits.append(1 if dNew > self.rtCal/2 else 0) # data
        
        if not self.bits:
            raise ValueError('No bits in edges {}'.format(edges))

        # convert bits to message
        try:
            self.command = fromBits(self.bits)
        except LookupError:
            self.command = None
            print('Could not lookup command message from bits {} (edges: {})'.format(
                self.bits, ', '.join('{:.1f}'.format(e) for e in edges)))
        
        # calculate backscatter if message was Query
        if isinstance(self.command, Query):
            self.blf = self.command.dr.value/self.trCal
