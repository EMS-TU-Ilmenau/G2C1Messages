from g2c1.base import crc5, pulsesToSamples # to test checksum and convert pulses to samples
from g2c1.messages import Query, QueryRep, fromBits # to test commands
from g2c1.command import Reader # to test reader functionalities
from g2c1.respond import Tag # to test tag functionalities


def visualizePulses(pulses, samplerate=1e6, reportLens=True):
    # print out pulse-lenghts
    if reportLens:
        print('{} pulses lengths [us]: {}'.format(len(pulses), pulses))
    # visualize pulses as sample magnitudes
    samples = pulsesToSamples(pulses, samplerate)
    sampleStr = ''.join('_' if s < 0.5 else '\u203e' for s in samples)
    print('Pulse magnitudes: {}'.format(sampleStr))


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
    msgEmpty.fromBits(validBits)
    if not all(v == part.value for v, part in zip(validValues, msgEmpty.parts[1:])):
        raise ValueError('Invalid values in {} for bits {}'.format(msgEmpty, validBits))

    # test lookup
    msgLookup = fromBits(validBits)
    if msgLookup != msg:
        raise ValueError('Invalid values in looked up message {} from bits {}'.format(msgLookup, validBits))


def testReader(Msg):
    '''
    Tests the generation of reader commands
    '''
    reader = Reader()
    msg = Msg()
    print('Testing commander with {}'.format(msg))
    pulses = reader.toPulses(msg)
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
    edges = tag.samplesToEdges(samples, synth=True)
    cmd = tag.fromEdges(edges)[0]
    
    # check if same
    if cmd.bits != msg.toBits():
        print('actual pulses: {}'.format(pulses))
        print('parsed edge durations: {}'.format(edges))
        print('parsed bits: {}'.format(cmd.bits))
        print('actual bits: {}'.format(msg.toBits()))
        raise ValueError('Invalid parsed bits')

    # check if messages was parsed
    if cmd.message != msg:
        print(cmd.message)
        raise TypeError('Bits where not converted to correct message')


def testPhysical():
    '''
    Tests the physical execution of commands with 
    the sequencer via serial port
    '''
    from rtlsdr import RtlSdr # for controlling the RTL SDR
    from multiprocessing.pool import ThreadPool # for simultaneous function execution
    import matplotlib.pyplot as plt # for plotting
    import numpy as np # for array math
    from matplotlib.mlab import psd, specgram # for fft
    from scipy import signal # for filtering

    tariUs = 12 # reader data-0 length in us
    freqMHz = 866.3 # reader center frequency
    blfMHz = 0.32 # tag backscatter link frequency
    
    # generate pulses
    reader = Reader(tariUs, blfMHz, 'COM4')

    # init sdr
    sdr = RtlSdr(serial_number='00000001')
    sdr.sample_rate = 2.048e6
    sdr.center_freq = freqMHz*1e6
    sdr.gain = 0
    sdr.read_samples(sdr.sample_rate*0.05) # dummy read

    # get samples asyncronously...
    pool = ThreadPool(processes=1)
    sampling = pool.apply_async(sdr.read_samples, (sdr.sample_rate*0.05,))
    # ...while sending command
    reader.enablePower()

    msg = Query(m=8, trExt=True)
    print('Testing physically with {}'.format(msg))
    reader.sendMsg(msg)

    msg = Query(m=1, trExt=False, q=1)
    print('Testing physically with {}'.format(msg))
    reader.sendMsg(msg)

    msg = QueryRep()
    print('Testing physically with {}'.format(msg))
    reader.sendMsg(msg)

    reader.enablePower(False)
    # block until samples are aquired
    samples = sampling.get()

    # plot
    _, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10))
    blfStyle = {'linewidth': 1, 'linestyle': 'dashed', 'alpha': 0.6}
    # time domain
    timeSec = np.arange(len(samples))/sdr.sample_rate
    ax1.plot(timeSec, np.abs(samples), linewidth=0.5)
    ax1.set_xlabel('time [s]')
    ax1.set_ylabel('magnitude')
    ax1.set_title('Observed communication with \n'
        'tari: {}us, freq: {}MHz, blf: {}MHz'.format(tariUs, freqMHz, blfMHz))
    ax1.grid()
    
    # frequency domain
    nFFT = 512
    maxHold = False
    if maxHold:
        traces, _, _ = specgram(samples, NFFT=nFFT)
        trace = np.max(traces, axis=1) # max hold over time
    else:
        trace, _ = psd(samples, NFFT=nFFT)
    trace = 20*np.log10(trace) # to dB
    freqsMHz = np.linspace(sdr.center_freq-sdr.sample_rate/2, sdr.center_freq+sdr.sample_rate/2, nFFT)/1e6
    ax2.plot(freqsMHz, trace, linewidth=0.5)
    ax2.set_xlabel('frequency [MHz]')
    ax2.set_ylabel('magnitude [dB]')
    ax2.grid()
    # mark tag response
    ax2.axvline(freqMHz-blfMHz, color='r', **blfStyle)
    ax2.axvline(freqMHz+blfMHz, color='r', label='backscatter frequency', **blfStyle)
    ax2.legend(loc='upper right')

    # spectrogram
    traces, _, _ = specgram(samples)
    traces = np.clip(20*np.log10(traces), -100, -30)
    ax3.imshow(traces, extent=(timeSec[0], timeSec[-1], freqsMHz[0], freqsMHz[-1]), aspect='auto', cmap='jet')
    ax3.axhline(freqMHz-blfMHz, color='w', **blfStyle)
    ax3.axhline(freqMHz+blfMHz, color='w', label='backscatter frequency', **blfStyle)
    ax3.legend(loc='upper right')
    ax3.set_xlabel('time [s]')
    ax3.set_ylabel('frequency [MHz]')

    # try to parse with tag
    tag = Tag()
    edges = tag.samplesToEdges(np.abs(samples), sdr.sample_rate)
    print('Parsed raising edge durations: {}'.format(edges))
    cmds = tag.fromEdges(edges)
    for cmd in cmds:
        print('Parsed edges: {}'.format(cmd.edges))
        print('Parsed bits: {}'.format(cmd.bits))
        print('Parsed message: {}'.format(cmd.message))
        if cmd.blf:
            print('Parsed BLF: {} kHz'.format(int(cmd.blf*1e3)))
        print('Parsed Tari: {} us'.format(cmd.tari))
        ax1.axvline(cmd.start/1e6, color='g')
        ax1.axvline(cmd.end/1e6, color='g')
        txt = str(cmd.bits) if not cmd.message else str(cmd.message)
        txt += '\nTari: {:.1f} us'.format(cmd.tari)
        if cmd.blf:
            txt += ', BLF: {} kHz'.format(int(cmd.blf*1e3))
        ax1.text(cmd.start/1e6, 0.5*np.max(np.abs(samples)), txt, color='g', backgroundcolor='w')
    
    plt.show()


def testPhysicalQueryCombos():
    '''
    Tests the physical execution of different commands with 
    the sequencer via serial port
    '''
    print('Testing physical query parameter combinations')
    drs = (8, 64/3)
    blfs = (0.1, 0.2, 0.3, 0.4)
    millers = (1, 2, 4, 8)
    pilots = (False, True)
    taris = range(7, 25)
    
    # prepare reader
    reader = Reader(port='COM4')
    reader.enablePower()

    for dr in drs:
        for blf in blfs:
            for miller in millers:
                for pilot in pilots:
                    for tari in taris:
                        # set protocol parameters
                        msg = Query(dr, miller, pilot)
                        reader.tari = tari
                        reader.blf = blf
                        try:
                            reader.sendMsg(msg)
                        except:
                            raise IOError('Could not send {}'.format(msg))
    
    reader.enablePower(False)


if __name__ == '__main__':
    testCRC5()
    testMessage(
        Query, 
        [64/3, 1, False, 'all1', 1, 'b', 1], 
        [1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1])
    testReader(Query)
    testReader(QueryRep)
    testTag(Query)
    testTag(QueryRep)
    try:
        #testPhysicalQueryCombos()
        testPhysical()
    except ImportError:
        print('Physical test requires additional packages')
    except IOError:
        print('No device for physical test found')
