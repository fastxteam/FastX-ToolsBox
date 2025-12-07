import math
from PySide6.QtWidgets import QWidget, QDialog, QApplication
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QColor, QPainter, QBrush, QPen, QConicalGradient, QRadialGradient

class ScreenColorPicker(QDialog):
    colorSelected = Signal(QColor)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self.pixmap = QApplication.primaryScreen().grabWindow(0)
        self.resize(self.pixmap.size())
        self.showFullScreen()
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            c = self.pixmap.toImage().pixelColor(int(e.pos().x()*self.devicePixelRatio()), int(e.pos().y()*self.devicePixelRatio()))
            self.colorSelected.emit(c); self.accept()
        else: self.reject()
    def paintEvent(self, e):
        p = QPainter(self); p.drawPixmap(0,0,self.pixmap); p.fillRect(self.rect(), QColor(0,0,0,1))

class ColorWheel(QWidget):
    colorChanged = Signal(QColor)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(220, 220)
        self.hue=0.0; self.sat=0.0; self.val=1.0; self.pos=QPoint(110,110); self.drag=False
    def set_val(self, v): self.val=v/255.0; self.update()
    def set_col(self, c): h,s,v,_=c.getHsvF(); self.hue=h if h!=-1 else 0; self.sat=s; self.val=v; self.upd_pos(); self.update()
    def upd_pos(self):
        r=(self.width()/2)-10; a=self.hue*2*math.pi; d=self.sat*r
        cx,cy=self.width()/2,self.height()/2
        self.pos=QPoint(int(cx+d*math.cos(a)), int(cy-d*math.sin(a)))
    def mousePressEvent(self, e):
        if e.button()==Qt.LeftButton: self.drag=True; self.handle(e.pos())
    def mouseMoveEvent(self, e):
        if self.drag: self.handle(e.pos())
    def mouseReleaseEvent(self, e): self.drag=False
    def handle(self, p):
        cx,cy=self.width()/2,self.height()/2; dx=p.x()-cx; dy=cy-p.y()
        d=math.sqrt(dx*dx+dy*dy); md=cx-10
        if d>md: r=md/d; dx*=r; dy*=r; d=md
        self.pos=QPoint(int(cx+dx), int(cy-dy)); a=math.atan2(dy,dx)
        if a<0: a+=2*math.pi
        self.hue=a/(2*math.pi); self.sat=d/md; self.emit(); self.update()
    def emit(self): self.colorChanged.emit(QColor.fromHsvF(self.hue,self.sat,self.val))
    def paintEvent(self, e):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r=(self.width()/2)-10; c=QPoint(self.width()//2,self.height()//2)
        con=QConicalGradient(c,0)
        for i,cl in enumerate([Qt.red,Qt.magenta,Qt.blue,Qt.cyan,Qt.green,Qt.yellow,Qt.red]): con.setColorAt(i/6,cl)
        p.setBrush(QBrush(con)); p.setPen(Qt.NoPen); p.drawEllipse(c,r,r)
        rad=QRadialGradient(c,r); rad.setColorAt(0,QColor(255,255,255)); rad.setColorAt(1,QColor(255,255,255,0))
        p.setBrush(QBrush(rad)); p.drawEllipse(c,r,r)
        p.setPen(QPen(Qt.white,2)); p.setBrush(Qt.NoBrush); p.drawEllipse(self.pos,6,6)
        p.setPen(QPen(Qt.black,1)); p.drawEllipse(self.pos,7,7)