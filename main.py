#-------------------------------------------------------------------------------
# Name:        Object bounding box label tool for Yolo Algorithm
# Purpose:     Label object bboxes
# Author:      UHRWEILLER Frederic
# Created:     06/01/2018
# Note:        Images have to be in ".jpg" extension --> case sensitive!
# Folders:     The images to be labeled reside in /Images/001, /Images/002, etc.

# Fork from original Author:      Qiushi
# Original Creation:     06/06/2014

#
#-------------------------------------------------------------------------------
from __future__ import division
from Tkinter import *
from PIL import Image, ImageTk
import os
import glob
import random
import xml.etree.ElementTree as ET
import tkFont

# colors for the bboxes
COLORS = ['red', 'blue', 'orange', 'pink', 'cyan', 'green', 'black']


class LabelTool():
    def __init__(self, master):
        # set up the main frame
        self.parent = master
        self.parent.title("LabelTool")
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=1)
        self.parent.resizable(width = FALSE, height = FALSE)

        # initialize global state
        self.imageDir = ''
        self.imageList= []
        self.outDir = ''
        self.cur = 0
        self.total = 0
        self.category = 0
        self.imagename = ''
        self.labelfilename = ''
        self.tkimg = None

        # initialize mouse state
        self.STATE = {}
        self.STATE['click'] = 0
        self.STATE['x'], self.STATE['y'] = 0, 0

        # reference to bbox
        self.bboxIdList = []
        self.bboxId = None
        self.bboxList = []
        self.hl = None
        self.vl = None
        self.className = [] #to save the name of the selected objects

        # ----------------- GUI stuff ---------------------
        # dir entry & load
        self.label = Label(self.frame, text = "Image Dir:")
        self.label.grid(row = 0, column = 0, sticky = E)
        self.entry = Entry(self.frame)
        self.entry.grid(row = 0, column = 1, sticky = W+E)

        self.labelClassName = Label(self.frame, text = "Class:")
        self.labelClassName.grid(row = 1, column = 0, sticky = E)
        self.entryClassName = Entry(self.frame)
        self.entryClassName.grid(row = 1, column = 1, sticky = W+E)

        self.ldBtn = Button(self.frame, text = "Load", command = self.loadDir)
        self.ldBtn.grid(row = 0, column = 2, sticky = W+E)

        # main panel for labeling
        self.mainPanel = Canvas(self.frame, cursor='tcross')
        self.mainPanel.bind("<Button-1>", self.mouseClick)
        self.mainPanel.bind("<Motion>", self.mouseMove)
        self.parent.bind("<Escape>", self.cancelBBox)  # press <Escape> to cancel current bbox
        #self.parent.bind("s", self.cancelBBox)
        self.parent.bind("<Left>", self.prevImage) # press 'a' to go backforward
        self.parent.bind("<Right>", self.nextImage) # press 'd' to go forward
        self.mainPanel.grid(row = 2, column = 1, rowspan = 4, sticky = W+N)

        # showing bbox info & delete bbox
        self.lb1 = Label(self.frame, text = 'Bounding boxes:')
        self.lb1.grid(row = 1, column = 2,  sticky = W+N)
        self.listbox = Listbox(self.frame, width = 28, height = 12)
        self.listbox.grid(row = 2, column = 2, sticky = N)
        self.btnDel = Button(self.frame, text = 'Delete', command = self.delBBox)
        self.btnDel.grid(row = 3, column = 2, sticky = W+E+N)
        self.btnClear = Button(self.frame, text = 'ClearAll', command = self.clearBBox)
        self.btnClear.grid(row = 4, column = 2, sticky = W+E+N)

        # control panel for image navigation
        self.ctrPanel = Frame(self.frame)
        self.ctrPanel.grid(row = 6, column = 1, columnspan = 2, sticky = W+E)
        self.prevBtn = Button(self.ctrPanel, text='<< Prev', width = 10, command = self.prevImage)
        self.prevBtn.pack(side = LEFT, padx = 5, pady = 3)
        self.nextBtn = Button(self.ctrPanel, text='Next >>', width = 10, command = self.nextImage)
        self.nextBtn.pack(side = LEFT, padx = 5, pady = 3)
        self.progLabel = Label(self.ctrPanel, text = "Progress:     /    ")
        self.progLabel.pack(side = LEFT, padx = 5)
        self.tmpLabel = Label(self.ctrPanel, text = "Go to Image No.")
        self.tmpLabel.pack(side = LEFT, padx = 5)
        self.idxEntry = Entry(self.ctrPanel, width = 5)
        self.idxEntry.pack(side = LEFT)
        self.goBtn = Button(self.ctrPanel, text = 'Go', command = self.gotoImage)
        self.goBtn.pack(side = LEFT)


        # display mouse position
        self.disp = Label(self.ctrPanel, text='')
        self.disp.pack(side = RIGHT)

        self.frame.columnconfigure(1, weight = 1)
        self.frame.rowconfigure(4, weight = 1)


    def loadDir(self, dbg = False):
        if not dbg:
            s = self.entry.get()
            self.parent.focus()
            self.category = int(s)
        else:
            s = r'D:\workspace\python\labelGUI'

        # get image list
        self.imageDir = os.path.join(r'./Images', '%03d' %(self.category))
        self.imageList = glob.glob(os.path.join(self.imageDir, '*.jpg'))
        if len(self.imageList) == 0:
            print ('No .jpg images found in the specified dir!')
            return

        # default to the 1st image in the collection
        self.cur = 1
        self.total = len(self.imageList)

         # set up output dir
        self.outDir = os.path.join(r'./Labels', '%03d' %(self.category))

        if not os.path.exists(self.outDir):
            os.mkdir(self.outDir)

        self.loadImage()
        print ('%d images loaded from %s' %(self.total, s))

    def loadImage(self):
        # load image
        imagepath = self.imageList[self.cur - 1]
        self.img = Image.open(imagepath)
        self.tkimg = ImageTk.PhotoImage(self.img)
        self.mainPanel.config(width = max(self.tkimg.width(), 400), height = max(self.tkimg.height(), 400))
        self.mainPanel.create_image(0, 0, image = self.tkimg, anchor=NW)
        self.progLabel.config(text = "%04d/%04d" %(self.cur, self.total))

        # load labels
        self.clearBBox()
        self.imagename = os.path.split(imagepath)[-1].split('.')[0]
        labelname = self.imagename + '.xml'
        self.labelfilename = os.path.join(self.outDir, labelname)
        bbox_cnt = 0
        if os.path.exists(self.labelfilename):
            tree = ET.parse(self.labelfilename)
            root = tree.getroot()
            tmp = []
            for object in root.findall('object'):
                bbox_cnt += 1
            for object in root.findall('object'):
                bndbox = object.find('bndbox')
                self.className.append(object.find('name').text)
                tmp.append(int(bndbox.find('xmin').text))
                tmp.append(int(bndbox.find('ymin').text))
                tmp.append(int(bndbox.find('xmax').text))
                tmp.append(int(bndbox.find('ymax').text))
                self.bboxList.append(tuple(tmp))
                tmpId = self.mainPanel.create_rectangle(tmp[0], tmp[1], \
                                                             tmp[2], tmp[3], \
                                                             width = 2, \
                                                             outline = COLORS[(len(self.bboxList)-1) % len(COLORS)])
                self.bboxIdList.append(tmpId)
                self.listbox.insert(END, '%s: (%d, %d) -> (%d, %d)' %(self.className[-1], tmp[0], tmp[1], tmp[2], tmp[3]))
                self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = COLORS[(len(self.bboxIdList) - 1) % len(COLORS)])
                tmp = []


    def saveImage(self): #Save ".xml" file
        with open(self.labelfilename, 'w') as f:
            f.write("<annotation verified=\"yes\">\
                        \n\t<folder>%03d" %(self.category) + "</folder>\
                        \n\t<filename>"+self.imagename+".jpg</filename>\
                        \n\t<path>"+self.imageList[self.cur - 1]+"</path>\
                        \n\t<source>\
                        \n\t\t<database>Unknown</database>\
                        \n\t</source>\
                        \n\t<size>\
                            \n\t\t<width>480</width>\
                            \n\t\t<height>360</height>\
                            \n\t\t<depth>3</depth>\
                        \n\t</size>\
                        \n\t<segmented>0</segmented>")
            for id, bbox in enumerate(self.bboxList):
                f.write("\n\t<object>\
                            \n\t\t<name>%s" %(self.className[id])+"</name>\
                            \n\t\t<pose>Unspecified</pose>\
                            \n\t\t<truncated>0</truncated>\
                            \n\t\t<difficult>0</difficult>")
                f.write("\n\t\t<bndbox>")
                f.write("\n\t\t\t<xmin>")
                f.write(str(bbox[0]))
                f.write("</xmin>")
                f.write("\n\t\t\t<ymin>")
                f.write(str(bbox[1]))
                f.write("</ymin>")
                f.write("\n\t\t\t<xmax>")
                f.write(str(bbox[2]))
                f.write("</xmax>")
                f.write("\n\t\t\t<ymax>")
                f.write(str(bbox[3]))
                f.write("</ymax>")
                f.write("\n\t\t</bndbox>")
                f.write("\n\t</object>")
            f.write("\n</annotation>")

        print ('Image No. %d saved' %(self.cur))


    def mouseClick(self, event):
        if self.STATE['click'] == 0:
            self.STATE['x'], self.STATE['y'] = event.x, event.y
        else:
            x1, x2 = min(self.STATE['x'], event.x), max(self.STATE['x'], event.x)
            y1, y2 = min(self.STATE['y'], event.y), max(self.STATE['y'], event.y)
            self.bboxList.append((x1, y1, x2, y2))
            self.bboxIdList.append(self.bboxId)
            self.bboxId = None
            self.listbox.insert(END, '%s: (%d, %d) -> (%d, %d)' %(self.entryClassName.get(), x1, y1, x2, y2))
            self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = COLORS[(len(self.bboxIdList) - 1) % len(COLORS)])
            self.className.append(self.entryClassName.get())
        self.STATE['click'] = 1 - self.STATE['click']

    def mouseMove(self, event):
        self.disp.config(text = 'x: %d, y: %d' %(event.x, event.y))
        if self.tkimg:
            if self.hl:
                self.mainPanel.delete(self.hl)
            self.hl = self.mainPanel.create_line(0, event.y, self.tkimg.width(), event.y, width = 2)
            if self.vl:
                self.mainPanel.delete(self.vl)
            self.vl = self.mainPanel.create_line(event.x, 0, event.x, self.tkimg.height(), width = 2)
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
            self.bboxId = self.mainPanel.create_rectangle(self.STATE['x'], self.STATE['y'], \
                                                            event.x, event.y, \
                                                            width = 2, \
                                                            outline = COLORS[len(self.bboxList) % len(COLORS)])

    def cancelBBox(self, event):
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
                self.bboxId = None
                self.STATE['click'] = 0

    def delBBox(self):
        sel = self.listbox.curselection()
        if len(sel) != 1 :
            return
        idx = int(sel[0])
        self.mainPanel.delete(self.bboxIdList[idx])
        self.bboxIdList.pop(idx)
        self.bboxList.pop(idx)
        self.listbox.delete(idx)
        self.className.pop(idx)

    def clearBBox(self):
        for idx in range(len(self.bboxIdList)):
            self.mainPanel.delete(self.bboxIdList[idx])
        self.listbox.delete(0, len(self.bboxList))
        self.bboxIdList = []
        self.bboxList = []
        self.className = []

    def prevImage(self, event = None):
        self.saveImage()
        if self.cur > 1:
            self.cur -= 1
            self.loadImage()

    def nextImage(self, event = None):
        self.saveImage()
        if self.cur < self.total:
            self.cur += 1
            self.loadImage()

    def gotoImage(self):
        idx = int(self.idxEntry.get())
        if 1 <= idx and idx <= self.total:
            self.saveImage()
            self.cur = idx
            self.loadImage()


if __name__ == '__main__':
    root = Tk()
    tool = LabelTool(root)
    root.resizable(width =  True, height = True)
    root.minsize(1024, 768)
    root.mainloop()
