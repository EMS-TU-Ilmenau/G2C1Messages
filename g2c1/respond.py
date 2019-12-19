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

        # very simple algorithm at the moment
        thresh = 0.5*(sMin+sMax)
        def binLevel(sample):
            return 1. if sample > thresh else 0.
        
        oldLevel = binLevel(samples[0])
        raisedTime = 0.
        edges = []
        for sample in samples:
            newLevel = binLevel(sample)
            # raising edge
            if newLevel > oldLevel:
                edges.append(raisedTime*1e6)
                raisedTime = 0. # reset
            
            raisedTime += 1./samplerate # count duration
            oldLevel = newLevel # remember old binary level
        
        return edges[1:]
    

    def fromEdges(self, edges):
        '''
        Converts durations between raising edges 
        from reader pulses to reader command bits

        :param edges: list of durations in us
        :returns: list of 0/1 ints
        '''
        tolerance = 1 # tolerance in us
        bits = []
        dNew = 0
        for edge in edges:
            dOld = dNew
            dNew = edge
            if dNew > 100:
                self.reset()
            # wait for reader -> tag calibration symbol
            if not self.rtCal:
                if dOld >= self.MIN_TARI and dOld <= self.MAX_TARI:
                    self.rtCal = dNew # valid rtCal duration
                else:
                    self.reset() # unexpected symbol after aquiring tari
            else:
                # wait either for tag -> reader calibration symbol OR data
                if not self.trCal and dNew >= 1.1*self.rtCal-tolerance and dNew <= 3*self.rtCal+tolerance:
                    self.trCal = dNew # full reader -> tag preamble (query command)
                else:
                    bits.append(1 if dNew > self.rtCal/2 else 0) # data
        
        return bits