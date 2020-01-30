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
    

    @property
    def blfMHz(self):
        '''
        :returns: tag backscatter frequency configured by last reader Query
        '''
        if isinstance(self.command, Query):
            return self.command.dr/self.trCal
        else:
            raise AttributeError('Did not parse a Query command yet')
    

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
        
        # convert to binary levels
        thresh = 0.3*(sMin+sMax)
        binLevels = [1 if sample > thresh else 0 for sample in samples]

        # get raising edges
        edges = []
        iOldRaising = 0
        for iSample in range(len(binLevels)-1):
            if binLevels[iSample+1] > binLevels[iSample]:
                # raising edge occured
                iNewRaising = iSample+1
                edges.append(1e6*(iNewRaising-iOldRaising)/samplerate)
                iOldRaising = iNewRaising
        
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
                if not self.trCal and 1.1*self.rtCal <= dNew <= 3*self.rtCal:
                    self.trCal = dNew # full reader -> tag preamble (query command)
                else:
                    if dNew > self.EDGE_SPLIT_THRESH:
                        break # end of command
                    self.bits.append(1 if dNew > self.rtCal/2 else 0) # data
        
        self.command = fromBits(self.bits)
