from g2c1.base import crc5, pulsesToSamples # to test checksum and convert pulses to samples
from g2c1.messages import Query, QueryRep # to test commands
from g2c1.command import Reader # to test reader functionalities
from g2c1.respond import Tag # to test tag functionalities


def visualizePulses(pulses, samplerate=1e6, reportLens=True):
    # print out pulse-lenghts
    if reportLens:
        print('Pulse lengths [us]: {}'.format(pulses))
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
    from rtlsdr import RtlSdr # for controlling the RTL SDR
    from multiprocessing.pool import ThreadPool # for simultaneous function execution
    import matplotlib.pyplot as plt # for plotting
    import numpy as np # for array math
    from matplotlib.mlab import psd, specgram # for fft
    from scipy import signal # for filtering

    tariUs = 12 # reader data-0 length in us
    freqMHz = 866 # reader center frequency
    blfMHz = 0.32 # tag backscatter link frequency
    
    # generate pulses
    reader = Reader(tariUs, blfMHz, 'COM4')
    msg = Query(m=8, trExt=True, target='a', q=0)
    print('Testing physically with {}'.format(msg))
    '''
    # visualize/debug
    pulses = reader.toPulses(msg, True)
    print(pulses)
    visualizePulses(pulses)
    '''

    # init sdr
    sdr = RtlSdr(serial_number='00000001')
    sdr.sample_rate = 2.048e6
    sdr.center_freq = freqMHz*1e6
    sdr.gain = 0

    # get samples asyncronously...
    pool = ThreadPool(processes=1)
    sampling = pool.apply_async(sdr.read_samples, (sdr.sample_rate*0.05,))
    # ...while sending command
    reader.enablePower()
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
        'tari: {}us, freq: {}MHz, blf: {}MHz, {}'.format(tariUs, freqMHz, blfMHz, msg))
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

    plt.show()

    # try to parse with tag
    tag = Tag()
    edges = tag.fromSamples(np.abs(samples), sdr.sample_rate)
    print('Parsed raising edge durations: {}'.format(edges))
    bits = tag.fromEdges(edges)
    print('Parsed bits: {}'.format(bits))
    msgEmpty = Query()
    msgEmpty.toValue(bits)
    print('Parsed message: {}'.format(msgEmpty))


if __name__ == '__main__':
    testCRC5()
    testMessage(
        Query, 
        [64/3, 1, False, 'all1', 1, 'b', 1], 
        [1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1])
    testReader()
    testTag(Query)
    testTag(QueryRep)
    try:
        testPhysical()
    except ImportError:
        print('Physical test requires additional packages')
