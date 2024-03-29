import numpy as np
import logging
import matplotlib

matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from scipy.signal import argrelextrema
import scipy.io as sio
import pywt

from scipy.signal import butter, lfilter, filtfilt

all_s = {}
fs = 5000.0
lowcut = 30.0
highcut = 1000.0
v='bior4.4'
thres=[0.1,0.4,0.6]
counter = 0

def lowpassfilter(signal, thresh=0.4, wavelet=v):
    thresh = thresh*np.nanmax(signal)
    coeff = pywt.wavedec(signal, wavelet, level=8,mode="per" )
    coeff[1:] = (pywt.threshold(i, value=thresh, mode='soft' ) for i in coeff[1:])
    reconstructed_signal = pywt.waverec(coeff, wavelet, mode="per" )
    return reconstructed_signal

def lowfilter(signal, N = 2, Wn = 0.08):
    B, A = butter(N, Wn, output='ba')
    signalf = filtfilt(B, A, signal)
    return signalf

def butter_bandpass(lowcut, highcut, fs, order=5):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a

def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = lfilter(b, a, data)
    return y

def get_indexes(start, end, titles, filter = False):             #берёт индексы из мышцы-флексера пациента
    k=0                                                          #фильтрует график, выбирает максимумы
    for s, e, t in zip(start, end, titles):                      #по нескольким критериям
        if "TA L" in t:
            d = data[int(s+50*40):int(e)] + 2 * k
            if len(d) == 0:
                d = np.array([0] * 200)
            if filter:
                d = butter_bandpass_filter(np.array(d), lowcut, highcut, fs) + 2 * k
                d = lowfilter(np.array(d))
            indexes = argrelextrema(d, np.greater)[0]       #берёт пики
            values = d[indexes]
            indexes = indexes[values > max(values)*0.745]   #экстремумы не менее 75% от максимума
            values = values[values > max(values)*0.745]

            diff_steps = []
            diff_steps.append(True)
            for i in range (1, len(indexes)):               #убирает максимумы, лежащие ближе 4000мс друг от друга
                if indexes[i] - indexes[i-1] > 1000/0.25:
                    diff_steps.append(True)
                else:
                    diff_steps.append(False)
            indexes = indexes[diff_steps]
            values = values[diff_steps]
        k += 1
    return indexes, values

def draw_channels(start, end, titles, k = 0, filter = False): #no usage
    logger.info("channels")
    yticks = []
    titl = []
    indexes, values = get_indexes(start, end, titles, True)
    for s, e, t in zip(start, end, titles):
        # channels
        if "ACC" not in t and "GYRO" not in t and "MAG" not in t and "Art" not in t and "Channel" not in t:
            d = data[int(s+50*40):int(e)] + k*0.7
            if len(d) == 0:
                d = np.array([0] * 200) + k

            if filter:
                d = butter_bandpass_filter(np.array(d), lowcut, highcut, fs) + k*0.4
                d = lowfilter(np.array(d))
            print(len(indexes))
            for i in range(1, len(indexes)):
                plt.plot(i*20000+np.arange(len(d[indexes[i-1]:indexes[i]])) * 0.25, d[indexes[i-1]:indexes[i]])

            titl.append(t)
            yticks.append(d[0])
            k += 1
    plt.yticks(yticks, titl)
    plt.show()

def get_two_max_pics(p):
    indexes_extrem_in_slice = argrelextrema(p, np.greater)[0]
    if len(indexes_extrem_in_slice) == 0:
        return 'Maximum not found'
    values_extrem_in_slice = p[indexes_extrem_in_slice]

    def get_index(val, target):
        return np.where(target == val)[0][0]

    max_pic = max(values_extrem_in_slice)
    index_of_max = get_index(max_pic, values_extrem_in_slice)
    cuted_veis = values_extrem_in_slice[index_of_max + 1 :]   #вырезаем значения до максимума включительно из массива
    if len(cuted_veis) == 0:
        return 'Second largest extremum not found'
    max_pic2 = max(cuted_veis)
    return np.array([max_pic, max_pic2]), np.array([get_index(max_pic, p), get_index(max_pic2, p)])

def get_coord(slice, mod_formater = False):
    if min(slice) < 0 and mod_formater:                                       # поднимаем график если есть отрицателное значение
        slice_of_pics_formated = slice - np.array([min(slice)] * len(slice))  # вычитаем массив минимума из массива всех значений
    else:
        slice_of_pics_formated = slice
    quadro_between_pics = np.array([slice_of_pics_formated[0], slice_of_pics_formated[-1]])  # отрезок между двумя максимумами
    pics_x = np.arange(len(slice_of_pics_formated)) * 0.25                                   # массив оси Х
    quadro_x = np.array([pics_x[0], pics_x[-1]])

    return slice_of_pics_formated, quadro_between_pics, pics_x, quadro_x

def get_s_of_pics(p):
    global counter
    two_max_pics = get_two_max_pics(p)
    if two_max_pics == 'Maximum not found' or two_max_pics == 'Second largest extremum not found':
        return two_max_pics
    values_of_max_pics, indexes_of_max = two_max_pics
    slice_of_pics = p[indexes_of_max[0]: indexes_of_max[1]]  #вырезаем массив между двумя максимумами

    slice_of_pics_formated, quadro_between_pics, pics_x, quadro_x = get_coord(slice_of_pics, mod_formater=True)
    s_sop = np.trapz(slice_of_pics_formated, pics_x)
    s_qbp = np.trapz(quadro_between_pics, quadro_x)

    cord = get_coord(slice_of_pics)
    y = cord[1]
    x = cord[3] + [np.arange(indexes_of_max[0] + 1)[-1] * 0.25] * len(cord[3])
    colors = ["blue", "orange", "green", "red", "purple"]
    square = s_qbp - s_sop
    plt.plot(x[0], y[0], 'g^')
    plt.plot(x[1], y[1], 'g^')
    plt.text(x[0] + 5, y[0], square, color = colors[counter], fontsize= 15)
    return square

def draw_slices(start, end, titles, period, filter = False):          #нарезает слайсы между экстремумами TA L и Art 2
    logger.info("slices")
    indexes, values = get_indexes(start, end, titles, True)
    plt.figure(figsize=(10, 20))                                                    #
    global counter
    starts = []
    for j in range(0, len(indexes)-1):
        for s, e, t in zip(start, end, titles):
            if "Art 2" in t:
                d = data[int(s+50*40):int(e)]
                d = d[indexes[j]:indexes[j+1]]     # создает массив с всеми данными по арт 2 по заданным параметрам
                s = argrelextrema(d, np.greater)[0]# + 2 *k #фильтрует Арт 2 так же как ТА Л
                values = d[s]
                s = s[values > max(values)*0.745]
                starts.append(s[0]+indexes[j])
                print(f'ind - {indexes[j]}, start {s[0]} {starts[j]}')

    for j in range(0, len(indexes)-1):
        for s, e, t in zip(start, end, titles):
            # slices
            if "ACC" not in t and "GYRO" not in t and "MAG" not in t and "Channel" not in t:
                all_s[f'{t}_time{starts[j] * 0.25}_f'] = []
                logger.info("muscle is here")
                d = data[int(s+50*40):int(e)]
                if filter:
                    d = lowfilter(np.array(d))

                    d = butter_bandpass_filter(np.array(d), lowcut, highcut, fs)

                logger.info(len(d))
                plt.clf()
                slice_height = (np.max(d[indexes[j]:indexes[j+1]]) - np.min(d[indexes[j]:indexes[j+1]]))*0.25
                step_len = int((indexes[j+1]-indexes[j])*0.25/period)
                print(f'step len {step_len}')
                if step_len > 5:
                    step_len = 5
                for i in range(step_len):
                    p = d[starts[j]+i*period*4:starts[j]+(i+1)*period*4] + slice_height *i  #formula for plot
                    plt.plot(np.arange(len(p)) * 0.25, p)
                    # plt.legend(['Original','Filtered', 'R', 'Bandpass'])
                    all_s[f'{t}_time{starts[j] * 0.25}_f'].append(get_s_of_pics(p))
                    counter += 1
                    if counter > 4:
                        counter = 0
                plt.savefig(f'./graphs/new/{t}_time{starts[j]*0.25}_f.png')

#Start it up!
slice_height = 0.02
logging.basicConfig(format='[%(funcName)s]: %(message)s', level=logging.INFO)
logger = logging.getLogger()
mat_contents = sio.loadmat('./humandata_new/6v/17062021 2+5- 210ms 20hz 10.2ma  walk 3.mat')

for i in sorted(mat_contents.keys()):
    logger.info(i)
    logger.info(mat_contents[i])
    logger.info(len(mat_contents[i]))

starts = mat_contents['datastart']
print(len(starts))
ends = mat_contents['dataend']
logger.info(ends - starts)
data = mat_contents['data'][0]
titles = mat_contents['titles']
logger.info(len(data))

# constants
period = 50

for i in range(1):
    start = starts[:, i]
    end = ends[:, i]
    k = 0
    # draw_channels(start, end, titles, filter = True)
    draw_slices(start, end, titles,  period, filter = True)