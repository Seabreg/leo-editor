# -*- coding: utf-8 -*-
#@+leo-ver=5-thin
#@+node:ekr.20150514035943.1: * @file ../commands/baseCommands.py
#@@first

'''The base class for all of Leo's user commands.'''

import leo.core.leoGlobals as g

class BaseEditCommandsClass:
    '''The base class for all edit command classes'''
    #@+others
    #@+node:ekr.20150516040334.1: ** BaseEdit.ctor
    def __init__ (self,c):
        '''Ctor for the BaseEditCommandsClass class.'''
        # To keep pylint happy.
        # Subclasses just set self.c rather than calling this ctor.
        self.c = c
    #@+node:ekr.20150514043714.3: ** BaseEdit.begin/endCommand (handles undo)
    #@+node:ekr.20150514043714.4: *3* BaseEdit.beginCommand
    def beginCommand (self,w,undoType='Typing'):
        '''Do the common processing at the start of each command.'''
        c,p = self.c,self.c.p
        name = c.widget_name(w)
        if name.startswith('body'):
            oldSel =  w.getSelectionRange()
            oldText = p.b
            self.undoData = b = g.Bunch()
            # To keep pylint happy.
            b.ch=''
            b.name=name
            b.oldSel=oldSel
            b.oldText=oldText
            b.w=w
            b.undoType=undoType
        else:
            self.undoData = None
        return w
    #@+node:ekr.20150514043714.6: *3* BaseEdit.endCommand
    def endCommand(self,label=None,changed=True,setLabel=True):
        '''
        Do the common processing at the end of each command.
        Handles undo only if we are in the body pane.
        '''
        trace =  False and not g.unitTesting
        c,k = self.c,self.c.k
        b = self.undoData 
        if trace: g.trace('changed',changed)
        if b and b.name.startswith('body') and changed:
            c.frame.body.onBodyChanged(undoType=b.undoType,
                oldSel=b.oldSel,oldText=b.oldText,oldYview=None)
        self.undoData = None
        k.clearState()
        # Warning: basic editing commands **must not** set the label.
        if setLabel:
            if label:
                k.setLabelGrey(label)
            else:
                k.resetLabel()
    #@+node:ekr.20150514043714.7: ** BaseEdit.editWidget
    def editWidget (self,event,forceFocus=True):
        '''Return the edit widget for the event. Also sets self.w'''
        trace = False and not g.unitTesting
        c = self.c
        w = event and event.widget
        wname = (w and c.widget_name(w)) or '<no widget>'
        if w and g.isTextWrapper(w):
            pass
        else:
            w = c.frame.body and c.frame.body.wrapper
        if trace: g.trace(g.isTextWrapper(w),wname,w)
        if w and forceFocus:
            c.widgetWantsFocusNow(w)
        self.w = w
        return w
    #@+node:ekr.20150514043714.8: ** BaseEdit.getWSString
    def getWSString (self,s):

        return ''.join([ch if ch=='\t' else ' ' for ch in s])
    #@+node:ekr.20150514043714.9: ** BaseEdit.oops
    def oops (self):

        g.pr("BaseEditCommandsClass oops:",
            g.callers(),
            "must be overridden in subclass")
    #@+node:ekr.20150514043714.10: ** BaseEdit.Helpers
    #@+node:ekr.20150514043714.11: *3* BaseEdit._chckSel
    def _chckSel (self,event,warning='no selection'):
        '''Return True if there is a selection in the edit widget.'''
        k = self.c.k
        w = self.editWidget(event)
        val = w and w.hasSelection()
        if warning and not val:
            # k.setLabelGrey(warning)
            g.es(warning,color='red')
        return val
    #@+node:ekr.20150514043714.13: *3* BaseEdit.getRectanglePoints
    def getRectanglePoints (self,w):

        c = self.c
        c.widgetWantsFocusNow(w)

        s = w.getAllText()
        i,j = w.getSelectionRange()
        r1,r2 = g.convertPythonIndexToRowCol(s,i)
        r3,r4 = g.convertPythonIndexToRowCol(s,j)

        return r1+1,r2,r3+1,r4
    #@+node:ekr.20150514043714.14: *3* BaseEdit.keyboardQuit
    def keyboardQuit (self,event=None):

        '''Clear the state and the minibuffer label.'''

        return self.c.k.keyboardQuit()
    #@-others
#@-leo
