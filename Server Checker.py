#Developed by Ashank Anshuman
#Written on Python 2.7.9
#Server Checker v1.0.1
#This program checks for active CoD4 Servers on IPs present in the IP list periodically.
#IPs can be added and removed from the IP list via the IP Manager.
#This program uses multi-threading to run GUI(Tkinter) on Main thread and the function which checks for servers indefinitely on another thread.
#Winico and TkTray are external libraries required for this program(Taskbar Icon)
# -*- coding: utf-8 -*-
import Tkinter
import platform
import types
import os
import TkTray
import Winico
import threading
from time import sleep
from Tkinter import *
import socket
from win32api import *
from win32gui import *
import win32con
import sys
import ttk
from PIL import ImageTk, Image
import tkMessageBox
_platform = platform.system()

port = int(28960)           #Port on which CoD4 servers run
global ip_list
try:
    ip_list = [line.strip() for line in open("ip_list.txt", 'r')]       #Retrieves IPs from the file "ip_list.txt"
except:
    file = open("ip_list.txt", 'w')
    file.close()
    ip_list = []

##########################################################################################################################
##########################################################################################################################
##Minimisation to Taskbar
    
# ToolTip class, taken from the tkinter wiki, with the coords() method
# modified for use with tray icons;
# winico icons have a built-in tooltip which is mandatory,
# to be compatible, we need to create our own tooltips on X
class ToolTip:
    def __init__(self, master, text='Your text here', delay=1500, **opts):
        self.master = master
        self._opts = {'anchor':'center', 'bd':1, 'bg':'lightyellow', 'delay':delay, 'fg':'black',\
                      'follow_mouse':0, 'font':None, 'justify':'left', 'padx':4, 'pady':2,\
                      'relief':'solid', 'state':'normal', 'text':text, 'textvariable':None,\
                      'width':0, 'wraplength':150}
        self.configure(**opts)
        self._tipwindow = None
        self._id = None
        self._id1 = self.master.bind("<Enter>", self.enter, '+')
        self._id2 = self.master.bind("<Leave>", self.leave, '+')
        self._id3 = self.master.bind("<ButtonPress>", self.leave, '+')
        self._follow_mouse = 0
        if self._opts['follow_mouse']:
            self._id4 = self.master.bind("<Motion>", self.motion, '+')
            self._follow_mouse = 1

    def configure(self, **opts):
        for key in opts:
            if self._opts.has_key(key):
                self._opts[key] = opts[key]
            else:
                KeyError = 'KeyError: Unknown option: "%s"' %key
                raise KeyError

    ##----these methods handle the callbacks on "<Enter>", "<Leave>" and "<Motion>"---------------##
    ##----events on the parent widget; override them if you want to change the widget's behavior--##

    def enter(self, event=None):
        self._schedule()

    def leave(self, event=None):
        self._unschedule()
        self._hide()

    def motion(self, event=None):
        if self._tipwindow and self._follow_mouse:
            x, y = self.coords()
            self._tipwindow.wm_geometry("+%d+%d" % (x, y))

    ##------the methods that do the work:---------------------------------------------------------##

    def _schedule(self):
        self._unschedule()
        if self._opts['state'] == 'disabled':
            return
        self._id = self.master.after(self._opts['delay'], self._show)

    def _unschedule(self):
        id = self._id
        self._id = None
        if id:
            self.master.after_cancel(id)

    def _show(self):
        if self._opts['state'] == 'disabled':
            self._unschedule()
            return
        if not self._tipwindow:
            self._tipwindow = tw = Tkinter.Toplevel(self.master)
            # hide the window until we know the geometry
            tw.withdraw()
            tw.wm_overrideredirect(1)

            if tw.tk.call("tk", "windowingsystem") == 'aqua':
                tw.tk.call("::tk::unsupported::MacWindowStyle", "style", tw._w, "help", "none")

            self.create_contents()
            tw.update_idletasks()
            x, y = self.coords()
            tw.wm_geometry("+%d+%d" % (x, y))
            tw.deiconify()

    def _hide(self):
        tw = self._tipwindow
        self._tipwindow = None
        if tw:
            tw.destroy()
    ##----these methods might be overridden in derived classes:----------------------------------##

    def coords(self):
        # The tip window must be completely outside the master widget;
        # otherwise when the mouse enters the tip window we get
        # a leave event and it disappears, and then we get an enter
        # event and it reappears, and so on forever :-(
        x0, y0, x1, y1 = self.master.bbox()
        tw = self._tipwindow
        twx, twy = tw.winfo_reqwidth(), tw.winfo_reqheight()
        w, h = tw.winfo_screenwidth(), tw.winfo_screenheight()
        # as x coord simply use x0, just make sure we're inside the screen
        if x0 < 0:
            x0 = 0
        elif x0 + twx > w:
            x0 = w - twx
        # now calculate y
        if y0 > w / 2:
            # assume the panel is at the bottom of the screen, so put the tooltip
            # above the tray icon
            y = y0 - twy - 3
        else:
            # panel at the top of the screen, put the tooltip below the tray icon
            y = y1 + 3
        return x0, y

    def create_contents(self):
        opts = self._opts.copy()
        for opt in ('delay', 'follow_mouse', 'state'):
            del opts[opt]
        label = Tkinter.Label(self._tipwindow, **opts)
        label.pack()

########################################################################

class Icon:
    def __init__(self, image=None, ico=None, tooltip='Your text here', menu=True, command=None):
        '''Platform-independent Tray-icon wrapper. Options:
        image     - may be either a filename of a gif image file (or any other
                    image format supported by Tk) or a string of base64
                    encoded image data or a PhotoImage object to use with TkTray
        ico       - pathname to an .ico file to use with winico
        tooltip   - text shown in a tooltip when the mouse enters the icon
        menu      - a boolean that determines whether the icon should have an
                    associated context menu. If True, this menu can be accessed
                    through the icon's menu attribute
        command   - optional Python command that will be executed when the left
                    mouse button is pressed on the icon; the x- and y-coordinates
                    of the event will be passed to that command.'''
        self.master = Tkinter._default_root
        if not self.master:
            raise RuntimeError, 'Too early to create tray icon.'

        if menu:
            self.menu = Tkinter.Menu(self.master, tearoff=0)
        else:
            self.menu = None

        if _platform == 'Windows':
            self.image = None
            self.icon = Winico.Icon(ico)
            if self.menu:
                def _do_command_win(eventtype, x, y):
                    if eventtype == "WM_RBUTTONDOWN":
                        self.menu.tk_popup(x, y)
                    elif command and eventtype == "WM_LBUTTONDOWN":
                        command(x, y)
                func = self.master.register(_do_command_win)
                self.icon.taskbar_add(text=tooltip, callback=(func, '%m', '%x', '%y'))
            else:
                self.icon.taskbar_add(text=tooltip)
        else:
            if type(image) in types.StringTypes:
                if os.path.isfile(image):
                    self.image = Tkinter.PhotoImage(file=image)
                else:
                    self.image = Tkinter.PhotoImage(data=image)
            else:
                self.image = image
            self.icon = TkTray.Icon(self.master, image=self.image)
            if self.menu:
                self.icon.bind('<3>', self._context_menu_x)
            if command:
                def _do_command_x(event):
                    command(event.x_root, event.y_root)
                self.icon.bind('<1>', _do_command_x)
            # new versions of tktray have a balloon command built in, but it
            # did not work here with most WMs and isn't trivial to set up either,
            # so for now we better stick with our tooltips here
            ToolTip(self.icon, text=tooltip)

    def _context_menu_x(self, event):
        if self.menu:
            w, h = self.menu.winfo_reqwidth(), self.menu.winfo_reqheight()
            x0, y0, x1, y1 = self.icon.bbox()
            # get the coords for the popup menu; we want it to the mouse pointer's
            # left and above the pointer in case the taskbar is on the bottom of the
            # screen, else below the pointer; add 1 pixel towards the pointer in each
            # dimension, so the pointer is '*inside* the menu when the button is being
            # released, so the menu will not unpost on the initial button-release event
            if y0 > self.icon.winfo_screenheight() / 2:
                # assume the panel is at the bottom of the screen
                x, y = event.x_root - w + 1, event.y_root - h + 1
            else:
                x, y = event.x_root - w + 1, event.y_root - 1
            # make sure that x is not outside the screen
            if x < 5:
                x = 5
            self.menu.tk_popup(x, y)

    def coords(self):
        if _platform == 'Windows':
            return None
        else:
            return self.icon.bbox()

    def destroy(self):
        self.icon.destroy()

    def destroy_all(self):
        self.destroy()
        if _platform == 'Windows':
            self.icon.delete_all()

#######################################################################################################################
#######################################################################################################################
##Balloon Notification for Windows##

class WindowsBalloonTip:
    def __init__(self, title, msg):
        message_map = {
                win32con.WM_DESTROY: self.OnDestroy,
        }
        # Register the Window class.
        wc = WNDCLASS()
        hinst = wc.hInstance = GetModuleHandle(None)
        wc.lpszClassName = "PythonTaskbar"
        wc.lpfnWndProc = message_map # could also specify a wndproc.
        classAtom = RegisterClass(wc)
        # Create the Window.
        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        self.hwnd = CreateWindow( classAtom, "Taskbar", style, \
                0, 0, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT, \
                0, 0, hinst, None)
        UpdateWindow(self.hwnd)
        #iconPathName = os.path.abspath(os.path.join( sys.path[0], "balloontip.ico" ))
        iconPathName = "icon.ico"
        icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
        try:
           hicon = LoadImage(hinst, iconPathName, \
                    win32con.IMAGE_ICON, 0, 0, icon_flags)
        except:
          hicon = LoadIcon(0, win32con.IDI_APPLICATION)
        flags = NIF_ICON | NIF_MESSAGE | NIF_TIP
        nid = (self.hwnd, 0, flags, win32con.WM_USER+20, hicon, "COD4")
        Shell_NotifyIcon(NIM_ADD, nid)
        Shell_NotifyIcon(NIM_MODIFY, \
                         (self.hwnd, 0, NIF_INFO, win32con.WM_USER+20,\
                          hicon, "Balloon  tooltip",msg,200,title))
        # self.show_balloon(title, msg)
        sleep(10)
        DestroyWindow(self.hwnd)        # Unregister the Window Class (#Important)
        classAtom = UnregisterClass(classAtom, hinst)
    def OnDestroy(self, hwnd, msg, wparam, lparam):
        nid = (self.hwnd, 0)
        Shell_NotifyIcon(NIM_DELETE, nid)
        PostQuitMessage(0) # Terminate the app.

def balloon_tip(title, msg):
    w=WindowsBalloonTip(title, msg)


######################################################################################################################
######################################################################################################################
##IP List Manager

global user_choice
global ip_input
global ip_box

def ip_manager():
    if user_choice.get() == 1:
        addip()
    elif user_choice.get() == 2:
        removeip()
    else:
        tkMessageBox.showwarning("", "Select an option first")

def set_ip(event):                              #Inserts current IP in input box
    ip_input.delete(0,END)
    ip_input.insert(0,ip_box.get())
    

def addip():
    #print "add"
    if ip_input.get() == '':
        tkMessageBox.showwarning("Error", "Input field empty")
    elif (validate_ip(ip_input.get()) == True):
        if (check_duplicate(ip_input.get()) == False):
            file = open("ip_list.txt",'a')
            file.write(ip_input.get()+"\n")
            file.close()
            ip_list = [line.strip() for line in open("ip_list.txt", 'r')]
            ip_box['values'] = (ip_list)
            tkMessageBox.showinfo("Success", "Changes will be reflected once you restart the app")
        else:
            tkMessageBox.showinfo("Error", "IP already present in the list")
            
    else:
        tkMessageBox.showinfo("Error", "Invalid IP address")
    ip_input.delete(0, 'end')   #Clears entry field
    user_choice.set(3)          #Deselects radiobutton

def removeip():
    #print "remove"
    if ip_input.get() == '':
        tkMessageBox.showwarning("Error", "Input field empty")
        user_choice.set(3)
        return
    change = False
    file = open("ip_list.txt","r")
    lines = file.readlines()
    file.close()
    file = open("ip_list.txt","w")    
    for line in lines:
        #print "*"+(line)+"*"
        if line != ip_input.get()+"\n":
            file.write(line)
        else:
            change = True
    file.close()
    ip_list = [line.strip() for line in open("ip_list.txt", 'r')]
    ip_box['values'] = (ip_list)
    if change == False:
        tkMessageBox.showinfo("Error", "IP not present in the list!")
    else:
        tkMessageBox.showinfo("Success", "Changes will be reflected once you restart the app")
    ip_input.delete(0, 'end')   #Clears entry field
    user_choice.set(3)          #Deselects radiobutton

#Checks if entered IP address is valid
def validate_ip(s):
    a = s.split('.')
    if len(a) != 4:
        return False
    for x in a:
        if not x.isdigit():
            return False
        i = int(x)
        if i < 0 or i > 255:
            return False
    return True

def check_duplicate(s):
    for ip in ip_list:
        if s == ip:
            return True
    return False

############################################################################################################################
############################################################################################################################
#Checking IPs for active servers

##Creates a thread to infinitely check the IPs present in IP list for active servers
class myThread (threading.Thread):
    def __init__(self, threadID, name, counter):
        threading.Thread.__init__(self)
        #self.threadID = threadID
        #self.name = name
        #self.counter = counter
    def run(self):
        #print "Starting " + self.name
        check_server()
        #print "Exiting " + self.name

def check_server():
    global sv_status
    global label2
    sv_count = 0
    sv_status = False
    msg = "Server UP!!\n"
    while True:
        for ip in range(len(ip_list)):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(5)

            try:
                s.sendto("--TEST LINE--", (ip_list[ip], port))
                recv, svr = s.recvfrom(255)
                s.shutdown(2)
                #print "Success connecting to " + ip_list[ip] + " on UDP port: " + str(port)
                sv_status = True
                sv_count += 1
                msg += ip_list[ip]+"\n"
                #server_status.set("Server UP!!\nJoin : "+ip_list[ip])
                server_status.set(msg)
                try:
                    label2.configure(fg="green")
                except:
                    a = 5
                balloon_tip("COD4", "Server UP!!\nJoin : "+ip_list[ip])
                #break

            except Exception, e:
                try:
                    errno, errtxt = e
                except ValueError:
                    a = 2      # does nothing
                    #print "Cannot connect to " + ip_list[ip] + " on port: " + str(port)
                    if sv_status == False:
                        server_status.set("Server Unavailable :(")
                        try:
                            label2.configure(fg="red")
                        except:
                           a = 5        # does nothing
                    #balloon_tip("COD4", "Server unavailable :(")
                else:
                    if errno == 107:
                        #print "Success connecting to " + ip_list[ip] + " on UDP port: " + str(port)
                        sv_status = True
                        sv_count += 1
                        msg += ip_list[ip]+"\n"
                        server_status.set(msg)
                        try:
                            label2.configure(fg="green")
                        except:
                            a = 5   # does nothing
                        balloon_tip("COD4", "Server UP!!\nJoin : "+ip_list[ip])
                        #break
                    else:
                        a = 2  # does nothing
                        #print "Cannot connect to " + ip_list[ip] + " on port: " + str(port)
                        if sv_status == False:
                            server_status.set("Server unavailable :(")
                            try:
                                label2.configure(fg="red")
                            except:
                               a = 5    # does nothing
                        #balloon_tip("COD4", "Server unavailable :(")
                        #print e
        try:
            s.close
        except:
            a = 2   # does nothing
        if sv_count > 1:
            balloon_tip("COD4", msg)
        if sv_status == True:
            break
        sleep(100)

    


##############################################################################################################################
##############################################################################################################################

##User Interface
class app_ui(Frame):
  
    def __init__(self, parent):
        Frame.__init__(self, parent)   #Insert Background colour here
         
        self.parent = parent
        self.pack(fill=BOTH, expand=1)
        self.centerWindow()
        self.initUI()

    def initUI(self):
      

        global server_status
        global root
        global cod_close
        global about
        global howitworks
        global ip_box
        global ip_input
        global user_choice
        global label2
        self.img = Image.open("cod_img.png")        #Image inserted in GUI
        cod_img = ImageTk.PhotoImage(self.img)
        label = Label(self, image=cod_img)
        label.image = cod_img
        label.grid(row=0, column=0, columnspan=3, rowspan=2,
               sticky=W+E)
        label1 = Label(self, text="Server Status :").grid(row=3, column = 0, pady = 7,sticky=E)
        root.resizable(False,False)
        root.iconbitmap('icon.ico')        # icon of the application
        server_status = StringVar()
        server_status.set("Connecting...") # sets label text
        label2 = Label(self, textvariable=server_status)
        label2.grid(row=3, column = 2,sticky=W,pady = 7)
        frame2 = Frame(self,background="black")
        frame2.grid(row=6,column=0,columnspan=5,sticky='EW',pady=20)
        label3 = Label(self, text="IP List Manager",font=("Times",12)).grid(row=7, column = 0, sticky=W+E, columnspan=3)
        label4 = Label(self, text="IP List :").grid(row=8, column = 0, pady=20)
        ipvar = StringVar()
        ip_box = ttk.Combobox(self, textvariable=ipvar)
        ip_box['values'] = (ip_list)
        ip_box.bind("<<ComboboxSelected>>", set_ip)       # Executes set_ip when an item is selected from the list
        ip_box.grid(row=8,column=1, pady=20, sticky=W+E)
        label5 = Label(self, text="Enter IP :").grid(row=11, column = 0)
        ip_input = Entry(self)
        ip_input.grid(row=11, pady=10,column=1,sticky=W+E)
        user_choice = IntVar()
        Radiobutton(self, text="Add IP", variable=user_choice, value=1).grid(row=12, sticky=S, column=0, pady=5)
        Radiobutton(self, text="Remove IP", variable=user_choice, value=2).grid(row=12, sticky=S, column=1, pady=5)
        Button(self, text="Execute", command=ip_manager).grid(row = 12, column = 2)
        cod_menu=Menu()             #Main menu
        list_menu=Menu()            #Sub-menu
        cod_menu.add_cascade(label="File",menu=list_menu)
        list_menu.add_command(label="How does it work?",command = howitworks)
        list_menu.add_command(label="About",command = about)
        list_menu.add_command(label="Quit",command = cod_close)
        root.config(menu=cod_menu)
        

    def centerWindow(self):
      
        w = 460
        h = 510

        sw = self.parent.winfo_screenwidth()
        sh = self.parent.winfo_screenheight()
        
        x = (sw - w)/2
        y = (sh - h)/2
        self.parent.geometry('%dx%d+%d+%d' % (w, h, x, y))

##############################################################################
def test():
    
    global root
    global cod_close
    global about
    global howitworks
    root = Tkinter.Tk()
    root.withdraw()                                         #Minimises window to taskbar when the application is run
    root.protocol("WM_DELETE_WINDOW", root.withdraw)        #Minimises window instead of closing
    def cmd(x,y):
        root.deiconify()                                    #Maximises application window
    def cod_close():
        ask = tkMessageBox.askyesno("", "Are you sure you want to Quit?")
        global sv_status
        if ask == True:
            sv_status = True        #Sets sv_status to True so that the user-thread closes on next check to terminate the application
            root.quit()
    def about():
        tkMessageBox.showinfo("About", "Developed by Ashank Anshuman\nReport bugs and feedback at ashankanshuman@gmail.com")
    def howitworks():
        tkMessageBox.showinfo("How does it work?", "This application searches all the IPs in the IP list for active servers and notifies the user if any server is online.\nIt runs silently in the background using minimal resource.\nIPs can be added and removed from the IP list as desired by the user through IP List Manager.")
    def info():
        if (thread1.isAlive()):
            tkMessageBox.showinfo(message='COD4 Server Checker\nStatus : Running')
        else:
            tkMessageBox.showinfo(message='COD4 Server Checker\nStatus : Stopped')
    def sv_check():
        if (sv_status == True):
            root.deiconify()                                #Maximises application window when active server is found
        else:
            root.after(10000,sv_check)                      #Checks for active server periodically
    icon = Icon(os.path.join(sys.path[0], "icon.gif"),
            os.path.join(sys.path[0], "icon.ico").replace('\\library.zip',''), 'COD4 Server Checker', command=cmd)      #py2exe checks outside of library.zip for icon.ico
    icon.menu.add_command(label='About', command=info)
    icon.menu.add_separator()
    icon.menu.add_command(label='Quit', command=cod_close)


    ex = app_ui(root)
    root.title("COD4 Server Checker")

    thread1 = myThread(1, "Thread-1", 1)
    thread1.start()                             #Starts the thread which checks for active servers periodically
    root.after(6000, sv_check)
    root.mainloop()
    # on windows it seems like tray icons should be explicitely deleted:
    icon.destroy_all()
    root.destroy()
    thread1.join()                              #Waits for the thread to close before terminating all processes
    sys.exit()                                  #Terminates all processes

if __name__ == '__main__':
    test()
#Developed by Ashank Anshuman
