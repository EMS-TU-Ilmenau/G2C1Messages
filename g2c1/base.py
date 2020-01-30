def crc5(bits):
    '''
    Generates the CRC5 checksum for the reader command 
    based on https://www.lammertbies.nl/forum/viewtopic.php?t=1330

    :param bits: list of 0/1 ints of the message without checksum bits, starting with the MSB
    :returns: list of 0/1 ints of the checksum bits, starting with the MSB
    '''
    # preparations
    poly = [0, 1, 0, 0, 1]
    flag = 0

    def shift(bits):
        '''shifts 0s/1s in list bits to left by 1'''
        return bits[1:]+[0]

    def xor(bits):
        '''XOR 0s/1s in list bits with poly'''
        return [1 if b != p else 0 for b, p in zip(bits, poly)]

    reg = poly # initially fill Q[4:0] with polynom
    inp = bits # initially fill input with data bits

    # algorithms
    while len(inp) > 0:
        # check if MSBs of input and register trigger XOR in next round
        if reg[0] != inp[0]:
            flag = 1

        # shift register and input
        reg = shift(reg)
        inp = shift(inp)[:-1]

        # check flag to XOR register with polynom
        if flag:
            reg = xor(reg)
            flag = 0

    return reg


def pulsesToSamples(pulses, samplerate=1e6):
    '''
    Outputs a list of pulses as sample magnitudes
    
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
        # toggle level
        level = abs(1.-level)
    
    return samples


class Part:
    '''
    Part of a message
    '''
    def __init__(self, nBits, value=None):
        '''
        :param nBits: number of bits
        :param value: current/default data associated to bits
        '''
        self.nBits = nBits
        self.value = value
    

    def fromBits(self, bits):
        '''
        :param bits: list of 0/1 ints
        '''
        raise NotImplementedError('Define how the bit list is converted to a value')
    

    def toBits(self):
        '''
        :returns: bits corresponding to value
        '''
        raise NotImplementedError('Define how the value is converted to a bit list')


    def _bitStr(self, bits):
        '''
        :param bits: list of 0/1 ints
        '''
        return ''.join(str(b) for b in bits)


class Value(Part):
    '''
    Binary expression of a value and vice versa
    '''
    def fromBits(self, bits):
        self.value = int(self._bitStr(bits), 2)
    

    def toBits(self):
        bitStr = format(self.value, '0{}b'.format(self.nBits))
        return [int(b) for b in bitStr]


class LookUp(Part):
    '''
    Looks up value from bits and vice versa
    '''
    def __init__(self, *args, **kwargs):
        Part.__init__(self, *args, **kwargs)
        self.combos = {}
    

    def add(self, bits, value):
        '''
        Adds a bits <-> value association

        :param bits: list of 0/1 ints
        :param value: value/meaning of bits
        '''
        self.combos[self._bitStr(bits)] = value
    

    def fromBits(self, bits):
        self.value = self.combos.get(self._bitStr(bits))
    

    def toBits(self):
        for bitStr, value in self.combos.items():
            if value == self.value:
                return [int(b) for b in bitStr]
        
        raise KeyError('{} not in lookup table {}'.format(self.value, self.combos))


class Constant(LookUp):
    '''
    Simple bits <-> value association
    '''
    def __init__(self, bits, value):
        LookUp.__init__(self, len(bits), value)
        self.add(bits, value)


class Message:
    '''
    Reader or tag message consisting of bits
    '''
    def __init__(self, checksumFunc=None):
        '''
        :param checksumFunc: when set to a function handler, 
            the checksum over all the other message parts are calculated 
            and appended to the bits
        '''
        self.checksumFunc = checksumFunc
        self.parts = [] # parts of the message without checksum
    

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, ', '.join(str(p.value)[:5] for p in self.parts[1:]))
    

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return all(sPart.value == oPart.value for sPart, oPart in zip(self.parts, other.parts))
        else:
            return False
    

    def add(self, part):
        '''
        Adds a part to the message
        '''
        self.parts.append(part)
    

    @property
    def nBits(self):
        '''
        :returns: sum of all message part bits
        '''
        return sum(part.nBits for part in self.parts)
    

    def fromBits(self, bits):
        '''
        Converts the bits into parts value

        :param bits: list of 0/1 ints
        :returns: list of value/meaning of bits
        '''
        # sanity check
        if self.nBits > len(bits):
            raise TypeError('Invalid number of bits for message')
        
        # parse bits
        bitSum = 0
        for part in self.parts:
            # select bits for part
            parseBits = bits[bitSum:bitSum+part.nBits]
            bitSum += part.nBits
            # convert to value and store in part
            part.fromBits(parseBits)
    

    def toBits(self):
        '''
        Converts the current state of message to bits
        
        :returns: list of 0/1 ints
        '''
        bits = []
        # make parts to bits
        for part in self.parts:
            bits.extend(part.toBits())
        
        # optionally append checksum
        if self.checksumFunc:
            bits.extend(self.checksumFunc(bits))
        
        return bits
