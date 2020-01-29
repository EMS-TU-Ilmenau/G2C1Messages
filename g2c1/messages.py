from .base import Constant, LookUp, Value, Message, crc5 # to generate message bits and checksum


class Query(Message):
    '''
    Reader query command
    '''
    cmd = Constant([1, 0, 0, 0], 'Query')

    def __init__(self, dr=64/3, m=1, trExt=False, sel='all1', session=1, target='a', q=0):
        '''
        :param dr: divide ration. 
            Can be 8 or 64/3
        :param m: miller factor (cycles per symbol). 
            Can be 1, 2, 4 or 8
        :param trExt: tag to reader preamble extension (use pilot tone).
            Can be True or False
        :param sel: chooses which tag respond (selection).
            Can be "all0", "all1" (same as "all0"), "-sl" or "sl"
        :param session: session for the inventory round.
            Can be 0, 1, 2 or 3
        :param target: selects tags in inventory round with corresponding inventoried flag.
            Can be "a" or "b"
        :param q: number of slots in the inventory round (estimated tag population 0...2^q-1)
        '''
        Message.__init__(self, crc5)
        # add parts
        
        # command
        self.add(self.cmd)
        
        # divide ratio
        self.dr = LookUp(1, dr)
        self.dr.add([0], 8)
        self.dr.add([1], 64/3)
        self.add(self.dr)
        
        # miller factor
        self.m = LookUp(2, m)
        self.m.add([0, 0], 1)
        self.m.add([0, 1], 2)
        self.m.add([1, 0], 4)
        self.m.add([1, 1], 8)
        self.add(self.m)

        # pilot tone
        self.trExt = LookUp(1, trExt)
        self.trExt.add([0], False)
        self.trExt.add([1], True)
        self.add(self.trExt)

        # selection
        self.sel = LookUp(2, sel)
        self.sel.add([0, 0], 'all0')
        self.sel.add([0, 1], 'all1')
        self.sel.add([1, 0], '-sl')
        self.sel.add([1, 1], 'sl')
        self.add(self.sel)

        # session
        self.session = Value(2, session)
        self.add(self.session)

        # target
        self.target = LookUp(1, target)
        self.target.add([0], 'a')
        self.target.add([1], 'b')
        self.add(self.target)

        # q
        self.q = Value(4, q)
        self.add(self.q)


class QueryRep(Message):
    '''
    Reader query repeat command
    '''
    cmd = Constant([0, 0], 'QueryRep')

    def __init__(self, session=1):
        '''
        :param session: session for the inventory round.
            Can be 0, 1, 2 or 3
        '''
        Message.__init__(self)
        # add parts
        
        # command
        self.add(self.cmd)

        # session
        self.session = Value(2, session)
        self.add(self.session)


_messages = (
    Query, 
    QueryRep
)


def fromBits(bits):
    '''
    Looks up message from bits

    :param bits: list of 0/1 ints
    :returns: instance of message
    '''
    for Msg in _messages:
        cmdBits = Msg.cmd.toBits()
        nCmdBits = len(cmdBits)
        # check if command ID in bits
        if len(bits) >= nCmdBits:
            if cmdBits == bits[:nCmdBits]:
                # build message from bits
                msg = Msg()
                msg.fromBits(bits)
                return msg
    
    raise LookupError('No message type found associated with {}'.format(bits))
