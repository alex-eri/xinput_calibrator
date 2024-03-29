import gi
import shlex
import subprocess
import json
import itertools
import functools
import argparse
import sys
import logging

from pprint import pformat

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")

from gi.repository import Gtk, Gdk, GLib

class Matrix(list):
    def __matmul__(a,b):
        return Matrix([[sum(ele_a*ele_b for ele_a, ele_b in zip(row_a, col_b)) for col_b in list(zip(*b))] for row_a in a])
    def __invert__(a):
        a = [ list(l) for l in a ]
        h = list(range(len(a)))
        ia = [ [ 1 if c==l else 0  for c in h ] for l in h ]
        for fd in h:
            fdScaler = 1.0 / a[fd][fd]
            for j in h:
                a[fd][j] *= fdScaler
                ia[fd][j] *= fdScaler
            for i in h[0:fd] + h[fd+1:]:
                crScaler = a[i][fd]
                for j in h:
                    a[i][j] = a[i][j] - crScaler * a[fd][j]
                    ia[i][j] = ia[i][j] - crScaler * ia[fd][j]
        return Matrix(ia)
    def __add__(a,b):
        return Matrix([[ i+j for i,j in zip(l,k) ] for l,k in zip(a,b)])
    def __truediv__(a,b):
        return Matrix( [[i/b for i in l] for l in a] )
    def flatten(a):
        return list(itertools.chain(*a))
    def __getitem__(a, i):
        if type(i) == int:
            return super().__getitem__(i)
        elif type(i) == tuple:
            y,x=i
            return a[y][x]
    def __setitem__(a, i, v):
        if type(i) == int:
            super().__setitem__(i, v)
        elif type(i) == tuple:
            y,x=i
            a[y][x] = v

class Calibrator():
    def __init__(self, n=1, a=6, args=None):
        self.saved_accuracy = sys.maxsize
        display = Gdk.Display.get_default()
        screen = display.get_default_screen()
        self.args=args

        def get_screen_size(display):
            mon_geoms = [
                display.get_monitor(i).get_geometry()
                for i in range(display.get_n_monitors())
            ]
            x0 = min(r.x            for r in mon_geoms)
            y0 = min(r.y            for r in mon_geoms)
            x1 = max(r.x + r.width  for r in mon_geoms)
            y1 = max(r.y + r.height for r in mon_geoms)
            return x1 - x0, y1 - y0

        self.screen_size = get_screen_size(display)
        self.windows = []
        self.draws = []
        self.main_window = None
        self.POINTS = {}
        self.MATRICES = {}
        self.DEVICES = {}
        #self.timer = GLib.Timer()

        for m in range(display.get_n_monitors()):
            monitor = Gdk.Display.get_monitor(display, m)
            geometry = monitor.get_geometry()
            win = Gtk.Window()
            eventbox = Gtk.EventBox()
            draw = Gtk.DrawingArea()
            eventbox.connect('button-press-event', self.on_click)
            eventbox.add(draw)
            win.add(eventbox)
            win.connect("destroy", Gtk.main_quit)
            win.move(geometry.x, geometry.y)
            win.fullscreen()
            self.windows.append(win)
            self.draws.append(draw)
            if m == n:
                self.monitor_geometry = geometry
                self.main_window = win
                sw,sh = geometry.width, geometry.height
                dw,dh = (sw/a, sh/a)
                points = [(dw, dh), (sw-dw, dh), (sw-dw, sh-dh), (dw, sh-dh), (sw/2, sh/2)]
                self.mp = points
                self.sp = [ (x + geometry.x, y + geometry.y) for x,y in points ]
                draw.connect("draw", functools.partial(self.on_draw_main, m))
            else:
                draw.connect("draw", functools.partial(self.on_draw, m))

    def calculate(self, tp, did):
        logging.debug(pformat(tp))

        sp = self.sp
        logging.debug(pformat(sp))
        p = itertools.combinations(range(4),3)
        ca = []
        for p3 in p:
            sp2 = [sp[i] for i in p3]
            tp2 = [tp[i] for i in p3]
            s = Matrix( list(zip(*sp2))+ [(1,1,1)] )
            t = Matrix( list(zip(*tp2))+ [(1,1,1)] )
            logging.debug(s)
            ca.append(s @ ~t)
        c = functools.reduce(lambda a,b: a+b, ca)/len(ca)
        p5 = [[i] for i in list(tp[4])+[1]]
        logging.debug(pformat(p5))
        cp5 = c @ p5
        logging.debug(pformat(cp5))
        sw, sh = self.screen_size
        dx, dy = self.monitor_geometry.x/sw, self.monitor_geometry.y/sh # TODO check with dx, dy
        logging.debug((dx, dy))
        logging.debug(pformat(c))

        c[0,1] *= sh/sw # b
        c[0,2] *= 1/sw # c
        #c[0,2] -= dx
        #c[0,2] += c[0,0] * dx + c[0,1] * dy
        c[1,0] *= sw/sh # d
        c[1,2] *= 1/sh # f
        #c[1,2] -= dy
        #c[1,2] += c[1,0] * dx + c[1,1] * dy

        matrix = c.flatten()
        delta = ((cp5[0][0]-sp[4][0])**2 + (cp5[1][0]-sp[4][1])**2)**(1/2)
        logging.debug(f"# Accuracy: {delta}")

        m = " ".join(map(lambda x: "%.10f" % x, matrix))
        cmd = 'xinput set-float-prop %d "libinput Calibration Matrix" \\\n %s' %  (did, m)
        if self.args and self.args.save_xinput_num:
            if self.saved_accuracy > delta:
                self.saved_accuracy = delta
                with open(self.args.save_xinput_num, "w") as f:
                    f.write(cmd)

        logging.debug(cmd)
        cmd = 'xinput set-float-prop "%s" "libinput Calibration Matrix" \\\n %s' %  (self.DEVICES[did]['name'], m)
        if self.args and self.args.save_xinput_name:
            if self.saved_accuracy > delta:
                self.saved_accuracy = delta
                with open(self.args.save_xinput_name, "w") as f:
                    f.write(cmd)

        logging.debug(cmd) # TODO save ~/.xsession

        cmd = 'ACTION=="add|change", KERNEL=="event[0-9]*", ENV{ID_VENDOR_ID}=="%s", \
ENV{ID_MODEL_ID}=="%s", ENV{LIBINPUT_CALIBRATION_MATRIX}="%s"' % (self.DEVICES[did]['vid'], self.DEVICES[did]['pid'], m)
        if self.args and self.args.save_udev_vendev:
            if self.saved_accuracy > delta:
                self.saved_accuracy = delta
                with open(self.args.save_udev_vendev, "w") as f:
                    f.write(cmd)
        logging.debug(cmd)  # TODO save as rule
                    # TODO set seat

        """
        ENV{LIBINPUT_CALIBRATION_MATRIX}="1 0 0 0 1 0" # default
        ENV{LIBINPUT_CALIBRATION_MATRIX}="0 -1 1 1 0 0" # 90 degree clockwise
        ENV{LIBINPUT_CALIBRATION_MATRIX}="-1 0 1 0 -1 1" # 180 degree clockwise
        ENV{LIBINPUT_CALIBRATION_MATRIX}="0 1 0 -1 0 1" # 270 degree clockwise
        ENV{LIBINPUT_CALIBRATION_MATRIX}="-1 0 1 0 1 0" # reflect along y axis
        """

        if not self.MATRICES.get(did):
            self.MATRICES[did] = []
        self.MATRICES[did].append((delta, [m]))


    def print_n(self, n, area, ctx):
        height = area.get_allocation().height
        ctx.set_font_size(height/2)
        ctx.set_source_rgb(0.8, 0.8, 0.8)
        ctx.move_to(10, height - 10)
        ctx.show_text(str(n))

    def draw_x(self, ctx, x, y, i):
        ctx.set_source_rgb(0.2, 0.2, 0.2)
        ctx.move_to(x+10, y-10)
        ctx.set_font_size(30)
        ctx.show_text(str(i+1))
        ctx.set_source_rgb(1, 0, 0)
        ctx.move_to(x-10, y)
        ctx.line_to(x+10, y)
        ctx.move_to(x, y-10)
        ctx.line_to(x, y+10)

    def redraw(self):
        for draw in self.draws:
            draw.queue_draw()

    def on_draw(self, n, area, ctx):
        self.print_n(n, area, ctx)
        ctx.stroke()

    def on_draw_main(self, n, area, ctx):
        self.print_n(n, area, ctx)
        ctx.set_font_size(12)
        ctx.set_source_rgb(0, 0, 0.5)
        ln = 0
        for k, v in self.MATRICES.items():
            ln += 15
            ctx.move_to(15, ln)
            ctx.show_text(f"Calibration Matrix {k}: ")
            for i,(d,p) in enumerate(v):
                ln += 15
                ctx.move_to(15, ln)
                ctx.show_text(f"№{i+1} accuracy {d:.2f} {p}")

        ctx.set_source_rgb(0, 0.5, 0)
        for k, v in self.POINTS.items():
            ln += 15
            ctx.move_to(15, ln)
            ctx.show_text("{vid}:{pid}  {name}  {did}: ".format(**self.DEVICES[k]))
            for i,p in enumerate(v):
                ln += 15
                ctx.move_to(15, ln)
                ctx.show_text(f"{i+1} {p}")
        for i,(x,y) in enumerate(self.mp):
            self.draw_x(ctx, x, y, i)
        ctx.stroke()

    def on_click(self, widget, event):

        props = event.get_source_device().props
        did = props.device_id
        self.DEVICES[did] = {
            'name': props.name,
            'vid': props.vendor_id,
            'pid': props.product_id,
            'did': props.device_id
        }
        if props.tool:
            self.DEVICES[did]['hid'] = props.tool.get_hardware_id()
            self.DEVICES[did]['serial'] = props.tool.get_serial()

        geom = widget.props.window.get_geometry()
        logging.debug(geom)
        x, y = geom.x + event.x, geom.y + event.y
        if not self.POINTS.get(did):
            self.POINTS[did]=[]
        self.POINTS[did].append((x,y))
        if len(self.POINTS[did]) == 5:
            tp = self.POINTS.pop(did)
            self.calculate(tp, did)
        self.redraw()

    def main(self):
        for win in self.windows:
            win.show_all()
        Gtk.main()

    


def entry_point():
    parser = argparse.ArgumentParser()
    parser.add_argument('--monitor', help='Monitor', type=int, default=0)
    parser.add_argument('--area', help='Place for calibration points. 10 - near corners, 6 - near center', type=int, default=8)
    parser.add_argument('--save-xinput-name', help='File to save xinput script by name', type=str)
    parser.add_argument('--save-xinput-num', help='File to save xinput script by num', type=str)
    parser.add_argument('--save-udev-vendev', help='File to save udev rule by ven dev', type=str)
    parser.add_argument('-d','--debug', action='store_true')
    parser.add_argument('-r','--last', type=bool)
    args = parser.parse_args()
    assert args.area > 2, 'Area must be >2'
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    c = Calibrator(args.monitor, args.area, args)
    c.main()

if __name__ == "__main__":
    entry_point()
