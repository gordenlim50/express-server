import numpy as np

def cal_LER(spd):
    Photopic_data = [ 3.90000000000000e-05, 6.40000000000000e-05, 0.000120000000000000, 0.000217000000000000, 
                     0.000396000000000000, 0.000640000000000000, 0.00121000000000000, 0.00218000000000000, 
                     0.00400000000000000, 0.00730000000000000, 0.0116000000000000, 0.0168400000000000, 
                     0.0230000000000000, 0.0298000000000000, 0.0380000000000000, 0.0480000000000000, 
                     0.0600000000000000, 0.0739000000000000, 0.0909800000000000, 0.112600000000000, 
                     0.139020000000000, 0.169300000000000, 0.208020000000000, 0.258600000000000, 
                     0.323000000000000, 0.407300000000000, 0.503000000000000, 0.608200000000000, 
                     0.710000000000000, 0.793200000000000, 0.862000000000000, 0.914850000000000, 
                     0.954000000000000, 0.980300000000000, 0.994950000000000, 1, 0.995000000000000, 
                     0.978600000000000, 0.952000000000000, 0.915400000000000, 0.870000000000000, 
                     0.816300000000000, 0.757000000000000, 0.694900000000000, 0.631000000000000, 
                     0.566800000000000, 0.503000000000000, 0.441200000000000, 0.381000000000000, 
                     0.321000000000000, 0.265000000000000, 0.217000000000000, 0.175000000000000, 
                     0.138200000000000, 0.107000000000000, 0.0816000000000000, 0.0610000000000000, 
                     0.0445800000000000, 0.0320000000000000, 0.0232000000000000, 0.0170000000000000, 
                     0.0119200000000000, 0.00821000000000000, 0.00572300000000000, 0.00410200000000000, 
                     0.00292900000000000, 0.00209100000000000, 0.00148400000000000, 0.00104700000000000, 
                     0.000740000000000000, 0.000520000000000000, 0.000361000000000000, 0.000249000000000000, 
                     0.000172000000000000, 0.000120000000000000, 8.50000000000000e-05, 6.00000000000000e-05, 
                     4.20000000000000e-05, 3.00000000000000e-05, 2.10000000000000e-05, 1.50000000000000e-05 ]

    wavelengths = np.arange(380, 781, 5)

    sum_p = 0
    sum_spd = 0
    for i in range(0,81):
        sum_p = sum_p + Photopic_data[i] * spd[i] * 100

    plux = 6.83 * sum_p * 5 # lm/m^2
    #print('plux', plux)

    total_irr = np.trapz(y=spd, x=wavelengths) # W/m^2
    #print('total_irr', total_irr)
    #total_power = total_irr * 19.77 # W

    ler = plux/total_irr # lm/W
    return ler