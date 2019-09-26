from g2c1.base import crc5, pulsesToSamples # to test checksum and convert pulses to samples
from g2c1.messages import Query, QueryRep # to test commands
from g2c1.command import Reader # to test reader functionalities
from g2c1.respond import Tag # to test tag functionalities


def visualizePulses(pulses, samplerate=1e6):
    # visualize pulses as sample magnitudes
    samples = pulsesToSamples(pulses, samplerate)
    sampleStr = ''.join('_' if s < 0.5 else '\u203e' for s in samples)
    print(sampleStr)


def testCRC5():
    '''
    Tests the crc5 checksum function
    '''
    print('Testing CRC5 checksum')
    dataBits = [1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1]
    validCRC = [1, 0, 0, 0, 1]
    
    # check checksum generation
    testCRC = crc5(dataBits)
    if testCRC != validCRC:
        raise ValueError('Invalid checksum {} for bits {}'.format(testCRC, dataBits))
    
    # check data+checksum match
    check = crc5(dataBits+validCRC)
    if not all(b == 0 for b in check):
        raise ValueError('Invalid checksum check {} for bits+crc {}'.format(check, dataBits+validCRC))


def testMessage(Msg, validValues, validBits):
    '''
    Tests a message
    '''
    print('Testing '+Msg.__name__)
    msg = Msg(*validValues)
    
    # test to bits
    testBits = msg.toBits()
    if testBits != validBits:
        raise ValueError('Invalid bits {} for {}'.format(testBits, msg))

    # test to values
    msgEmpty = Msg(*(len(validValues)*[None]))
    msgEmpty.toValue(validBits)
    if not all(v == part.value for v, part in zip(validValues, msgEmpty.parts[1:])):
        raise ValueError('Invalid values in {} for bits {}'.format(msgEmpty, validBits))


def testReader():
    '''
    Tests the generation of reader commands
    '''
    reader = Reader()

    # test query because of the preamble
    query = Query()
    print('Testing commander with {}'.format(query))
    pulses = reader.toPulses(query)
    visualizePulses(pulses)

    # test simpler message with frame-sync only
    queryRep = QueryRep()
    print('Testing commander with {}'.format(queryRep))
    pulses = reader.toPulses(queryRep)
    visualizePulses(pulses)


def testTag(Msg):
    '''
    Tests the parsing of reader commands
    '''
    # generate samples from reader command
    reader = Reader()
    msg = Msg()
    print('Testing responder with {}'.format(msg))
    pulses = reader.toPulses(msg)
    samples = pulsesToSamples(pulses)
    # try to parse with tag
    tag = Tag()
    edges = tag.fromSamples(samples, synth=True)
    bits = tag.fromEdges(edges)
    # check if same
    if bits != msg.toBits():
        print('actual pulses: {}'.format(pulses))
        print('parsed edge durations: {}'.format(edges))
        print('parsed bits: {}'.format(bits))
        print('actual bits: {}'.format(msg.toBits()))
        raise ValueError('Invalid parsed bits')


def testPhysical():
    '''
    Tests the physical execution of commands with 
    the sequencer via serial port
    '''
    reader = Reader(port='/dev/tty.usbserial')
    msg = Query()
    print(reader.toPulses(msg, True))
    reader.enablePower()
    reader.sendMsg(msg)
    reader.enablePower(False)


if __name__ == '__main__':
    '''
    testCRC5()
    testMessage(
        Query, 
        [64/3, 1, False, 'all1', 1, 'b', 1], 
        [1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1])
    testReader()
    testTag(Query)
    testTag(QueryRep)
    '''
    testPhysical()
