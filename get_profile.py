import Tkinter as tk

import cv2
from PIL import Image, ImageTk
import numpy as np
import time

import matplotlib
matplotlib.use('TkAgg')

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from lib import analysis

root = tk.Tk()
root.bind('<Escape>', lambda e: root.quit())
lmain = tk.Label(root)
lmain.pack()

class Controller(tk.Frame):
    def __init__(self, parent=root, camera_index=0):
        '''Initialises basic variables and GUI elements.'''
        self.start_time = time.time()
        self.angle = 0
        self.camera_index = 0
        self.colourmap = None
        self.centroid = None
        self.fig_type = 'cross profile'

        frame = tk.Frame.__init__(self, parent,relief=tk.GROOVE,width=100,height=100,bd=1)
        self.parent = parent
        self.var = tk.IntVar()

        self.parent.title('Laser Beam Profiler')
        
        menubar = tk.Menu(self.parent)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Export Data")
        filemenu.add_separator()
        filemenu.add_command(label="Quit", command=self.close_window)
        menubar.add_cascade(label="File", menu=filemenu)
        
        controlmenu = tk.Menu(menubar, tearoff=0)
        controlmenu.add_command(label="Take Screenshot", command=self.save_screenshot)
        controlmenu.add_separator()
        controlmenu.add_command(label="Clear Windows")
        menubar.add_cascade(label="Control", menu=controlmenu)
        
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", command=self.donothing)
        menubar.add_cascade(label="Help", menu=helpmenu)

        self.parent.config(menu=menubar)

        labelframe = tk.Frame(self)
        labelframe.pack(side=tk.LEFT) #.grid(row=0, column=0) 
        
        self.scale1 = tk.Scale(labelframe, label='exposure',
            from_=-1000000000, to=-10000,
            length=300, tickinterval=10000,
            showvalue='yes', 
            orient='horizontal',
            command = self.change_exp)
        self.scale1.pack()
        
        self.scale2 = tk.Scale(labelframe, label='gain',
            from_=-10000, to=10000,
            length=300, tickinterval=1,
            showvalue='yes', 
            orient='horizontal',
            command = self.change_gain)
        self.scale2.pack()
        
        self.scale3 = tk.Scale(labelframe, label='rotate',
            from_=0, to=360,
            length=300, tickinterval=30,
            showvalue='yes', 
            orient='horizontal',
            command = self.set_angle)
        self.scale3.pack()

        self.variable = tk.StringVar(labelframe)
        self.variable.set("0")
        self.dropdown1 = tk.OptionMenu(labelframe, self.variable, "0", "1", "2", command = self.change_cam)
        self.dropdown1.pack()
        
        self.variable2 = tk.StringVar(labelframe)
        self.variable2.set("normal")
        self.dropdown2 = tk.OptionMenu(labelframe, self.variable2, "normal", "jet", command = self.change_colourmap)
        self.dropdown2.pack()

        self.variable3 = tk.StringVar(labelframe)
        self.variable3.set("cross profile")
        self.dropdown3 = tk.OptionMenu(labelframe, self.variable3, "cross profile", "2d gaussian fit", command = self.change_fig)
        self.dropdown3.pack()
        
        self.make_fig()
        self.init_camera()
        self.show_frame() #initialise camera

    def make_fig(self):
        '''Creates a matplotlib figure to be placed in the GUI.'''

        plt.clf()
        plt.cla()
        
        if self.fig_type == 'cross profile':
            self.fig, self.ax = plt.subplots(1,2, gridspec_kw = {'width_ratios':[16, 9]})
        elif self.fig_type == '2d gaussian fit':
            self.fig = Figure(figsize=(4,4), dpi=100)

        # self.ax.set_ylim(0,255)
        canvas = FigureCanvasTkAgg(self.fig, self) 
        canvas.show() 
        canvas.get_tk_widget().pack() 

        toolbar = NavigationToolbar2TkAgg(canvas, self) 
        toolbar.update() 
        canvas._tkcanvas.pack()
        
    def refresh_plot(self):
        '''Updates the matplotlib figure with new data.'''
       
        grayscale = np.array(Image.fromarray(self.img).convert('L'))
        
        if self.fig_type == 'cross profile':
            if self.centroid != None:
                self.ax[0].plot(range(self.width), grayscale[self.centroid[1],:],'k-')
                self.ax[1].plot(grayscale[:,self.centroid[0]], range(self.height),'k-')              
                self.ax[0].set_ylim(0,255)
                self.ax[1].set_xlim(0,255)
                
        elif self.fig_type == '2d gaussian fit':
            if self.centroid != None:
                size = 50
                x, y = self.centroid
                img = grayscale[y-size/2:y+size/2, x-size/2:x+size/2]
                params = analysis.fit_gaussian(img, with_bounds=False)
                analysis.plot_gaussian(plt.gca(), img, params)
        
        # self.ax[0].hold(True)
        # self.ax[1].hold(True)
        
        self.fig.canvas.draw() 
        
        for axis in self.fig.get_axes():
            axis.clear()
    
    def change_exp(self, option):
        '''Changes the exposure time of the camera.'''
        exp = float(option)
        print 'changing exp to', exp
        self.cap.set(15, exp)
        
    def change_gain(self, option):
        '''Changes the gain of the camera.'''
        gain = float(option)
        print 'changing gain to', gain
        self.cap.set(14, gain)

    def init_camera(self):
        '''Initialises the camera with a set resolution.'''
        self.width, self.height = 640, 360
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap:
            raise Exception("Camera not accessible")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                  
    def change_cam(self, option):
        '''Switches between camera_indexes and therefore different connected cameras.'''
        if self.camera_index != int(self.variable.get()):
            self.camera_index = int(self.variable.get())
            print 'camera index change, now to update view...', self.camera_index
            self.cap.release()
            self.init_camera()
            self.show_frame()
    
    def change_colourmap(self, option):
        '''Changes the colourmap used in the camera feed.'''
        if self.colourmap != option:
            print 'changed colourmap', option
            if option == 'jet':
                self.colourmap = cv2.COLORMAP_JET
            else:
                self.colourmap = None
            
    def change_fig(self, option):
        '''Changes the fig used.'''
        if self.fig_type != option:
            print 'changed fig', option
            self.fig_type = option
    
    def show_frame(self):
        '''Shows camera view with relevant labels and annotations included.'''
        _, frame = self.cap.read()
        # frame = cv2.flip(frame, 1)
        if self.colourmap is None:
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        else:
            cv2image = cv2.applyColorMap(frame, self.colourmap)
        
        cv2.putText(cv2image,"Laser Beam profiler", (10,40), cv2.FONT_HERSHEY_PLAIN, 1, (255,255,255))
        dim = np.shape(cv2image)
        
        # convert to greyscale
        tracking = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        
        cv2.putText(cv2image,'Peak Value: ' + str(np.max(tracking)) + str(analysis.get_max(tracking,3)), (10,325), cv2.FONT_HERSHEY_PLAIN, 1, (255,255,255))
        
        centroid = analysis.find_centroid(tracking)
        if centroid[0] < self.width or centroid[1] < self.height:
            if centroid != (None, None):
                cv2.circle(cv2image,centroid,10,255,thickness=10)
                cv2.putText(cv2image,'Centroid position: ' + str(centroid), (10,310), cv2.FONT_HERSHEY_PLAIN, 1, (255,255,255))
                self.centroid = centroid
            else:
                self.centroid = None
        else:
            self.centroid = None

        # ellipse = analysis.find_ellipse(tracking)
        # if ellipse != None:
            # print 'ellipse success'
            # cv2.ellipse(cv2image,ellipse,(0,255,0),20)
            
        if self.angle != 0:
            img = self.rotate_image(cv2image)
        else:
            img = Image.fromarray(cv2image)
            
        imgtk = ImageTk.PhotoImage(image=img)
            
        lmain.imgtk = imgtk
        lmain.configure(image=imgtk)
        lmain.after(10, self.show_frame)
        
        self.img = frame
        if time.time() - self.start_time > 1:
            self.refresh_plot()
            self.start_time = time.time()
        
    def set_angle(self, option):
        '''Sets the rotation angle.'''
        self.angle = float(option)
        
    def rotate_image(self, image):
        '''Rotates the given array by the rotation angle, returning as a PIL image.'''
        image_centre = tuple(np.array(image.shape)/2)
        image_centre = (image_centre[0], image_centre[1])
        rot_mat = cv2.getRotationMatrix2D(image_centre,self.angle,1.0)
        result = cv2.warpAffine(image, rot_mat, (image.shape[0], image.shape[1]), flags=cv2.INTER_LINEAR)
        return Image.fromarray(result)
  
    def close_window(self):
        '''Closes the GUI.'''
        self.parent.quit()
        self.parent.destroy()
        
    def donothing(self):
       filewin = tk.Toplevel(self.parent)
       input = tk.Text(filewin)
       input.configure(state=tk.DISABLED,
        borderwidth=0,
        background=root.cget('background'))
       input.insert(tk.END, "Laser Beam Profiler created by Samuel Bancroft \n Summer 2016 Internship Project \n Dr Jon Goldwin, Birmingham University")
       
    def save_screenshot(self):
        cv2.imwrite('output.png', self.img) 
        
c = Controller(root)
c.pack()
root.mainloop()