import time

from os.path import isfile
from PyQt5.QtCore import QObject, pyqtSlot

from arduino.programmerfactory import ProgrammerFactory
from instr.instrumentfactory import NetworkAnalyzerFactory, SourceFactory, mock_enabled
from measureresult import MeasureResult


class InstrumentController(QObject):
    states = {
        i * 0.25: i for i in range(64)
    }

    main_states = [0, 1, 2, 4, 8, 16, 32, 63]

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.requiredInstruments = {
            'Анализатор': NetworkAnalyzerFactory('GPIB0::9::INSTR'),
            'Источник питания': SourceFactory('GPIB0::5::INSTR'),
            'Программатор': ProgrammerFactory('COM5')
        }

        self.deviceParams = {
            'Цифровой аттенюатор': {
                'F': [1.15, 1.35, 1.75, 1.92, 2.25, 2.54, 2.7, 3, 3.47, 3.86, 4.25],
                'mul': 2,
                'P1': 15,
                'P2': 21,
                'Istat': [None, None, None],
                'Idyn': [None, None, None]
            },
        }

        if isfile('./params.ini'):
            import ast
            with open('./params.ini', 'rt', encoding='utf-8') as f:
                raw = ''.join(f.readlines())
                self.deviceParams = ast.literal_eval(raw)

        self.secondaryParams = {
            'Pin': -10,
            'F1': 4,
            'F2': 8,
            'kp': 0,
            'Fborder1': 4,
            'Fborder2': 8
        }

        self.sweep_points = 201
        self.cal_set = '-20db_pyatkin_6G'

        self._instruments = dict()
        self.found = False
        self.present = False
        self.hasResult = False
        self.only_main_states = False

        self.result = MeasureResult()

        self._freqs = list()
        self._mag_s11s = list()
        self._mag_s22s = list()
        self._mag_s21s = list()
        self._phs_s21s = list()
        self._amp_values = list()
        self._current = [0.0, 0.0]

    def __str__(self):
        return f'{self._instruments}'

    def connect(self, addrs):
        print(f'searching for {addrs}')
        for k, v in addrs.items():
            self.requiredInstruments[k].addr = v
        self.found = self._find()

    def _find(self):
        self._instruments = {
            k: v.find() for k, v in self.requiredInstruments.items()
        }
        return all(self._instruments.values())

    def check(self, params):
        print(f'call check with {params}')
        device, secondary = params
        self.present = self._check(device, secondary)
        print('sample pass')

    def _check(self, device, secondary):
        print(f'launch check with {self.deviceParams[device]} {self.secondaryParams}')
        return self._runCheck(self.deviceParams[device], self.secondaryParams)

    def _runCheck(self, param, secondary):
        print(f'run check with {param}, {secondary}')
        return True

    def measure(self, params):
        print(f'call measure with {params}')
        device, _ = params
        self.result.raw_data = self.sweep_points, self._measure(device), self._amp_values, self.secondaryParams, self._current
        self.hasResult = bool(self.result)

    def _measure(self, device):
        param = self.deviceParams[device]
        secondary = self.secondaryParams
        print(f'launch measure with {param} {secondary}')

        self._clear()
        self._init()

        return self._measure_s_params()

    def _clear(self):
        self._amp_values.clear()

    def _init(self):
        pna = self._instruments['Анализатор']
        prog = self._instruments['Программатор']

        pna.send('SYST:PRES')
        pna.query('*OPC?')
        # pna.send('SENS1:CORR ON')

        pna.send('CALC1:PAR:DEF "CH1_S21",S21')

        # c:\program files\agilent\newtowrk analyzer\UserCalSets
        pna.send(f'SENS1:CORR:CSET:ACT "{self.cal_set}",1')
        # pna.send('SENS2:CORR:CSET:ACT "-20dBm_1.1-1.4G",1')

        pna.send(f'SENS1:SWE:POIN {self.sweep_points}')

        pna.send(f'SENS1:FREQ:STAR {self.secondaryParams["F1"]}GHz')
        pna.send(f'SENS1:FREQ:STOP {self.secondaryParams["F2"]}GHz')

        pna.send('SENS1:SWE:MODE CONT')
        pna.send(f'FORM:DATA ASCII')

        prog.set_lpf_code(0)

    def _measure_s_params(self):
        pna = self._instruments['Анализатор']
        prog = self._instruments['Программатор']
        src = self._instruments['Источник питания']

        src.send('inst:sel outp1')
        src.send('apply 5.25v,15ma')
        if not mock_enabled:
            time.sleep(0.5)
        cur1 = float(src.query('MEAS:CURR?'))

        src.send('inst:sel outp2')
        src.send('apply 5.25v,15ma')
        if not mock_enabled:
            time.sleep(0.5)
        cur2 = float(src.query('MEAS:CURR?'))

        self._current = [cur1, cur2]
        if mock_enabled:
            self._current = [0.0035, 0.0045]
        print('read current: ', self._current)

        src.send('inst:sel outp1')
        src.send('apply 4.75v,15ma')
        src.send('inst:sel outp2')
        src.send('apply 4.75v,15ma')

        cycles = self.secondaryParams['cycles']
        out = list()
        for cycle in range(cycles):
            print('measure cycle:', cycle)

            out.clear()
            self._amp_values.clear()

            for amp, code in self.states.items():
                if self.only_main_states and code not in self.main_states:
                    continue
                self._amp_values.append((code, amp))

                prog.set_lpf_code(code)

                if not mock_enabled:
                    time.sleep(0.5)

                pna.send(f'CALC1:PAR:SEL "CH1_S21"')
                pna.query('*OPC?')
                res = pna.query(f'CALC1:DATA:SNP? 2')

                # pna.send(f'CALC:DATA:SNP:PORTs:Save "1,2", "d:/ksa/att_simple/s{code}.s2p"')
                # pna.send(f'MMEM:STOR "d:/ksa/att_simple1/s{code}.s2p"')

                # with open(f's2p_{code}.s2p', mode='wt', encoding='utf-8') as f:
                #     f.write(res)
                if mock_enabled:
                    with open(f'ref/sample_data/s2p_{code}.s2p', mode='rt', encoding='utf-8') as f:
                        res = list(f.readlines())[0].strip()
                out.append(parse_float_list(res))

                if not mock_enabled:
                    time.sleep(0.5)

        src.send('*RST')
        return out

    def pow_sweep(self):
        print('pow sweep')
        return [4, 5, 6], [4, 5, 6]

    @pyqtSlot(dict)
    def on_secondary_changed(self, params):
        self.secondaryParams = params

    @property
    def status(self):
        return [i.status for i in self._instruments.values()]


def parse_float_list(lst):
    return [float(x) for x in lst.split(',')]
