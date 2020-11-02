import itertools

from PyQt5.QtWidgets import QGridLayout, QWidget
from mytools.plotwidget import PlotWidget


class PrimaryPlotWidget(QWidget):
    main_states = [0, 1, 2, 4, 8, 16, 32, 63]

    params = {
        0: {
            '00': {
                'xlabel': 'F, ГГц',
                'xlim': [],
                'ylabel': 'S21, дБм',
                'ylim': []
            },
            '01': {
                'xlabel': 'F, ГГц',
                'xlim': [],
                'ylabel': 'КСВ вх, дБм',
                'ylim': []
            },
            '11': {
                'xlabel': 'F, ГГц',
                'xlim': [],
                'ylabel': 'КСВ вых, дБм',
                'ylim': []
            },
        },
    }

    def __init__(self, parent=None, result=None):
        super().__init__(parent)

        self._result = result
        self.only_main_states = False

        self._grid = QGridLayout()

        self._plotS21 = PlotWidget(parent=None, toolbar=True)
        self._plotVswrIn = PlotWidget(parent=None, toolbar=True)
        self._plotVswrOut = PlotWidget(parent=None, toolbar=True)

        self._grid.addWidget(self._plotS21, 0, 0)
        self._grid.addWidget(self._plotVswrIn, 0, 1)
        self._grid.addWidget(self._plotVswrOut, 1, 1)

        self.setLayout(self._grid)

        self._init()

    def _init(self, dev_id=0):

        def setup_plot(plot, pars: dict):
            plot.set_tight_layout(True)
            plot.subplots_adjust(bottom=0.150)
            # plot.set_title(pars['title'])
            plot.set_xlabel(pars['xlabel'], labelpad=-2)
            plot.set_ylabel(pars['ylabel'], labelpad=-2)
            # plot.set_xlim(pars['xlim'][0], pars['xlim'][1])
            # plot.set_ylim(pars['ylim'][0], pars['ylim'][1])
            plot.grid(b=True, which='major', color='0.5', linestyle='-')
            plot.tight_layout()

        setup_plot(self._plotS21, self.params[dev_id]['00'])
        setup_plot(self._plotVswrIn, self.params[dev_id]['01'])
        setup_plot(self._plotVswrOut, self.params[dev_id]['11'])

    def clear(self):
        self._plotS21.clear()
        self._plotVswrIn.clear()
        self._plotVswrOut.clear()

    def plot(self, dev_id=0):
        print('plotting primary stats')
        self.clear()
        self._init(dev_id)

        for_states = self.main_states if self.only_main_states else range(64)
        # for_states = range(len(self.main_states))

        freqs = self._result.freqs
        s21s = self._result.s21[:1]
        vswr_in = self._result.vswr_in[:1]
        vswr_out = self._result.vswr_out[:1]

        n = len(s21s)

        for xs, ys in zip(itertools.repeat(freqs, n), s21s):
            self._plotS21.plot(xs, ys)

        for xs, ys in zip(itertools.repeat(freqs, n), vswr_in):
            self._plotVswrIn.plot(xs, ys)

        for xs, ys in zip(itertools.repeat(freqs, n), vswr_out):
            self._plotVswrOut.plot(xs, ys)
