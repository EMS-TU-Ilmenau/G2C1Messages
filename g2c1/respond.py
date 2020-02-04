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


    def samplesToEdges(self, samples, samplerate=1e6, mid=0.4):
        '''
        Converts sample magnitudes to raising edge durations

        :param samples: list of sample magnitudes
        :param samplerate: sample rate in Hz
        :param mid: ratio (0=low...1=high) to define middle level
        :returns: list of durations in us
        '''
        sMin = min(samples)
        sMax = max(samples)
        
        # prepare schmitt trigger
        delta = sMax-sMin
        hyst = 0.1
        threshMid = sMin+mid*delta
        threshHigh = threshMid+hyst*delta
        threshLow = threshMid-hyst*delta
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
        cmds = []
        cmd = ReceivedCommand()
        def finish():
            if cmd.rtCal:
                cmd.end = sum(edges[:iEdge])
                cmd.edges = edges[iStart:iEdge]
                cmds.append(cmd) # collect finished command

        # get command data bits and meta infos
        dNew = 0.
        for iEdge, edge in enumerate(edges):
            dOld = dNew
            dNew = edge
            if not cmd.rtCal:
                # wait for reader -> tag calibration symbol
                if self.MIN_TARI <= dOld <= self.MAX_TARI and 2*dOld <= dNew <= 3.5*dOld:
                    cmd.tari = dOld # get tari
                    cmd.rtCal = dNew # valid rtCal duration
                    iStart = iEdge-1
                    cmd.start = sum(edges[:iStart]) # get command start
            else:
                # wait either for tag -> reader calibration symbol OR data
                if not cmd.trCal and cmd.rtCal <= dNew <= 3*cmd.rtCal:
                    cmd.trCal = dNew # full reader -> tag preamble (query command)
                else:
                    if cmd.bits and dNew > cmd.rtCal:
                        # end of command
                        finish()
                        cmd = ReceivedCommand() # make new command
                    else:
                        cmd.bits.append(1 if dNew > cmd.rtCal/2 else 0) # data
        
        # collect finished command
        iEdge += 1
        finish()

        # convert command data bits to messages
        for cmd in cmds:
            if cmd.bits:
                try:
                    cmd.message = fromBits(cmd.bits)
                except:
                    print('Could not lookup command message from bits {} (edges: {})'.format(
                        cmd.bits, ', '.join('{:.1f}'.format(e) for e in cmd.edges)))
                
                # calculate backscatter if message was Query
                if isinstance(cmd.message, Query):
                    cmd.blf = cmd.message.dr.value/cmd.trCal
            else:
                print('Could not parse bits from edges: '+', '.join('{:.1f}'.format(e) for e in cmd.edges))
        
        return cmds
