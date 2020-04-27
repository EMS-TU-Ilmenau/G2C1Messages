# G2C1Messages
Software to generate and parse Gen2 Class1 UHF RFID messages (currently reader-only)

## Description
The project aims at mapping the G2C1 protocol at different layers (message parameters, bits, pulses, samples) and to convert between them. 
This can be used to parse messages from baseband samples or generate pulses to transmit messages.

## Getting started
Install as Python package with `pip3 install .` and/or run `python3 tests.py` and have a look at its source code.

### Examples
To generate a message use the `Reader` class and derivations of the `Message` class like `Query`, `QueryRep` or `ACK` found in [messages](g1c1/messages).

```python
import g2c1

# generate FM0 query command without preamble
msg = g2c1.messages.Query(dr=8, m=1, trExt=False)
print(msg) # show message with all parameters
print(msg.toBits()) # show the message as bits including checksum

# make a reader object with 160 kHz backscatter frequency and 20 us tari
reader = g2c1.Reader(tariUs=20, blfMHz=0.16)
print(reader.toPulses(msg)) # show message as pulse durations in us
```

Note that pulse durations refer to alternating high/low levels starting from high level (carrier), so first pulse duration is the duration how long the level is low, the second pulse duration is the duration how long the level is high after that and so on.

To parse message parameters, either use the intermediate layer parsers, e.g. bits to parameters:

```python
msg = g2c1.messages.Query()
bits = [1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1]
msg.fromBits(bits) # parse Query parameters from bits
print(msg)
```

if you don't know which message to expect:

```python
from g2c1.messages import fromBits
bits = [1, 0, 0, 1, 1, 0, 1, 1, 0]
msg = fromBits(bits)
print(msg)
```

Or, parse reader commands directly from a vector of baseband sample magnitudes, e.g. recorded by an SDR using the `Tag` class:

```python
tag = g2c1.Tag() # make a receiver object
edges = tag.samplesToEdges(samples) # convert real sample magnitudes to durations in us between raising edges
for cmd in tag.fromEdges(edges):
    print(cmd.message) # show all parsed reader command messages
```
