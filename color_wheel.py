# MIT License
#
# Copyright (c) 2018 - 2021 Electrostatus
# https://orthallelous.wordpress.com/2018/12/19/custom-color-dialog/
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from PySide6.QtCore import (QBuffer, QEvent, QIODevice, QRegularExpression, Qt,  # QTimer,
                            QPoint, QPointF, QRectF, QSize, QSizeF, QRect,
                            Signal)  # PySide6
from PySide6.QtWidgets import (QAbstractSpinBox, QApplication, QColorDialog,
                               QComboBox, QDialog, QGraphicsPixmapItem,
                               QDialogButtonBox, QFrame, QGraphicsScene,
                               QGraphicsView, QGridLayout, QGraphicsItem,
                               QLabel, QLineEdit, QPushButton, QSizePolicy,
                               QSpinBox, QStyle, QWidget)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QIcon,
                           QImage, QPainter, QPainterPath, QPixmap,
                           QRadialGradient, QRegularExpressionValidator, QCursor,
                           QScreen)
from math import degrees, radians, sqrt, atan2, sin, cos, pi
import random
import substance_painter.ui

plugin_widgets = []
"""Keep track of added ui elements for cleanup"""


class colorPicker(QDialog):
    "custom colorDialog from Orthallelous"
    currentColorChanged = Signal(QColor)
    colorSelected = Signal(QColor)

    def __init__(self, initial=None, parent=None):
        super(colorPicker, self).__init__(parent)
        self.setup()
        self.setColor(initial)

    def currentColor(self): return self._color

    def setColor(self, qcolor=None):
        if qcolor is None:
            self._color = QColor('#ffffff')
        else:
            self._color = QColor(qcolor)
        self._colorEdited()

    @staticmethod
    def getColor(initial=None, parent=None, title=None):
        dialog = colorPicker(initial, parent)
        if title:
            dialog.setWindowTitle(title)
        result = dialog.exec_()
        color = dialog._color
        return color

    def closeValid(self):
        "emits colorSelected signal with valid color on OK"
        self.currentColorChanged.emit(self._color)
        self.colorSelected.emit(self._color)

    def closeInvalid(self):
        "emits colorSelected signal with invalid color on Cancel"
        self._color = QColor()
        self.colorSelected.emit(QColor())

    def setOption(self, option, Bool=True):
        if option == QColorDialog.NoButtons:
            if not Bool:
                self.dialogButtons.blockSignals(False)
                self.dialogButtons.setEnabled(True)
                self.dialogButtons.show()
            else:
                self.dialogButtons.blockSignals(True)
                self.dialogButtons.setEnabled(False)
                self.dialogButtons.hide()
        self.setFixedSize(self.sizeHint())

    def _colorEdited(self):
        "internal color editing"
        sender, color = self.sender(), self._color
        for i in self.inputs:
            i.blockSignals(True)

        # get values
        if sender in self.rgbInputs:       # RGB
            color.setRgb(*[i.value() for i in self.rgbInputs])
        elif sender in self.hsvInputs:     # HSV
            color.setHsv(*[i.value() for i in self.hsvInputs])
        elif sender in self.cmykInputs:    # CMYK
            color.setCmyk(*[i.value() for i in self.cmykInputs])
        elif sender is self.htmlInput:     # HTML
            color.setNamedColor('#' + str(self.htmlInput.text()).lower())
        elif sender is self.colorWheel:    # WHEEL
            color = self._color = self.colorWheel.getColor()
        elif sender is self.colorNamesCB:  # NAMED
            dat = self.colorNamesCB.itemData(self.colorNamesCB.currentIndex())
            try:
                color = self._color = QColor(dat.toString())  # PyQt
            except:
                color = self._color = QColor(str(dat))     # PySide
            self.colorNamesCB.setToolTip(self.colorNamesCB.currentText())
        else:
            pass

        # set values
        for i, j in zip(color.getRgb()[:-1], self.rgbInputs):
            j.setValue(i)
        for i, j in zip(color.getHsv()[:-1], self.hsvInputs):
            j.setValue(i)
        for i, j in zip(color.getCmyk()[:-1], self.cmykInputs):
            j.setValue(i)
        self.htmlInput.setText(color.name()[1:])
        self.colorWheel.setColor(color)
        idx = self.colorNamesCB.findData(color.name())
        self.colorNamesCB.setCurrentIndex(idx)  # will be blank if not in list

        pal = self.colorDisplay.palette()
        pal.setColor(self.colorDisplay.backgroundRole(), color)
        self.colorDisplay.setPalette(pal)

        for i in self.inputs:
            i.blockSignals(False)
        self.currentColorChanged.emit(color)

    def pickColor(self):
        "pick a color on the screen, part 1"
        # screenshot desktop
        self._img = QApplication.primaryScreen().grabWindow(0)

        self._view = QGraphicsView(self)
        scene = QGraphicsScene(self)  # display screenshot at full size

        self._view.setWindowFlags(Qt.FramelessWindowHint)
        self._view.setWindowFlags(Qt.WindowType_Mask)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scene.addPixmap(self._img)  # ; self._view.setScene(scene)

        self._mag = magnifier()
        self._mag.setBackground(self._img)
        self._mag.setSize(11, 11)
        scene.addItem(self._mag)
        self._view.setScene(scene)

        self._appview = QApplication
        self._appview.setOverrideCursor(Qt.CrossCursor)

        self._view.showFullScreen()
        self._view.mousePressEvent = self._pickedColor

    def _pickedColor(self, event):
        "pick a color on the screen, part 2"
        color = QColor(self._img.toImage().pixel(event.globalPos()))

        self._view.hide()
        self._appview.restoreOverrideCursor()
        self._color = color
        self._colorEdited()
        self._mag = self._appview = self._view = self._img = None

    def showColors(self):
        "show location of colors on color wheel"
        if self.showButton.isChecked():
            self.colorWheel.showNamedColors(True)
        else:
            self.colorWheel.showNamedColors(False)

    def randomColor(self):
        "select a random color"
        rand = random.randint
        col = QColor()
        col.setHsv(rand(0, 359), rand(0, 255), rand(0, 255))
        self.setColor(col)
        return col

    def getNamedColors(self):
        "returns a list [(name, #html)] from the named colors combobox"
        lst = []
        for i in range(self.colorNamesCB.count()):
            name = str(self.colorNamesCB.itemText(i))
            try:                    # PyQt
                html = str(self.colorNamesCB.itemData(i).toString())
            except AttributeError:  # PySide
                html = str(self.colorNamesCB.itemData(i))
            lst.append((name, html))
        return lst

    def addNamedColors(self, lst):
        "add a list [('name', '#html'), ] of named colors (repeats removed)"
        col = self.getNamedColors() + lst
        lst = [(i[0], QColor(i[1])) for i in col]
        sen = set()
        add = sen.add  # http://stackoverflow.com/a/480227
        uni = [x for x in lst if not (x[1].name() in sen or add(x[1].name()))]

        self.colorNamesCB.clear()
        for i, j in sorted(uni, key=lambda q: q[1].getHsv()):
            icon = QPixmap(16, 16)
            icon.fill(j)
            self.colorNamesCB.addItem(QIcon(icon), i, j.name())
        self.colorWheel.setNamedColors([(i, j.name()) for i, j in uni])
        self.cNameLabel.setToolTip(
            'Named colors\n{:,} colors'.format(len(uni)))

    def setup(self):
        self.setAttribute(Qt.WA_DeleteOnClose)
        fixed = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        rightCenter = (Qt.AlignRight | Qt.AlignVCenter)

        # all the input boxes
        self.inputGrid = QGridLayout()
        self.inputGrid.setSpacing(5)
        h_spc = self.inputGrid.horizontalSpacing()
        v_spc = self.inputGrid.verticalSpacing()

        # RGB
        self.redInput = QSpinBox()
        self.grnInput = QSpinBox()
        self.bluInput = QSpinBox()
        self.rgbInputs = [self.redInput, self.grnInput, self.bluInput]

        self.redLabel = QLabel('&R:')
        self.redLabel.setToolTip('Red')
        self.grnLabel = QLabel('&G:')
        self.grnLabel.setToolTip('Green')
        self.bluLabel = QLabel('&B:')
        self.bluLabel.setToolTip('Blue')
        self.rgbLabels = [self.redLabel, self.grnLabel, self.bluLabel]

        self.redLabel.setBuddy(self.redInput)
        self.grnLabel.setBuddy(self.grnInput)
        self.bluLabel.setBuddy(self.bluInput)

        # HSV
        self.hueInput = QSpinBox()
        self.satInput = QSpinBox()
        self.valInput = QSpinBox()
        self.hsvInputs = [self.hueInput, self.satInput, self.valInput]
        self.hueInput.setWrapping(True)

        self.hueLabel = QLabel('&H:')
        self.hueLabel.setToolTip('Hue')
        self.satLabel = QLabel('&S:')
        self.satLabel.setToolTip('Saturation')
        self.valLabel = QLabel('&V:')
        self.valLabel.setToolTip('Value')
        self.hsvLabels = [self.hueLabel, self.satLabel, self.valLabel]

        self.hueLabel.setBuddy(self.hueInput)
        self.satLabel.setBuddy(self.satInput)
        self.valLabel.setBuddy(self.valInput)

        # CMYK
        self.cInput = QSpinBox()
        self.mInput = QSpinBox()
        self.yInput = QSpinBox()
        self.kInput = QSpinBox()
        self.cmykInputs = [self.cInput, self.mInput, self.yInput, self.kInput]

        self.cLabel = QLabel('&C:')
        self.cLabel.setToolTip('Cyan')
        self.mLabel = QLabel('&M:')
        self.mLabel.setToolTip('Magenta')
        self.yLabel = QLabel('&Y:')
        self.yLabel.setToolTip('Yellow')
        self.kLabel = QLabel('&K:')
        self.kLabel.setToolTip('Black')
        self.cmykLabels = [self.cLabel, self.mLabel, self.yLabel, self.kLabel]

        self.cLabel.setBuddy(self.cInput)
        self.mLabel.setBuddy(self.mInput)
        self.yLabel.setBuddy(self.yInput)
        self.kLabel.setBuddy(self.kInput)

        for i in self.rgbInputs + self.hsvInputs + self.cmykInputs:
            i.setRange(0, 255)
            i.setFixedSize(44, 22)
            i.setAlignment(Qt.AlignCenter)
            i.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.hueInput.setRange(0, 359)

        # HTML
        self.htmlInput = QLineEdit()
        self.htmlInput.setFixedSize(35 + 22 + h_spc, 22)  # spans 2 cols
        self.htmlInput.setPlaceholderText('html')
        self.htmlInput.setAlignment(Qt.AlignCenter)
        regex = QRegularExpression('[0-9A-Fa-f]{1,6}')
        valid = QRegularExpressionValidator(regex)
        self.htmlInput.setValidator(valid)

        self.htmlLabel = QLabel('&#')
        self.htmlLabel.setToolTip('Web color')
        self.htmlLabel.setBuddy(self.htmlInput)

        self.inputLabels = (self.rgbLabels + self.hsvLabels +
                            self.cmykLabels + [self.htmlLabel, ])
        for i in self.inputLabels:
            i.setFixedSize(22, 22)
            i.setAlignment(rightCenter)

        self.inputs = self.rgbInputs + self.hsvInputs + self.cmykInputs
        for i in self.inputs:
            i.valueChanged.connect(self._colorEdited)
        self.htmlInput.editingFinished.connect(self._colorEdited)

        # picker button
        self.pickButton = QPushButton('&Pick')
        self.pickButton.setToolTip('Pick a color from the screen')
        self.pickButton.setFixedSize(35, 22)
        self.pickButton.clicked.connect(self.pickColor)

        # color display
        self.colorDisplay = QFrame()
        self.colorDisplay.setFixedSize(55, 4 * 22 + 3 * v_spc)  # spans 4 rows
        self.colorDisplay.setFrameShape(QFrame.Panel)
        self.colorDisplay.setFrameShadow(QFrame.Sunken)
        self.colorDisplay.setAutoFillBackground(True)

        # show button / random button
        self.showButton = QPushButton('Sho&w')
        self.showButton.setToolTip('Show named colors on color wheel')
        self.showButton.setFixedSize(35, 22)
        self.showButton.setCheckable(True)
        self.showButton.clicked.connect(self.showColors)

        self.colorWheel = wheel()
        self.colorWheel.setFixedSize(256, 256)  # 265, 265)
        self.colorWheel.currentColorChanged.connect(self.setColor)

        self.colorNamesCB = QComboBox()
        self.colorNamesCB.setFixedSize(70 + 66 + 4 * h_spc, 22)  # spans 5 cols

        self.cNameLabel = QLabel('&Named:')
        self.cNameLabel.setBuddy(self.colorNamesCB)
        self.cNameLabel.setAlignment(rightCenter)
        self.cNameLabel.setFixedSize(55, 22)

        lst = [i for i in QColor.colorNames() if str(i) != 'transparent']
        lst = [(i, QColor(i)) for i in lst]
        lst.append(('Cosmic latte', '#fff8e7'))
        lst.append(('rebeccapurple', '#663399'))
        self.addNamedColors(lst)
        self.colorNamesCB.currentIndexChanged.connect(self._colorEdited)

        self.inputs += [self.htmlInput, self.colorWheel, self.colorNamesCB]

        # ok/cancel buttons
        self.dialogButtons = QDialogButtonBox(QDialogButtonBox.Ok
                                              | QDialogButtonBox.Cancel)
        self.dialogButtons.accepted.connect(self.closeValid)
        self.dialogButtons.rejected.connect(self.closeInvalid)
        self.dialogButtons.setCenterButtons(True)
        self.inputGrid.addWidget(self.colorWheel, 0, 0, 1, 7)
        self.inputGrid.addWidget(self.colorDisplay, 1, 0, 4, 1)

        for i, lab in enumerate(self.rgbLabels, 1):
            self.inputGrid.addWidget(lab, 1, i, 1, 1)
            self.inputGrid.addWidget(self.htmlLabel, 3, 0, 1, 1)

        for i, wid in enumerate(self.rgbInputs, 1):
            self.inputGrid.addWidget(wid, 2, i)
            self.inputGrid.addWidget(self.htmlInput, 3, 1, 1, 2)

        #for i, lab in enumerate(self.hsvLabels, 1):
            #self.inputGrid.addWidget(lab, i, 3, 1, 1)

        #for i, wid in enumerate(self.hsvInputs, 1):
        self.inputGrid.addWidget(wid, 3, 1, 1, 1)
        self.inputGrid.addWidget(self.pickButton, 3, 3, 1, 1)

        self.inputGrid.addWidget(self.colorNamesCB, 4, 1, 1, 5)
        self.inputGrid.addWidget(self.cNameLabel, 4, 0, 1, 1)
        #self.inputGrid.addWidget(self.showButton, 5, 6, 1, 1)
        #self.inputGrid.addWidget(self.dialogButtons, 6, 0, 1, 7)

        #self.setWindowTitle('Select color')
        style = QApplication.style()
        ico = style.standardIcon(QStyle.SP_DialogResetButton)
        self.setWindowIcon(ico)
        self.setLayout(self.inputGrid)
        self.setFixedSize(self.sizeHint())


class wheel(QWidget):
    currentColorChanged = Signal(QColor)

    def __init__(self, parent=None):
        super(wheel, self).__init__(parent)
        self.setFixedSize(256, 256)

        # start, end angles for value arc
        self.s_ang, self.e_ang = 135, 225

        # offset angle and direction for color wheel
        self.o_ang, self.rot_d = 45, -1  # 1 for clock-wise, -1 for widdershins

        # other initializations
        self.pos = QPointF(-100, -100)
        self.vIdCen = QPointF(-100, -100)
        self.vIdAng = radians(self.s_ang)
        self.chPt = self.pos
        self.hue = self.sat = self.value = 255

        self.setup()
        self.pos = self.cWhBox.center()

        self._namedColorList = []
        self._namedColorPts = []
        self._showNames = False

        self.setMouseTracking(True)
        self.installEventFilter(self)

        self._startedTimer = False
        plugin_widgets.append(wheel)

    def resizeEvent(self, event):
        self.setup()  # re-construct the sizes
        self.setNamedColors(self._namedColorList)

    def getColor(self):
        col = QColor()
        col.setHsv(self.hue, self.sat, self.value)
        return col

    def setNamedColors(self, colorList):
        "sets list [(name, #html)] of named colors"
        self._namedColorList = colorList
        lst = []
        r2 = (self.vAoBox.width() + self.vAiBox.width()) / 4.0
        for i in self._namedColorList:
            h, s, v, a = QColor(i[1]).getHsv()

            t = radians(h + self.o_ang * -self.rot_d) * -self.rot_d
            r = s / 255.0 * self.cW_rad
            x, y = r * cos(t) + self.cen.x(), r * -sin(t) + self.cen.y()
            lst.append(QPointF(x, y))

        self._namedColorPts = lst

    def showNamedColors(self, flag=False):
        "show/hide location of named colors on color wheel"
        self._showNames = flag
        self.update()

    def setColor(self, color):                    # saturation -> radius
        h, s, v, a = color.getHsv()               # hue -> angle
        self.hue, self.sat, self.value = h, s, v  # value -> side bar thingy

        t = radians(h + self.o_ang * -self.rot_d) * -self.rot_d
        r = s / 255.0 * self.cW_rad
        x, y = r * cos(t) + self.cen.x(), r * -sin(t) + self.cen.y()
        self.chPt = QPointF(x, y)  # hue, saturation

        self.vIdAng = t2 = (v / 255.0) * self.ang_w + radians(self.e_ang)
        self.vIdAng = t2 = t2 if t2 > 0 else t2 + 2 * pi
        r2 = self.vAoBox.width() / 2.0

        x, y = r2 * cos(t2) + self.cen.x(), r2 * -sin(t2) + self.cen.y()
        self.vIdCen, self.vIdAng = QPointF(x, y), t2  # value
        self.vIdBox.moveCenter(self.vIdCen)
        self.update()

    def eventFilter(self, source, event):
        if (event.type() == QEvent.MouseButtonPress or
            (event.type() == QEvent.MouseMove and
             event.buttons() == Qt.LeftButton)):
            self.pos = pos = event.pos()

            t = atan2(self.cen.y() - pos.y(), pos.x() - self.cen.x())
            if self.colWhlPath.contains(pos):  # in the color wheel
                self.chPt = pos

                h = (int(degrees(t)) - self.o_ang) * -self.rot_d
                self.hue = (h if h > 0 else h + 360) % 360

                # saturation -> mouse radius (clipped to wheel radius)
                m_rad = sqrt((self.pos.x() - self.cen.x()) **
                             2 + (self.pos.y() - self.cen.y()) ** 2)
                self.sat = int(255 * min(m_rad / self.cW_rad, 1))

            if self.vInArcPath.contains(pos):  # in the value selection arc
                self.vIdAng = t if t > 0 else t + 2 * pi
                r2 = self.vAoBox.width() / 2.0

                x, y = r2 * cos(t) + self.cen.x(), r2 * -sin(t) + self.cen.y()
                self.vIdCen = QPointF(x, y)
                self.vIdBox.moveCenter(self.vIdCen)
                self.value = int(
                    255 * (t - radians(self.e_ang)) / self.ang_w) % 256

            self.update()
            col = QColor()
            col.setHsv(self.hue, self.sat, self.value)
            self.currentColorChanged.emit(col)
        return QWidget.eventFilter(self, source, event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(painter.RenderHint.Antialiasing)

        painter.setBrush(QBrush(Qt.black, Qt.SolidPattern))
        painter.drawPie(self.vIdBox, 16 * (degrees(self.vIdAng) - 22.5), 720)

        painter.setClipPath(self.vArcPath)
        painter.setPen(Qt.NoPen)
        arc = QConicalGradient(self.cen, self.e_ang)
        color = QColor()
        color.setHsv(self.hue, self.sat, 255)
        arc.setColorAt(1 - (self.e_ang - self.s_ang) / 360.0, color)
        arc.setColorAt(1, Qt.black)
        arc.setColorAt(0, Qt.black)
        painter.setBrush(arc)
        painter.drawPath(self.vArcPath)
        painter.setClipPath(self.vArcPath, Qt.NoClip)

        # color wheel
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.cWhlBrush1)
        painter.drawEllipse(self.cWhBox)
        painter.setBrush(self.cWhlBrush2)
        painter.drawEllipse(self.cWhBox)

        # crosshairs
        painter.setClipPath(self.colWhlPath)
        painter.setBrush(QBrush(Qt.black, Qt.SolidPattern))
        chVert = QRectF(0, 0, 2, 20)
        chHort = QRectF(0, 0, 20, 2)
        chVert.moveCenter(self.chPt)
        chHort.moveCenter(self.chPt)
        painter.drawRect(chVert)
        painter.drawRect(chHort)

        # named color locations
        if self._showNames:
            painter.setClipPath(self.vArcPath, Qt.NoClip)
            painter.setPen(Qt.SolidLine)
            try:
                painter.drawPoints(*self._namedColorPts)    # PyQt
            except:
                painter.drawPoints(self._namedColorPts)  # PySide

    def setup(self):
        "sets bounds on value arc and color wheel"
        # bounding boxes
        self.winBox = QRectF(self.rect())
        self.vIoBox = QRectF()  # value indicator arc outer
        self.vIdBox = QRectF()  # value indicator box
        self.vAoBox = QRectF()  # value arc outer
        self.vAiBox = QRectF()  # value arc inner
        self.cWhBox = QRectF()  # color wheel

        self.vIdBox.setSize(QSizeF(15, 15))
        self.vIoBox.setSize(self.winBox.size())
        self.vAoBox.setSize(self.winBox.size() - self.vIdBox.size() / 2.0)
        self.vAiBox.setSize(self.vAoBox.size() - QSizeF(20, 20))
        self.cWhBox.setSize(self.vAiBox.size() - QSizeF(20, 20))

        # center - shifted to the right slightly
        x = self.winBox.width()-(self.vIdBox.width()+self.vAiBox.width()) / 2.0
        self.cen = QPointF(x, self.winBox.height() / 2.0)

        # positions and initial settings
        self.vAoBox.moveCenter(self.cen)
        self.vAiBox.moveCenter(self.cen)
        self.cWhBox.moveCenter(self.cen)
        self.vIdBox.moveCenter(self.vIdCen)

        self.cW_rad = self.cWhBox.width() / 2.0
        self.ang_w = radians(self.s_ang) - radians(self.e_ang)

        # gradients
        colWhl = QConicalGradient(self.cen, self.o_ang)
        whl_cols = [Qt.red, Qt.magenta, Qt.blue,
                    Qt.cyan, Qt.green,
                    Qt.yellow, Qt.red]
        for i, c in enumerate(whl_cols[::self.rot_d]):
            colWhl.setColorAt(i / 6.0, c)

        rad = min(self.cWhBox.width() / 2.0, self.cWhBox.height() / 2.0)
        cWhlFade = QRadialGradient(self.cen, rad, self.cen)
        cWhlFade.setColorAt(0, Qt.white)
        cWhlFade.setColorAt(1, QColor(255, 255, 255, 0))

        self.cWhlBrush1 = QBrush(colWhl)
        self.cWhlBrush2 = QBrush(cWhlFade)

        # painter paths (arcs, wheel)
        rad = self.vAoBox.width() / 2.0
        x, y = rad * cos(radians(self.s_ang)), -rad * sin(radians(self.s_ang))
        x += self.cen.x()
        y += self.cen.y()

        self.vArcPath = QPainterPath(QPointF(x, y))  # value arc (for color)
        self.vArcPath.arcTo(self.vAoBox, self.s_ang, self.e_ang - self.s_ang)
        self.vArcPath.arcTo(self.vAiBox, self.e_ang, self.s_ang - self.e_ang)
        self.vArcPath.closeSubpath()

        self.vInArcPath = QPainterPath(QPointF(x, y))  # value arc (for mouse)
        self.vInArcPath.arcTo(self.vIoBox, self.s_ang, self.e_ang - self.s_ang)
        self.vInArcPath.arcTo(self.vAiBox, self.e_ang, self.s_ang - self.e_ang)
        self.vInArcPath.closeSubpath()

        self.colWhlPath = QPainterPath()
        self.colWhlPath.addEllipse(self.cWhBox)


class magnifier(QGraphicsPixmapItem):
    "zoomed in view around mouse\nfrom Orthallelous"
    # could use QGraphicsPixmapItem's built-in scale function
    # but then wouldn't be able to have the fancy grid
    # and that's what matters!

    def __init__(self, parent=None):
        super(magnifier, self).__init__(parent)

        self.setFlags(QGraphicsItem.ItemIsMovable)
        self.setAcceptHoverEvents(True)  # setAcceptsHoverEvents(True)

        self.zoom = self.width = self.height = 10
        self.size = QSize(self.width, self.height)

        # +zw, zh so the mouse isn't sitting on the grid itself
        zw = 0 if self.width % 2 else self.zoom
        zh = 0 if self.height % 2 else self.zoom
        self.offset = QPoint((self.width * self.zoom + zw) // 2,
                             (self.height * self.zoom + zh) // 2)

        self.background = None
        self.setPos(QCursor().pos() - self.offset)

    def drawGrid(self, image):
        "draws a grid on image"
        img = QPixmap(image.width() + 1, image.height() + 1)
        p = QPainter(img)
        p.drawPixmap(1, 1, image)
        # the +1 is for the grid around the image; otherwise grid is cut off

        w, h, z = img.width(), img.height(), self.zoom
        for i in range(max(self.width, self.height) + 1):
            p.drawLine(QPoint(0, i * z), QPoint(w, i * z))  # horiztonal lines
            p.drawLine(QPoint(i * z, 0), QPoint(i * z, h))  # vertical lines

        return img

    def setBackground(self, img):
        self.background = img
        self._readjust()

    def setSize(self, w, h):
        self.width = w
        self.height = h
        self._readjust()

    def setZoom(self, z):
        self.zoom = z
        self._readjust()

    def _readjust(self):
        "re-set some things"
        w, h, z = self.width, self.height, self.zoom
        zw = 0 if w % 2 else z
        zh = 0 if h % 2 else z

        self.size = QSize(w, h)
        self.offset = QPoint((w * z + zw) // 2, (h * z + zh) // 2)

        pos = QCursor().pos() - self.offset
        self.setPos(pos)
        self._setView(pos)

    def _setView(self, pos):
        "grab viewpoint around pos, set as image"
        if self.background is None:
            return

        topLeft = pos - QPoint(self.width // 2, self.height // 2)
        try:
            topLeft = topLeft.toPoint()
        except:
            pass  # ugh

        rect = QRect(topLeft, self.size)
        img = self.background.copy(rect)  # crop small section

        w, h, z = img.width(), img.height(), self.zoom  # scale small section
        img = img.scaled(w * z, h * z, Qt.KeepAspectRatio)
        self.setPixmap(self.drawGrid(img))

    def hoverMoveEvent(self, event):
        pos = event.scenePos()
        self.setPos(pos - self.offset)
        self._setView(pos)


def start_plugin():
    """This method is called when the plugin is started."""
    widget = colorPicker()
    widget.setWindowTitle("Color Wheel")
    substance_painter.ui.add_dock_widget(widget)
    plugin_widgets.append(widget)


def close_plugin():
    """This method is called when the plugin is stopped."""
    # We need to remove all added widgets from the UI.
    for widget in plugin_widgets:
        substance_painter.ui.delete_ui_element(widget)
    plugin_widgets.clear()
    self.close()


if __name__ == '__main__':
    start_plugin()
