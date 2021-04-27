import gi
import shlex
import subprocess

AREA = 8
POINTS = []

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

win = Gtk.Window()
win.connect("destroy", Gtk.main_quit)

def aply():
            m = " ".join(map(lambda x: "%.6f" % x, matrix))
            cmd = 'xinput set-float-prop %d "Coordinate Transformation Matrix" %s' %  (self.touch_id, m)
            cmd = shlex.split(cmd)
            subprocess.run(cmd)


def calibrate(self, w=1024, h=768):
        a0, b0, c0, d0, e0, f0, g0, h0, i0 = self.matrix

        x0,y0,x1,y1 = self.x0,self.y0,self.x1,self.y1

        a1 = 6*w/8/(x1-x0)
        c1 = (w/8-a1*x0)/w
        e1 = 6*h/8/(y1-y0)
        f1 = (h/8-e1*y0)/h
        """
        print((a1, e1))

        print(self.matrix)
        a = a1*a0
        e = e1*e0
        c = (c0/a0 + c1/a1) * a
        f = (f0/e0 + f1/e1) * e
        """
        matrix = [a1, b0, c1, d0, e1, f1, g0, h0, i0]
        logging.info(matrix)
        print(matrix)
        self.recalibrate(matrix)



def calculate(widget):
    a0, b0, c0, d0, e0, f0, g0, h0, i0 =  1.000000, 0.000000, 0.000000, 0.000000, 1.000000, 0.000000, 0.000000, 0.000000, 1.000000
    w, h = widget.get_allocated_width(), widget.get_allocated_height()

    print(w, h )

    qa = AREA
    q1 = 1/qa
    q3 = (qa-2)/qa

    x0 = (POINTS[0][0]+POINTS[3][0])/2
    x1 = (POINTS[1][0]+POINTS[2][0])/2

    y0 = (POINTS[0][1]+POINTS[1][1])/2
    y1 = (POINTS[2][1]+POINTS[3][1])/2

    a1 = q3*w/(x1-x0)
    c1 = (q1*w-a1*x0)/w
    e1 = q3*h/(y1-y0)
    f1 = (q1*h-e1*y0)/h
    matrix = [a1, b0, c1, d0, e1, f1, g0, h0, i0]
    print(matrix)

    m = " ".join(map(lambda x: "%.6f" % x, matrix))
    cmd = 'xinput set-float-prop %d "Coordinate Transformation Matrix" %s' %  (14, m)
    print(cmd)


def on_draw(area, ctx):

    fa = AREA
    f1 = 1/fa
    f2 = (fa-1)/fa

    width, height = area.get_allocated_width(), area.get_allocated_height()



    #ctx.scale(width, height)
    ctx.set_line_width(1)
    ctx.set_source_rgb(1, 0, 0)
    ctx.fill()

    ctx.move_to(width*f1,0)
    ctx.line_to(width*f1,height)

    ctx.move_to(width*f2,0)
    ctx.line_to(width*f2,height)

    ctx.move_to(0, height*f1)
    ctx.line_to(width, height*f1)

    ctx.move_to(0, height*f2)
    ctx.line_to(width, height*f2)
    ctx.stroke()

def on_click(widget, event):
    POINTS.append((event.x,event.y))
    if len(POINTS) == 4:
        calculate(widget)
        Gtk.main_quit()

eventbox = Gtk.EventBox()

draw = Gtk.DrawingArea()
draw.connect("draw", on_draw)

eventbox.connect('button-press-event', on_click)

eventbox.add(draw)

win.add(eventbox)


win.fullscreen()
win.show_all()



Gtk.main()
