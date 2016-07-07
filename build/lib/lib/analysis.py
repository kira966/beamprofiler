import cv2
import numpy as np

import scipy.optimize as opt

import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.patches import Circle

def find_centroid(tracking):
    '''Takes greyscale cv2 image and finds one centroid position.'''
    
    kernel = np.ones((5,5),np.uint8)

    #These values work well 
    gmn = 240
    gmx = 255

    #initialise centroid variables for later in programme
    cx = 0
    cy = 0

    #apply thresholding to greyscale frames. 
    #inRange checks if array elements lie between the elements of two other arrays
    gthresh = cv2.inRange(np.array(tracking),np.array(gmn),np.array(gmx))

    # Some morphological filtering
    dilation = cv2.dilate(tracking,kernel,iterations = 2)
    closing = cv2.morphologyEx(dilation, cv2.MORPH_CLOSE, kernel)
    closing = cv2.Canny(closing, 50, 200)

    # find contours in the threshold image
    _,contours,hierarchy = cv2.findContours(closing,cv2.RETR_LIST,cv2.CHAIN_APPROX_TC89_L1)

    # finding contour with maximum area and store it as best_cent
    max_area = 0

    for cent in contours:
        area = cv2.contourArea(cent)
        if area > max_area:
            max_area = area
            best_cent = cent

            # finding centroids of best_cent and draw a circle there
            M = cv2.moments(best_cent)
            cx,cy = int(M['m10']/M['m00']), int(M['m01']/M['m00'])
            break
    else:
        cx = None
        cy = None
        
    centroid = (cx, cy)

    return centroid
    
def find_ellipse(tra):
        ret,thresh = cv2.threshold(tracking,127,255,0)
        _,contours,hierarchy = cv2.findContours(thresh, 1, 2)
        cnt = contours[0]
        try:
            ellipse = cv2.fitEllipse(cnt)
        except:
            ellipse = None
        
        return ellipse
    
# 2D Gaussian model
def func(xy, x0, y0, sigma, H):

    x, y = xy

    A = 1 / (2 * sigma**2)
    I = H * np.exp(-A * ( (x - x0)**2 + (y - y0)**2))
    return I
    
def fit_gaussian(image, with_bounds):

    # Prepare fitting
    x = np.arange(0, image.shape[1], 1)
    y = np.arange(0, image.shape[0], 1)
    xx, yy = np.meshgrid(x, y)

    # Guess initial parameters
    x0 = int(image.shape[0])/2 # Middle of the image
    y0 = int(image.shape[1])/2 # Middle of the image
    sigma = max(*image.shape) * 0.1 # 10% of the image
    H = np.max(image) # Maximum value of the image
    initial_guess = [x0, y0, sigma, H]

    # Constraints of the parameters
    if with_bounds:
        lower = [0, 0, 0, 0]
        upper = [image.shape[0], image.shape[1], max(*image.shape), image.max() * 2]
        bounds = [lower, upper]
    else:
        bounds = [-np.inf, np.inf]

    try:
        pred_params, uncert_cov = opt.curve_fit(func, (xx.ravel(), yy.ravel()), image.ravel(),
                                        p0=initial_guess, bounds=bounds)
    except:
        pred_params, uncert_cov = [[0,0,1], [0,0,1]]

    # Get residual
    predictions = func((xx, yy), *pred_params)
    rms = np.sqrt(np.mean((image.ravel() - predictions.ravel())**2))

    # print("True params : ", true_parameters)
    # print("Predicted params : ", pred_params)
    # print("Residual : ", rms)

    return pred_params

def plot_gaussian(ax, image, params):
    ax.imshow(image, cmap=plt.cm.BrBG, interpolation='nearest', origin='lower')

    ax.scatter(params[0], params[1], s=100, c="red", marker="x")

    circle = Circle((params[0], params[1]), params[2], facecolor='none',
            edgecolor="red", linewidth=1, alpha=0.8)
    ax.add_patch(circle)
    
def get_max(image,sigma,alpha=3,size=10):
    # preallocate a lot of peak storage
    k_arr = np.zeros((10000,2))
    image_temp = image.copy()
    peak_ct=0
    while True:
        k = np.argmax(image_temp)
        j,i = np.unravel_index(k, image_temp.shape)
        if(image_temp[j,i] >= alpha*sigma):
            k_arr[peak_ct]=[j,i]
            # this is the part that masks already-found peaks.
            x = np.arange(i-size, i+size)
            y = np.arange(j-size, j+size)
            xv,yv = np.meshgrid(x,y)
            # the clip here handles edge cases where the peak is near the 
            #    image edge
            image_temp[yv.clip(0,image_temp.shape[0]-1),
                               xv.clip(0,image_temp.shape[1]-1) ] = 0
            peak_ct+=1
        else:
            break
    # trim the output for only what we've actually found
    if len(k_arr[:peak_ct]) > 0:
        firstmaxvalue = ' at position (' + str(k_arr[:peak_ct][:,1][0]) + ', ' + str(k_arr[:peak_ct][:,0][0]) + ')'
    else:
        firstmaxvalue = ''
    return firstmaxvalue #returns one value at the moment, should be good enough for now