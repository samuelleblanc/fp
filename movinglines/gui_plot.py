#!/usr/bin/python3
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox


from matplotlib.figure import Figure
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

try:
    from matplotlib.backends.backend_tkagg import  NavigationToolbar2Tk as NavigationToolbar2TkAgg
except:
    from matplotlib.backends.backend_tkagg import NavigationToolbar2TkAgg
	
import numpy as np

__version__ = 'v1.26'

profile_filename = 'profiles.txt'
platform_filename = 'platform.txt'
icon_filename = 'arc.ico'

class window:
    def __init__(self, root):
        self.root = root
        self.root.wm_title('Moving Lines: Flight planning '+__version__)
        self.root.geometry('900x950')
        self.w = 900
        self.fig = Figure()
        #self.ax1 = self.fig.add_subplot(111)
        try:
            self.root.tk.call('wm','iconbitmap',ui.root._w,'-default',icon_filename)
        except:
            pass
        self.create_left_buttons()
        self.create_right_graph()    

    def create_right_graph(self):
        right_frame = ttk.Frame(self.root)
        right_frame.pack(side=tk.RIGHT,fill=tk.BOTH,expand=True)
        self.canvas = FigureCanvasTkAgg(self.fig,right_frame) 
        self.canvas.get_tk_widget().pack(in_=right_frame,side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        self.canvas.draw()
        self.tb = NavigationToolbar2TkAgg(self.canvas,right_frame)
        self.tb.pack(in_=right_frame,side=tk.BOTTOM)
        self.tb.update()
        self.canvas._tkcanvas.pack(in_=right_frame,side=tk.TOP,fill=tk.BOTH, expand=1)

    def create_left_buttons(self):
        left_frame = ttk.Frame(self.root)
        left_frame.pack(side=tk.LEFT,expand=False)
        side = tk.TOP
        h = 2
        w = 20
        label = ttk.Label(self.root,text='by Samuel LeBlanc\n NASA Ames')
        label.pack(in_=left_frame,side=tk.BOTTOM)
        self.left_frame = left_frame
        self.top = left_frame


if __name__ == '__main__':
    
    ui = window(tk.Tk())
    ui.root.mainloop()