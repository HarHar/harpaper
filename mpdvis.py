#!/usr/bin/env python2
# -*- coding: utf-8 -*-
### GStreamer Spectrum Dump ####
# V20111005-1 by Scott Garrett #
# Wintervenom [(at)] gmail.com #
################################
# Dependencies:
#
# pygobject
# gst-python (gstreamer0.10-python)
# gstreamer0.10-good
#
# Optional Dependencies:
# gconf (python2-gconf)
#
#################################

import curses
try:
    import gconf
except ImportError:
    pass
import sys
import getopt
import gobject
gobject.threads_init()
import pygst
pygst.require('0.10')
import gst
import math
import os
import textwrap


VERSION = 20111005-1
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)


def stdout(message):
    """
    Writes a message to STDOUT.
    """
    sys.stdout.write("{0}\n".format(message))
    sys.stdout.flush()


def stderr(message):
    """
    Writes a message to STDERR.
    """
    sys.stderr.write("{0}\n".format(message))
    sys.stderr.flush()


def fatal(error):
    """
    Output an error message to STDERR and exit with status 1.
    """
    stderr("Error: {0}".format(error))
    sys.exit(1)


class GstSpectrumDump(object):
    """
    Dumps the spectrum magnitudes of incoming audio as volume units per band.

    Optional arguments:
    <source>        Source of the audio (default: alsasrc or gconf setting).
    <precision>     How many decimal places to round the magnitudes to
                    (default: 16).
    <bands>         How many frequency bands to output (default: 128).
    <amplify>       Amplify output by this much (default: 1).
    <logamplify>    Amplify magnitude values logarithmically to compensate for
                    softer higher frequencies.  (default: False)
    <autoamp>       Automatically control amplification levels when they are
                    too loud.
    <threshold>     Minimal magnitude of a band in decibels (default: 70).
    <cufoff>        Cut off magnitudes at this value after amplification has
                    been applied (default: 100).
    <scale>         Scale magnitudes to this value (default: 100).
    <raw>           Don't clip or apply logarithmic upscale the output.
                    (default: True).
    <db>            Return output in decibels instead of a percentage.
                    <logamplify> is ignored (default: True).
    <iec>           Convert decibels to percentages with IEC 60268-18 scaling
                    (default: False).
    <vumeter>       Return VU meter output instead of spectrum.  <bands>
                    controls how many channels to output here.  <threshold> is
                    ignored.
    <interval>      Milliseconds to wait between polls (default: 50).
    <quiet>         Don't output to STDERR (default: False if no callback).
    <callback>      Return the magnitude list to this function (default: None).
    """
    def __init__(self, **opts):
        #self.source = 'mpd:///tmp/mpd.fifo'
        self.source = False
        self.precision = opts.get('precision')
        self.bands = opts.get('bands', 30)
        self.amplify = opts.get('amplify', 1)
        self.logamplify = opts.get('logamplify', False)
        self.autoamp = opts.get('autoamp', False)
        self.threshold = opts.get('threshold', 70)
        self.cutoff = opts.get('cutoff', 100)
        self.scaleto = opts.get('scale', 100)
        self.raw = opts.get('raw', True)
        self.db = opts.get('db', False)
        self.iec = opts.get('iec', False)
        self.vumeter = opts.get('vumeter', False)
        self.interval = opts.get('interval', 40)
        self.callback = opts.get('callback')
        self.quiet = opts.get('quiet', self.callback is not None)
        self.pipeline = None
        self.gainhits = 0
        self.origamp = self.amplify
        if not self.source:
            defaultsrc = 'alsasrc'
            try:
                conf = gconf.client_get_default()
                source = conf.get('/system/gstreamer/%d.%d/default/audiosrc' %
                                  gst.gst_version[:-1])
                if source:
                    self.source = source.get_string()
                else:
                    self.source = defaultsrc
            except NameError:
                stderr('Python2 GConf module not installed; using default source.')
                self.source = defaultsrc
        elif self.source.startswith('mpd'):
            fifo = self.source.split(' ', 1)
            fifo = fifo[1] if len(fifo) > 1 else '/tmp/mpd.fifo'
            pipeline = 'filesrc location={} ! audio/x-raw-int, ' \
                       'rate=44100, cha9nnels=2, endianness=1234, width=16, ' \
                       'depth=16, signed=true ! audioconvert'
            self.source = pipeline.format(fifo)



    def printopts(self):
        opts = {
            'source': self.source,
            'precision': self.precision,
            'bands': self.bands,
            'amplify': self.amplify,
            'logamplify': self.logamplify,
            'threshold': self.threshold,
            'cutoff': self.cutoff,
            'scaleto': self.scaleto,
            'autoamp': self.autoamp,
            'raw': self.raw,
            'db': self.db,
            'iec': self.iec,
            'vumeter': self.vumeter,
            'interval': self.interval,
            'quiet': self.quiet,
            'pipeline': self.pipeline,
        }
        stderr('# GStreamer Spectrum Dump')
        stderr('# Version {0} by Scott Garrett'.format(VERSION))
        stderr('')
        stderr('[Parameters]')
        for k, v in opts.iteritems():
            stderr('{0:>10}: {1}'.format(k, v))


    def initscr(self):
        try:
            curses.curs_set(0)
        except:
            pass
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_WHITE)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_YELLOW)
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_RED)


    def draw(self, magnitudes):
        size = [n - 1 for n in self.stdscr.getmaxyx()]
        if self.scaleto != size[0]:
            self.scaleto = size[0]
        if self.bands > size[1]:
            self.bands = size[1]
        self.stdscr.erase()
        for i, m in enumerate(magnitudes):
            if not self.db:
                m = int(round(m, 0))
            else:
                m = int(round(self.threshold + m, 0))
            if m != 0:
                color = 1 + int(m * (3 / float(self.threshold)))
                self.stdscr.addstr(size[0] - m, i, ' ', curses.color_pair(color))
        self.stdscr.refresh()


    def round(self, n):
        if self.precision:
            return round(n, self.precision)
        elif self.precision == 0:
            return int(n)
        return n


    def dbtopct(self, db, index=None):
        indexamp = 1
        if self.iec:
            pct = 0.0
            if db < -70.0:
                pct = 0.0
            elif db < -60.0:
                pct = (db + 70.0) * 0.25
            elif db < -50.0:
                pct = (db + 60.0) * 0.5 + 2.5
            elif db < -40.0:
                pct = (db + 50.0) * 0.75 + 7.5
            elif db < -30.0:
                pct = (db + 40.0) * 1.5 + 15.0
            elif db < -20.0:
                pct = (db + 30.0) * 2.0 + 30.0
            elif db < 0.0:
                pct = (db + 20.0) * 2.5 + 50.0
            else:
                pct = 100.0
        else:
            pct = (self.threshold + db) / float(self.threshold) * 100
        if index and index > 0:
            indexamp += math.log10(index)
        pct = min(self.cutoff, self.amplify * (indexamp * pct))
        if self.autoamp:
            if pct == 100:
                self.gainhits += 1
                if self.amplify > 0:
                    self.amplify -= 0.1
            elif pct == 0:
                self.gainhits -= 1
                if self.gainhits < -100:
                    if self.amplify < self.origamp:
                        self.amplify += 0.01
                    self.gainhits = 0
        return pct * (self.scaleto / 100.0)


    def interpolate(self, a, b, points):
        points = round(points, 0) + 1.0
        return [a + ((b - a) / points) * x for x in range(0, int(points))]


    def scale(self, floats, maxlen=None):
        if len(floats) < 2:
            return floats
        scaled = []
        for i in range(1, len(floats)):
            length = 1 + math.log10(i - 0)
            scaled += self.interpolate(floats[i-1], floats[i], length)[:-1]
        scaled.append(floats[-1])
        if maxlen and len(scaled) > maxlen:
            downscaled = []
            incr = len(scaled) / float(maxlen)
            index = 0
            for v in range(0, maxlen):
                downscaled.append(scaled[int(round(index, 0))])
                index += incr
            return downscaled
        else:
            return scaled


    def on_message(self, bus, message):
        try:
            s = message.structure
            name = s.get_name()
            if name == 'spectrum':
                if self.bands > 40:
                    cutoff = int(round(self.bands * (7/8.0), 0))
                else:
                    cutoff = None
                magnitudes = s['magnitude'][0][:cutoff]
                if not self.db:
                    if self.logamplify:
                        magnitudes = [self.dbtopct(db, i) for i, db
                                      in enumerate(magnitudes)]
                    else:
                        magnitudes = [self.dbtopct(db) for i, db
                                      in enumerate(magnitudes)]
                if not self.raw:
                    magnitudes = self.scale(magnitudes, self.bands)
                magnitudes = [self.round(m) for m in magnitudes]
            elif name == 'level':
                magnitudes = []
                for channel in range(0, min(self.bands, len(s['peak']))):
                    peak = max(-self.threshold, min(0, s['peak'][channel]))
                    decay = max(-self.threshold, min(0, s['decay'][channel]))
                    if not self.db:
                        if self.logamplify:
                            peak = self.dbtopct(peak, peak)
                            decay = self.dbtopct(decay, decay)
                        else:
                            peak = self.dbtopct(peak)
                            decay = self.dbtopct(decay)
                    magnitudes.append(self.round(peak))
                    magnitudes.append(self.round(decay))
            else:
                return True
            if not self.quiet:
                try:
                    print(' '.join((str(m) for m in magnitudes)))
                except IOError:
                    self.loop.quit()
            if self.callback:
                self.callback(magnitudes)
        except KeyboardInterrupt:
            self.loop.quit()
        return True


    def start_pipeline(self):
        pipeline = [self.source]
        interval = 'interval={0}'.format(1000000 * self.interval)
        if self.vumeter:
            pipeline.append('level message=true {}'.format(interval))
        else:
            spectrum = 'spectrum message=true {} bands={} threshold=-{} multi-channel=true'
            spectrum = spectrum.format(interval, self.bands, self.threshold)
            pipeline.append(spectrum)
        pipeline.append('fakesink')
        self.pipeline = gst.parse_launch(' ! '.join(pipeline))
        self.bus = self.pipeline.get_bus()
        self.bus.enable_sync_message_emission()
        self.bus.add_signal_watch()
        self.conn = self.bus.connect("message::element", self.on_message)
        self.pipeline.set_state(gst.STATE_PLAYING)


    def stop_pipeline(self):
        if self.pipeline:
            self.bus.disconnect(self.conn)
            self.bus.remove_signal_watch()
            self.pipeline.set_state(gst.STATE_NULL)


    def run(self, stdscr=None):
        self.stdscr = stdscr
        if stdscr:
            self.initscr()
        try:
            self.start_pipeline()
            self.loop = gobject.MainLoop()
            try:
                self.loop.run()
            except KeyboardInterrupt:
                pass
            self.stop_pipeline()
            sys.exit(0)
        except gobject.GError as error:
            stderr('Error creating pipeline: {0}'.format(error))
            stderr('Do you have gstreamer0.10-good installed?')
            sys.exit(1)


    def rundraw(self):
        self.quiet = True
        self.callback = self.draw
        curses.wrapper(self.run)


if __name__ == "__main__":
    opt_precision = False
    opt_bands = 128
    opt_amplify = 1
    opt_lamplify = False
    opt_autoamp = False
    opt_cutoff = 500
    opt_scale = 100
    opt_interval = 50
    opt_raw = False
    opt_db = False
    opt_iec = False
    opt_vumeter = False
    opt_source = None
    opt_draw = False
    try:
        longopts = ['source=', 'precision=', 'bands=', 'amplify=', 'lamplify',
                    'autoamp', 'cutoff=', 'scale=', 'vu', 'interval=', 'draw',
                    'raw', 'db', 'iec', 'help']
        shortopts = 'p:b:a:lgc:s:i:rdevoh'
        opts, args = getopt.getopt(sys.argv[1:], shortopts, longopts)
    except getopt.GetoptError as error:
        stderr(error)
        usage()
    for o, a in opts:
        if o == '--source':
            opt_source = a
        elif o in ('-p', '--precision'):
            if a.isdigit():
                opt_precision = int(a)
            else:
                fatal('Precision should be an integer zero or greater.')
        elif o in ('-a', '--amplify'):
            try:
                if a in ('inf', 0):
                    raise ValueError
                opt_amplify = float(a)
            except ValueError:
                fatal('Amplify should be a float greater than zero.')
        elif o in ('-b', '--bands'):
            if a.isdigit():
                opt_bands = max(1, min(128, int(a)))
            else:
                fatal('Bands should be an integer between 1 and 128.')
        elif o in ('-l', '--lamplify'):
            opt_lamplify = True
        elif o in ('-g', '--autoamp'):
            opt_autoamp = True
        elif o in ('-c', '--cutoff'):
            try:
                if a in ('inf', 0):
                    raise ValueError
                opt_cutoff = float(a)
            except ValueError:
                fatal('Cutoff should be a float greater than zero.')
        elif o in ('-s', '--scale'):
            try:
                if a in ('inf', 0):
                    raise ValueError
                opt_scale = float(a)
            except ValueError:
                fatal('Scale should be a float greater than zero.')
        elif o in ('-i', '--interval'):
            try:
                if a == 0:
                    raise ValueError
                opt_interval = int(a)
            except ValueError:
                fatal('Interval should be an integer greater than zero.')
        elif o in ('-v', '--vu'):
            opt_vumeter = True
        elif o in ('-r', '--raw'):
            opt_raw = True
        elif o in ('-d', '--db'):
            opt_db = True
        elif o in ('-e', '--iec'):
            opt_iec = True
        elif o in ('-o', '--draw'):
            opt_draw = True
        elif o in ('-h', '--help'):
            usage()
    spectrum = GstSpectrumDump(
        source=opt_source,
        precision=opt_precision,
        bands=opt_bands,
        amplify=opt_amplify,
        logamplify=opt_lamplify,
        autoamp=opt_autoamp,
        cutoff=opt_cutoff,
        scale=opt_scale,
        raw=opt_raw,
        db=opt_db,
        iec=opt_iec,
        vumeter=opt_vumeter,
        interval=opt_interval
    )
    spectrum.printopts()
    if opt_draw:
        spectrum.rundraw()
    else:
        spectrum.run()

