# -*- coding: utf-8 -*-

# The MIT License (MIT) - Copyright (c) Dave Vandenbout.

"""
Drawing routines used for debugging place & route.
"""

from collections import defaultdict
from random import randint

from skidl.utilities import export_to_all
from .geometry import BBox, Point, Segment, Tx, Vector


# Dictionary for storing colors to visually distinguish routed nets.
net_colors = defaultdict(lambda: (randint(0, 200), randint(0, 200), randint(0, 200)))


@export_to_all
def draw_box(bbox, scr, tx, color=(192, 255, 192), thickness=0):
    """Draw a box in the drawing area.

    Args:
        bbox (BBox): Bounding box for the box.
        scr (PyGame screen): Screen object for PyGame drawing.
        tx (Tx): Transformation matrix from real to screen coords.
        color (tuple, optional): Box color. Defaults to (192, 255, 192).

    Returns:
        None.
    """

    bbox = bbox * tx
    corners = (
        (bbox.min.x, bbox.min.y),
        (bbox.min.x, bbox.max.y),
        (bbox.max.x, bbox.max.y),
        (bbox.max.x, bbox.min.y),
    )
    pygame.draw.polygon(scr, color, corners, thickness)


@export_to_all
def draw_endpoint(pt, scr, tx, color=(100, 100, 100), dot_radius=10):
    """Draw a line segment endpoint in the drawing area.

    Args:
        pt (Point): A point with (x,y) coords.
        scr (PyGame screen): Screen object for PyGame drawing.
        tx (Tx): Transformation matrix from real to screen coords.
        color (tuple, optional): Segment color. Defaults to (192, 255, 192).
        dot_Radius (int, optional): Endpoint dot radius. Defaults to 3.
    """

    pt = pt * tx  # Convert to drawing coords.

    # Draw diamond for terminal.
    sz = dot_radius / 2 * tx.a  # Scale for drawing coords.
    corners = (
        (pt.x, pt.y + sz),
        (pt.x + sz, pt.y),
        (pt.x, pt.y - sz),
        (pt.x - sz, pt.y),
    )
    pygame.draw.polygon(scr, color, corners, 0)

    # Draw dot for terminal.
    radius = dot_radius * tx.a
    pygame.draw.circle(scr, color, (pt.x, pt.y), radius)


@export_to_all
def draw_seg(seg, scr, tx, color=(100, 100, 100), thickness=5, dot_radius=10):
    """Draw a line segment in the drawing area.

    Args:
        seg (Segment, Interval, NetInterval): An object with two endpoints.
        scr (PyGame screen): Screen object for PyGame drawing.
        tx (Tx): Transformation matrix from real to screen coords.
        color (tuple, optional): Segment color. Defaults to (192, 255, 192).
        seg_thickness (int, optional): Segment line thickness. Defaults to 5.
        dot_Radius (int, optional): Endpoint dot radius. Defaults to 3.
    """

    # Use net color if object has a net. Otherwise use input color.
    try:
        color = net_colors[seg.net]
    except AttributeError:
        pass

    # draw endpoints.
    draw_endpoint(seg.p1, scr, tx, color=color, dot_radius=dot_radius)
    draw_endpoint(seg.p2, scr, tx, color=color, dot_radius=dot_radius)

    # Transform segment coords to screen coords.
    seg = seg * tx

    # Draw segment.
    pygame.draw.line(
        scr, color, (seg.p1.x, seg.p1.y), (seg.p2.x, seg.p2.y), width=thickness
    )


@export_to_all
def draw_text(txt, pt, scr, tx, font, color=(100, 100, 100), real=True):
    """Render text in drawing area.

    Args:
        txt (str): Text string to be rendered.
        pt (Point): Real or screen coord for start of rendered text.
        scr (PyGame screen): Screen object for PyGame drawing.
        tx (Tx): Transformation matrix from real to screen coords.
        font (PyGame font): Font for rendering text.
        color (tuple, optional): Segment color. Defaults to (100,100,100).
        real (Boolean): If true, transform real pt to screen coords. Otherwise, pt is screen coords.
    """

    # Transform real text starting point to screen coords.
    if real:
        pt = pt * tx

    # Render text.
    font.render_to(scr, (pt.x, pt.y), txt, color)


@export_to_all
def draw_part(part, scr, tx, font):
    """Draw part bounding box.

    Args:
        part (Part): Part to draw.
        scr (PyGame screen): Screen object for PyGame drawing.
        tx (Tx): Transformation matrix from real to screen coords.
        font (PyGame font): Font for rendering text.
    """
    tx_bbox = (
        getattr(part, "lbl_bbox", getattr(part, "place_bbox", Vector(0, 0))) * part.tx
    )
    draw_box(tx_bbox, scr, tx, color=(180, 255, 180), thickness=0)
    draw_box(tx_bbox, scr, tx, color=(90, 128, 90), thickness=5)
    draw_text(part.ref, tx_bbox.ctr, scr, tx, font)
    try:
        for pin in part:
            if hasattr(pin, "place_pt"):
                pt = pin.place_pt * part.tx
                draw_endpoint(pt, scr, tx, color=(200, 0, 200), dot_radius=10)
    except TypeError:
        # Probably trying to draw a block of parts which has no pins and can't iterate thru them.
        pass


@export_to_all
def draw_net(net, parts, scr, tx, font, color=(0, 0, 0), thickness=2, dot_radius=5):
    """Draw net and connected terminals.

    Args:
        net (Net): Net of conmnected terminals.
        parts (list): List of parts to which net will be drawn.
        scr (PyGame screen): Screen object for PyGame drawing.
        tx (Tx): Transformation matrix from real to screen coords.
        font (PyGame font): Font for rendering text.
        color (tuple, optional): Segment color. Defaults to (0,0,0).
        thickness (int, optional): Thickness of net line. Defaults to 2.
        dot_radius (int, optional): Radius of terminals on net. Defaults to 5.
    """
    pts = []
    for pin in net.pins:
        part = pin.part
        if part in parts:
            pt = pin.route_pt * part.tx
            pts.append(pt)
    for pt1, pt2 in zip(pts[:-1], pts[1:]):
        draw_seg(
            Segment(pt1, pt2),
            scr,
            tx,
            color=color,
            thickness=thickness,
            dot_radius=dot_radius,
        )


@export_to_all
def draw_force(part, force, scr, tx, font, color=(128, 0, 0)):
    """Draw force vector affecting a part.

    Args:
        part (Part): The part affected by the force.
        force (Vector): The force vector.
        scr (PyGame screen): Screen object for PyGame drawing.
        tx (Tx): Transformation matrix from real to screen coords.
        font (PyGame font): Font for rendering text.
        color (tuple, optional): Segment color. Defaults to (0,0,0).
    """
    force *= 1
    anchor = part.place_bbox.ctr * part.tx
    draw_seg(
        Segment(anchor, anchor + force), scr, tx, color=color, thickness=5, dot_radius=5
    )


@export_to_all
def draw_placement(parts, nets, scr, tx, font):
    """Draw placement of parts and interconnecting nets.

    Args:
        parts (list): List of Part objects.
        nets (list): List of Net objects.
        scr (PyGame screen): Screen object for PyGame drawing.
        tx (Tx): Transformation matrix from real to screen coords.
        font (PyGame font): Font for rendering text.
    """
    draw_clear(scr)
    for part in parts:
        draw_part(part, scr, tx, font)
        draw_force(part, getattr(part, "force", Vector(0, 0)), scr, tx, font)
    for net in nets:
        draw_net(net, parts, scr, tx, font)
    draw_redraw()


@export_to_all
def draw_routing(node, bbox, parts, *other_stuff, **options):
    """Draw routing for debugging purposes.

    Args:
        node (Node): Hierarchical node.
        bbox (BBox): Bounding box of drawing area.
        node (Node): The Node being routed.
        parts (list): List of Parts.
        other_stuff (list): Other stuff with a draw() method.
        options (dict, optional): Dictionary of options and values. Defaults to {}.
    """

    # Initialize drawing area.
    draw_scr, draw_tx, draw_font = draw_start(bbox)

    # Draw parts.
    for part in parts:
        draw_part(part, draw_scr, draw_tx, draw_font)

    # Draw wiring.
    for wires in node.wires.values():
        for wire in wires:
            draw_seg(wire, draw_scr, draw_tx, (255, 0, 255), 3, dot_radius=10)

    # Draw other stuff (global routes, switchbox routes, etc.) that has a draw() method.
    for stuff in other_stuff:
        for obj in stuff:
            obj.draw(draw_scr, draw_tx, draw_font, **options)

    draw_end()


@export_to_all
def draw_clear(scr, color=(255, 255, 255)):
    """Clear drawing area.

    Args:
        scr (PyGame screen): Screen object to be cleared.
        color (tuple, optional): Background color. Defaults to (255, 255, 255).
    """
    scr.fill(color)


@export_to_all
def draw_start(bbox):
    """
    Initialize PyGame drawing area.

    Args:
        bbox: Bounding box of object to be drawn.

    Returns:
        scr: PyGame screen that is drawn upon.
        tx: Matrix to transform from real coords to screen coords.
        font: PyGame font for rendering text.
    """

    # Only import pygame if drawing is being done to avoid the startup message.
    import pygame
    import pygame.freetype

    # Make pygame module available to other functions.
    globals()["pygame"] = pygame

    # Screen drawing area.
    scr_bbox = BBox(Point(0, 0), Point(2000, 1500))

    # Place a blank region around the object by expanding it's bounding box.
    border = max(bbox.w, bbox.h) / 20
    bbox = bbox.resize(Vector(border, border))
    bbox = bbox.round()

    # Compute the scaling from real to screen coords.
    scale = min(scr_bbox.w / bbox.w, scr_bbox.h / bbox.h)
    scale_tx = Tx(a=scale, d=scale)

    # Flip the Y coord.
    flip_tx = Tx(d=-1)

    # Compute the translation of the object center to the drawing area center
    new_bbox = bbox * scale_tx * flip_tx  # Object bbox transformed to screen coords.
    move = scr_bbox.ctr - new_bbox.ctr  # Vector to move object ctr to drawing ctr.
    move_tx = Tx(dx=move.x, dy=move.y)

    # The final transformation matrix will scale the object's real coords,
    # flip the Y coord, and then move the object to the center of the drawing area.
    tx = scale_tx * flip_tx * move_tx

    # Initialize drawing area.
    pygame.init()
    scr = pygame.display.set_mode((scr_bbox.w, scr_bbox.h))

    # Set font for text rendering.
    font = pygame.freetype.SysFont("consolas", 24)

    # Clear drawing area.
    draw_clear(scr)

    # Return drawing screen, transformation matrix, and font.
    return scr, tx, font


@export_to_all
def draw_redraw():
    """Redraw the PyGame display."""
    pygame.display.flip()


@export_to_all
def draw_pause():
    """Pause drawing and then resume after button press."""

    # Display drawing.
    draw_redraw()

    # Wait for user to press a key or close PyGame window.
    running = True
    while running:
        for event in pygame.event.get():
            if event.type in (pygame.KEYDOWN, pygame.QUIT):
                running = False


@export_to_all
def draw_end():
    """Display drawing and wait for user to close PyGame window."""

    draw_pause()
    pygame.quit()
