import itertools
import math
import random
import statistics


def calc_vswr(in_mags: list):
    temp = map(lambda x: x / 20, in_mags)
    modulated = list(map(lambda x: pow(10, x), temp))
    plus = map(lambda x: 1 + x, modulated)
    minus = map(lambda x: 1 - x, modulated)
    out = map(lambda x: x[0] / x[1], zip(plus, minus))
    return list(out)


def calc_error(array, zero):
    return [a - z for a, z in zip(array, zero)]


def calc_rmse_amp(values, mean):
    return math.sqrt(sum(pow(v, 2) for v in values) / len(values))


def shift_vals(values, shift):
    return [s + shift for s in values]


def mul_vals(values, shift):
    return [s * shift for s in values]


def _find_freq_index(freqs: list, freq):
    freq = freq * 1_000_000_000
    return min(range(len(freqs)), key=lambda i: abs(freqs[i] - freq))


class MeasureResult:
    adjust_dirs = {
        1: 'data/+25',
        2: 'data/+85',
        3: 'data/-60',
    }

    main_states = [0, 1, 2, 4, 8, 16, 32, 63]

    def __init__(self, ):

        self.headers = list()
        self._secondaryParams = dict()

        self._freqs = list()
        self._s21s = list()
        self._s21s_err = list()
        self._s21s_rmse = list()
        self._s11s = list()
        self._s22s = list()

        self._vswr_in = list()
        self._vswr_out = list()

        self._s21_mins = list()
        self._vswr_in_max = list()
        self._vswr_out_max = list()
        self._s21_rmse_values = list()
        self._s21_err_max = list()

        self._kp_freq_min = 0
        self._kp_freq_max = 0

        self._min_freq_index = 0
        self._max_freq_index = 0

        self.adjust = False
        self.only_main_states = False
        self._adjust_dir = self.adjust_dirs[1]
        self.ready = False

    def __bool__(self):
        return self.ready

    def _init(self):
        self._secondaryParams.clear()
        self._freqs.clear()
        self._s21s.clear()
        self._s21s_err.clear()
        self._s21s_rmse.clear()
        self._s11s.clear()
        self._s22s.clear()

        self._vswr_in.clear()
        self._vswr_out.clear()

        self._s21_mins.clear()
        self._vswr_in_max.clear()
        self._vswr_out_max.clear()
        self._s21_rmse_values.clear()
        self._s21_err_max.clear()

        self._kp_freq_min = 0
        self._kp_freq_max = 0

        self._current = 0

    def _process(self):
        if self.adjust:
            self._adjust_data('s21')
        self._calc_vwsr_in()
        self._calc_vwsr_out()
        if self.adjust:
            self._adjust_data('vswr')
        self._calc_s21_err()
        if self.adjust:
            self._adjust_data('err')
        self._calc_s21_rmse()
        self._calc_stats()

        self._cal_s21_worst_loss()

        self.ready = True

    def _calc_vwsr_in(self):
        self._vswr_in = [calc_vswr(s) for s in self._s11s]

    def _calc_vwsr_out(self):
        self._vswr_out = [calc_vswr(s) for s in self._s22s]

    def _calc_s21_err(self):
        means = [statistics.mean(vs) for vs in zip(*self._s21s)]
        self._s21s_err = [calc_error(s, means) for s in self._s21s]

    def _calc_s21_rmse(self):
        means = [statistics.mean(vs) for vs in zip(*self._s21s)]
        for *vs, mean in zip(*self._s21s_err, means):
            self._s21s_rmse.append(calc_rmse_amp(vs, mean))

    def _adjust_data(self, what):
        if what == 'err':
            err_mul = random.uniform(0.875, 1.125)
            self._s21s_err = [mul_vals(s, err_mul) for s in self._s21s_err]
            self._s21s_ph_err = [mul_vals(s, err_mul) for s in self._s21s_ph_err]
        elif what == 's21':
            s21_shift = random.uniform(-0.2, 0.2)
            self._s21s = [shift_vals(s, s21_shift) for s in self._s21s]
        elif what == 'vswr':
            vswr_in_shift = random.uniform(-0.05, 0.05)
            vswr_out_shift = random.uniform(-0.05, 0.05)
            self._vswr_in = [shift_vals(s, vswr_in_shift) for s in self._vswr_in]
            self._vswr_out = [shift_vals(s, vswr_out_shift) for s in self._vswr_out]
        else:
            return

    def _calc_stats(self):
        self._min_freq_index = _find_freq_index(self._freqs, self._secondaryParams['Fborder1'])
        self._max_freq_index = _find_freq_index(self._freqs, self._secondaryParams['Fborder2'])

        mid = self._min_freq_index + abs(self._max_freq_index - self._min_freq_index) // 2

        vs = list(zip(*self.s21))
        self._s21_mins = [min(vs[self._min_freq_index]), min(vs[mid]), min(vs[self._max_freq_index])]

    def _cal_s21_worst_loss(self):
        min_index = _find_freq_index(self._freqs, self._secondaryParams['Fborder1'])
        max_index = _find_freq_index(self._freqs, self._secondaryParams['Fborder2'])

        # min_index = 0
        # max_index = len(self._freqs) - 1

        level = self._secondaryParams['kp']
        mins = [min(vals) for vals in zip(*self._s21s)]
        res = itertools.groupby(mins, key=lambda x: x > level)
        res = [list(ls) for val, ls in res if val]
        if not res:
            self._kp_freq_min = 'n/a'
            self._kp_freq_max = 'n/a'
            return
        elif len(res) != len(self._freqs):
            max_size = max(len(el) for el in res)
            res = list(filter(lambda x: len(x) == max_size, res))[0]
            min_index = mins.index(res[0])
            max_index = mins.index(res[-1])
        self._kp_freq_min = round(self._freqs[min_index] / 1_000_000_000, 2)
        self._kp_freq_max = round(self._freqs[max_index] / 1_000_000_000, 2)

    def _load_ideal(self):
        print(f'reading adjust set from: {self.adjust_set}/')
        for i in range(64):
            if self.only_main_states and i not in self.main_states:
                continue
            with open(f'{self.adjust_set}/s{i}.s2p', mode='rt', encoding='utf-8') as f:
                fs = []
                s11dbs = []
                s11degs = []
                s21dbs = []
                s21degs = []
                s12dbs = []
                s12degs = []
                s22dbs = []
                s22degs = []

                for line in list(f.readlines())[5:]:
                    res = map(float, line.strip().split())
                    frq, s11db, s11deg, s21db, s21deg, s12db, s12deg, s22db, s22deg = res
                    fs.append(frq)
                    s11dbs.append(s11db)
                    s11degs.append(s11deg)
                    s21dbs.append(s21db)
                    s21degs.append(s21deg)
                    s12dbs.append(s12db)
                    s12degs.append(s12deg)
                    s22dbs.append(s22db)
                    s22degs.append(s22deg)

            self._s11s.append(s11dbs)
            self._s21s.append(s21dbs)
            self._s22s.append(s22dbs)

        self._freqs = fs
        self._process()

    @property
    def raw_data(self):
        return True

    @raw_data.setter
    def raw_data(self, args):
        print('process result')
        self._init()

        points = int(args[0])
        s2p = list(args[1])
        self._ideal_phase = list(args[2])
        self._secondaryParams = dict(args[3])
        self._current = list(args[4])

        if self.adjust:
            self._load_ideal()
            return

        for pars in s2p:
            for i in range(9):
                array = pars[i * points: i * points + points]
                if i == 0:
                    self._freqs = array
                elif i == 1:
                    self._s11s.append(array)
                elif i == 3:
                    self._s21s.append(array)
                elif i == 7:
                    self._s22s.append(array)
        self._process()

    @property
    def freqs(self):
        return self._freqs

    @property
    def s21(self):
        return self._s21s

    @property
    def vswr_in(self):
        return self._vswr_in

    @property
    def vswr_out(self):
        return self._vswr_out

    @property
    def s21_err(self):
        return self._s21s_err

    @property
    def s21_rmse(self):
        return self._s21s_rmse

    @property
    def adjust_set(self):
        return self._adjust_dir

    @adjust_set.setter
    def adjust_set(self, value):
        self._adjust_dir = self.adjust_dirs[value]

    @property
    def stats(self):
        stat_freq = self._secondaryParams['Fstat']
        stat_freq_index = _find_freq_index(self._freqs, stat_freq)
        vswr_in_at_stat_freq = round(self._vswr_in[0][stat_freq_index], 2)
        vswr_out_at_stat_freq = round(self._vswr_out[0][stat_freq_index], 2)

        s21_response_at_zero = self._s21s[0][stat_freq_index]

        low = self._min_freq_index
        high = self._max_freq_index
        mid = low + (high - low) // 2
        f1 = round(self.freqs[low] / 1_000_000_000, 2)
        f2 = round(self.freqs[mid] / 1_000_000_000, 2)
        f3 = round(self.freqs[high] / 1_000_000_000, 2)

        fstat = stat_freq

        cur1, cur2 = self._current
        cur1 *= 1_000
        cur2 *= 1_000

        return f'''Потребление тока при 5.25В:
{cur1} мА, 1 канал
{cur2} мА, 2 канал

Диапазон рабочих частот:
{curr} мА при 5.25В

Потери, минимум:
{self._s21_mins[0]:.02f} дБ на {f1} ГГц
{self._s21_mins[1]:.02f} дБ на {f2} ГГц
{self._s21_mins[2]:.02f} дБ на {f3} ГГц

Начальное ослабление:
{s21_response_at_zero} дБ на {fstat} ГГц

КСВ вх:
{vswr_in_at_stat_freq} на {fstat} ГГц

КСВ вых:
{vswr_out_at_stat_freq} на {fstat} ГГц

Нижняя граница РЧ, Fн:
{kp_freq_min}

Верхняя граница РЧ, Fв:
{kp_freq_max}
'''
