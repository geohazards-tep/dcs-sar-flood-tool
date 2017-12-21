import numpy as np

# damping factor for lee enhanced
K_DEFAULT = 1.0

# coefficient of variation for lee enhanced of noise
CU_DEFAULT = 0.523

# max coefficient of variation for lee enhanced
CMAX_DEFAULT = 1.73


def assert_window_size(win_size):
    """
    Asserts invalid window size.
    Window size must be odd and bigger than 3.
    """
    assert win_size >= 3, 'ERROR: win size must be at least 3'

    if win_size % 2 == 0:
        print 'It is highly recommended to user odd window sizes.'\
              'You provided %s, an even number.' % (win_size, )


def assert_parameters(k, cu, cmax):
    """
    Asserts parameters in range.
    Parameters:
        - k: in [0:10]
        - cu: positive
        - cmax: positive and greater equal than cu
    """

    assert 0 <= k <= 10, \
        "k parameter out of range 0<= k <= 10, submitted %s" % k

    assert cu >= 0, \
        "cu can't be negative"

    assert cmax >= 0 and cmax >= cu, \
        "cmax must be positive and greater equal to cu: %s" % cu


def nan_uniform_filter(img, win_size):
    from scipy.ndimage import uniform_filter

    nan_mask = ~np.isfinite(img)
    
    filled_img = np.copy(img)
    filled_img[nan_mask] = 0.0

    mean_nan = (1. - uniform_filter(nan_mask.astype(float), win_size))
    filtered_image = uniform_filter(filled_img, win_size)
    filtered_image /= mean_nan

    filtered_image[filtered_image < 0.0] = 0.0
    filtered_image[~np.isfinite(filtered_image)] = np.nan

    return filtered_image

def lee_enhanced_filter(img, win_size=3, k=K_DEFAULT, cu=CU_DEFAULT, cmax=CMAX_DEFAULT):
    """
    Apply Enhanced Lee filter to a numpy matrix containing the image, with a
    window of win_size x win_size.
    """


    assert_window_size(win_size)
    assert_parameters(k, cu, cmax)

    img = img.astype("float64")

#    print "Variation Coefficients calculation"
    mean_image = nan_uniform_filter(img, win_size)
    ci_image = np.sqrt(nan_uniform_filter(img**2, win_size) - mean_image**2)  # standard deviation image
    ci_image /= mean_image

#    print "Weights calculation"
    w_t_image = np.exp((-k * (ci_image - cu)) / (cmax - ci_image))
    w_t_image[ci_image <= cu] = 1.0
    w_t_image[ci_image >= cmax] = 0.0


#    print "Filter Execution"
    img_filtered = mean_image * w_t_image + img * (1.0 - w_t_image)
    img_filtered[img_filtered < 0.0] = 0.0

    return img_filtered
