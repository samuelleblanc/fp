#!/usr/bin/python3
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

import threading
import queue
import time

from matplotlib.figure import Figure
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

try:
    from matplotlib.backends.backend_tkagg import  NavigationToolbar2Tk as nav_tool
except:
    from matplotlib.backends.backend_tkagg import NavigationToolbar2TkAgg as nav_tool

import numpy as np


class MyThread(threading.Thread):

    def __init__(self, queue, which, ops, interval):
        threading.Thread.__init__(self)

        self.queue = queue
        self.check = True
        self.which = which
        self.ops = ops
        self.interval = interval

    def stop(self):
        self.check = False

    def run(self):

        while self.check:

            if self.which.get() ==0:
                lam = np.random.exponential(scale=.1, size = 100).reshape(-1,1)
            else:
                lam = np.random.normal(loc=5, scale=1, size = 100).reshape(-1,1)

            time.sleep(self.interval.get())
            args = (lam, self.ops[self.which.get()])
            self.queue.put(args)
        else:
            args = (None, "I'm stopped")
            self.queue.put(args)

class Main(ttk.Frame):
    def __init__(self, parent):
        super().__init__()

        self.parent = parent

        self.which = tk.IntVar()
        self.interval = tk.DoubleVar()
        self.queue = queue.Queue()
        self.my_thread = None

        self.init_ui()

    def init_ui(self):

        f = ttk.Frame()
        #create graph!
        self.fig = Figure()
        self.fig.suptitle("Hello Matplotlib", fontsize=16)
        self.a = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, f)
        toolbar = nav_tool(self.canvas, f)
        toolbar.update()
        self.canvas._tkcanvas.pack(fill=tk.BOTH, expand=1)

        w = ttk.Frame()

        ttk.Button(w, text="Animate", command=self.launch_thread).pack()
        ttk.Button(w, text="Stop", command=self.stop_thread).pack()
        ttk.Button(w, text="Close", command=self.on_close).pack()

        self.ops = ('Exponential','Normal',)            

        self.get_radio_buttons(w,'Choice', self.ops, self.which,self.on_choice_plot).pack(side=tk.TOP, fill=tk.Y, expand=0)

        ttk.Label(w, text = "Interval").pack()

        tk.Spinbox(w,
                    bg='white',
                    from_=1.0, to=5.0,increment=0.5,
                    justify=tk.CENTER,
                    width=8,
                    wrap=False,
                    insertwidth=1,
                    textvariable=self.interval).pack(anchor=tk.CENTER) 

        w.pack(side=tk.RIGHT, fill=tk.BOTH, expand=1)
        f.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

    def launch_thread(self):

        self.on_choice_plot()

    def stop_thread(self):

        if self.my_thread is not None:
            if(threading.active_count()!=0):
                self.my_thread.stop()

    def on_choice_plot(self, evt=None):

        if self.my_thread is not None:

            if (threading.active_count()!=0):

                self.my_thread.stop()

        self.my_thread = MyThread(self.queue,self.which, self.ops, self.interval)
        self.my_thread.start()
        self.periodiccall()

    def periodiccall(self):

        self.checkqueue()
        if self.my_thread.is_alive():
            self.after(1, self.periodiccall)
        else:
            pass

    def checkqueue(self):
        while self.queue.qsize():
            try:

                args = self.queue.get()
                self.a.clear()
                self.a.grid(True)

                if args[0] is not None:
                    self.a.step(list(range(100)), list(args[0]))
                    self.a.set_title(args[1], weight='bold',loc='left')
                else:
                    self.a.set_title(args[1], weight='bold',loc='left')

                self.canvas.draw()

            except queue.Empty:
                pass        


    def get_radio_buttons(self, container, text, ops, v, callback=None):

        w = ttk.LabelFrame(container, text=text,)

        for index, text in enumerate(ops):
            ttk.Radiobutton(w,
                            text=text,
                            variable=v,
                            command=callback,
                            value=index,).pack(anchor=tk.W)     
        return w        


    def on_close(self):

        if self.my_thread is not None:

            if(threading.active_count()!=0):
                self.my_thread.stop()

        self.parent.on_exit()

class App(tk.Tk):
    """Start here"""

    def __init__(self):
        super().__init__()

        self.protocol("WM_DELETE_WINDOW", self.on_exit)

        self.set_title()
        self.set_style()

        Main(self)

    def set_style(self):
        self.style = ttk.Style()
        #('winnative', 'clam', 'alt', 'default', 'classic', 'vista', 'xpnative')
        self.style.theme_use("clam")

    def set_title(self):
        s = "{0}".format('Simple App')
        self.title(s)

    def on_exit(self):
        """Close all"""
        if messagebox.askokcancel("Simple App", "Do you want to quit?", parent=self):
            self.destroy()               

if __name__ == '__main__':
    app = App()
    app.mainloop()