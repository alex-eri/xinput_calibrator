import gi
import shlex
import subprocess
import json
#import numpy
import itertools

from pprint import pprint

AREA = 6

def matmult(a,b):
    return [[sum(ele_a*ele_b for ele_a, ele_b in zip(row_a, col_b)) for col_b in list(zip(*b))] for row_a in a]

def matinv(AM):
    AM = [ l.copy() for l in AM ]
    h = list(range(len(AM)))
    IM = [ [ 1 if c==l else 0  for c in h ] for l in h ]
    for fd in h:
        fdScaler = 1.0 / AM[fd][fd]
        for j in h:
            AM[fd][j] *= fdScaler
            IM[fd][j] *= fdScaler
        for i in h[0:fd] + h[fd+1:]:
            crScaler = AM[i][fd]
            for j in h:
                AM[i][j] = AM[i][j] - crScaler * AM[fd][j]
                IM[i][j] = IM[i][j] - crScaler * IM[fd][j]
    return IM



def dots(sw, sh):
        dw,dh = (sw/AREA,sh/AREA)
        sp = [(dw,dh), (sw-dw,dh), (sw-dw,sh-dh), (dw,sh-dh), (sw/2,sh/2)]
        return sp


def main():
    POINTS = {}

    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")

    from gi.repository import Gtk, Gdk

    win = Gtk.Window()
    win.connect("destroy", Gtk.main_quit)

    def fullscreen_at_monitor(window, n):
        display = Gdk.Display.get_default()
        monitor = Gdk.Display.get_monitor(display, n)
        geometry = monitor.get_geometry()
        x = geometry.x
        y = geometry.y
        window.move(x,y)
        window.fullscreen()


    def calculate(sw, sh, tp, did):
        sp = dots(sw, sh)
        p = itertools.combinations(range(4),3)
        ca = []

        for p3 in p:
            sp2 = [sp[i] for i in p3]
            tp2 = [tp[i] for i in p3]

            s = list(zip(*sp2))+ [(1,1,1)]
            t = list(zip(*tp2))+ [(1,1,1)]

            ca.append(matmult(s,matinv(t)))  # (numpy.matmul(s, numpy.linalg.inv(t)))

        c = sum(ca)/len(ca)
        c1 = c.copy()

        print(c)
        print(c[0,2])

        c[0,1] *= sh/sw
        c[0,2] *= 1/sw
        c[1,0] *= sw/sh
        c[1,2] *= 1/sh

        print(c)

        #pre = [[1, 0, 0.5], [0, 1, 0], [0, 0, 1]]

        #c = pre * c


        print(c.flatten())

        matrix = c.flatten()

        m = " ".join(map(lambda x: "%.8f" % x, matrix))
        cmd = 'xinput set-float-prop %d "libinput Calibration Matrix" %s' %  (did, m)
        print(cmd)

        p5 = list(tp[4])+[1]

        cp5 = matmult(c1,p5)  # numpy.matmul(c1,p5)
        print(cp5)
        print(sp[4])

        delta = ((cp5[0]-sp[4][0])**2 + (cp5[1]-sp[4][1])**2)**(1/2)
        print(delta)

        if not POINTS.get((did,)):
            POINTS[(did,)] = []
        POINTS[(did,)].append((delta, list(matrix)))


        """
        dx = minx = 0
        dy = miny = 0

        sy = 1/sh
        sx = 1/sw


        x, y = 0, 1

        p1,p2,p3 = 0,1,4



        norma = (t[p1][x]*t[p2][y]-t[p2][x]*t[p1][y])

        a = (s[p1][x]*t[p2][y] - s[p2][x]*t[p1][y]) / norma
        b = (-s[p1][x]*t[p2][x] + s[p2][x]*t[p1][x] ) / norma
        c = (
            s[p1][x]*(t[p2][x]*t[p3][y] - t[p3][x]*t[p2][y])
             + s[p2][x]*(t[p1][x]*t[p3][y] - t[p3][x]*t[p1][y])
             + s[p3][x]*(t[p1][x]*t[p2][y] - t[p2][x]*t[p1][y])
              ) / norma
        d = (s[p1][y]*t[p2][y] - s[p2][y]*t[p1][y] ) / norma
        e = (-s[p1][y]*t[p2][x] +s[p2][y]*t[p1][x]) / norma
        f = s[p1][y]*(t[p2][x]*t[p3][y] - t[p3][x]*t[p2][y]) - s[p2][y]*(t[p1][x]*t[p3][y] - t[p3][x]*t[p1][y]) + s[p3][y]*(t[p1][x]*t[p2][y] - t[p2][x]*t[p1][y]) / norma

        b = b * sy/sx
        c = a * dx + b*dy*sy/sx + c/sx - dx
        d = d * sx/sy
        f = d *dx*sx/sy + e*dy -dy + f/sy

        matrix = [a, b , c, d, e, f, 0, 0, 1]



        print(matrix)

        m = " ".join(map(lambda x: "%.8f" % x, matrix))
        cmd = 'xinput set-float-prop %d "Coordinate Transformation Matrix" %s' %  (did, m)
        print(cmd)
        """

    def calculate2d(w, h, points, did):
        a0, b0, c0, d0, e0, f0, g0, h0, i0 =  1.000000, 0.000000, 0.000000, 0.000000, 1.000000, 0.000000, 0.000000, 0.000000, 1.000000
        print(w, h )

        qa = AREA
        q1 = 1/qa
        q3 = (qa-2)/qa

        x0 = (points[0][0]+points[3][0])/2
        x1 = (points[1][0]+points[2][0])/2

        y0 = (points[0][1]+points[1][1])/2
        y1 = (points[2][1]+points[3][1])/2

        a1 = q3*w/(x1-x0)
        c1 = (q1*w-a1*x0)/w
        e1 = q3*h/(y1-y0)
        f1 = (q1*h-e1*y0)/h
        matrix = [a1, b0, c1, d0, e1, f1, g0, h0, i0]
        print(matrix)

        m = " ".join(map(lambda x: "%.8f" % x, matrix))
        cmd = 'xinput set-float-prop %d "Coordinate Transformation Matrix" %s' %  (did, m)
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
        ctx.move_to(0, height/2)
        ctx.line_to(width, height/2)
        ctx.move_to(width/2,0)
        ctx.line_to(width/2,height)
        ctx.stroke()

        ctx.set_font_size(10)
        ctx.set_source_rgb(0, 0.5, 0)

        ln = 0
        for k, v in POINTS.items():
            ln+=15
            ctx.move_to(15,ln)
            ctx.show_text(f"{k}: ")
            for i,p in enumerate(v):
                ln+=15
                ctx.move_to(15,ln)
                ctx.show_text(f"{i+1} {p}")

        ctx.stroke()

        sw,sh = width, height
        sp = dots(sw, sh)

        ctx.set_source_rgb(0.1, 0.1, 0.1)
        ctx.set_font_size(sh/AREA/5)

        for i in range(len(sp)):
            ctx.move_to(*sp[i])
            ctx.show_text(str(i+1))
        ctx.stroke()

    eventbox = Gtk.EventBox()
    draw = Gtk.DrawingArea()


    def on_click(widget, event):
        did = event.get_source_device().props.device_id
        if not POINTS.get(did):
            POINTS[did]=[]
        POINTS[did].append((event.x,event.y))
        print(did, event.x, event.y)
        if len(POINTS[did]) == 5:
            w, h = widget.get_allocated_width(), widget.get_allocated_height()
            tp = POINTS.pop(did)
            calculate(w, h, tp, did)
            #calculate2d(w, h, tp, did)
        draw.queue_draw()

    draw.connect("draw", on_draw)
    eventbox.connect('button-press-event', on_click)
    eventbox.add(draw)
    win.add(eventbox)
    fullscreen_at_monitor(win, 0)
    win.show_all()
    Gtk.main()


def entry_point():
    main()
    
if __name__ == "__main__":
    main()

