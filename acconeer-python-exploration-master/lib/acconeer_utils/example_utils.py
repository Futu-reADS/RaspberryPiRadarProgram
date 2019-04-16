from argparse import ArgumentParser
import signal
import numpy as np
from datetime import datetime
import logging
import sys
import serial.tools.list_ports
import pyqtgraph as pg
from PyQt5 import QtCore


class ExampleArgumentParser(ArgumentParser):
    def __init__(self, num_sens="+"):
        super().__init__()

        server_group = self.add_mutually_exclusive_group(required=False)
        server_group.add_argument(
            "-u",
            "--uart",
            metavar="port",
            dest="serial_port",
            help="connect via uart (using register-based protocol)",
            nargs="?",
            const="",  # as argparse does not support setting const to None
            )
        server_group.add_argument(
            "-s",
            "--socket",
            metavar="address",
            dest="socket_addr",
            default='0.0.0.0',
            help="connect via socket on given address (using json-based protocol)",
            )

        self.add_argument(
            "--sensor",
            metavar="id",
            dest="sensors",
            type=int,
            default=[1],
            nargs=num_sens,
            help="the sensor(s) to use (default: 1)",
        )

        verbosity_group = self.add_mutually_exclusive_group(required=False)
        verbosity_group.add_argument(
            "-v",
            "--verbose",
            action="store_true",
        )
        verbosity_group.add_argument(
            "-vv",
            "--debug",
            action="store_true",
        )
        verbosity_group.add_argument(
            "-q",
            "--quiet",
            action="store_true",
        )


class ExampleInterruptHandler:
    def __init__(self):
        self._signal_count = 0
        signal.signal(signal.SIGINT, self.interrupt_handler)

    @property
    def got_signal(self):
        return self._signal_count > 0

    def force_signal_interrupt(self):
        self.interrupt_handler(signal.SIGINT, None)

    def interrupt_handler(self, signum, frame):
        self._signal_count += 1
        if self._signal_count >= 3:
            raise KeyboardInterrupt


def mpl_setup_yaxis_for_phase(ax):
    ax.set_ylim(-np.pi, np.pi)
    ax.set_yticks(np.linspace(-np.pi, np.pi, 5))
    ax.set_yticklabels([r"$-\pi$", r"$-\pi/2$", r"0", r"$\pi/2$", r"$\pi$"])


def timestamp():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def config_logging(args):
    fmt = "[%(asctime)s] %(levelname)s - %(name)s - %(message)s"
    datefmt = "%H:%M:%S"

    if args.debug:
        level = logging.DEBUG
    elif args.verbose:
        level = logging.INFO
    elif args.quiet:
        level = logging.ERROR
    else:
        level = logging.WARN

    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter(fmt, datefmt=datefmt)
    stream_handler.setFormatter(formatter)
    log = logging.getLogger(__name__.split(".")[0])
    log.setLevel(level)
    log.addHandler(stream_handler)

    logging.getLogger(__name__).debug("logging configured")


def autodetect_serial_port():
    port_infos = serial.tools.list_ports.comports()

    for port_info in port_infos:
        port, desc, _ = port_info
        if desc.startswith("XB112"):
            print("Autodetected XB112 on {}\n".format(port))
            return port

    for port_info in port_infos:
        port, desc, _ = port_info
        if desc == "FT230X Basic UART":
            print("Autodetected FT230X Basic UART on {}\n".format(port))
            return port

    if len(port_infos) == 0:
        print("Could not autodetect serial port, no ports available")
        sys.exit()
    elif len(port_infos) == 1:
        print("Autodetected single available serial port on {}\n".format(port))
        return port_infos[0][0]
    else:
        print("Multiple serial ports are available:")
        for port_info in port_infos:
            port, desc, _ = port_info
            print("  {:<13}  ({})".format(port, desc))
        print("\nRe-run the script with a given port")
        sys.exit()

    print("Could not autodetect serial port")
    sys.exit()


def color_cycler(i=0):
    category10 = [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf",
    ]

    return category10[i % len(category10)]


def pg_pen_cycler(i=0, style=None):
    pen = pg.mkPen(color_cycler(i), width=2)
    if style == "--":
        pen.setStyle(QtCore.Qt.DashLine)
    elif style is not None:
        pen.setStyle(style)
    return pen


class SmoothMax:
    def __init__(self, f, hysteresis=0.5, tau_decay=2.0, tau_grow=0.5):
        self.h = hysteresis
        self.ax = np.exp(-1 / (tau_decay * f))
        self.ay = np.exp(-1 / (tau_grow * f))

        self.x = -1
        self.y = -1

    def update(self, m):
        m = max(m, 1e-12)

        if m > self.x:
            self.x = m
        else:
            self.x = (1 - self.ax) * m + self.ax * self.x

        if self.y < 0:
            self.y = self.x
        elif self.x > self.y:
            self.y = (1 - self.ay) * self.x * (1 + self.h) + self.ay * self.y
        elif self.x < (1 - self.h) * self.y:
            self.y = self.x / (1 - self.h)

        return self.y


pg_phase_ticks = [
    list(zip(np.linspace(-np.pi, np.pi, 5), ["-π", "-π/2", "0", "π/2", "π"])),
    [(x, "") for x in np.linspace(-np.pi, np.pi, 9)],
]


def pg_setup_polar_plot(plot, max_r=1):
    plot.showAxis("left", False)
    plot.showAxis("bottom", False)
    plot.setAspectLocked()
    plot.disableAutoRange()
    s = 1.15
    plot.setXRange(-s*max_r, s*max_r)
    plot.setYRange(-s*max_r, s*max_r)

    for i, r in enumerate(np.linspace(0, max_r, 5)[1:]):
        circle = pg.QtGui.QGraphicsEllipseItem(-r, -r, r*2, r*2)
        circle.setPen(pg.mkPen("k" if i == 3 else 0.5))
        plot.addItem(circle)

        if i == 3:
            text_item = pg.TextItem(text=str(r), color="k", anchor=(0, 1))
            text_item.setPos(np.cos(np.pi/8)*r, np.sin(np.pi/8)*r)
            plot.addItem(text_item)

    for i in range(8):
        deg = (360 / 8) * i
        rad = np.radians(deg)
        x = np.sin(rad)
        y = np.cos(rad)
        text = str(int(deg)) + '\u00b0'
        ax = (-x + 1) / 2
        ay = (y + 1) / 2
        text_item = pg.TextItem(text, color="k", anchor=(ax, ay))
        text_item.setPos(max_r*x*1.02, max_r*y*1.02)
        plot.addItem(text_item)
        plot.plot([0, max_r*x], [0, max_r*y], pen=pg.mkPen(0.5))


def pg_mpl_cmap(name):
    import matplotlib.pyplot as plt
    cmap = plt.get_cmap(name)
    cmap._init()
    return np.array(cmap._lut) * 255
