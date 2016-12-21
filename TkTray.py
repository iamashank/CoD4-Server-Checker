# -*- coding: utf-8 -*-
'''Tktray is an extension that is able to create system tray icons.
It follows http://www.freedesktop.org specifications when looking up the
system tray manager. This protocol is supported by modern versions of
KDE and Gnome panels, and by some other panel-like application.'''

import Tkinter

class Icon(Tkinter.BaseWidget, Tkinter.Wm):
    def __init__(self, master=None, cnf={}, **kw):
        '''Create a new icon for the system tray. The application managing the
        system tray is notified about the new icon. It normally results in the
        icon being added to the tray. If there is no system tray at the icon
        creation time, the icon will be invisible. When a new system tray appears,
        the icon will be added to it. Since tktray 1.3, if the tray crashes and
        destroys your icon, it will be recreated on a new system tray when it's
        available.
        OPTIONS:
            class   WM_CLASS attribute for icon window. Tray manager may use class
                    name to remember icon position or other attributes. This name
                    may be used for event binding as well. For now, real icon
                    window is distinct from the user-specified widget: it may be
                    recreated and destroyed several times during icon lifetime,
                    when a system tray crashes, terminates, disappears or appears.
                    However, tktray tries to forward click and motion events from
                    this inner window to user widget, so event bindings on widget
                    name should work as they used to. This option applies to a real
                    icon window, not to a user-visible widget, so don't rely on it
                    to set widget defaults from an option database: the standard
                    "TrayIcon" class name is used for it.

            docked  boolean indicating whether the real icon window should be
                    embedded into a tray when it exists. Think of it as a heavier
                    version of -visible option: there is a guarantee that no place
                    for icon will be reserved on any tray.

            image   image to show in the system tray. Since tktray 1.3, image type
                    "photo" is not mandatory anymore. Icon will be automatically
                    redrawn on any image modifications. For Tk, deleting an image
                    and creating an image with the same name later is a kind of
                    image modification, and tktray follows this convention. Photo
                    image operations that modify existing image content are another
                    example of events triggering redisplay. Requested size for icon
                    is set according to the image's width and height, but obeying
                    (or disobeying) this request is left for the tray.

            shape   used to put a nonrectangular shape on an icon window. Ignored
                    for compatibility.

            visible boolean value indicating whether the icon must be visible.
                    The system tray manager continues to manage the icon whether
                    it is visible or not. Thus when invisible icon becomes visible,
                    its position on the system tray is likely to remain the same.
                    Tktray currently tries to find a tray and embed into it as
                    soon as possible, whether visible is true or not. _XEMBED_INFO
                    property is set for embedded window: a tray should show or
                    hide an icon depending on this property. There may be, and
                    indeed are, incomplete tray implementations ignoring
                    _XEMBED_INFO (ex. docker). Gnome-panel "unmaps" an icon by
                    making it one pixel wide, that might to be what you expect.
                    For those implementations, the place for an icon will be
                    reserved but no image will be displayed: tktray takes care of
                    it. Tktray also blocks mouse event forwarding for invisible
                    icons, so you may be confident that no<Button> bindings will
                    be invoked at this time.

        WINDOW MANAGEMENT
            Current implementation of tktray is designed to present an interface
            of a usual toplevel window, but there are some important differences
            (some of them may come up later). System Tray specification is based
            on XEMBED protocol, and the later has a problem: when the embedder
            crashes, nothing can prevent embedded windows from destruction. Since
            tktray 1.3, no explicit icon recreation code is required on Tcl level.
            The widget was split in two: one represented by a caller-specified name,
            and another (currently $path.inner) that exists only when a tray is
            available (and dies and comes back and so on). This solution has some
            disadvantages as well. User-created widget is not mapped at all, thus
            it can't be used any more as a parent for other widgets, showing them
            instead of an image. A temporal inner window, however, may contain
            widgets.

            This version (1.3.9) introduces three virtual events: <<IconCreate>>
            <<IconConfigure>> and <<IconDestroy>>. <<IconCreate>> is generated
            when docking is requesting for an icon. <<IconConfigure>> is generated
            when an icon window is resized or changed in some other way.
            <<IconDestroy>> is generated when an icon is destroyed due to panel
            crash or undocked with unsetting -docked option.'''
        if not master:
            if Tkinter._support_default_root:
                if not Tkinter._default_root:
                    Tkinter._default_root = Tkinter.Tk()
                master = Tkinter._default_root
        self.TktrayVersion = master.tk.call('package', 'require', 'tktray')

        # stolen from Tkinter.Toplevel
        if kw:
            cnf = Tkinter._cnfmerge((cnf, kw))
        extra = ()
        for wmkey in ['screen', 'class_', 'class', 'visible', 'colormap']:
            if cnf.has_key(wmkey):
                val = cnf[wmkey]
                # TBD: a hack needed because some keys
                # are not valid as keyword arguments
                if wmkey[-1] == '_': opt = '-'+wmkey[:-1]
                else: opt = '-'+wmkey
                extra = extra + (opt, val)
                del cnf[wmkey]
        Tkinter.BaseWidget.__init__(self, master, 'tktray::icon', cnf, {}, extra)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def balloon(self, message, timeout=None):
        '''Post a message that any decent tray implementation would show alongside
        the icon (or a place allocated for it). The message will disappear
        automatically after timeout milliseconds. Unfortunately, there is
        absolutely no way to know if the tray supports this feature, so don't rely
        on it for any critical information to be delivered. When no timeout or
        zero timeout is given, the message should not be hidden without user
        action (usually a mouse click). The return value is an integer, a message
        handle that may be used for cancelling the message before timeout
        expiration, or zero if there is currently no system tray to handle the
        request.'''
        return int(self.tk.call(self._w, 'balloon', message, 1000))

    def bbox(self):
        '''Get the list of left, top, right and bottom coordinates of the icon
        relative to the root window of the icon's screen. This command should be
        used in preference to winfo_rootx() and winfo_rooty() to get icon location,
        though the latter may seem to work on your system. Bounding box information
        is updated asynchronously. Don't rely on its correctness on script startup,
        just after icon creation. This command is for event handlers: on
        <ButtonPress-3> you'd like to have a popup menu, but where it should be
        posted? Use event.widget.bbox() to determine it right at the moment when
        a click happened.'''
        return self._getints(self.tk.call(self._w, 'bbox')) or None

    def cancel(self, messagehandle):
        '''Cancel an earlier-posted balloon message. Zero message_handle is
        silently ignored. If there is no message with this handle, or its timeout
        has expired, or it was posted to another system tray and is unknow to the
        current one, nothing bad should happen (but it depends on the tray
        implementation).'''
        self.tk.call(self._w, 'cancel', messagehandle)

    def docked(self):
        '''Query icon if it's currently embedded into some system tray. Invisible
        icons may be docked too (and tktray strives for it). If this method
        returns false, the icon is not visible to anyone, and no chance to get
        balloon messages displayed.'''
        return self.getboolean(self.tk.call(self._w, 'docked'))

    def orientation(self):
        '''Query orientation of a system tray that is currently embedding the icon.'''
        return self.tk.call(self._w, 'orientation')
    orient = orientation

################################################################################
if __name__ == '__main__':
    root = Tkinter.Tk()
    root.img = Tkinter.PhotoImage(file='phone.gif')
    icon = Icon(image=root.img)
    print icon.TktrayVersion
    print 'version:', icon.TktrayVersion
    print 'docked:', icon.docked()
    print 'orient:', icon.orient()
    print 'bbox:', icon.bbox()

    icon._timer = None
    icon._handle = None
    def showballoon():
        if not icon._handle is None:
            icon.cancel(icon._handle)
        icon._handle = icon.balloon('foobar', 2000)
    def postballoon(ev):
        if not icon._timer is None:
            icon.after_cancel(icon._timer)
        icon._timer = icon.after(1000, showballoon)
    def hideballoon(ev):
        if not icon._handle is None:
            icon.cancel(icon._handle)
        if not icon._timer is None:
            icon.after_cancel(icon._timer)

    icon.bind('<Enter>', postballoon)
    icon.bind('<Leave>', hideballoon)

    m = Tkinter.Menu(tearoff=0)
    m.add_command(label='Quit', command=root.quit)
    def postmenu(ev):
        x0, y0, x1, y1 = icon.bbox()
        m.tk_popup(x0, y0-10)
    icon.bind('<3>', postmenu)

    root.mainloop()
