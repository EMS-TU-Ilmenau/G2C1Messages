from .messages import Query, fromBits # to get type of special message


class ReceivedCommand:
    '''
    Meta infos and parsed message from a reader command
    '''
    def __init__(self):
        self.tari = None # data-0 length in us
        self.rtCal = None # reader -> tag calibration symbol length in us
        self.trCal = None # tag -> reader calibration symbol length in us
        self.edges = [] # durations between raising edges of the command in us
        self.bits = [] # parsed command data bits
        self.message = None # command message object
        self.blf = None # backscatter frequency in MHz
        self.start = 0. # begin of command in us
        self.end = 0. # end of command in us


class Tag:
    '''
    Parses pulses from commander and respond 
    with tag pulses
    '''
    MIN_TARI = 6.25
    MAX_TARI = 25


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
    

    def fromEdges(self, edges):
        '''
        Parses durations between raising edges from reader pulses 
        to collect the data bits, meta infos and corresponding messages

        :param edges: list of durations in us
        :returns: list of received commands
        '''
        iStart = 0
        recCmds = []
        recCmd = ReceivedCommand()
        def finish():
            recCmd.end = sum(edges[:iEdge])
            recCmd.edges = edges[iStart:iEdge]
            recCmds.append(recCmd) # collect finished command

        # get command data bits and meta infos
        dNew = 0.
        for iEdge, edge in enumerate(edges):
            dOld = dNew
            dNew = edge
            if not recCmd.rtCal:
                # wait for reader -> tag calibration symbol
                if self.MIN_TARI <= dOld <= self.MAX_TARI:
                    recCmd.tari = dOld # get tari
                    recCmd.rtCal = dNew # valid rtCal duration
                    iStart = iEdge-1
                    recCmd.start = sum(edges[:iStart]) # get command start
            else:
                # wait either for tag -> reader calibration symbol OR data
                if not recCmd.trCal and recCmd.rtCal <= dNew <= 3*recCmd.rtCal:
                    recCmd.trCal = dNew # full reader -> tag preamble (query command)
                else:
                    if dNew > recCmd.rtCal:
                        # end of command
                        finish()
                        recCmd = ReceivedCommand() # make new command
                    else:
                        recCmd.bits.append(1 if dNew > recCmd.rtCal/2 else 0) # data
        
        # collect finished command
        iEdge += 1
        finish()

        # convert command data bits to messages
        for recCmd in recCmds:
            if recCmd.bits:
                try:
                    recCmd.message = fromBits(recCmd.bits)
                except LookupError:
                    Warning('Could not lookup command message from bits {} (edges: {})'.format(
                        recCmd.bits, ', '.join('{:.1f}'.format(e) for e in recCmd.edges)))
                
                # calculate backscatter if message was Query
                if isinstance(recCmd.message, Query):
                    recCmd.blf = recCmd.message.dr.value/recCmd.trCal
            else:
                Warning('Could not parse bits from edges: {}'.format(recCmd.edges))
        
        return recCmds
