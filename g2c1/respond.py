class Tag:
    '''
    Parses pulses from commander and respond 
    with tag pulses
    '''
    MIN_TARI = 6.25
    MAX_TARI = 25

    def __init__(self):
        self.reset()
    

    def reset(self):
        '''
        Resets all parsed values
        '''
        self.rtCal = None
        self.trCal = None
        self.bits = []
    

    def fromSamples(self, samples, samplerate=1e6, synth=False):
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
    

    def fromEdges(self, edges, tolerance=0.5):
        '''
        Converts durations between raising edges 
        from reader pulses to reader command bits

        :param edges: list of durations in us
        :param tolerance: pulse length tolerance in us
        :returns: list of 0/1 ints per command
        '''
        self.reset()
        bits = []
        def collectBits():
            if self.bits:
                bits.append(self.bits)
        
        dNew = 0
        for edge in edges:
            dOld = dNew
            dNew = edge
            if dNew > 250:
                collectBits()
                self.reset()
            elif not self.rtCal:
                # wait for reader -> tag calibration symbol
                if self.MIN_TARI-tolerance <= dOld <= self.MAX_TARI+tolerance:
                    self.rtCal = dNew # valid rtCal duration
            else:
                # wait either for tag -> reader calibration symbol OR data
                if not self.trCal and 1.1*self.rtCal-tolerance <= dNew <= 3*self.rtCal+tolerance:
                    self.trCal = dNew # full reader -> tag preamble (query command)
                else:
                    self.bits.append(1 if dNew > self.rtCal/2 else 0) # data
        
        collectBits() # get remaining bits

        return bits if len(bits) > 1 else bits[0]