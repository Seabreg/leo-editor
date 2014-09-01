# -*- coding: utf-8 -*-
#@+leo-ver=5-thin
#@+node:ekr.20140831085423.18598: * @file ../plugins/qt_text.py
#@@first
'''Text classes for the Qt version of Leo'''
import leo.core.leoGlobals as g
import leo.core.leoFrame as leoFrame
import time
from leo.core.leoQt import isQt5,QtCore,QtGui,QtWidgets
from leo.core.leoQt import Qsci
#@+others
#@+node:tbrown.20130411145310.18857: **    Commands: zoom_in/out
@g.command("zoom-in")
def zoom_in(event=None, delta=1):
    """increase body font size by one
    
    requires that @font-size-body is being used in stylesheet
    """
    c = event.get('c')
    if c:
        c._style_deltas['font-size-body'] += delta
        ss = g.expand_css_constants(c, c.active_stylesheet)
        c.frame.body.wrapper.widget.setStyleSheet(ss)
    
@g.command("zoom-out")
def zoom_out(event=None):
    """decrease body font size by one
    
    requires that @font-size-body is being used in stylesheet
    """
    zoom_in(event=event, delta=-1)
#@+node:ekr.20110605121601.18023: **   class BaseQTextWrapper
class BaseQTextWrapper (leoFrame.BaseTextWrapper):
    '''
    A general wrapper class supporting the interface of BaseTextWrapper.
    The redirection methods of HighLevelInterface redirect calls
    from LeoBody & LeoLog to *this* class.
    '''
    #@+others
    #@+node:ekr.20110605121601.18024: *3* bqtw.Birth
    #@+node:ekr.20110605121601.18025: *4* bqtw.ctor
    def __init__ (self,widget,name='BaseQTextWrapper',c=None):
        '''The ctor for the BaseQTextWrapper class.'''
        # g.trace('(BaseQTextWrapper)',name,self.qt_widget,g.callers(2))
        self.c = c or widget.leo_c
        # Init the base class.
        leoFrame.BaseTextWrapper.__init__(
            self,c,baseClassName='BaseQTextWrapper',
            name=name,widget=widget)
        assert self.widget
        self.qt_widget = widget
                # Note: allows access to the widget without knowing its type.
        # Init ivars.
        self.changingText = False # A lockout for onTextChanged.
        self.tags = {}
        self.permanent = True # False if selecting the minibuffer will make the widget go away.
        self.configDict = {} # Keys are tags, values are colors (names or values).
        self.configUnderlineDict = {} # Keys are tags, values are True
        self.useScintilla = False # This is used!
        if not c:
            return # Can happen.
        if name in ('body','rendering-pane-wrapper') or name.startswith('head'):
            # g.trace('hooking up qt events',name)
            # Hook up qt events.
            g.app.gui.setFilter(c,self.qt_widget,self,tag=name)
        if name == 'body':
            w = self.qt_widget
            w.textChanged.connect(self.onTextChanged)
            w.cursorPositionChanged.connect(self.onCursorPositionChanged)
        if name in ('body','log'):
            # Monkey patch the event handler.
            #@+<< define mouseReleaseEvent >>
            #@+node:ekr.20110605121601.18026: *5* << define mouseReleaseEvent >> (BaseQTextWrapper)
            def mouseReleaseEvent (*args,**keys):
                '''
                Override QLineEdit.mouseReleaseEvent.
                Simulate alt-x if we are not in an input state.
                '''
                c,vc = self.c,self.c.vimCommands
                trace = False and not g.unitTesting
                # if trace: g.trace('(BaseQTextWrapper)',self.c.shortFileName())
                # Call the base class method.
                if len(args) == 1:
                    event = args[0]
                    # There seems to be no way to disable mouse events...
                    # if c.vim_mode and vc and vc.trainer:
                        # if trace: g.trace('1: ignore:',event)
                        # event.ignore() # Doesn't work.
                        # return
                    QtWidgets.QTextBrowser.mouseReleaseEvent(widget,event) # widget is unbound.
                elif len(args) == 2:
                    # In vim-trainer mode, stuff a 0 into the location field.  Hehe.
                    event = args[1]
                    if c.vim_mode and vc and vc.trainer:
                        if trace: g.trace('2',event)
                    QtWidgets.QTextBrowser.mouseReleaseEvent(*args)
                else:
                    g.trace('can not happen')
                    return
                # Open the url on a control-click.
                if QtCore.Qt.ControlModifier & event.modifiers():
                    event = {'c':c}
                    g.openUrlOnClick(event)
                if name == 'body':
                    c.p.v.insertSpot = c.frame.body.wrapper.getInsertPoint()
                    if trace: g.trace(c.p.v.insertSpot)
                g.doHook("bodyclick2",c=c,p=c.p,v=c.p)                    
                # 2011/05/28: Do *not* change the focus!
                # This would rip focus away from tab panes.
                c.k.keyboardQuit(setFocus=False)
            #@-<< define mouseReleaseEvent >>
            self.qt_widget.mouseReleaseEvent = mouseReleaseEvent
        self.injectIvars(c)
    #@+node:ekr.20110605121601.18027: *4* bqtw.injectIvars
    def injectIvars (self,name='1',parentFrame=None):

        w = self ; p = self.c.currentPosition()

        if name == '1':
            w.leo_p = None # Will be set when the second editor is created.
        else:
            w.leo_p = p.copy()

        w.leo_active = True

        # New in Leo 4.4.4 final: inject the scrollbar items into the text widget.
        w.leo_bodyBar = None
        w.leo_bodyXBar = None
        w.leo_chapter = None
        w.leo_frame = None
        w.leo_name = name
        w.leo_label = None
        return w
    #@+node:ekr.20110605121601.18029: *3* bqtw.signals
    #@+node:ekr.20110605121601.18030: *4* bqtw.onCursorPositionChanged
    def onCursorPositionChanged(self,event=None):

        c = self.c
        name = c.widget_name(self)

        # Apparently, this does not cause problems
        # because it generates no events in the body pane.
        if name.startswith('body'):
            if hasattr(c.frame,'statusLine'):
                c.frame.statusLine.update()
    #@+node:ekr.20111114013726.9968: *3* bqtw.High-level interface
    # HighLevelInterface methods call these methods.
    #@+node:ekr.20110605121601.18032: *4* bqtw.Focus
    def getFocus(self):

        # g.trace('LeoQtBody',self.qt_widget,g.callers(4))
        return g.app.gui.get_focus(self.c) # Bug fix: 2009/6/30

    findFocus = getFocus

    # def hasFocus (self):

        # val = self.qt_widget == g.app.gui.get_focus(self.c)
        # # g.trace('LeoQtBody returns',val,self.qt_widget,g.callers(4))
        # return val

    def setFocus (self):

        trace = False and not g.unitTesting
        if trace: print('BaseQTextWrapper.setFocus',
            # g.app.gui.widget_name(self.qt_widget),
            self.qt_widget,g.callers(3))
        # Call the base class
        assert isinstance(self.qt_widget,
            (QtWidgets.QTextBrowser,QtWidgets.QLineEdit,QtWidgets.QTextEdit)),self.qt_widget
        QtWidgets.QTextBrowser.setFocus(self.qt_widget)
    #@+node:ekr.20110605121601.18033: *4* bqtw.Indices
    #@+node:ekr.20110605121601.18034: *5* bqtw.toPythonIndex
    def toPythonIndex (self,index):

        s = self.getAllText()
        return g.toPythonIndex(s,index)

    toGuiIndex = toPythonIndex
    #@+node:ekr.20110605121601.18049: *5* bqtw.indexWarning
    # warningsDict = {}

    def indexWarning (self,s):

        return
    #@+node:ekr.20110605121601.18036: *4* bqtw.Text getters/settters
    #@+node:ekr.20110605121601.18037: *5* bqtw.appendText
    def appendText(self,s):

        s2 = self.getAllText()
        self.setAllText(s2+s)
        self.setInsertPoint(len(s2))

    #@+node:ekr.20110605121601.18040: *5* bqtw.getLastPosition
    def getLastPosition(self):

        return len(self.getAllText())
    #@+node:ekr.20110605121601.18041: *5* bqtw.getSelectedText
    def getSelectedText(self):

        # w = self.qt_widget
        # g.trace(w,self)
        i,j = self.getSelectionRange()
        if i == j:
            return ''
        else:
            s = self.getAllText()
            # g.trace(repr(s[i:j]))
            return s[i:j]
    #@+node:ekr.20110605121601.18042: *5* bqtw.get
    def get(self,i,j=None):
        """ Slow implementation of get() - ok for QLineEdit """
        #g.trace('Slow get', g.callers(5))

        s = self.getAllText()
        i = self.toGuiIndex(i)

        if j is None: 
            j = i+1

        j = self.toGuiIndex(j)
        return s[i:j]
    #@+node:ekr.20110605121601.18043: *5* bqtw.insert
    def insert(self,i,s):

        s2 = self.getAllText()
        i = self.toGuiIndex(i)
        self.setAllText(s2[:i] + s + s2[i:])
        self.setInsertPoint(i+len(s))
        return i
    #@+node:ekr.20110605121601.18044: *5* bqtw.selectAllText
    def selectAllText(self,insert=None):

        w = self.qt_widget
        w.selectAll()
        # if insert is not None:
            # self.setInsertPoint(insert)
        # Bug fix: 2012/03/25.
        self.setSelectionRange(0,'end',insert=insert)

    #@+node:ekr.20110605121601.18045: *5* bqtw.setSelectionRange & dummy helper
    # Note: this is used by QTextEditWrapper.

    def setSelectionRange (self,i,j,insert=None):

        i,j = self.toGuiIndex(i),self.toGuiIndex(j)

        return self.setSelectionRangeHelper(i,j,insert)
    #@+node:ekr.20110605121601.18046: *6* bqtw.setSelectionRangeHelper
    def setSelectionRangeHelper(self,i,j,insert=None,s=None):

        self.oops()
    #@+node:ekr.20110605121601.18050: *4* bqtw.HighLevelInterface
    # Do not delete.
    # The redirection methods of HighLevelInterface redirect calls
    # from LeoBody & LeoLog to *this* class.

    # Essential methods...
    def getName (self):
        return self.name

    # Optional methods...
    def flashCharacter(self,i,bg='white',fg='red',flashes=3,delay=75):
        pass

    def getYScrollPosition(self):           return None # A flag
    def seeInsertPoint (self):              self.see(self.getInsertPoint())
    def setBackgroundColor(self,color):     pass
    def setEditorColors (self,bg,fg):       pass
    def setForegroundColor(self,color):     pass
    def setYScrollPosition(self,pos):       pass

    # Must be defined in subclasses.
    def getAllText(self):                       self.oops()
    def getInsertPoint(self):                   self.oops()
    def getSelectionRange(self,sort=True):      self.oops()
    def hasSelection(self):                     self.oops()
    def see(self,i):                            self.oops()
    def setAllText(self,s):                     self.oops()
    def setInsertPoint(self,i,s=None):          self.oops()
    #@+node:ekr.20110605121601.18056: *5* bqtw.tag_configure
    def tag_configure (self,*args,**keys):

        trace = False and not g.unitTesting
        if trace: g.trace(args,keys)

        if len(args) == 1:
            key = args[0]
            self.tags[key] = keys
            val = keys.get('foreground')
            underline = keys.get('underline')
            if val:
                # if trace: g.trace(key,val)
                self.configDict [key] = val
            if underline:
                self.configUnderlineDict [key] = True
        else:
            g.trace('oops',args,keys)

    tag_config = tag_configure
    #@+node:ekr.20110605121601.18052: *4* bqtw.Idle time
    def after_idle(self,func,threadCount):
        # g.trace(func.__name__,'threadCount',threadCount)
        return func(threadCount)

    def after(self,n,func,threadCount):
        def after_callback(func=func,threadCount=threadCount):
            # g.trace(func.__name__,threadCount)
            return func(threadCount)
        QtCore.QTimer.singleShot(n,after_callback)

    def scheduleIdleTimeRoutine (self,function,*args,**keys):
        g.trace()
        # if not g.app.unitTesting:
            # self.qt_widget.after_idle(function,*args,**keys)
    #@+node:ekr.20110605121601.18048: *4* bqtw.onTextChanged
    def onTextChanged (self):

        '''Update Leo after the body has been changed.

        self.selecting is guaranteed to be True during
        the entire selection process.'''

        # Important: usually w.changingText is True.
        # This method very seldom does anything.
        trace = False and not g.unitTesting
        verbose = False
        w = self
        c = self.c ; p = c.p
        tree = c.frame.tree
        
        if w.changingText: 
            if trace and verbose: g.trace('already changing')
            return
        if tree.tree_select_lockout:
            if trace and verbose: g.trace('selecting lockout')
            return
        if tree.selecting:
            if trace and verbose: g.trace('selecting')
            return
        if tree.redrawing:
            if trace and verbose: g.trace('redrawing')
            return
        if not p:
            if trace: g.trace('*** no p')
            return
        newInsert = w.getInsertPoint()
        newSel = w.getSelectionRange()
        newText = w.getAllText() # Converts to unicode.

        # Get the previous values from the VNode.
        oldText = p.b
        if oldText == newText:
            # This can happen as the result of undo.
            # g.error('*** unexpected non-change')
            return
        # g.trace('**',len(newText),p.h,'\n',g.callers(8))
        # oldIns  = p.v.insertSpot
        i,j = p.v.selectionStart,p.v.selectionLength
        oldSel  = (i,i+j)
        if trace: g.trace('oldSel',oldSel,'newSel',newSel)
        oldYview = None
        undoType = 'Typing'
        c.undoer.setUndoTypingParams(p,undoType,
            oldText=oldText,newText=newText,
            oldSel=oldSel,newSel=newSel,oldYview=oldYview)
        # Update the VNode.
        p.v.setBodyString(newText)
        if True:
            p.v.insertSpot = newInsert
            i,j = newSel
            i,j = self.toGuiIndex(i),self.toGuiIndex(j)
            if i > j: i,j = j,i
            p.v.selectionStart,p.v.selectionLength = (i,j-i)

        # No need to redraw the screen.
        if not self.useScintilla:
            c.recolor()
        if g.app.qt_use_tabs:
            if trace: g.trace(c.frame.top)
        if not c.changed and c.frame.initComplete:
            c.setChanged(True)
        c.frame.body.updateEditors()
        c.frame.tree.updateIcon(p)
        if 1: # This works, and is probably better.
            # Set a hook for the old jEdit colorer.
            colorer = c.frame.body.colorizer.highlighter.colorer
            colorer.initFlag = True
        else:
            # Allow incremental recoloring.
            c.incrementalRecolorFlag = True
            c.outerUpdate()
    #@+node:ekr.20120325032957.9730: *3* bqtw.rememberSelectionAndScroll
    def rememberSelectionAndScroll(self):

        trace = (False or g.trace_scroll) and not g.unitTesting
        w = self
        v = self.c.p.v # Always accurate.
        v.insertSpot = w.getInsertPoint()
        i,j = w.getSelectionRange()
        if i > j: i,j = j,i
        assert(i<=j)
        v.selectionStart = i
        v.selectionLength = j-i
        v.scrollBarSpot = spot = w.getYScrollPosition()
        if trace:
            g.trace(spot,v.h)
            # g.trace(id(v),id(w),i,j,ins,spot,v.h)
    #@-others
#@+node:ekr.20110605121601.18058: **  class QLineEditWrapper(BaseQTextWrapper)
class QLineEditWrapper (BaseQTextWrapper):

    #@+others
    #@+node:ekr.20110605121601.18059: *3* qlew.Birth
    #@+node:ekr.20110605121601.18060: *4* qlew.ctor (QLineEditWrapper)
    def __init__ (self,widget,name,c=None):
        '''Ctor for QLineEditWrapper class.'''
        # g.trace('(QLineEditWrapper):widget',name,self.qt_widget)
        BaseQTextWrapper.__init__(self,widget,name,c=c)
            # Init the base class.
        assert self.qt_widget
        self.widget = self.qt_widget
            # Note: allows access to the widget without knowing its type.
        self.baseClassName='QLineEditWrapper'
    #@+node:ekr.20110605121601.18061: *4* qlew.__repr__
    def __repr__ (self):

        return '<QLineEditWrapper: widget: %s' % (self.qt_widget)

    __str__ = __repr__
    #@+node:ekr.20110605121601.18062: *3* qlew.Widget-specific overrides
    #@+node:ekr.20110605121601.18063: *4* qlew.getAllText
    def getAllText(self):

        w = self.qt_widget
        s = w.text()
        return g.u(s)
    #@+node:ekr.20110605121601.18064: *4* qlew.getInsertPoint
    def getInsertPoint(self):

        i = self.qt_widget.cursorPosition()
        # g.trace(i)
        return i
    #@+node:ekr.20110605121601.18065: *4* qlew.getSelectionRange
    def getSelectionRange(self,sort=True):

        w = self.qt_widget
        if w.hasSelectedText():
            i = w.selectionStart()
            s = w.selectedText()
            s = g.u(s)
            j = i + len(s)
        else:
            i = j = w.cursorPosition()
        # g.trace(i,j)
        return i,j
    #@+node:ekr.20110605121601.18066: *4* qlew.hasSelection
    def hasSelection(self):

        # 2011/05/26: was hasSelection.
        return self.qt_widget.hasSelectedText()
    #@+node:ekr.20110605121601.18067: *4* qlew.see & seeInsertPoint
    def see(self,i):
        pass

    def seeInsertPoint (self):
        pass
    #@+node:ekr.20110605121601.18068: *4* qlew.setAllText
    def setAllText(self,s):

        w = self.qt_widget
        disabled = hasattr(w,'leo_disabled') and w.leo_disabled
        if disabled:
            w.setEnabled(True)
        w.setText(s)
        if disabled:
            w.setEnabled(False)
    #@+node:ekr.20110605121601.18069: *4* qlew.setInsertPoint
    def setInsertPoint(self,i,s=None):

        w = self.qt_widget
        if s is None:
            s = w.text()
            s = g.u(s)
        i = self.toPythonIndex(i) # 2010/10/22.
        i = max(0,min(i,len(s)))
        w.setCursorPosition(i)
    #@+node:ekr.20110605121601.18070: *4* qlew.setSelectionRangeHelper
    def setSelectionRangeHelper(self,i,j,insert=None,s=None):

        w = self.qt_widget
        # g.trace(i,j,insert,w)
        if i > j: i,j = j,i
        if s is None:
            s = w.text()
            s = g.u(s)
        n = len(s)
        i = max(0,min(i,n))
        j = max(0,min(j,n))
        if j < i: i,j = j,i
        if insert is None: insert = j
        insert = max(0,min(insert,n))
        if i == j:
            w.setCursorPosition(i)
        else:
            length = j-i
            if insert < j:
                w.setSelection(j,-length)
            else:
                w.setSelection(i,length)
    #@-others
#@+node:ekr.20110605121601.18005: ** class LeoQTextBrowser (QtWidgets.QTextBrowser)
class LeoQTextBrowser (QtWidgets.QTextBrowser):
    '''A subclass of QTextBrowser that overrides the mouse event handlers.'''
    #@+others
    #@+node:ekr.20110605121601.18006: *3*   ctor (LeoQTextBrowser)
    def __init__(self,parent,c,wrapper):
        '''ctor for LeoQTextBrowser class.'''
        # g.trace('(LeoQTextBrowser)',c.shortFileName(),parent,wrapper)
        for attr in ('leo_c','leo_wrapper',):
            assert not hasattr(QtWidgets.QTextBrowser,attr),attr
        self.leo_c = c
        self.leo_s = '' # The cached text.
        self.leo_wrapper = wrapper
        self.htmlFlag = True
        QtWidgets.QTextBrowser.__init__(self,parent)
        # Connect event handlers...
        if 0: # Not a good idea: it will complicate delayed loading of body text.
            self.textChanged.connect(self.onTextChanged)
        # This event handler is the easy way to keep track of the vertical scroll position.
        self.leo_vsb = vsb = self.verticalScrollBar()
        vsb.valueChanged.connect(self.onSliderChanged)
        # Signal that the widget can accept delayed-load buttons.
        self.leo_load_button = None
        self.leo_paste_button = None
        self.leo_big_text = None
        # g.trace('(LeoQTextBrowser)',repr(self.leo_wrapper))
        # For QCompleter
        self.leo_q_completer = None
        self.leo_options = None
        self.leo_model = None
    #@+node:ekr.20110605121601.18007: *3*  __repr__ & __str__
    def __repr__ (self):

        return '(LeoQTextBrowser) %s' % id(self)

    __str__ = __repr__
    #@+node:ekr.20110605121601.18008: *3* Auto completion (LeoQTextBrowser)
    #@+node:ekr.20110605121601.18009: *4* class LeoQListWidget(QListWidget)
    class LeoQListWidget(QtWidgets.QListWidget):

        #@+others
        #@+node:ekr.20110605121601.18010: *5* ctor (LeoQListWidget)
        def __init__(self,c):
            '''ctor for LeoQListWidget class'''
            QtWidgets.QListWidget.__init__(self)
            self.setWindowFlags(QtCore.Qt.Popup | self.windowFlags())
            # Make this window a modal window.
            # Calling this does not fix the Ubuntu-specific modal behavior.
            # self.setWindowModality(QtCore.Qt.NonModal) # WindowModal)
            if 0:
                # embed the window in a splitter.
                splitter2 = c.frame.top.splitter_2
                splitter2.insertWidget(1,self)
            # Inject the ivars
            self.leo_w = c.frame.body.wrapper.qt_widget
                # A LeoQTextBrowser, a subclass of QtWidgets.QTextBrowser.
            self.leo_c = c
            # A weird hack.
            self.leo_geom_set = False # When true, self.geom returns global coords!
            self.itemClicked.connect(self.select_callback)
        #@+node:ekr.20110605121601.18011: *5* closeEvent
        def closeEvent(self,event):

            '''Kill completion and close the window.'''

            self.leo_c.k.autoCompleter.abort()
        #@+node:ekr.20110605121601.18012: *5* end_completer
        def end_completer(self):

            # g.trace('(LeoQListWidget)')

            c = self.leo_c
            c.in_qt_dialog = False

            # This is important: it clears the autocompletion state.
            c.k.keyboardQuit()
            c.bodyWantsFocusNow()

            self.deleteLater()
        #@+node:ekr.20110605121601.18013: *5* keyPressEvent (LeoQListWidget)
        def keyPressEvent(self,event):

            '''Handle a key event from QListWidget.'''

            trace = False and not g.unitTesting
            c = self.leo_c
            w = c.frame.body.wrapper
            qt = QtCore.Qt
            key = event.key()
            if event.modifiers() != qt.NoModifier and not event.text():
                # A modifier key on it's own.
                pass
            elif key in (qt.Key_Up,qt.Key_Down):
                QtWidgets.QListWidget.keyPressEvent(self,event)
            elif key == qt.Key_Tab:
                if trace: g.trace('<tab>')
                self.tab_callback()
            elif key in (qt.Key_Enter,qt.Key_Return):
                if trace: g.trace('<return>')
                self.select_callback()
            else:
                # Pass all other keys to the autocompleter via the event filter.
                w.ev_filter.eventFilter(obj=self,event=event)
        #@+node:ekr.20110605121601.18014: *5* select_callback
        def select_callback(self):  

            '''Called when user selects an item in the QListWidget.'''

            trace = False and not g.unitTesting
            c = self.leo_c ; w = c.frame.body

            # Replace the tail of the prefix with the completion.
            completion = self.currentItem().text()
            prefix = c.k.autoCompleter.get_autocompleter_prefix()

            parts = prefix.split('.')
            if len(parts) > 1:
                tail = parts[-1]
            else:
                tail = prefix

            if trace: g.trace('prefix',repr(prefix),'tail',repr(tail),'completion',repr(completion))

            if tail != completion:
                j = w.getInsertPoint()
                i = j - len(tail)
                w.delete(i,j)
                w.insert(i,completion)
                j = i+len(completion)
                c.setChanged(True)
                w.setInsertPoint(j)
                c.frame.body.onBodyChanged('Typing')

            self.end_completer()
        #@+node:tbrown.20111011094944.27031: *5* tab_callback
        def tab_callback(self):  

            '''Called when user hits tab on an item in the QListWidget.'''

            trace = False and not g.unitTesting
            c = self.leo_c ; w = c.frame.body
            # Replace the tail of the prefix with the completion.
            completion = self.currentItem().text()
            prefix = c.k.autoCompleter.get_autocompleter_prefix()
            parts = prefix.split('.')
            if len(parts) < 2:
                return
            # var = parts[-2]
            if len(parts) > 1:
                tail = parts[-1]
            else:
                tail = prefix
            if trace: g.trace(
                'prefix',repr(prefix),'tail',repr(tail),
                'completion',repr(completion))
            w = c.k.autoCompleter.w
            i = j = w.getInsertPoint()
            s = w.getAllText()
            while (0 <= i < len(s) and s[i] != '.'):
                i -= 1
            i += 1
            if j > i:
                w.delete(i,j)
            w.setInsertPoint(i)
            c.k.autoCompleter.klass = completion
            c.k.autoCompleter.compute_completion_list()
        #@+node:ekr.20110605121601.18015: *5* set_position (LeoQListWidget)
        def set_position (self,c):

            trace = False and not g.unitTesting
            w = self.leo_w

            def glob(obj,pt):
                '''Convert pt from obj's local coordinates to global coordinates.'''
                return obj.mapToGlobal(pt)

            vp = self.viewport()
            r = w.cursorRect()
            geom = self.geometry() # In viewport coordinates.

            gr_topLeft = glob(w,r.topLeft())

            # As a workaround to the setGeometry bug,
            # The window is destroyed instead of being hidden.
            assert not self.leo_geom_set

            # This code illustrates the bug...
            # if self.leo_geom_set:
                # # Unbelievable: geom is now in *global* coords.
                # gg_topLeft = geom.topLeft()
            # else:
                # # Per documentation, geom in local (viewport) coords.
                # gg_topLeft = glob(vp,geom.topLeft())

            gg_topLeft = glob(vp,geom.topLeft())

            delta_x = gr_topLeft.x() - gg_topLeft.x() 
            delta_y = gr_topLeft.y() - gg_topLeft.y()

            # These offset are reasonable.
            # Perhaps they should depend on font size.
            x_offset,y_offset = 10,60

            # Compute the new geometry, setting the size by hand.
            geom2_topLeft = QtCore.QPoint(
                geom.x()+delta_x+x_offset,
                geom.y()+delta_y+y_offset)

            geom2_size = QtCore.QSize(400,100)

            geom2 = QtCore.QRect(geom2_topLeft,geom2_size)

            # These assert's fail once offsets are added.
            if x_offset == 0 and y_offset == 0:
                if self.leo_geom_set:
                    assert geom2.topLeft() == glob(w,r.topLeft()),'geom.topLeft: %s, geom2.topLeft: %s' % (
                        geom2.topLeft(),glob(w,r.topLeft()))
                else:
                    assert glob(vp,geom2.topLeft()) == glob(w,r.topLeft()),'geom.topLeft: %s, geom2.topLeft: %s' % (
                        glob(vp,geom2.topLeft()),glob(w,r.topLeft()))

            self.setGeometry(geom2)
            self.leo_geom_set = True

            if trace:
                g.trace(self,
                    # '\n viewport:',vp,
                    # '\n size:    ',geom.size(),
                    '\n delta_x',delta_x,
                    '\n delta_y',delta_y,
                    '\n r:     ',r.x(),r.y(),         glob(w,r.topLeft()),
                    '\n geom:  ',geom.x(),geom.y(),   glob(vp,geom.topLeft()),
                    '\n geom2: ',geom2.x(),geom2.y(), glob(vp,geom2.topLeft()),
                )
        #@+node:ekr.20110605121601.18016: *5* show_completions
        def show_completions(self,aList):

            '''Set the QListView contents to aList.'''

            # g.trace('(qc) len(aList)',len(aList))

            self.clear()
            self.addItems(aList)
            self.setCurrentRow(0)
            self.activateWindow()
            self.setFocus()
        #@-others
    #@+node:ekr.20110605121601.18017: *4* init_completer (LeoQTextBrowser)
    def init_completer(self,options):

        '''Connect a QCompleter.'''

        trace = False and not g.unitTesting
        c = self.leo_c
        if trace:
            g.trace('(LeoQTextBrowser) len(options): %s' % (len(options)))
        self.leo_qc = qc = self.LeoQListWidget(c)
        # Move the window near the body pane's cursor.
        qc.set_position(c)
        # Show the initial completions.
        c.in_qt_dialog = True
        qc.show()
        qc.activateWindow()
        c.widgetWantsFocusNow(qc)
        qc.show_completions(options)
        return qc
    #@+node:ekr.20110605121601.18018: *4* redirections to LeoQListWidget
    def end_completer(self):

        if hasattr(self,'leo_qc'):
            self.leo_qc.end_completer()
            delattr(self,'leo_qc')

    def show_completions(self,aList):

        if hasattr(self,'leo_qc'):
            self.leo_qc.show_completions(aList)
    #@+node:ekr.20110605121601.18019: *3* leo_dumpButton
    def leo_dumpButton(self,event,tag):
        trace = False and not g.unitTesting
        button = event.button()
        table = (
            (QtCore.Qt.NoButton,'no button'),
            (QtCore.Qt.LeftButton,'left-button'),
            (QtCore.Qt.RightButton,'right-button'),
            (QtCore.Qt.MidButton,'middle-button'),
        )
        for val,s in table:
            if button == val:
                kind = s; break
        else: kind = 'unknown: %s' % repr(button)
        if trace: g.trace(tag,kind)
        return kind
    #@+node:ekr.20110605121601.18020: *3* event handlers (LeoQTextBrowser)
    #@+node:ekr.20110605121601.18021: *4* mousePress/ReleaseEvent (LeoQTextBrowser) (never called!)
    # def mousePressEvent (self,event):
        # QtWidgets.QTextBrowser.mousePressEvent(self,event)

    def mouseReleaseEvent(self,*args,**keys):
        '''Handle a mouse release event in a LeoQTextBrowser.'''
        g.trace('LeoQTextBrowser',args,keys)
        if 0: # Crashed for QScintilla
            if len(args) == 1:
                event = args[0]
                self.onMouseUp(event)
                QtWidgets.QTextBrowser.mouseReleaseEvent(event) # widget is unbound.
            elif len(args) == 2:
                event = args[1]
                QtWidgets.QTextBrowser.mouseReleaseEvent(*args)
            else:
                g.trace('can not happen')
                return
    #@+node:ekr.20110605121601.18022: *4* onMouseUp (LeoQTextBrowser)
    def onMouseUp(self,event=None):

        # Open the url on a control-click.
        if QtCore.Qt.ControlModifier & event.modifiers():
            event = {'c':self.leo_c}
            g.openUrlOnClick(event)
    #@+node:ekr.20111002125540.7021: *3* get/setYScrollPosition (LeoQTextBrowser)
    def getYScrollPosition(self):

        trace = (False or g.trace_scroll) and not g.unitTesting

        w = self
        sb = w.verticalScrollBar()
        pos = sb.sliderPosition()
        if trace: g.trace(pos)
        return pos

    def setYScrollPosition(self,pos):

        trace = (False or g.trace_scroll) and not g.unitTesting
        w = self

        if g.no_scroll:
            if trace: g.trace('no scroll')
            return
        elif pos is None:
            if trace: g.trace('None')
        else:
            if trace: g.trace(pos,g.callers())
            sb = w.verticalScrollBar()
            sb.setSliderPosition(pos)

    #@+node:ekr.20120925061642.13506: *3* onSliderChanged (LeoQTextBrowser)
    def onSliderChanged(self,arg):
        '''Handle a Qt onSliderChanged event.'''
        trace = False and not g.unitTesting
        c = self.leo_c
        p = c.p
        # Careful: changing nodes changes the scrollbars.
        if hasattr(c.frame.tree,'tree_select_lockout'):
            if c.frame.tree.tree_select_lockout:
                if trace: g.trace('locked out: c.frame.tree.tree_select_lockout')
                return
        # Only scrolling in the body pane should set v.scrollBarSpot.
        if not c.frame.body or self != c.frame.body.wrapper.qt_widget:
            if trace: g.trace('**** wrong pane')
            return
        if p:
            if trace: g.trace(arg,c.p.v.h,g.callers())
            p.v.scrollBarSpot = arg
    #@+node:tbrown.20130411145310.18855: *3* wheelEvent
    def wheelEvent(self, event):
        '''Handle a wheel event.'''
        if QtCore.Qt.ControlModifier & event.modifiers():
            d = {'c':self.leo_c}
            delta = event.angleDelta() if isQt5 else event.delta()
            if delta < 0:
                zoom_out(d)
            else:
                zoom_in(d)
            event.accept()
            return
        QtWidgets.QTextBrowser.wheelEvent(self,event)
    #@-others
#@+node:ekr.20110605121601.18116: ** class QHeadlineWrapper (BaseQTextWrapper)
class QHeadlineWrapper (BaseQTextWrapper):
    '''A wrapper class for QLineEdit widgets in QTreeWidget's.

    This wrapper must appear to be a leoFrame.BaseTextWrapper to Leo's core.
    '''

    #@+others
    #@+node:ekr.20110605121601.18117: *3* qhlw.Birth
    def __init__ (self,c,item,name,widget):
        '''The ctor for the QHeadlineWrapper class.'''
        #g.trace('(QHeadlineWrapper)',item,qt_widget)
        BaseQTextWrapper.__init__(self,widget,name,c)
        assert isinstance(widget,QtWidgets.QLineEdit),widget
        assert self.qt_widget == widget
            # Init the base class.
            # Note: the .widget ivar allows callers not to know the implementation type.
        # Set ivars.
        self.item=item
        self.permanent = False # Warn the minibuffer that we can go away.
        # self.badFocusColors = []

    def __repr__ (self):
        return 'QHeadlineWrapper: %s' % id(self)
    #@+node:ekr.20110605121601.18118: *3* qhlw.Widget-specific overrides
    # These are safe versions of QLineEdit methods.
    #@+node:ekr.20110605121601.18119: *4* qhlw.check
    def check (self):
        '''Return True if the tree item exists and it's edit widget exists.'''
        trace = False and not g.unitTesting
        tree = self.c.frame.tree
        e = tree.treeWidget.itemWidget(self.item,0)
        valid = tree.isValidItem(self.item)
        result = valid and e == self.qt_widget
        if trace: g.trace('result %s self.qt_widget %s itemWidget %s' % (
            result,self.qt_widget,e))

        return result
    #@+node:ekr.20110605121601.18120: *4* qhlw.getAllText
    def getAllText(self):

        if self.check():
            w = self.qt_widget
            s = w.text()
            return g.u(s)
        else:
            return ''
    #@+node:ekr.20110605121601.18121: *4* qhlw.getInsertPoint
    def getInsertPoint(self):

        if self.check():
            i = self.qt_widget.cursorPosition()
            return i
        else:
            return 0
    #@+node:ekr.20110605121601.18122: *4* qhlw.getSelectionRange
    def getSelectionRange(self,sort=True):

        w = self.qt_widget
        if self.check():
            if w.hasSelectedText():
                i = w.selectionStart()
                s = w.selectedText()
                s = g.u(s)
                j = i + len(s)
            else:
                i = j = w.cursorPosition()
            return i,j
        else:
            return 0,0
    #@+node:ekr.20110605121601.18123: *4* qhlw.hasSelection
    def hasSelection(self):

        if self.check():
            return self.qt_widget.hasSelectedText()
        else:
            return False
    #@+node:ekr.20110605121601.18124: *4* qhlw.see & seeInsertPoint
    def see(self,i):
        pass

    def seeInsertPoint (self):
        pass
    #@+node:ekr.20110605121601.18125: *4* qhlw.setAllText
    def setAllText(self,s):
        '''Set all text of a Qt headline widget.'''
        if self.check():
            w = self.qt_widget
            w.setText(s)
    #@+node:ekr.20110605121601.18128: *4* qhlw.setFocus
    def setFocus (self):

        if self.check():
            g.app.gui.set_focus(self.c,self.qt_widget)
    #@+node:ekr.20110605121601.18129: *4* qhlw.setInsertPoint
    def setInsertPoint(self,i,s=None):

        if not self.check(): return
        w = self.qt_widget
        if s is None:
            s = w.text()
            s = g.u(s)
        i = self.toPythonIndex(i)
        i = max(0,min(i,len(s)))
        w.setCursorPosition(i)
    #@+node:ekr.20110605121601.18130: *4* qhlw.setSelectionRangeHelper
    def setSelectionRangeHelper(self,i,j,insert=None,s=None):

        if not self.check(): return
        w = self.qt_widget
        # g.trace(i,j,insert,w)
        if i > j: i,j = j,i
        if s is None:
            s = w.text()
            s = g.u(s)
        n = len(s)
        i = max(0,min(i,n))
        j = max(0,min(j,n))
        if insert is None:
            insert = j
        else:
            insert = self.toPythonIndex(insert)
            insert = max(0,min(insert,n))
        if i == j:
            w.setCursorPosition(i)
        else:
            length = j-i
            if insert < j:
                w.setSelection(j,-length)
            else:
                w.setSelection(i,length)
    #@-others
#@+node:ekr.20110605121601.18131: ** class QMinibufferWrapper (QLineEditWrapper)
class QMinibufferWrapper (QLineEditWrapper):

    def __init__ (self,c):
        '''Ctor for QMinibufferWrapper class.'''
        self.c = c
        w = c.frame.top.leo_ui.lineEdit # QLineEdit
        # g.trace('(QMinibufferWrapper)',w)
        # Init the base class.
        QLineEditWrapper.__init__(self,widget=w,name='minibuffer',c=c)
        assert self.qt_widget
        self.widget = self.qt_widget
            # Note: allows access to the widget without knowing its type.
        g.app.gui.setFilter(c,w,self,tag='minibuffer')
        # Monkey-patch the event handlers
        #@+<< define mouseReleaseEvent >>
        #@+node:ekr.20110605121601.18132: *3* << define mouseReleaseEvent >> (QMinibufferWrapper)
        def mouseReleaseEvent (*args,**keys):
            '''Override QLineEdit.mouseReleaseEvent.

            Simulate alt-x if we are not in an input state.
            '''
            # g.trace('(QMinibufferWrapper)',args,keys)
            # Important: c and w must be unbound here.
            k = c.k
            # Call the base class method.
            if len(args) == 1:
                event = args[0]
                QtWidgets.QLineEdit.mouseReleaseEvent(w,event)
            elif len(args) == 2:
                event = args[1]
                QtWidgets.QLineEdit.mouseReleaseEvent(*args)
            else:
                g.trace('can not happen')
                return
            # g.trace('state',k.state.kind,k.state.n)
            if not k.state.kind:
                # c.widgetWantsFocusNow(w) # Doesn't work.
                event2 = g.app.gui.create_key_event(c,
                    char='',stroke='',w=c.frame.body.wrapper)
                k.fullCommand(event2)
                # c.outerUpdate() # Doesn't work.
        #@-<< define mouseReleaseEvent >>
        w.mouseReleaseEvent = mouseReleaseEvent

    # Note: can only set one stylesheet at a time.
    def setBackgroundColor(self,color):
        self.qt_widget.setStyleSheet('background-color:%s' % color)

    def setForegroundColor(self,color):
        self.qt_widget.setStyleSheet('color:%s' % color)

    def setBothColors(self,background_color,foreground_color):
        self.qt_widget.setStyleSheet('background-color:%s; color: %s' % (
            background_color,foreground_color))
            
    def setStyleClass(self,style_class):
        self.qt_widget.setProperty('style_class', style_class)
        # to get the appearance to change because of a property
        # change, unlike a focus or hover change, we need to
        # re-apply the stylesheet.  But re-applying at the top level
        # is too CPU hungry, so apply just to this widget instead.
        # It may lag a bit when the style's edited, but the new top
        # level sheet will get pushed down quite frequently.
        self.qt_widget.setStyleSheet(self.c.frame.top.styleSheet())
#@+node:ekr.20110605121601.18103: ** class QScintillaWrapper (BaseQTextWrapper)
class QScintillaWrapper (BaseQTextWrapper):

    #@+others
    #@+node:ekr.20110605121601.18104: *3* qsci.Birth
    #@+node:ekr.20110605121601.18105: *4* qsci.ctor
    def __init__ (self,parent,c,name=None):
        '''Ctor for the QScintillaWrapper class.'''
        # g.trace('(QScintillaWrapper)',c.shortFileName(),name,g.callers())
        BaseQTextWrapper.__init__(self,parent,name,c=c)
            # Init the base class
        self.parent = parent
            # Ensure parent stays around.
        self.qt_widget = Qsci.QsciScintilla(parent)
        self.widget = self.qt_widget
            # Note: the .widget ivar allows callers not to know the implementation type.
        self.baseClassName='QScintillaWrapper'
        self.useScintilla = True
        self.setConfig()
    #@+node:ekr.20110605121601.18106: *4* qsci.setConfig
    def setConfig (self):
        '''Set QScintillaWrapper configuration options.'''
        c,w = self.c,self.qt_widget
        lexer = Qsci.QsciLexerPython(w)
        self.configure_lexer(lexer)
        w.setLexer(lexer)
        n = c.config.getInt('qt-scintilla-zoom-in')
        if n not in (None,0):
            w.zoomIn(n)
        w.setIndentationWidth(4)
        w.setIndentationsUseTabs(False)
        w.setAutoIndent(True)
    #@+node:ekr.20140831054256.18458: *4* qsci.configureLexer
    def configure_lexer(self,lexer):
        '''Configure the QScintilla lexer.'''
        # To do: make this more configurable in the Leo way.
        def oops(s):
            g.trace('bad @data qt-scintilla-styles:',s)
        # A small font size, to be magnified.
        c = self.c
        qcolor,qfont = QtWidgets.QColor,QtWidgets.QFont
        font = qfont("Courier New",8,qfont.Bold)
        lexer.setFont(font)
        table = None
        aList = c.config.getData('qt-scintilla-styles')
        if aList:
            aList = [s.split(',') for s in aList]
            table = []
            for z in aList:
                if len(z) == 2:
                    color,style = z
                    table.append((color.strip(),style.strip()),)
                else: oops('entry: %s' % z)
            # g.trace(g.printList(table))
        if not table:
            table = (
                ('red','Comment'),
                ('green','SingleQuotedString'),
                ('green','DoubleQuotedString'),
                ('green','TripleSingleQuotedString'),
                ('green','TripleDoubleQuotedString'),
                ('green','UnclosedString'),
                ('blue','Keyword'),
            )
        for color,style in table:
            if hasattr(lexer,style):
                style = getattr(lexer,style)
                try:
                    lexer.setColor(qcolor(color),style)
                except Exception:
                    oops('bad color: %s' % color)
            else: oops('bad style: %s' % style)
    #@+node:ekr.20110605121601.18107: *3* qsci.overrides
    #@+node:ekr.20110605121601.18108: *4* qsci.getAllText
    def getAllText(self):
        '''Get all text from a QsciScintilla widget.'''
        w = self.qt_widget
        s = w.text()
        s = g.u(s)
        return s
    #@+node:ekr.20110605121601.18109: *4* qsci.getInsertPoint
    def getInsertPoint(self):
        '''Get the insertion point from a QsciScintilla widget.'''
        w = self.qt_widget
        s = self.getAllText()
        row,col = w.getCursorPosition()  
        i = g.convertRowColToPythonIndex(s, row, col)
        return i
    #@+node:ekr.20110605121601.18110: *4* qsci.getSelectionRange
    def getSelectionRange(self,sort=True):
        '''Get the selection range from a QsciScintilla widget.'''
        w = self.qt_widget
        if w.hasSelectedText():
            s = self.getAllText()
            row_i,col_i,row_j,col_j = w.getSelection()
            i = g.convertRowColToPythonIndex(s, row_i, col_i)
            j = g.convertRowColToPythonIndex(s, row_j, col_j)
            if sort and i > j:
                i,j = j,i # 2013/03/02: real bug fix.
        else:
            i = j = self.getInsertPoint()
        return i,j
    #@+node:ekr.20110605121601.18111: *4* qsci.hasSelection
    def hasSelection(self):
        '''Return True if a QsciScintilla widget has a selection range.'''
        return self.qt_widget.hasSelectedText()
    #@+node:ekr.20110605121601.18112: *4* qsci.see
    def see(self,i):
        '''Ensure insert point i is visible in a QsciScintilla widget.'''
        # Ok for now.  Using SCI_SETYCARETPOLICY might be better.
        w = self.qt_widget
        s = self.getAllText()
        row,col = g.convertPythonIndexToRowCol(s,i)
        w.ensureLineVisible(row)

    # Use base-class method for seeInsertPoint.
    #@+node:ekr.20110605121601.18113: *4* qsci.setAllText
    def setAllText(self,s):
        '''Set the text of a QScintilla widget.'''
        w = self.qt_widget
        assert isinstance(w,Qsci.QsciScintilla),w
        g.trace(len(s))
        w.setText(s)
        w.update()

    #@+node:ekr.20110605121601.18114: *4* qsci.setInsertPoint
    def setInsertPoint(self,i,s=None):
        '''Set the insertion point in a QsciScintilla widget.'''
        w = self.qt_widget
        w.SendScintilla(w.SCI_SETCURRENTPOS,i)
        w.SendScintilla(w.SCI_SETANCHOR,i)
    #@+node:ekr.20110605121601.18115: *4* qsci.setSelectionRangeHelper
    def setSelectionRangeHelper(self,i,j,insert=None,s=None):
        '''Set the selection range in a QsciScintilla widget.'''
        w = self.qt_widget
        # g.trace('i',i,'j',j,'insert',insert,g.callers(4))
        if insert in (j,None):
            self.setInsertPoint(j)
            w.SendScintilla(w.SCI_SETANCHOR,i)
        else:
            self.setInsertPoint(i)
            w.SendScintilla(w.SCI_SETANCHOR,j)
    #@-others
#@+node:ekr.20110605121601.18071: ** class QTextEditWrapper(BaseQTextWrapper)
class QTextEditWrapper (BaseQTextWrapper):
    '''
    A class representing the QTextEdit widget,
    Supporting the BaseQTextWRapper interface.
    '''
    #@+others
    #@+node:ekr.20110605121601.18072: *3* qtew.Birth
    #@+node:ekr.20110605121601.18073: *4* qtew.ctor
    def __init__ (self,qt_widget,name,c=None):
        '''
        Ctor for QTextEditWrapper class.
        qt_widget is a QTextEdit or QTextBrowser.
        '''
        # Init the base class.
        BaseQTextWrapper.__init__(self,qt_widget,name,c=c)
        assert qt_widget == self.qt_widget,(qt_widget,self.qt_widget)
        self.widget = self.qt_widget
            # Important: this allow callers not to know the implementation type.
        self.baseClassName='QTextEditWrapper'
        self.qt_widget.setUndoRedoEnabled(False)
        self.setConfig()
    #@+node:ekr.20110605121601.18076: *4* qtew.setConfig
    def setConfig (self):
        '''Set configuration options for QTextEdit.'''
        c = self.c
        w = self.qt_widget
        n = c.config.getInt('qt-rich-text-zoom-in')
        w.setWordWrapMode(QtGui.QTextOption.NoWrap)
        # w.zoomIn(1)
        # w.updateMicroFocus()
        if n not in (None,0):
            # This only works when there is no style sheet.
            # g.trace('zoom-in',n)
            w.zoomIn(n)
            w.updateMicroFocus()
        # tab stop in pixels - no config for this (yet)        
        w.setTabStopWidth(24)
    #@+node:ekr.20110605121601.18077: *3* qtew.leoMoveCursorHelper & helper
    def leoMoveCursorHelper (self,kind,extend=False,linesPerPage=15):
        '''Move the cursor in a QTextEdit.'''
        trace = False and not g.unitTesting
        verbose = True
        w = self.qt_widget
        if trace:
            g.trace(kind,'extend',extend)
            if verbose:
                g.trace(len(w.toPlainText()))
        tc = QtGui.QTextCursor
        d = {
            'exchange': True, # Dummy.
            'down':tc.Down,'end':tc.End,'end-line':tc.EndOfLine,
            'home':tc.Start,'left':tc.Left,'page-down':tc.Down,
            'page-up':tc.Up,'right':tc.Right,'start-line':tc.StartOfLine,
            'up':tc.Up,
        }
        kind = kind.lower()
        op = d.get(kind)
        mode = tc.KeepAnchor if extend else tc.MoveAnchor
        if not op:
            return g.trace('can not happen: bad kind: %s' % kind)
        if kind in ('page-down','page-up'):
            self.pageUpDown(op, mode)
        elif kind == 'exchange': # exchange-point-and-mark
            cursor = w.textCursor()
            anchor = cursor.anchor()
            pos = cursor.position()
            cursor.setPosition(pos,tc.MoveAnchor)
            cursor.setPosition(anchor,tc.KeepAnchor)
            w.setTextCursor(cursor)
        else:
            if not extend:
                # Fix an annoyance. Make sure to clear the selection.
                cursor = w.textCursor()
                cursor.clearSelection()
                w.setTextCursor(cursor)
            w.moveCursor(op,mode)
        # 2012/03/25.  Add this common code.
        self.seeInsertPoint()
        self.rememberSelectionAndScroll()
        self.c.frame.updateStatusLine()
    #@+node:btheado.20120129145543.8180: *4* qtew.pageUpDown
    def pageUpDown (self, op, moveMode):

        '''The QTextEdit PageUp/PageDown functionality seems to be "baked-in"
           and not externally accessible.  Since Leo has its own keyhandling
           functionality, this code emulates the QTextEdit paging.  This is
           a straight port of the C++ code found in the pageUpDown method
           of gui/widgets/qtextedit.cpp'''

        control = self.qt_widget
        cursor = control.textCursor()
        moved = False
        lastY = control.cursorRect(cursor).top()
        distance = 0
        # move using movePosition to keep the cursor's x
        while True:
            y = control.cursorRect(cursor).top()
            distance += abs(y - lastY)
            lastY = y
            moved = cursor.movePosition(op, moveMode)
            if (not moved or distance >= control.height()):
                break
        tc = QtGui.QTextCursor
        sb = control.verticalScrollBar()
        if moved:
            if (op == tc.Up):
                cursor.movePosition(tc.Down, moveMode)
                sb.triggerAction(QtWidgets.QAbstractSlider.SliderPageStepSub)
            else:
                cursor.movePosition(tc.Up, moveMode)
                sb.triggerAction(QtWidgets.QAbstractSlider.SliderPageStepAdd)
        control.setTextCursor(cursor)
    #@+node:ekr.20110605121601.18078: *3* qtew.Widget-specific overrides
    #@+node:ekr.20110605121601.18099: *4* qtew. PythonIndex
    #@+node:ekr.20110605121601.18100: *5* qtew.toPythonIndex (Fast)
    def toPythonIndex (self,index):
        '''This is much faster than versions using g.toPythonIndex.'''
        w = self
        te = self.qt_widget
        if index is None:
            return 0
        if type(index) == type(99):
            return index
        elif index == '1.0':
            return 0
        elif index == 'end':
            # g.trace('===== slow =====',repr(index))
            return w.getLastPosition()
        else:
            # g.trace('===== slow =====',repr(index))
            doc = te.document()
            data = index.split('.')
            if len(data) == 2:
                row,col = data
                row,col = int(row),int(col)
                bl = doc.findBlockByNumber(row-1)
                return bl.position() + col
            else:
                g.trace('bad string index: %s' % index)
                return 0

    toGuiIndex = toPythonIndex
    #@+node:ekr.20110605121601.18101: *5* qtew.toPythonIndexRowCol
    def toPythonIndexRowCol(self,index):

        w = self 
        if index == '1.0':
            return 0, 0, 0
        if index == 'end':
            index = w.getLastPosition()
        te = self.qt_widget
        doc = te.document()
        i = w.toPythonIndex(index)
        bl = doc.findBlock(i)
        row = bl.blockNumber()
        col = i - bl.position()
        return i,row,col
    #@+node:ekr.20110605121601.18079: *4* qtew.delete (avoid call to setAllText)
    def delete(self,i,j=None):

        trace = False and not g.unitTesting
        c,w = self.c,self.qt_widget
        colorer = c.frame.body.colorizer.highlighter.colorer
        # n = colorer.recolorCount
        if trace: g.trace(self.getSelectionRange())
        i = self.toGuiIndex(i)
        if j is None: j = i+1
        j = self.toGuiIndex(j)
        if i > j: i,j = j,i
        if trace: g.trace(i,j)
        # Set a hook for the colorer.
        colorer.initFlag = True
        sb = w.verticalScrollBar()
        pos = sb.sliderPosition()
        cursor = w.textCursor()
        try:
            self.changingText = True # Disable onTextChanged
            old_i,old_j = self.getSelectionRange()
            if i == old_i and j == old_j:
                # Work around an apparent bug in cursor.movePosition.
                cursor.removeSelectedText()
            elif i == j:
                pass
            else:
                # g.trace('*** using dubious code')
                cursor.setPosition(i)
                moveCount = abs(j-i)
                cursor.movePosition(cursor.Right,cursor.KeepAnchor,moveCount)
                w.setTextCursor(cursor)  # Bug fix: 2010/01/27
                if trace:
                    i,j = self.getSelectionRange()
                    g.trace(i,j)
                cursor.removeSelectedText()
                if trace: g.trace(self.getSelectionRange())
        finally:
            self.changingText = False
        sb.setSliderPosition(pos)
        # g.trace('%s calls to recolor' % (colorer.recolorCount-n))
    #@+node:ekr.20110605121601.18080: *4* qtew.flashCharacter
    def flashCharacter(self,i,bg='white',fg='red',flashes=3,delay=75):

        # numbered color names don't work in Ubuntu 8.10, so...
        if bg[-1].isdigit() and bg[0] != '#':
            bg = bg[:-1]
        if fg[-1].isdigit() and fg[0] != '#':
            fg = fg[:-1]

        # This might causes problems during unit tests.
        # The selection point isn't restored in time.
        if g.app.unitTesting:
            return
        w = self.qt_widget # A QTextEdit.
        e = QtWidgets.QTextCursor

        def after(func):
            QtCore.QTimer.singleShot(delay,func)

        def addFlashCallback(self=self,w=w):
            n,i = self.flashCount,self.flashIndex
            cursor = w.textCursor() # Must be the qt_widget's cursor.
            cursor.setPosition(i)
            cursor.movePosition(e.Right,e.KeepAnchor,1)
            extra = w.ExtraSelection()
            extra.cursor = cursor
            if self.flashBg: extra.format.setBackground(QtWidgets.QColor(self.flashBg))
            if self.flashFg: extra.format.setForeground(QtWidgets.QColor(self.flashFg))
            self.extraSelList = [extra] # keep the reference.
            w.setExtraSelections(self.extraSelList)
            self.flashCount -= 1
            after(removeFlashCallback)

        def removeFlashCallback(self=self,w=w):
            w.setExtraSelections([])
            if self.flashCount > 0:
                after(addFlashCallback)
            else:
                w.setFocus()

        self.flashCount = flashes
        self.flashIndex = i
        self.flashBg = None if bg.lower()=='same' else bg
        self.flashFg = None if fg.lower()=='same' else fg
        addFlashCallback()
    #@+node:ekr.20110605121601.18102: *4* qtew.get
    def get(self,i,j=None):

        if 1:
            # 2012/04/12: fix the following two bugs by using the vanilla code:
            # https://bugs.launchpad.net/leo-editor/+bug/979142
            # https://bugs.launchpad.net/leo-editor/+bug/971166
            s = self.getAllText()
            i = self.toGuiIndex(i)
            j = self.toGuiIndex(j)
            return s[i:j]
        else:
            # This fails when getting text from the html-encoded log panes.
            i = self.toGuiIndex(i)
            if j is None: 
                j = i+1
            else:
                j = self.toGuiIndex(j)
            te = self.qt_widget
            doc = te.document()
            bl = doc.findBlock(i)
            #row = bl.blockNumber()
            #col = index - bl.position()

            # common case, e.g. one character    
            if bl.contains(j):
                s = g.u(bl.text())
                offset = i - bl.position()
                ret = s[ offset : offset + (j-i)]
                #print "fastget",ret
                return ret

            # This is much slower, but will have to do        
            #g.trace('Slow get()', g.callers(5))
            s = self.getAllText()
            i = self.toGuiIndex(i)
            j = self.toGuiIndex(j)
            return s[i:j]
    #@+node:ekr.20110605121601.18081: *4* qtew.getAllText
    def getAllText(self):

        w = self.qt_widget
        s = g.u(w.toPlainText())
        return s
    #@+node:ekr.20110605121601.18082: *4* qtew.getInsertPoint
    def getInsertPoint(self):

        return self.qt_widget.textCursor().position()
    #@+node:ekr.20110605121601.18083: *4* qtew.getSelectionRange
    def getSelectionRange(self,sort=True):

        w = self.qt_widget
        tc = w.textCursor()
        i,j = tc.selectionStart(),tc.selectionEnd()
        return i,j
    #@+node:ekr.20110605121601.18084: *4* qtew.getYScrollPosition
    def getYScrollPosition(self):

        # **Important**: There is a Qt bug here: the scrollbar position
        # is valid only if cursor is visible.  Otherwise the *reported*
        # scrollbar position will be such that the cursor *is* visible.
        trace = False and g.trace_scroll and not g.unitTesting
        w = self.qt_widget
        sb = w.verticalScrollBar()
        pos = sb.sliderPosition()
        if trace: g.trace(pos)
        return pos
    #@+node:ekr.20110605121601.18085: *4* qtew.hasSelection
    def hasSelection(self):

        return self.qt_widget.textCursor().hasSelection()
    #@+node:ekr.20110605121601.18089: *4* qtew.insert (avoid call to setAllText)
    def insert(self,i,s):

        c,w = self.c,self.qt_widget
        colorer = c.frame.body.colorizer.highlighter.colorer
        # n = colorer.recolorCount
        # Set a hook for the colorer.
        colorer.initFlag = True
        i = self.toGuiIndex(i)
        cursor = w.textCursor()
        try:
            self.changingText = True # Disable onTextChanged.
            cursor.setPosition(i)
            cursor.insertText(s) # This cause an incremental call to recolor.
            w.setTextCursor(cursor) # Bug fix: 2010/01/27
        finally:
            self.changingText = False
    #@+node:ekr.20110605121601.18086: *4* qtew.scrolling
    #@+node:ekr.20110605121601.18087: *5* qtew.indexIsVisible and linesPerPage
    def linesPerPage (self):
        '''Return the number of lines presently visible.'''
        w = self.qt_widget
        h = w.size().height()
        lineSpacing = w.fontMetrics().lineSpacing()
        n = h/lineSpacing
        return n
    #@+node:ekr.20110605121601.18088: *5* qtew.scrollDelegate (QTextEdit)
    def scrollDelegate(self,kind):
        '''
        Scroll a QTextEdit up or down one page.
        direction is in ('down-line','down-page','up-line','up-page')
        '''
        c = self.c
        w = self.qt_widget
        vScroll = w.verticalScrollBar()
        h = w.size().height()
        lineSpacing = w.fontMetrics().lineSpacing()
        n = h/lineSpacing
        n = max(2,n-3)
        if   kind == 'down-half-page': delta = n/2
        elif kind == 'down-line':      delta = 1
        elif kind == 'down-page':      delta = n
        elif kind == 'up-half-page':   delta = -n/2
        elif kind == 'up-line':        delta = -1
        elif kind == 'up-page':        delta = -n
        else:
            delta = 0 ; g.trace('bad kind:',kind)
        val = vScroll.value()
        # g.trace(kind,n,h,lineSpacing,delta,val,g.callers())
        vScroll.setValue(val+(delta*lineSpacing))
        c.bodyWantsFocus()
    #@+node:ekr.20110605121601.18090: *4* qtew.see & seeInsertPoint
    def see(self,i):

        trace = g.trace_see and not g.unitTesting

        if g.no_see:
            pass
        else:
            if trace: g.trace('*****',i,g.callers())
            self.qt_widget.ensureCursorVisible()

    def seeInsertPoint (self):

        trace = g.trace_see and not g.unitTesting
        if g.no_see:
            pass
        else:
            if trace: g.trace('*****',g.callers())
            self.qt_widget.ensureCursorVisible()
    #@+node:ekr.20110605121601.18092: *4* qtew.setAllText
    def setAllText(self,s):
        '''Set the text of body pane.'''
        traceTime = True and not g.unitTesting
        c,w = self.c,self.qt_widget
        colorizer = c.frame.body.colorizer
        highlighter = colorizer.highlighter
        colorer = highlighter.colorer
        try:
            if traceTime:
                t1 = time.time()
            colorer.initFlag = True
            self.changingText = True # Disable onTextChanged.
            colorizer.changingText = True # Disable colorizer.
            # g.trace('read/write text')
            w.setReadOnly(False)
            w.setPlainText(s)
            # w.update()
                # 2014/08/30: w.update does not ensure that all text is loaded
                # before the user starts editing it!
            if traceTime:
                delta_t = time.time()-t1
                if False or delta_t > 0.1:
                    g.trace('w.setPlainText: %2.3f sec.' % (delta_t))
                    # g.trace('isinstance(w,QTextEdit)',isinstance(w,QtGui.QTextEdit))
        finally:
            self.changingText = False
            colorizer.changingText = False
    #@+node:ekr.20110605121601.18095: *4* qtew.setInsertPoint
    def setInsertPoint(self,i,s=None):

        # Fix bug 981849: incorrect body content shown.
        # Use the more careful code in setSelectionRangeHelper & lengthHelper.
        self.setSelectionRangeHelper(i=i,j=i,insert=i,s=s)
    #@+node:ekr.20110605121601.18096: *4* qtew.setSelectionRangeHelper
    def setSelectionRangeHelper(self,i,j,insert=None,s=None):
        '''Set the selection range and the insert point.'''
        traceTime = False and not g.unitTesting
        # Part 1
        if traceTime: t1 = time.time()
        w = self.qt_widget
        i = self.toPythonIndex(i)
        j = self.toPythonIndex(j)
        if s is not None:
            n = len(s)
        elif 1:
            s = self.getAllText()
            n = len(s)
        i = max(0,min(i,n))
        j = max(0,min(j,n))
        if insert is None:
            ins = max(i,j)
        else:
            ins = self.toPythonIndex(insert)
            ins = max(0,min(ins,n))
        if traceTime:
            delta_t = time.time()-t1
            if delta_t > 0.1: g.trace('part1: %2.3f sec' % (delta_t))
        # Part 2:
        if traceTime: t2 = time.time()
        # 2010/02/02: Use only tc.setPosition here.
        # Using tc.movePosition doesn't work.
        tc = w.textCursor()
        if i == j:
            tc.setPosition(i)
        elif ins == j:
            # Put the insert point at j
            tc.setPosition(i)
            tc.setPosition(j,tc.KeepAnchor)
        elif ins == i:
            # Put the insert point at i
            tc.setPosition(j)
            tc.setPosition(i,tc.KeepAnchor)
        else:
            # 2014/08/21: It doesn't seem possible to put the insert point somewhere else!
            tc.setPosition(j)
            tc.setPosition(i,tc.KeepAnchor)
            # g.trace('***',i,j,ins)
        w.setTextCursor(tc)
        # Remember the values for v.restoreCursorAndScroll.
        v = self.c.p.v # Always accurate.
        v.insertSpot = ins
        if i > j: i,j = j,i
        assert(i<=j)
        v.selectionStart = i
        v.selectionLength = j-i
        v.scrollBarSpot = spot = w.verticalScrollBar().value()
        # g.trace(spot,v.h)
        # g.trace('i: %s j: %s ins: %s spot: %s %s' % (i,j,ins,spot,v.h))
        if traceTime:
            delta_t = time.time()-t2
            tot_t = time.time()-t1
            if delta_t > 0.1: g.trace('part2: %2.3f sec' % (delta_t))
            if tot_t > 0.1:   g.trace('total: %2.3f sec' % (tot_t))
    #@+node:ekr.20110605121601.18098: *4* qtew.setYScrollPosition
    def setYScrollPosition(self,pos):

        trace = (False or g.trace_scroll) and not g.unitTesting
        w = self.qt_widget
        if g.no_scroll:
            return
        elif pos is None:
            if trace: g.trace('None')
        else:
            if trace: g.trace(pos,g.callers())
            sb = w.verticalScrollBar()
            sb.setSliderPosition(pos)
    #@-others
#@-others
#@-leo
