class Responder:
    '''
    Parses pulses from commander and respond 
    with tag pulses
    '''
    def __init__(self):
        self.reset()
    

    def reset(self):
        '''
        Resets all parsed values
        '''
        self.tari = None
        self.rtCal = None
        self.trCal = None
        self.blf = None
    

    def fromSamples(self, samples, samplerate=1e6):
        '''
        Converts sample magnitudes to raising edge durations

        :param samples: list of sample magnitudes
        :param samplerate: sample rate in Hz
        :returns: list of durations in us
        '''
        raise NotImplementedError('Conversion yet undefined')
    

    def fromEdges(self, edges):
        '''
        Converts durations between raising edges 
        from reader pulses to reader command bits

        :param edges: list of durations in us
        :returns: list of 0/1 ints
        '''
        tolerance = 1 # tolerance in us
        bits = []
        dOld = 0
        for edge in edges:
            dNew = edge
            # wait for tari (data0 symbol)
            if not self.tari:
                if dNew >= 6.25 and dNew <= 25 and dOld > 100:
                    self.tari = dNew
            else:
                # wait for reader -> tag calibration symbol
                if not self.rtCal:
                    if dNew >= 2.5*self.tari-tolerance and dNew <= 3*self.tari+tolerance:
                        self.rtCal = dNew # valid rtCal duration
                    else:
                        self.reset() # unexpected symbol after aquiring tari
                else:
                    # wait for end
                    if bits and dNew >= self.tari-tolerance and dNew <= 2*self.tari+tolerance:
                        break
                    # wait either for tag -> reader calibration symbol OR data
                    if not self.trCal and dNew >= 1.1*self.rtCal-tolerance and dNew <= 3*self.rtCal+tolerance:
                        self.trCal = dNew # full reader -> tag preamble (query command)
                    else:
                        bits.append(1 if dNew > self.rtCal/2 else 0) # data
            
            dOld = dNew
        
        return bits