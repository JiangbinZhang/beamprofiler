import math
import numpy as np
import cv2
import pyaudio
import threading

class WavePlayerLoop(threading.Thread) :
  """
  A simple class based on PyAudio to play sine wave at certain frequency.
  It's a threading class. You can play audio while your application
  continues to do stuff.
  """

  def __init__(self, freq=440., length=1., volume=0.5):
    threading.Thread.__init__(self)
    self.p = pyaudio.PyAudio()

    self.volume = volume     # range [0.0, 1.0]
    self.fs = 44100          # sampling rate, Hz, must be integer
    self.duration = length   # in seconds, may be float
    self.f = freq            # sine frequency, Hz, may be float

  def run(self) :
    """
    Just another name for self.start()
    """
    # generate samples, note conversion to float32 array
    self.samples = (np.sin(2*np.pi*np.arange(self.fs*self.duration)*self.f/self.fs)).astype(np.float32)

    # for paFloat32 sample values must be in range [-1.0, 1.0]
    self.stream = self.p.open(format=pyaudio.paFloat32,
                    channels=1,
                    rate=self.fs,
                    output=True)

    # play. May repeat with different volume values (if done interactively) 
    self.stream.write(self.volume*self.samples)

    self.stream.stop_stream()
    self.stream.close()

    self.p.terminate()
    
def rotate_image(image, angle):
    """
    Rotates an OpenCV 2 / NumPy image about it's centre by the given angle
    (in degrees). The returned image will be large enough to hold the entire
    new image, with a black background
    """

    # Get the image size
    # No that's not an error - NumPy stores image matricies backwards
    image_size = (image.shape[1], image.shape[0])
    image_centre = tuple(np.array(image_size) / 2)

    # Convert the OpenCV 3x2 rotation matrix to 3x3
    rot_mat = np.vstack(
        [cv2.getRotationMatrix2D(image_centre, angle, 1.0), [0, 0, 1]]
    )

    rot_mat_notranslate = np.matrix(rot_mat[0:2, 0:2])

    # Shorthand for below calcs
    image_w2 = image_size[0] * 0.5
    image_h2 = image_size[1] * 0.5

    # Obtain the rotated coordinates of the image corners
    rotated_coords = [
        (np.array([-image_w2,  image_h2]) * rot_mat_notranslate).A[0],
        (np.array([ image_w2,  image_h2]) * rot_mat_notranslate).A[0],
        (np.array([-image_w2, -image_h2]) * rot_mat_notranslate).A[0],
        (np.array([ image_w2, -image_h2]) * rot_mat_notranslate).A[0]
    ]

    # Find the size of the new image
    x_coords = [pt[0] for pt in rotated_coords]
    x_pos = [x for x in x_coords if x > 0]
    x_neg = [x for x in x_coords if x < 0]

    y_coords = [pt[1] for pt in rotated_coords]
    y_pos = [y for y in y_coords if y > 0]
    y_neg = [y for y in y_coords if y < 0]

    right_bound = max(x_pos)
    left_bound = min(x_neg)
    top_bound = max(y_pos)
    bot_bound = min(y_neg)

    new_w = int(abs(right_bound - left_bound))
    new_h = int(abs(top_bound - bot_bound))

    # We require a translation matrix to keep the image centred
    trans_mat = np.matrix([
        [1, 0, int(new_w * 0.5 - image_w2)],
        [0, 1, int(new_h * 0.5 - image_h2)],
        [0, 0, 1]
    ])

    # Compute the tranform for the combined rotation and translation
    affine_mat = (np.matrix(trans_mat) * np.matrix(rot_mat))[0:2, :]

    # Apply the transform
    result = cv2.warpAffine(
        image,
        affine_mat,
        (new_w, new_h),
        flags=cv2.INTER_LINEAR
    )

    return result

def largest_rotated_rect(w, h, angle):
    """
    Given a rectangle of size wxh that has been rotated by 'angle' (in
    radians), computes the width and height of the largest possible
    axis-aligned rectangle within the rotated rectangle.

    Original JS code by 'Andri' and Magnus Hoff from Stack Overflow

    Converted to Python by Aaron Snoswell
    """

    quadrant = int(math.floor(angle / (math.pi / 2))) & 3
    sign_alpha = angle if ((quadrant & 1) == 0) else math.pi - angle
    alpha = (sign_alpha % math.pi + math.pi) % math.pi

    bb_w = w * math.cos(alpha) + h * math.sin(alpha)
    bb_h = w * math.sin(alpha) + h * math.cos(alpha)

    gamma = math.atan2(bb_w, bb_w) if (w < h) else math.atan2(bb_w, bb_w)

    delta = math.pi - alpha - gamma

    length = h if (w < h) else w

    d = length * math.cos(alpha)
    a = d * math.sin(alpha) / math.sin(delta)

    y = a * math.cos(gamma)
    x = y * math.tan(gamma)

    return (
        bb_w - 2 * x,
        bb_h - 2 * y
    )

def crop_around_centre(image, width, height):
    """
    Given a NumPy / OpenCV 2 image, crops it to the given width and height,
    around its centre point
    """

    image_size = (image.shape[1], image.shape[0])
    image_centre = (int(image_size[0] * 0.5), int(image_size[1] * 0.5))

    if(width > image_size[0]):
        width = image_size[0]

    if(height > image_size[1]):
        height = image_size[1]

    x1 = int(image_centre[0] - width * 0.5)
    x2 = int(image_centre[0] + width * 0.5)
    y1 = int(image_centre[1] - height * 0.5)
    y2 = int(image_centre[1] + height * 0.5)

    return image[y1:y2, x1:x2]
       
def scale(A, B, k):     
    '''fill A with B scaled by k'''
    Y = A.shape[0]
    X = A.shape[1]
    for y in range(0, k):
        for x in range(0, k):
            A[y:Y:k, x:X:k] = B
            
def gauss(x, *p):
    A, mu, sigma = p
    return A*np.exp(-(x-mu)**2/(2.*sigma**2))