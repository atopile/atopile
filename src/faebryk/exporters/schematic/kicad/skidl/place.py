# -*- coding: utf-8 -*-

# The MIT License (MIT) - Copyright (c) Dave Vandenbout.

"""
Autoplacer for arranging symbols in a schematic.
"""

import functools
import itertools
import math
import random
import sys
from collections import defaultdict
from copy import copy

from skidl import Pin
from skidl.utilities import export_to_all, rmv_attr, sgn
from .debug_draw import (
    draw_end,
    draw_pause,
    draw_placement,
    draw_redraw,
    draw_start,
    draw_text,
)
from .geometry import BBox, Point, Segment, Tx, Vector


__all__ = [
    "PlacementFailure",
]


###################################################################
#
# OVERVIEW OF AUTOPLACER
#
# The input is a Node containing child nodes and parts. The parts in
# each child node are placed, and then the blocks for each child are
# placed along with the parts in this node.
#
# The individual parts in a node are separated into groups:
# 1) multiple groups of parts that are all interconnected by one or
# more nets, and 2) a single group of parts that are not connected
# by any explicit nets (i.e., floating parts).
#
# Each group of connected parts are placed using force-directed placement.
# Each net exerts an attractive force pulling parts together, and
# any overlap of parts exerts a repulsive force pushing them apart.
# Initially, the attractive force is dominant but, over time, it is
# decreased while the repulsive force is increased using a weighting
# factor. After that, any part overlaps are cleared and the parts
# are aligned to the routing grid.
#
# Force-directed placement is also used with the floating parts except
# the non-existent net forces are replaced by a measure of part similarity.
# This collects similar parts (such as bypass capacitors) together.
#
# The child-node blocks are then arranged with the blocks of connected
# and floating parts to arrive at a total placement for this node.
#
###################################################################


class PlacementFailure(Exception):
    """Exception raised when parts or blocks could not be placed."""

    pass


# Small functions for summing Points and Vectors.
pt_sum = lambda pts: sum(pts, Point(0, 0))
force_sum = lambda forces: sum(forces, Vector(0, 0))


def is_net_terminal(part):
    from skidl.schematics.net_terminal import NetTerminal

    return isinstance(part, NetTerminal)


def get_snap_pt(part_or_blk):
    """Get the point for snapping the Part or PartBlock to the grid.

    Args:
        part_or_blk (Part | PartBlock): Object with snap point.

    Returns:
        Point: Point for snapping to grid or None if no point found.
    """
    try:
        return part_or_blk.pins[0].pt
    except AttributeError:
        try:
            return part_or_blk.snap_pt
        except AttributeError:
            return None


def snap_to_grid(part_or_blk):
    """Snap Part or PartBlock to grid.

    Args:
        part (Part | PartBlk): Object to snap to grid.
    """

    # Get the position of the current snap point.
    pt = get_snap_pt(part_or_blk) * part_or_blk.tx

    # This is where the snap point should be on the grid.
    snap_pt = pt.snap(GRID)

    # This is the required movement to get on-grid.
    mv = snap_pt - pt

    # Update the object's transformation matrix.
    snap_tx = Tx(dx=mv.x, dy=mv.y)
    part_or_blk.tx *= snap_tx


def add_placement_bboxes(parts, **options):
    """Expand part bounding boxes to include space for subsequent routing."""
    from skidl.schematics.net_terminal import NetTerminal

    for part in parts:
        # Placement bbox starts off with the part bbox (including any net labels).
        part.place_bbox = BBox()
        part.place_bbox.add(part.lbl_bbox)

        # Compute the routing area for each side based on the number of pins on each side.
        padding = {"U": 1, "D": 1, "L": 1, "R": 1}  # Min padding of 1 channel per side.
        for pin in part:
            if pin.stub is False and pin.is_connected():
                padding[pin.orientation] += 1

        # expansion_factor > 1 is used to expand the area for routing around each part,
        # usually in response to a failed routing phase. But don't expand the routing
        # around NetTerminals since those are just used to label wires.
        if isinstance(part, NetTerminal):
            expansion_factor = 1
        else:
            expansion_factor = options.get("expansion_factor", 1.0)

        # Add padding for routing to the right and upper sides.
        part.place_bbox.add(
            part.place_bbox.max
            + (Point(padding["L"], padding["D"]) * GRID * expansion_factor)
        )

        # Add padding for routing to the left and lower sides.
        part.place_bbox.add(
            part.place_bbox.min
            - (Point(padding["R"], padding["U"]) * GRID * expansion_factor)
        )


def get_enclosing_bbox(parts):
    """Return bounding box that encloses all the parts."""
    return BBox().add(*(part.place_bbox * part.tx for part in parts))


def add_anchor_pull_pins(parts, nets, **options):
    """Add positions of anchor and pull pins for attractive net forces between parts.

    Args:
        part (list): List of movable parts.
        nets (list): List of attractive nets between parts.
        options (dict): Dict of options and values that enable/disable functions.
    """

    def add_place_pt(part, pin):
        """Add the point for a pin on the placement boundary of a part."""

        pin.route_pt = pin.pt  # For drawing of nets during debugging.
        pin.place_pt = Point(pin.pt.x, pin.pt.y)
        if pin.orientation == "U":
            pin.place_pt.y = part.place_bbox.min.y
        elif pin.orientation == "D":
            pin.place_pt.y = part.place_bbox.max.y
        elif pin.orientation == "L":
            pin.place_pt.x = part.place_bbox.max.x
        elif pin.orientation == "R":
            pin.place_pt.x = part.place_bbox.min.x
        else:
            raise RuntimeError("Unknown pin orientation.")

    # Remove any existing anchor and pull pins before making new ones.
    rmv_attr(parts, ("anchor_pins", "pull_pins"))

    # Add dicts for anchor/pull pins and pin centroids to each movable part.
    for part in parts:
        part.anchor_pins = defaultdict(list)
        part.pull_pins = defaultdict(list)
        part.pin_ctrs = dict()

    if nets:
        # If nets exist, then these parts are interconnected so
        # assign pins on each net to part anchor and pull pin lists.
        for net in nets:
            # Get net pins that are on movable parts.
            pins = {pin for pin in net.pins if pin.part in parts}

            # Get the set of parts with pins on the net.
            net.parts = {pin.part for pin in pins}

            # Add each pin as an anchor on the part that contains it and
            # as a pull pin on all the other parts that will be pulled by this part.
            for pin in pins:
                pin.part.anchor_pins[net].append(pin)
                add_place_pt(pin.part, pin)
                for part in net.parts - {pin.part}:
                    # NetTerminals are pulled towards connected parts, but
                    # those parts are not attracted towards NetTerminals.
                    if not is_net_terminal(pin.part):
                        part.pull_pins[net].append(pin)

        # For each net, assign the centroid of the part's anchor pins for that net.
        for net in nets:
            for part in net.parts:
                if part.anchor_pins[net]:
                    part.pin_ctrs[net] = pt_sum(
                        pin.place_pt for pin in part.anchor_pins[net]
                    ) / len(part.anchor_pins[net])

    else:
        # There are no nets so these parts are floating freely.
        # Floating parts are all pulled by each other.
        all_pull_pins = []
        for part in parts:
            try:
                # Set anchor at top-most pin so floating part tops will align.
                anchor_pull_pin = max(part.pins, key=lambda pin: pin.pt.y)
                add_place_pt(part, anchor_pull_pin)
            except ValueError:
                # Set anchor for part with no pins at all.
                anchor_pull_pin = Pin()
                anchor_pull_pin.place_pt = part.place_bbox.max
            part.anchor_pins["similarity"] = [anchor_pull_pin]
            part.pull_pins["similarity"] = all_pull_pins
            all_pull_pins.append(anchor_pull_pin)


def save_anchor_pull_pins(parts):
    """Save anchor/pull pins for each part before they are changed."""
    for part in parts:
        part.saved_anchor_pins = copy(part.anchor_pins)
        part.saved_pull_pins = copy(part.pull_pins)


def restore_anchor_pull_pins(parts):
    """Restore the original anchor/pull pin lists for each Part."""

    for part in parts:
        if hasattr(part, "saved_anchor_pins"):
            # Saved pin lists exist, so restore them to the original anchor/pull pin lists.
            part.anchor_pins = part.saved_anchor_pins
            part.pull_pins = part.saved_pull_pins

    # Remove the attributes where the original lists were saved.
    rmv_attr(parts, ("saved_anchor_pins", "saved_pull_pins"))


def adjust_orientations(parts, **options):
    """Adjust orientation of parts.

    Args:
        parts (list): List of Parts to adjust.
        options (dict): Dict of options and values that enable/disable functions.

    Returns:
        bool: True if one or more part orientations were changed. Otherwise, False.
    """

    def find_best_orientation(part):
        """Each part has 8 possible orientations. Find the best of the 7 alternatives from the starting one."""

        # Store starting orientation.
        part.prev_tx = copy(part.tx)

        # Get centerpoint of part for use when doing rotations/flips.
        part_ctr = (part.place_bbox * part.tx).ctr

        # Now find the orientation that has the largest decrease (or smallest increase) in cost.
        # Go through four rotations, then flip the part and go through the rotations again.
        best_delta_cost = float("inf")
        calc_starting_cost = True
        for i in range(2):
            for j in range(4):

                if calc_starting_cost:
                    # Calculate the cost of the starting orientation before any changes in orientation.
                    starting_cost = net_tension(part, **options)
                    # Skip the starting orientation but set flag to process the others.
                    calc_starting_cost = False
                else:
                    # Calculate the cost of the current orientation.
                    delta_cost = net_tension(part, **options) - starting_cost
                    if delta_cost < best_delta_cost:
                        # Save the largest decrease in cost and the associated orientation.
                        best_delta_cost = delta_cost
                        best_tx = copy(part.tx)

                # Proceed to the next rotation.
                part.tx = part.tx.move(-part_ctr).rot_90cw().move(part_ctr)

            # Flip the part and go through the rotations again.
            part.tx = part.tx.move(-part_ctr).flip_x().move(part_ctr)

        # Save the largest decrease in cost and the associated orientation.
        part.delta_cost = best_delta_cost
        part.delta_cost_tx = best_tx

        # Restore the original orientation.
        part.tx = part.prev_tx

    # Get the list of parts that don't have their orientations locked.
    movable_parts = [part for part in parts if not part.orientation_locked]

    if not movable_parts:
        # No movable parts, so exit without doing anything.
        return

    # Kernighan-Lin algorithm for finding near-optimal part orientations.
    # Because of the way the tension for part alignment is computed based on
    # the nearest part, it is possible for an infinite loop to occur.
    # Hence the ad-hoc loop limit.
    for iter_cnt in range(10):
        # Find the best part to move and move it until there are no more parts to move.
        moved_parts = []
        unmoved_parts = movable_parts[:]
        while unmoved_parts:
            # Find the best current orientation for each unmoved part.
            for part in unmoved_parts:
                find_best_orientation(part)

            # Find the part that has the largest decrease in cost.
            part_to_move = min(unmoved_parts, key=lambda p: p.delta_cost)

            # Reorient the part with the Tx that created the largest decrease in cost.
            part_to_move.tx = part_to_move.delta_cost_tx

            # Transfer the part from the unmoved to the moved part list.
            unmoved_parts.remove(part_to_move)
            moved_parts.append(part_to_move)

        # Find the point at which the cost reaches its lowest point.
        # delta_cost at location i is the change in cost *before* part i is moved.
        # Start with cost change of zero before any parts are moved.
        delta_costs = [0,]
        delta_costs.extend((part.delta_cost for part in moved_parts))
        try:
            cost_seq = list(itertools.accumulate(delta_costs))
        except AttributeError:
            # Python 2.7 doesn't have itertools.accumulate().
            cost_seq = list(delta_costs)
            for i in range(1, len(cost_seq)):
                cost_seq[i] = cost_seq[i - 1] + cost_seq[i]
        min_cost = min(cost_seq)
        min_index = cost_seq.index(min_cost)

        # Move all the parts after that point back to their starting positions.
        for part in moved_parts[min_index:]:
            part.tx = part.prev_tx

        # Terminate the search if no part orientations were changed.
        if min_index == 0:
            break

    rmv_attr(parts, ("prev_tx", "delta_cost", "delta_cost_tx"))

    # Return True if one or more iterations were done, indicating part orientations were changed.
    return iter_cnt > 0


def net_tension_dist(part, **options):
    """Calculate the tension of the nets trying to rotate/flip the part.

    Args:
        part (Part): Part affected by forces from other connected parts.
        options (dict): Dict of options and values that enable/disable functions.

    Returns:
        float: Total tension on the part.
    """

    # Compute the force for each net attached to the part.
    tension = 0.0
    for net, anchor_pins in part.anchor_pins.items():
        pull_pins = part.pull_pins[net]

        if not anchor_pins or not pull_pins:
            # Skip nets without pulling or anchor points.
            continue

        # Compute the net force acting on each anchor point on the part.
        for anchor_pin in anchor_pins:
            # Compute the anchor point's (x,y).
            anchor_pt = anchor_pin.place_pt * anchor_pin.part.tx

            # Find the dist from the anchor point to each pulling point.
            dists = [
                (anchor_pt - pp.place_pt * pp.part.tx).magnitude for pp in pull_pins
            ]

            # Only the closest pulling point affects the tension since that is
            # probably where the wire routing will go to.
            tension += min(dists)

    return tension


def net_torque_dist(part, **options):
    """Calculate the torque of the nets trying to rotate/flip the part.

    Args:
        part (Part): Part affected by forces from other connected parts.
        options (dict): Dict of options and values that enable/disable functions.

    Returns:
        float: Total torque on the part.
    """

    # Part centroid for computing torque.
    ctr = part.place_bbox.ctr * part.tx

    # Get the force multiplier applied to point-to-point nets.
    pt_to_pt_mult = options.get("pt_to_pt_mult", 1)

    # Compute the torque for each net attached to the part.
    torque = 0.0
    for net, anchor_pins in part.anchor_pins.items():
        pull_pins = part.pull_pins[net]

        if not anchor_pins or not pull_pins:
            # Skip nets without pulling or anchor points.
            continue

        pull_pin_pts = [pin.place_pt * pin.part.tx for pin in pull_pins]

        # Multiply the force exerted by point-to-point nets.
        force_mult = pt_to_pt_mult if len(pull_pin_pts) <= 1 else 1

        # Compute the net torque acting on each anchor point on the part.
        for anchor_pin in anchor_pins:
            # Compute the anchor point's (x,y).
            anchor_pt = anchor_pin.place_pt * part.tx

            # Compute torque around part center from force between anchor & pull pins.
            normalize = len(pull_pin_pts)
            lever_norm = (anchor_pt - ctr).norm
            for pull_pt in pull_pin_pts:
                frc_norm = (pull_pt - anchor_pt).norm
                torque += lever_norm.xprod(frc_norm) * force_mult / normalize

    return abs(torque)


# Select the net tension method used for the adjusting the orientation of parts.
net_tension = net_tension_dist
# net_tension = net_torque_dist


@export_to_all
def net_force_dist(part, **options):
    """Compute attractive force on a part from all the other parts connected to it.

    Args:
        part (Part): Part affected by forces from other connected parts.
        options (dict): Dict of options and values that enable/disable functions.

    Returns:
        Vector: Force upon given part.
    """

    # Get the anchor and pull pins for each net connected to this part.
    anchor_pins = part.anchor_pins
    pull_pins = part.pull_pins

    # Get the force multiplier applied to point-to-point nets.
    pt_to_pt_mult = options.get("pt_to_pt_mult", 1)

    # Compute the total force on the part from all the anchor/pulling points on each net.
    total_force = Vector(0, 0)

    # Parts with a lot of pins can accumulate large net forces that move them very quickly.
    # Accumulate the number of individual net forces and use that to attenuate
    # the total force, effectively normalizing the forces between large & small parts.
    net_normalizer = 0

    # Compute the force for each net attached to the part.
    for net in anchor_pins.keys():
        if not anchor_pins[net] or not pull_pins[net]:
            # Skip nets without pulling or anchor points.
            continue

        # Multiply the force exerted by point-to-point nets.
        force_mult = pt_to_pt_mult if len(pull_pins[net]) <= 1 else 1

        # Initialize net force.
        net_force = Vector(0, 0)

        pin_normalizer = 0

        # Compute the anchor and pulling point (x,y)s for the net.
        anchor_pts = [pin.place_pt * pin.part.tx for pin in anchor_pins[net]]
        pull_pts = [pin.place_pt * pin.part.tx for pin in pull_pins[net]]

        # Compute the net force acting on each anchor point on the part.
        for anchor_pt in anchor_pts:
            # Sum the forces from each pulling point on the anchor point.
            for pull_pt in pull_pts:
                # Get the distance from the pull pt to the anchor point.
                dist_vec = pull_pt - anchor_pt

                # Add the force on the anchor pin from the pulling pin.
                net_force += dist_vec

                # Increment the normalizer for every pull force added to the net force.
                pin_normalizer += 1

        if options.get("pin_normalize"):
            # Normalize the net force across all the anchor & pull pins.
            pin_normalizer = pin_normalizer or 1  # Prevent div-by-zero.
            net_force /= pin_normalizer

        # Accumulate force from this net into the total force on the part.
        # Multiply force if the net meets stated criteria.
        total_force += net_force * force_mult

        # Increment the normalizer for every net force added to the total force.
        net_normalizer += 1

    if options.get("net_normalize"):
        # Normalize the total force across all the nets.
        net_normalizer = net_normalizer or 1  # Prevent div-by-zero.
        total_force /= net_normalizer

    return total_force


# Select the net force method used for the attraction of parts during placement.
attractive_force = net_force_dist


@export_to_all
def overlap_force(part, parts, **options):
    """Compute the repulsive force on a part from overlapping other parts.

    Args:
        part (Part): Part affected by forces from other overlapping parts.
        parts (list): List of parts to check for overlaps.
        options (dict): Dict of options and values that enable/disable functions.

    Returns:
        Vector: Force upon given part.
    """

    # Bounding box of given part.
    part_bbox = part.place_bbox * part.tx

    # Compute the overlap force of the bbox of this part with every other part.
    total_force = Vector(0, 0)
    for other_part in set(parts) - {part}:
        other_part_bbox = other_part.place_bbox * other_part.tx

        # No force unless parts overlap.
        if part_bbox.intersects(other_part_bbox):
            # Compute the movement needed to separate the bboxes in left/right/up/down directions.
            # Add some small random offset to break symmetry when parts exactly overlay each other.
            # Move right edge of part to the left of other part's left edge, etc...
            moves = []
            rnd = Vector(random.random()-0.5, random.random()-0.5)
            for edges, dir in ((("ll", "lr"), Vector(1,0)), (("ul", "ll"), Vector(0,1))):
                move = (getattr(other_part_bbox, edges[0]) - getattr(part_bbox, edges[1]) - rnd) * dir
                moves.append([move.magnitude, move])
                # Flip edges...
                move = (getattr(other_part_bbox, edges[1]) - getattr(part_bbox, edges[0]) - rnd) * dir
                moves.append([move.magnitude, move])

            # Select the smallest move that separates the parts.
            move = min(moves, key=lambda m: m[0])

            # Add the move to the total force on the part.
            total_force += move[1]
                
    return total_force


@export_to_all
def overlap_force_rand(part, parts, **options):
    """Compute the repulsive force on a part from overlapping other parts.

    Args:
        part (Part): Part affected by forces from other overlapping parts.
        parts (list): List of parts to check for overlaps.
        options (dict): Dict of options and values that enable/disable functions.

    Returns:
        Vector: Force upon given part.
    """

    # Bounding box of given part.
    part_bbox = part.place_bbox * part.tx

    # Compute the overlap force of the bbox of this part with every other part.
    total_force = Vector(0, 0)
    for other_part in set(parts) - {part}:
        other_part_bbox = other_part.place_bbox * other_part.tx

        # No force unless parts overlap.
        if part_bbox.intersects(other_part_bbox):
            # Compute the movement needed to clear the bboxes in left/right/up/down directions.
            # Add some small random offset to break symmetry when parts exactly overlay each other.
            # Move right edge of part to the left of other part's left edge.
            moves = []
            rnd = Vector(random.random()-0.5, random.random()-0.5)
            for edges, dir in ((("ll", "lr"), Vector(1,0)), (("lr", "ll"), Vector(1,0)),
                          (("ul", "ll"), Vector(0,1)), (("ll", "ul"), Vector(0,1))):
                move = (getattr(other_part_bbox, edges[0]) - getattr(part_bbox, edges[1]) - rnd) * dir
                moves.append([move.magnitude, move])
            accum = 0
            for move in moves:
                accum += move[0]
            for move in moves:
                move[0] = accum - move[0]
            new_accum = 0
            for move in moves:
                move[0] += new_accum
                new_accum = move[0]
            select = new_accum * random.random()
            for move in moves:
                if move[0] >= select:
                    total_force += move[1]
                    break
                
    return total_force


# Select the overlap force method used for the repulsion of parts during placement.
repulsive_force = overlap_force
# repulsive_force = overlap_force_rand


def scale_attractive_repulsive_forces(parts, force_func, **options):
    """Set scaling between attractive net forces and repulsive part overlap forces."""

    # Store original part placement.
    for part in parts:
        part.original_tx = copy(part.tx)

    # Find attractive forces when they are maximized by random part placement.
    random_placement(parts, **options)
    attractive_forces_sum = sum(
        force_func(p, parts, alpha=0, scale=1, **options).magnitude for p in parts
    )

    # Find repulsive forces when they are maximized by compacted part placement.
    central_placement(parts, **options)
    repulsive_forces_sum = sum(
        force_func(p, parts, alpha=1, scale=1, **options).magnitude for p in parts
    )

    # Restore original part placement.
    for part in parts:
        part.tx = part.original_tx
    rmv_attr(parts, ["original_tx"])

    # Return scaling factor that makes attractive forces about the same as repulsive forces.
    try:
        return repulsive_forces_sum / attractive_forces_sum
    except ZeroDivisionError:
        # No attractive forces, so who cares about scaling? Set it to 1.
        return 1


def total_part_force(part, parts, scale, alpha, **options):
    """Compute the total of the attractive net and repulsive overlap forces on a part.

    Args:
        part (Part): Part affected by forces from other overlapping parts.
        parts (list): List of parts to check for overlaps.
        scale (float): Scaling factor for net forces to make them equivalent to overlap forces.
        alpha (float): Fraction of the total that is the overlap force (range [0,1]).
        options (dict): Dict of options and values that enable/disable functions.

    Returns:
        Vector: Weighted total of net attractive and overlap repulsion forces.
    """
    force = scale * (1 - alpha) * attractive_force(
        part, **options
    ) + alpha * repulsive_force(part, parts, **options)
    part.force = force  # For debug drawing.
    return force


def similarity_force(part, parts, similarity, **options):
    """Compute attractive force on a part from all the other parts connected to it.

    Args:
        part (Part): Part affected by similarity forces with other parts.
        similarity (dict): Similarity score for any pair of parts used as keys.
        options (dict): Dict of options and values that enable/disable functions.

    Returns:
        Vector: Force upon given part.
    """

    # Get the single anchor point for similarity forces affecting this part.
    anchor_pt = part.anchor_pins["similarity"][0].place_pt * part.tx

    # Compute the combined force of all the similarity pulling points.
    total_force = Vector(0, 0)
    for pull_pin in part.pull_pins["similarity"]:
        pull_pt = pull_pin.place_pt * pull_pin.part.tx
        # Force from pulling to anchor point is proportional to part similarity and distance.
        total_force += (pull_pt - anchor_pt) * similarity[part][pull_pin.part]

    return total_force


def total_similarity_force(part, parts, similarity, scale, alpha, **options):
    """Compute the total of the attractive similarity and repulsive overlap forces on a part.

    Args:
        part (Part): Part affected by forces from other overlapping parts.
        parts (list): List of parts to check for overlaps.
        similarity (dict): Similarity score for any pair of parts used as keys.
        scale (float): Scaling factor for similarity forces to make them equivalent to overlap forces.
        alpha (float): Proportion of the total that is the overlap force (range [0,1]).
        options (dict): Dict of options and values that enable/disable functions.

    Returns:
        Vector: Weighted total of net attractive and overlap repulsion forces.
    """
    force = scale * (1 - alpha) * similarity_force(
        part, parts, similarity, **options
    ) + alpha * repulsive_force(part, parts, **options)
    part.force = force  # For debug drawing.
    return force


def define_placement_bbox(parts, **options):
    """Return a bounding box big enough to hold the parts being placed."""

    # Compute appropriate size to hold the parts based on their areas.
    area = 0
    for part in parts:
        area += part.place_bbox.area
    side = 3 * math.sqrt(area)  # HACK: Multiplier is ad-hoc.
    return BBox(Point(0, 0), Point(side, side))


def central_placement(parts, **options):
    """Cluster all part centroids onto a common point.

    Args:
        parts (list): List of Parts.
        options (dict): Dict of options and values that enable/disable functions.
    """

    if len(parts) <= 1:
        # No need to do placement if there's less than two parts.
        return

    # Find the centroid of all the parts.
    ctr = get_enclosing_bbox(parts).ctr

    # Collapse all the parts to the centroid.
    for part in parts:
        mv = ctr - part.place_bbox.ctr * part.tx
        part.tx *= Tx(dx=mv.x, dy=mv.y)


def random_placement(parts, **options):
    """Randomly place parts within an appropriately-sized area.

    Args:
        parts (list): List of Parts to place.
    """

    # Compute appropriate size to hold the parts based on their areas.
    bbox = define_placement_bbox(parts, **options)

    # Place parts randomly within area.
    for part in parts:
        pt = Point(random.random() * bbox.w, random.random() * bbox.h)
        part.tx = part.tx.move(pt)


def push_and_pull(anchored_parts, mobile_parts, nets, force_func, **options):
    """Move parts under influence of attractive nets and repulsive part overlaps.

    Args:
        anchored_parts (list): Set of immobile Parts whose position affects placement.
        mobile_parts (list): Set of Parts that can be moved.
        nets (list): List of nets that interconnect parts.
        force_func: Function for calculating forces between parts.
        options (dict): Dict of options and values that enable/disable functions.
    """

    if not options.get("use_push_pull"):
        # Abort if push & pull of parts is disabled.
        return

    if not mobile_parts:
        # No need to do placement if there's nothing to move.
        return

    def cost(parts, alpha):
        """Cost function for use in debugging. Should decrease as parts move."""
        for part in parts:
            part.force = force_func(part, parts, scale=scale, alpha=alpha, **options)
        return sum((part.force.magnitude for part in parts))

    # Get PyGame screen, real-to-screen coord Tx matrix, font for debug drawing.
    scr = options.get("draw_scr")
    tx = options.get("draw_tx")
    font = options.get("draw_font")
    txt_org = Point(10, 10)

    # Create the total set of parts exerting forces on each other.
    parts = anchored_parts + mobile_parts

    # If there are no anchored parts, then compute the overall drift force
    # across all the parts. This will be subtracted so the
    # entire group of parts doesn't just continually drift off in one direction.
    # This only needs to be done if ALL parts are mobile (i.e., no anchored parts).
    rmv_drift = not anchored_parts

    # Set scale factor between attractive net forces and repulsive part overlap forces.
    scale = scale_attractive_repulsive_forces(parts, force_func, **options)

    # Setup the schedule for adjusting the alpha coefficient that weights the
    # combination of the attractive net forces and the repulsive part overlap forces.
    # Start at 0 (all attractive) and gradually progress to 1 (all repulsive).
    # Also, set parameters for determining when parts are stable and for restricting
    # movements in the X & Y directions when parts are being aligned.
    force_schedule = [
        (0.50, 0.0, 0.1, False, (1, 1)),  # Attractive forces only.
        (0.25, 0.0, 0.01, False, (1, 1)),  # Attractive forces only.
        # (0.25, 0.2, 0.01, False, (1,1)), # Some repulsive forces.
        (0.25, 0.4, 0.1, False, (1, 1)),  # More repulsive forces.
        # (0.25, 0.6, 0.01, False, (1,1)), # More repulsive forces.
        (0.25, 0.8, 0.1, False, (1, 1)),  # More repulsive forces.
        # (0.25, 0.7, 0.01, True, (1,0)), # Align parts horiz.
        # (0.25, 0.7, 0.01, True, (0,1)), # Align parts vert.
        # (0.25, 0.7, 0.01, True, (1,0)), # Align parts horiz.
        # (0.25, 0.7, 0.01, True, (0,1)), # Align parts vert.
        (0.25, 1.0, 0.01, False, (1, 1)),  # Remove any part overlaps.
    ]
    # N = 7
    # force_schedule = [(0.50, i/N, 0.01, False, (1,1)) for i in range(N+1)]

    # Step through the alpha sequence going from all-attractive to all-repulsive forces.
    for speed, alpha, stability_coef, align_parts, force_mask in force_schedule:
        if align_parts:
            # Align parts by only using forces between the closest anchor/pull pins.
            retain_closest_anchor_pull_pins(mobile_parts)
        else:
            # For general placement, use forces between all anchor/pull pins.
            restore_anchor_pull_pins(mobile_parts)

        # This stores the threshold below which all the parts are assumed to be stabilized.
        # Since it can never be negative, set it to -1 to indicate it's uninitialized.
        stable_threshold = -1

        # Move parts for this alpha until they all settle into fixed positions.
        # Place an iteration limit to prevent an infinite loop.
        for _ in range(1000):  # HACK: Ad-hoc iteration limit.
            # Compute forces exerted on the parts by each other.
            sum_of_forces = 0
            for part in mobile_parts:
                part.force = force_func(
                    part, parts, scale=scale, alpha=alpha, **options
                )
                # Mask X or Y component of force during part alignment.
                part.force = part.force.mask(force_mask)
                sum_of_forces += part.force.magnitude

            if rmv_drift:
                # Calculate the drift force across all parts and subtract it from each part
                # to prevent them from continually drifting in one direction.
                drift_force = force_sum([part.force for part in mobile_parts]) / len(
                    mobile_parts
                )
                for part in mobile_parts:
                    part.force -= drift_force

            # Apply movements to part positions.
            for part in mobile_parts:
                part.mv = part.force * speed
                part.tx *= Tx(dx=part.mv.x, dy=part.mv.y)

            # Keep iterating until all the parts are still.
            if stable_threshold < 0:
                # Set the threshold after the first iteration.
                initial_sum_of_forces = sum_of_forces
                stable_threshold = sum_of_forces * stability_coef
            elif sum_of_forces <= stable_threshold:
                # Part positions have stabilized if forces have dropped below threshold.
                break
            elif sum_of_forces > 10 * initial_sum_of_forces:
                # If the forces are getting higher, then that usually means the parts are
                # spreading out. This can happen if speed is too large, so reduce it so
                # the forces may start to decrease.
                speed *= 0.50

        if scr:
            # Draw current part placement for debugging purposes.
            draw_placement(parts, nets, scr, tx, font)
            draw_text(
                "alpha:{alpha:3.2f} iter:{_} force:{sum_of_forces:.1f} stable:{stable_threshold}".format(
                    **locals()
                ),
                txt_org,
                scr,
                tx,
                font,
                color=(0, 0, 0),
                real=False,
            )
            draw_redraw()


def evolve_placement(anchored_parts, mobile_parts, nets, force_func, **options):
    """Evolve part placement looking for optimum using force function.

    Args:
        anchored_parts (list): Set of immobile Parts whose position affects placement.
        mobile_parts (list): Set of Parts that can be moved.
        nets (list): List of nets that interconnect parts.
        force_func (function): Computes the force affecting part positions.
        options (dict): Dict of options and values that enable/disable functions.
    """

    parts = anchored_parts + mobile_parts

    # Force-directed placement.
    push_and_pull(anchored_parts, mobile_parts, nets, force_func, **options)

    # Snap parts to grid.
    for part in parts:
        snap_to_grid(part)


def place_net_terminals(net_terminals, placed_parts, nets, force_func, **options):
    """Place net terminals around already-placed parts.

    Args:
        net_terminals (list): List of NetTerminals
        placed_parts (list): List of placed Parts.
        nets (list): List of nets that interconnect parts.
        force_func (function): Computes the force affecting part positions.
        options (dict): Dict of options and values that enable/disable functions.
    """

    def trim_pull_pins(terminals, bbox):
        """Trim pullpins of NetTerminals to the part pins closest to an edge of the bounding box of placed parts.

        Args:
            terminals (list): List of NetTerminals.
            bbox (BBox): Bounding box of already-placed parts.

        Note:
            The rationale for this is that pin closest to an edge of the bounding box will be easier to access.
        """

        for terminal in terminals:
            for net, pull_pins in terminal.pull_pins.items():
                insets = []
                for pull_pin in pull_pins:
                    pull_pt = pull_pin.place_pt * pull_pin.part.tx

                    # Get the inset of the terminal pulling pin from each side of the placement area.
                    # Left side.
                    insets.append((abs(pull_pt.x - bbox.ll.x), pull_pin))
                    # Right side.
                    insets.append((abs(pull_pt.x - bbox.lr.x), pull_pin))
                    # Top side.
                    insets.append((abs(pull_pt.y - bbox.ul.y), pull_pin))
                    # Bottom side.
                    insets.append((abs(pull_pt.y - bbox.ll.y), pull_pin))

                # Retain only the pulling pin closest to an edge of the bounding box (i.e., minimum inset).
                terminal.pull_pins[net] = [min(insets, key=lambda off: off[0])[1]]

    def orient(terminals, bbox):
        """Set orientation of NetTerminals to point away from closest bounding box edge.

        Args:
            terminals (list): List of NetTerminals.
            bbox (BBox): Bounding box of already-placed parts.
        """

        for terminal in terminals:
            # A NetTerminal should already be trimmed so it is attached to a single pin of a part on a single net.
            pull_pin = list(terminal.pull_pins.values())[0][0]
            pull_pt = pull_pin.place_pt * pull_pin.part.tx

            # Get the inset of the terminal pulling pin from each side of the placement area
            # and the Tx() that should be applied if the terminal is placed on that side.
            insets = []
            # Left side, so terminal label juts out to the left.
            insets.append((abs(pull_pt.x - bbox.ll.x), Tx()))
            # Right side, so terminal label flipped to jut out to the right.
            insets.append((abs(pull_pt.x - bbox.lr.x), Tx().flip_x()))
            # Top side, so terminal label rotated by 270 to jut out to the top.
            insets.append((abs(pull_pt.y - bbox.ul.y), Tx().rot_90cw().rot_90cw().rot_90cw()))
            # Bottom side. so terminal label rotated 90 to jut out to the bottom.
            insets.append((abs(pull_pt.y - bbox.ll.y), Tx().rot_90cw()))

            # Apply the Tx() for the side the terminal is closest to.
            terminal.tx = min(insets, key=lambda inset: inset[0])[1]

    def move_to_pull_pin(terminals):
        """Move NetTerminals immediately to their pulling pins."""
        for terminal in terminals:
            anchor_pin = list(terminal.anchor_pins.values())[0][0]
            anchor_pt = anchor_pin.place_pt * anchor_pin.part.tx
            pull_pin = list(terminal.pull_pins.values())[0][0]
            pull_pt = pull_pin.place_pt * pull_pin.part.tx
            terminal.tx = terminal.tx.move(pull_pt - anchor_pt)

    def evolution(net_terminals, placed_parts, bbox):
        """Evolve placement of NetTerminals starting from outermost from center to innermost."""

        evolution_type = options.get("terminal_evolution", "all_at_once")

        if evolution_type == "all_at_once":
            evolve_placement(
                placed_parts, net_terminals, nets, total_part_force, **options
            )

        elif evolution_type == "outer_to_inner":
            # Start off with the previously-placed parts as anchored parts. NetTerminals will be added to this as they are placed.
            anchored_parts = copy(placed_parts)

            # Sort terminals from outermost to innermost w.r.t. the center.
            def dist_to_bbox_edge(term):
                pt = term.pins[0].place_pt * term.tx
                return min((
                    abs(pt.x - bbox.ll.x),
                    abs(pt.x - bbox.lr.x),
                    abs(pt.y - bbox.ll.y),
                    abs(pt.y - bbox.ul.y))
                )

            terminals = sorted(
                net_terminals,
                key=lambda term: dist_to_bbox_edge(term),
                reverse=True,
            )

            # Grab terminals starting from the outside and work towards the inside until a terminal intersects a previous one.
            mobile_terminals = []
            mobile_bboxes = []
            for terminal in terminals:
                terminal_bbox = terminal.place_bbox * terminal.tx
                mobile_terminals.append(terminal)
                mobile_bboxes.append(terminal_bbox)
                for bbox in mobile_bboxes[:-1]:
                    if terminal_bbox.intersects(bbox):
                        # The current NetTerminal intersects one of the previously-selected mobile terminals, so evolve the
                        # placement of all the mobile terminals except the current one.
                        evolve_placement(
                            anchored_parts,
                            mobile_terminals[:-1],
                            nets,
                            force_func,
                            **options
                        )
                        # Anchor the mobile terminals after their placement is done.
                        anchored_parts.extend(mobile_terminals[:-1])
                        # Remove the placed terminals, leaving only the current terminal.
                        mobile_terminals = mobile_terminals[-1:]
                        mobile_bboxes = mobile_bboxes[-1:]

            if mobile_terminals:
                # Evolve placement of any remaining terminals.
                evolve_placement(
                    anchored_parts, mobile_terminals, nets, total_part_force, **options
                )

    bbox = get_enclosing_bbox(placed_parts)
    save_anchor_pull_pins(net_terminals)
    trim_pull_pins(net_terminals, bbox)
    orient(net_terminals, bbox)
    move_to_pull_pin(net_terminals)
    evolution(net_terminals, placed_parts, bbox)
    restore_anchor_pull_pins(net_terminals)


@export_to_all
class Placer:
    """Mixin to add place function to Node class."""

    def group_parts(node, **options):
        """Group parts in the Node that are connected by internal nets

        Args:
            node (Node): Node with parts.
            options (dict, optional): Dictionary of options and values. Defaults to {}.

        Returns:
            list: List of lists of Parts that are connected.
            list: List of internal nets connecting parts.
            list: List of Parts that are not connected to anything (floating).
        """

        if not node.parts:
            return [], [], []

        # Extract list of nets having at least one pin in the node.
        internal_nets = node.get_internal_nets()

        # Group all the parts that have some interconnection to each other.
        # Start with groups of parts on each individual net.
        connected_parts = [
            set(pin.part for pin in net.pins if pin.part in node.parts)
            for net in internal_nets
        ]

        # Now join groups that have parts in common.
        for i in range(len(connected_parts) - 1):
            group1 = connected_parts[i]
            for j in range(i + 1, len(connected_parts)):
                group2 = connected_parts[j]
                if group1 & group2:
                    # If part groups intersect, collect union of parts into one group
                    # and empty-out the other.
                    connected_parts[j] = connected_parts[i] | connected_parts[j]
                    connected_parts[i] = set()
                    # No need to check against group1 any more since it has been
                    # unioned into group2 that will be checked later in the loop.
                    break

        # Remove any empty groups that were unioned into other groups.
        connected_parts = [group for group in connected_parts if group]

        # Find parts that aren't connected to anything.
        floating_parts = set(node.parts) - set(itertools.chain(*connected_parts))

        return connected_parts, internal_nets, floating_parts

    def place_connected_parts(node, parts, nets, **options):
        """Place individual parts.

        Args:
            node (Node): Node with parts.
            parts (list): List of Part sets connected by nets.
            nets (list): List of internal Nets connecting the parts.
            options (dict): Dict of options and values that enable/disable functions.
        """

        if not parts:
            # Abort if nothing to place.
            return

        # Add bboxes with surrounding area so parts are not butted against each other.
        add_placement_bboxes(parts, **options)

        # Set anchor and pull pins that determine attractive forces between parts.
        add_anchor_pull_pins(parts, nets, **options)

        # Randomly place connected parts.
        random_placement(parts)

        if options.get("draw_placement"):
            # Draw the placement for debug purposes.
            bbox = get_enclosing_bbox(parts)
            draw_scr, draw_tx, draw_font = draw_start(bbox)
            options.update(
                {"draw_scr": draw_scr, "draw_tx": draw_tx, "draw_font": draw_font}
            )

        if options.get("compress_before_place"):
            central_placement(parts, **options)

        # Do force-directed placement of the parts in the parts.

        # Separate the NetTerminals from the other parts.
        net_terminals = [part for part in parts if is_net_terminal(part)]
        real_parts = [part for part in parts if not is_net_terminal(part)]

        # Do the first trial placement.
        evolve_placement([], real_parts, nets, total_part_force, **options)

        if options.get("rotate_parts"):
            # Adjust part orientations after first trial placement is done.
            if adjust_orientations(real_parts, **options):
                # Some part orientations were changed, so re-do placement.
                evolve_placement([], real_parts, nets, total_part_force, **options)

        # Place NetTerminals after all the other parts.
        place_net_terminals(
            net_terminals, real_parts, nets, total_part_force, **options
        )

        if options.get("draw_placement"):
            # Pause to look at placement for debugging purposes.
            draw_pause()

    def place_floating_parts(node, parts, **options):
        """Place individual parts.

        Args:
            node (Node): Node with parts.
            parts (list): List of Parts not connected by explicit nets.
            options (dict): Dict of options and values that enable/disable functions.
        """

        if not parts:
            # Abort if nothing to place.
            return

        # Add bboxes with surrounding area so parts are not butted against each other.
        add_placement_bboxes(parts)

        # Set anchor and pull pins that determine attractive forces between similar parts.
        add_anchor_pull_pins(parts, [], **options)

        # Randomly place the floating parts.
        random_placement(parts)

        if options.get("draw_placement"):
            # Compute the drawing area for the floating parts
            bbox = get_enclosing_bbox(parts)
            draw_scr, draw_tx, draw_font = draw_start(bbox)
            options.update(
                {"draw_scr": draw_scr, "draw_tx": draw_tx, "draw_font": draw_font}
            )

        # For non-connected parts, do placement based on their similarity to each other.
        part_similarity = defaultdict(lambda: defaultdict(lambda: 0))
        for part in parts:
            for other_part in parts:
                # Don't compute similarity of a part to itself.
                if other_part is part:
                    continue

                # HACK: Get similarity forces right-sized.
                part_similarity[part][other_part] = part.similarity(other_part) / 100
                # part_similarity[part][other_part] = 0.1

            # Select the top-most pin in each part as the anchor point for force-directed placement.
            # tx = part.tx
            # part.anchor_pin = max(part.anchor_pins, key=lambda pin: (pin.place_pt * tx).y)

        force_func = functools.partial(
            total_similarity_force, similarity=part_similarity
        )

        if options.get("compress_before_place"):
            # Compress all floating parts together.
            central_placement(parts, **options)

        # Do force-directed placement of the parts in the group.
        evolve_placement([], parts, [], force_func, **options)

        if options.get("draw_placement"):
            # Pause to look at placement for debugging purposes.
            draw_pause()

    def place_blocks(node, connected_parts, floating_parts, children, **options):
        """Place blocks of parts and hierarchical sheets.

        Args:
            node (Node): Node with parts.
            connected_parts (list): List of Part sets connected by nets.
            floating_parts (set): Set of Parts not connected by any of the internal nets.
            children (list): Child nodes in the hierarchy.
            non_sheets (list): Hierarchical set of Parts that are visible.
            sheets (list): List of hierarchical blocks.
            options (dict): Dict of options and values that enable/disable functions.
        """

        # Global dict of pull pins for all blocks as they each pull on each other the same way.
        block_pull_pins = defaultdict(list)

        # Class for movable groups of parts/child nodes.
        class PartBlock:
            def __init__(self, src, bbox, anchor_pt, snap_pt, tag):
                self.src = src  # Source for this block.
                self.place_bbox = bbox  # FIXME: Is this needed if place_bbox includes room for routing?

                # Create anchor pin to which forces are applied to this block.
                anchor_pin = Pin()
                anchor_pin.part = self
                anchor_pin.place_pt = anchor_pt

                # This block has only a single anchor pin, but it needs to be in a list
                # in a dict so it can be processed by the part placement functions.
                self.anchor_pins = dict()
                self.anchor_pins["similarity"] = [anchor_pin]

                # Anchor pin for this block is also a pulling pin for all other blocks.
                block_pull_pins["similarity"].append(anchor_pin)

                # All blocks have the same set of pulling pins because they all pull each other.
                self.pull_pins = block_pull_pins

                self.snap_pt = snap_pt  # For snapping to grid.
                self.tx = Tx()  # For placement.
                self.ref = "REF"  # Name for block in debug drawing.
                self.tag = tag  # FIXME: what is this for?

        # Create a list of blocks from the groups of interconnected parts and the group of floating parts.
        part_blocks = []
        for part_list in connected_parts + [floating_parts]:
            if not part_list:
                # No parts in this list for some reason...
                continue

            # Find snapping point and bounding box for this group of parts.
            snap_pt = None
            bbox = BBox()
            for part in part_list:
                bbox.add(part.lbl_bbox * part.tx)
                if not snap_pt:
                    # Use the first snapping point of a part you can find.
                    snap_pt = get_snap_pt(part)

            # Tag indicates the type of part block.
            tag = 2 if (part_list is floating_parts) else 1

            # pad the bounding box so part blocks don't butt-up against each other.
            pad = BLK_EXT_PAD
            bbox = bbox.resize(Vector(pad, pad))

            # Create the part block and place it on the list.
            part_blocks.append(PartBlock(part_list, bbox, bbox.ctr, snap_pt, tag))

        # Add part blocks for child nodes.
        for child in children:
            # Calculate bounding box of child node.
            bbox = child.calc_bbox()

            # Set padding for separating bounding box from others.
            if child.flattened:
                # This is a flattened node so the parts will be shown.
                # Set the padding to include a pad between the parts and the
                # graphical box that contains them, plus the padding around
                # the outside of the graphical box.
                pad = BLK_INT_PAD + BLK_EXT_PAD
            else:
                # This is an unflattened child node showing no parts on the inside
                # so just pad around the outside of its graphical box.
                pad = BLK_EXT_PAD
            bbox = bbox.resize(Vector(pad, pad))

            # Set the grid snapping point and tag for this child node.
            snap_pt = child.get_snap_pt()
            tag = 3  # Standard child node.
            if not snap_pt:
                # No snap point found, so just use the center of the bounding box.
                snap_pt = bbox.ctr
                tag = 4  # A child node with no snapping point.

            # Create the child block and place it on the list.
            part_blocks.append(PartBlock(child, bbox, bbox.ctr, snap_pt, tag))

        # Get ordered list of all block tags. Use this list to tell if tags are
        # adjacent since there may be missing tags if a particular type of block
        # isn't present.
        tags = sorted({blk.tag for blk in part_blocks})

        # Tie the blocks together with strong links between blocks with the same tag,
        # and weaker links between blocks with adjacent tags. This ties similar
        # blocks together into "super blocks" and ties the super blocks into a linear
        # arrangement (1 -> 2 -> 3 ->...).
        blk_attr = defaultdict(lambda: defaultdict(lambda: 0))
        for blk in part_blocks:
            for other_blk in part_blocks:
                if blk is other_blk:
                    # No attraction between a block and itself.
                    continue
                if blk.tag == other_blk.tag:
                    # Large attraction between blocks of same type.
                    blk_attr[blk][other_blk] = 1
                elif abs(tags.index(blk.tag) - tags.index(other_blk.tag)) == 1:
                    # Some attraction between blocks of adjacent types.
                    blk_attr[blk][other_blk] = 0.1
                else:
                    # Otherwise, no attraction between these blocks.
                    blk_attr[blk][other_blk] = 0

        if not part_blocks:
            # Abort if nothing to place.
            return

        # Start off with a random placement of part blocks.
        random_placement(part_blocks)

        if options.get("draw_placement"):
            # Setup to draw the part block placement for debug purposes.
            bbox = get_enclosing_bbox(part_blocks)
            draw_scr, draw_tx, draw_font = draw_start(bbox)
            options.update(
                {"draw_scr": draw_scr, "draw_tx": draw_tx, "draw_font": draw_font}
            )

        # Arrange the part blocks with similarity force-directed placement.
        force_func = functools.partial(total_similarity_force, similarity=blk_attr)
        evolve_placement([], part_blocks, [], force_func, **options)

        if options.get("draw_placement"):
            # Pause to look at placement for debugging purposes.
            draw_pause()

        # Apply the placement moves of the part blocks to their underlying sources.
        for blk in part_blocks:
            try:
                # Update the Tx matrix of the source (usually a child node).
                blk.src.tx = blk.tx
            except AttributeError:
                # The source doesn't have a Tx so it must be a collection of parts.
                # Apply the block placement to the Tx of each part.
                for part in blk.src:
                    part.tx *= blk.tx

    def get_attrs(node):
        """Return dict of attribute sets for the parts, pins, and nets in a node."""
        attrs = {"parts": set(), "pins": set(), "nets": set()}
        for part in node.parts:
            attrs["parts"].update(set(dir(part)))
            for pin in part.pins:
                attrs["pins"].update(set(dir(pin)))
        for net in node.get_internal_nets():
            attrs["nets"].update(set(dir(net)))
        return attrs

    def show_added_attrs(node):
        """Show attributes that were added to parts, pins, and nets in a node."""
        current_attrs = node.get_attrs()
        for key in current_attrs.keys():
            print(
                "added {} attrs: {}".format(key, current_attrs[key] - node.attrs[key])
            )

    def rmv_placement_stuff(node):
        """Remove attributes added to parts, pins, and nets of a node during the placement phase."""

        for part in node.parts:
            rmv_attr(part.pins, ("route_pt", "place_pt"))
        rmv_attr(
            node.parts,
            ("anchor_pins", "pull_pins", "pin_ctrs", "force", "mv"),
        )
        rmv_attr(node.get_internal_nets(), ("parts",))

    def place(node, tool=None, **options):
        """Place the parts and children in this node.

        Args:
            node (Node): Hierarchical node containing the parts and children to be placed.
            tool (str): Backend tool for schematics.
            options (dict): Dictionary of options and values to control placement.
        """

        # Inject the constants for the backend tool into this module.
        import skidl
        from skidl.tools import tool_modules

        tool = tool or skidl.config.tool
        this_module = sys.modules[__name__]
        this_module.__dict__.update(tool_modules[tool].constants.__dict__)

        random.seed(options.get("seed"))

        # Store the starting attributes of the node's parts, pins, and nets.
        node.attrs = node.get_attrs()

        try:
            # First, recursively place children of this node.
            # TODO: Child nodes are independent, so can they be processed in parallel?
            for child in node.children.values():
                child.place(tool=tool, **options)

            # Group parts into those that are connected by explicit nets and
            # those that float freely connected only by stub nets.
            connected_parts, internal_nets, floating_parts = node.group_parts(**options)

            # Place each group of connected parts.
            for group in connected_parts:
                node.place_connected_parts(list(group), internal_nets, **options)

            # Place the floating parts that have no connections to anything else.
            node.place_floating_parts(list(floating_parts), **options)

            # Now arrange all the blocks of placed parts and the child nodes within this node.
            node.place_blocks(
                connected_parts, floating_parts, node.children.values(), **options
            )

            # Remove any stuff leftover from this place & route run.
            # print(f"added part attrs = {new_part_attrs}")
            node.rmv_placement_stuff()
            # node.show_added_attrs()

            # Calculate the bounding box for the node after placement of parts and children.
            node.calc_bbox()

        except PlacementFailure:
            node.rmv_placement_stuff()
            raise PlacementFailure

    def get_snap_pt(node):
        """Get a Point to use for snapping the node to the grid.

        Args:
            node (Node): The Node to which the snapping point applies.

        Returns:
            Point: The snapping point or None.
        """

        if node.flattened:
            # Look for a snapping point based on one of its parts.
            for part in node.parts:
                snap_pt = get_snap_pt(part)
                if snap_pt:
                    return snap_pt

            # If no part snapping point, look for one in its children.
            for child in node.children.values():
                if child.flattened:
                    snap_pt = child.get_snap_pt()
                    if snap_pt:
                        # Apply the child transformation to its snapping point.
                        return snap_pt * child.tx

        # No snapping point if node is not flattened or no parts in it or its children.
        return None
