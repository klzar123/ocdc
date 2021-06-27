# Copyright (C) 2020 Luceda Photonics
# This version of Luceda Academy and related packages
# (hereafter referred to as Luceda Academy) is distributed under a proprietary License by Luceda
# It does allow you to develop and distribute add-ons or plug-ins, but does
# not allow redistribution of Luceda Academy  itself (in original or modified form).
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.
#
# For the details of the licensing contract and the conditions under which
# you may use this software, we refer to the
# EULA which was distributed along with this program.
# It is located in the root of the distribution folder.

from route_through_control_points import RouteManhattanControlPoints
import warnings
from ipkiss3 import all as i3
import numpy as np
from utils import get_bezier_ra, get_template, get_max_bend_radius, line, intersection, get_bend_size
from functools import partial
from utils import get_D_ports
from circuit.waveguides.tapered.waveguide import InterpolatedWaveguideTemplate
from ipkiss3.pcell.routing.base import _RouteProperties
# Fetching tech defaults
try:
    tech_bend_radius = i3.TECH.TRACE.BEND_RADIUS
except Exception:
    warnings.warn('No bend radius found defaulting to 20')
    tech_bend_radius = 20.0


def get_manhattan_routing_properties(bend_radius, start_straight, end_straight, min_straight,
                                     adiabatic_angle):

    """Helper function to calculates the routing parameters for manhattan routes"""

    rt_dict = dict()
    if bend_radius is not None:
        rt_dict["bend_radius"] = bend_radius
    if start_straight is not None:
        rt_dict["start_straight"] = start_straight
    if end_straight is not None:
        rt_dict["end_straight"] = end_straight
    if min_straight is not None:
        rt_dict["min_straight"] = min_straight
    if adiabatic_angle > 0.0:
        rt_dict["rounding_algorithm"] = get_bezier_ra(adiabatic_angle=adiabatic_angle)

    return _RouteProperties(**rt_dict)._get_routing_parameters()


# Routes
def route_sbend(start_port, end_port, bend_radius=tech_bend_radius):
    """It calculates an S-bend between two ports, it returns the route and the used bend radius.
    """
    points = []
    points.append(start_port.position)
    points.append(start_port.position.move_polar_copy(bend_radius, start_port.angle))
    points.append(end_port.position.move_polar_copy(bend_radius, end_port.angle))
    points.append(end_port.position)

    return i3.Shape(points)


def route_manhattan(start_port, end_port, bend_radius=tech_bend_radius, control_points=[],
                    adiabatic_angle=0.0, start_straight=None, end_straight=None,
                    min_straight=None):

    rt_dict = get_manhattan_routing_properties(bend_radius=bend_radius,
                                               start_straight=start_straight,
                                               end_straight=end_straight,
                                               min_straight=min_straight,
                                               adiabatic_angle=adiabatic_angle)

    return RouteManhattanControlPoints(input_port=start_port, output_port=end_port,
                                       control_points=control_points, **rt_dict)


def route_u(start_port, end_port, dists=None):
    if dists is None:
        dists = [start_port.position.distance(end_port.position) / 2.0] * 2
    route_u = [start_port.position,
               start_port.position.move_polar_copy(distance=dists[0], angle=start_port.angle),
               end_port.position.move_polar_copy(distance=dists[1], angle=end_port.angle),
               end_port.position]
    return i3.Shape(route_u)


def route_bend(start_port, end_port):
    L1 = line(start_port.position, start_port.position.move_polar_copy(100.0, start_port.angle))
    L2 = line(end_port.position.move_polar_copy(100.0, end_port.angle), end_port.position)
    n_normal = intersection(L1, L2)
    route = i3.Shape([start_port.position, n_normal, end_port.position])
    return route


# Shapes

def shape_bezier_sbend_max_radius(start_port, end_port, adiabatic_angle, min_bend_radius):
    """It returns a bezier S-bend shape with maximal bend radius. It raises a warning if the bend radius is too small.
    """
    norm_angle = end_port.angle - start_port.angle - 180.0
    if np.abs(np.abs(norm_angle) % 360.0 - 0.0) > 1e-8:
        raise Exception("Start and end port must have the same angle")

    end_pos_norm = i3.Coord2(end_port.position).transform_copy(
        i3.Rotation(rotation=-start_port.angle, rotation_center=start_port.position))
    L = np.abs(start_port.x - end_pos_norm.x)
    H = np.abs(start_port.y - end_pos_norm.y)
    a = H / L

    tetha = np.arctan2(2 * a / (a ** 2 + 1), (1 - a ** 2) / (a ** 2 + 1))
    if tetha > 0:
        d = H / (2 * np.sin(tetha))

        points = []
        points.append(start_port.position)
        points.append(start_port.position.move_polar_copy(d, start_port.angle))
        points.append(end_port.position.move_polar_copy(d, end_port.angle))
        points.append(end_port.position)

        route = i3.Shape(points)
        angle = route.angles_deg()[1] - route.angles_deg()[0]
        ra = get_bezier_ra(adiabatic_angle=adiabatic_angle)
        curv = 1 / get_max_bend_radius(rounding_algorithm=ra, dist=d, angle=angle)
        rounded_shape = ra(original_shape=route, radius=1 / curv)
    else:
        rounded_shape = i3.Shape([start_port, end_port])
        curv = 0.0

    if min_bend_radius is not None:
        if 1 / min_bend_radius < curv:
            warnings.warn("The SBend between {} and {} has a curvature {} that "
                          "is lower than the minimal allowed curvature {}".format(start_port.position,
                                                                                  end_port.position,
                                                                                  1 / curv,
                                                                                  min_bend_radius))
    return rounded_shape


def shape_bezier_bend_max_radius(start_port, end_port, adiabatic_angle, min_bend_radius=None):
    """It returns a bezier S-bend shape with maximal bend radius.
    It raises a warning if the calculated bend radius is smaller than min_bend_radius.
    """

    route = route_bend(start_port=start_port, end_port=end_port)
    D = get_D_ports(start_port=start_port, end_port=end_port)
    ra = get_bezier_ra(adiabatic_angle=adiabatic_angle)
    dist = min(route.distances()[0:-1])
    angle = route.angles_deg()[1]
    rang = route.angles_deg()
    angle = 360 + rang[1] - rang[0]
    if np.abs(D) > 1e-13:
        curv = 1 / get_max_bend_radius(rounding_algorithm=ra, dist=dist, angle=angle)
        rounded_shape = ra(original_shape=route,
                           radius=1 / curv)
    else:
        rounded_shape = i3.Shape([start_port, end_port])
        curv = 0.0

    if min_bend_radius is not None:
        if 1 / min_bend_radius < curv:
            warnings.warn("The Bend between {} and {} has a curvature {} "
                          "that is lower than the minimal allowed curvature {}".format(start_port.position,
                                                                                       end_port.position, 1 / curv,
                                                                                       min_bend_radius))
    return rounded_shape


def shape_bezier_bend_fixed_radius(start_port, end_port, adiabatic_angle, bend_radius):
    """It returns a bezier S-bend shape with a fixed bend radius.
    """
    route = route_bend(start_port=start_port, end_port=end_port)
    D = get_D_ports(start_port=start_port, end_port=end_port)
    ra = get_bezier_ra(adiabatic_angle=adiabatic_angle)
    dist = min(route.distances()[0:-1])
    angle = route.angles_deg()[1]
    rang = route.angles_deg()
    angle = 360 + rang[1] - rang[0]

    if np.abs(D) > 1e-13:
        curv = 1 / get_max_bend_radius(rounding_algorithm=ra, dist=dist, angle=angle)
        rounded_shape = ra(original_shape=route,
                           radius=bend_radius)
    else:
        rounded_shape = i3.Shape([start_port, end_port])
        curv = 0.0

    if 1 / bend_radius < curv:
        warnings.warn(
            "The Bend between {} and {} has maximal bend radius of {} that"
            " is lower than the desired bend radius {}".format(
                start_port.position,
                end_port.position,
                1 / curv,
                bend_radius))
    return rounded_shape


def get_min_bend_size_ubend_fixed_radius(start_port, end_port, bend_radius, adiabatic_angle):
    shape_for_angles = route_u(start_port=start_port, end_port=end_port, dists=[1.0, 1.0])
    ra = get_bezier_ra(adiabatic_angle=adiabatic_angle)
    angles = [np.abs(shape_for_angles.angles_deg()[cnt]) % 180.0 for cnt in [0, 2]]
    min_bend_sizes = [max(get_bend_size(rounding_algorithm=ra, bend_radius=bend_radius, angle=a)) for a in angles]
    return min_bend_sizes


def min_max_bezier_ubend_fixed_bend_radius(start_port, end_port, adiabatic_angle=45.0, bend_radius=100):
    min_bend_size = get_min_bend_size_ubend_fixed_radius(
        start_port=start_port, end_port=end_port, bend_radius=bend_radius, adiabatic_angle=adiabatic_angle)
    offset = 0.1
    d_route1 = np.array(route_u(start_port=start_port, end_port=end_port, dists=min_bend_size).distances())
    d_route2 = np.array(route_u(start_port=start_port, end_port=end_port,
                                dists=[a + offset for a in min_bend_size]).distances())
    m = (d_route2 - d_route1) / offset
    limits = [min_bend_size[0], 2 * min_bend_size[0], min_bend_size[0], min_bend_size[0]]
    offset_limits = [(limits[cnt] - d_route1[cnt]) / m[cnt] if m[cnt] != 0 else 0 for cnt in range(len(m))]
    offset_limit = offset_limits[1]
    min_max = [shape_ubend_fixed_bend_radius(start_port=start_port, end_port=end_port, bend_radius=bend_radius,
                                             adiabatic_angle=adiabatic_angle, extra_bend_length=o.length()) for
               o in [0, offset_limit * 0.99]]
    return min_max


def route_ubend_fixed_bend_radius(start_port, end_port, bend_radius, adiabatic_angle, extra_bend_length):
    min_bend_sizes = get_min_bend_size_ubend_fixed_radius(
        start_port=start_port, end_port=end_port, bend_radius=bend_radius, adiabatic_angle=adiabatic_angle)
    bend_sizes = [max(min_bend_sizes) + extra_bend_length] * 2
    route = route_u(start_port=start_port, end_port=end_port, dists=bend_sizes)
    if route.distances()[1] < 2 * min_bend_sizes[0]:
        import warnings
        warnings.warn("Not enough space for a ubend with this rounding algorithm... Returning a straight")
        return route_line(start_port=start_port, end_port=end_port)

    return route


def shape_ubend_fixed_bend_radius(start_port, end_port, bend_radius, adiabatic_angle=0.0, extra_bend_length=0.0):
    ra = get_bezier_ra(adiabatic_angle=adiabatic_angle)
    route = route_ubend_fixed_bend_radius(start_port=start_port, end_port=end_port, bend_radius=bend_radius,
                                          adiabatic_angle=adiabatic_angle,
                                          extra_bend_length=extra_bend_length)
    rounded_shape = ra(original_shape=route, radius=bend_radius)

    return rounded_shape


def shape_ubend_fixed_bend_radius_fixed_length(start_port, end_port, bend_radius, length, adiabatic_angle=0.0):
    delta = 0.01
    l1 = shape_ubend_fixed_bend_radius(start_port=start_port, end_port=end_port,
                                       bend_radius=bend_radius, adiabatic_angle=adiabatic_angle,
                                       extra_bend_length=0.0).length()
    l2 = shape_ubend_fixed_bend_radius(start_port=start_port, end_port=end_port, bend_radius=bend_radius,
                                       adiabatic_angle=adiabatic_angle, extra_bend_length=delta).length()
    d_target = delta * (length - l1) / (l2 - l1)
    rounded_shape = shape_ubend_fixed_bend_radius(
        start_port=start_port, end_port=end_port, bend_radius=bend_radius, adiabatic_angle=adiabatic_angle,
        extra_bend_length=d_target)

    if np.abs(rounded_shape.length() - length) > 0.01:
        import warnings
        warnings.warn(
            "Could not make a shape between {} and {} with length {}- returning straigth".format(start_port.position,
                                                                                                 end_port.position,
                                                                                                 length))
        return route_line(start_port=start_port, end_port=end_port)
    return rounded_shape


def shape_ubend_bend_max_radius(start_port, end_port, adiabatic_angle, min_bend_radius, shape=None):
    ra = get_bezier_ra(adiabatic_angle=adiabatic_angle)

    if shape is None:
        r_u = route_u(start_port, end_port)
        route = i3.Route(r_u, rounding_algorithm=ra)
    else:
        route = shape
        # Get bend_size
    dist = route[0].distance(route[-1])
    curv = 1 / get_max_bend_radius(rounding_algorithm=ra, dist=dist / 2.0, angle=90.0)
    rounded_shape = ra(original_shape=route, radius=1 / curv)

    if min_bend_radius is not None:
        if 1 / min_bend_radius < curv:
            warnings.warn(
                "The UBend between {} and {} has a curvature {}"
                " that is lower than the minimal allowed curvature {}".format(
                    start_port.position,
                    end_port.position,
                    1 / curv,
                    min_bend_radius))

    return rounded_shape


# Connectors
def straight(start_port, end_port, name=None, shape=None, **kwargs):
    """Straight waveguide between the start port and the end port.
    """
    trace_template = get_template(start_port, end_port)
    shape = i3.Shape([start_port, end_port])
    pcell_kwargs = {"trace_template": trace_template}
    layout_kwargs = {"shape": shape.points}

    if name is not None:
        pcell_kwargs["name"] = name
    wav = i3.Waveguide(**pcell_kwargs)
    wav.Layout(**layout_kwargs)
    return wav


# S-bend
def sbend(start_port, end_port, bend_radius=tech_bend_radius, name=None, shape=None, **kwargs):
    """S-bend between the start port and the end port with fixed bend radius.

    Parameters
    ----------
    start_port : i3.OpticalPort
    end_port : i3.OpticalPort
    bend_radius: float, optional
    name : str, optional
        Name of the connector cell
    shape : i3.Shape, optional
        Shape of the S-Bend

    Return
    -------
    wav : i3.RoundedWaveguide
        Waveguide connector between start and end ports
    """
    trace_template = get_template(start_port, end_port)

    if shape is None:
        shape = route_sbend(start_port=start_port, end_port=end_port, bend_radius=bend_radius)

    pcell_kwargs = {"trace_template": trace_template}
    layout_kwargs = {"shape": shape.points,
                     "bend_radius": bend_radius}

    if name is not None:
        pcell_kwargs["name"] = name
    wav = i3.RoundedWaveguide(**pcell_kwargs)
    wav.Layout(**layout_kwargs)
    return wav


def bezier_sbend(start_port, end_port, adiabatic_angle=15.0, name=None, min_bend_radius=None, **kwargs):
    """Bezier S-bend with a maximum bend radius. It uses an angular transition given by the adiabatic angle.

    Parameters
    ----------
    start_port : i3.OpticalPort
    end_port : i3.OpticalPort
    adiabatic_angle : float, optional
        adiabatic angle of the spline in the bend - 0.0 is circular.
    name : str, optional
        Name of the connector cell
    min_bend_radius : float, optional
        Minimum bend radius, a warning is raised if not fulfilled

    Return
    --------
    wav : i3.Waveguide
        Waveguide connector
    """
    rounded_shape = shape_bezier_sbend_max_radius(
        start_port=start_port, end_port=end_port, adiabatic_angle=adiabatic_angle, min_bend_radius=min_bend_radius)
    trace_template = get_template(start_port=start_port, end_port=end_port)

    pcell_kwargs = {"trace_template": trace_template}
    layout_kwargs = {"shape": rounded_shape.points}

    if name is not None:
        pcell_kwargs["name"] = name
    wav = i3.Waveguide(**pcell_kwargs)
    wav.Layout(**layout_kwargs)
    return wav


def bezier_sbend_tapered(start_port, end_port, adiabatic_angle=15.0,
                         name=None, min_bend_radius=None, **kwargs):
    """Bezier S-bend where the core adapts linearly from the start core width to the end core width.

    Parameters
    ----------
     start_port : i3.OpticalPort
     end_port : i3.OpticalPort
     adiabatic_angle : float, optional
        Adiabatic angle of the spline in the bend, 0 is circular.
     name: str, optional
        Name of the connector cell
     min_bend_radius: float, optional
        Minimum bend radius, a warning is raised if not fulfilled

    Return
    --------
    wav : i3.RoundedWaveguide
        Waveguide connector
    """
    rounded_shape = shape_bezier_sbend_max_radius(
        start_port=start_port, end_port=end_port, adiabatic_angle=adiabatic_angle, min_bend_radius=min_bend_radius)

    trace_template = InterpolatedWaveguideTemplate(trace_template_start=start_port.trace_template.cell,
                                                   trace_template_end=end_port.trace_template.cell)

    pcell_kwargs = {"trace_template": trace_template}
    layout_kwargs = {"shape": rounded_shape.points}

    if name is not None:
        pcell_kwargs["name"] = name
    wav = i3.RoundedWaveguide(**pcell_kwargs)
    lv = wav.Layout(**layout_kwargs)
    lv.ports = lv.contents.ports
    return wav


# U-bend
def bezier_ubend(start_port, end_port, adiabatic_angle=45.0, name=None,
                 shape=None, min_bend_radius=None, **kwargs):
    """Bezier U-bend between the start port and the end port with maximal bend radius.
    Both start port and and port need to be oriented in the same direction.

    Parameters
    ----------
    start_port : i3.OpticalPort
    end_port : i3.OpticalPort
    adiabatic_angle : float, optional
        Adiabatic angle of the spline in the bend, 0 is circular
    name : str, optional
        Name of the waveguide connector PCell
    shape: i3.Shape, optional
        Shape of the U-bend
    min_bend_radius : float, optional
        Minimum bend radius, a warning is raised if not fulfilled

    Return
    -------
    wav : i3.Waveguide
        Waveguide connector
    """
    trace_template = get_template(start_port=start_port, end_port=end_port)
    rounded_shape = shape_ubend_bend_max_radius(
        start_port=start_port, end_port=end_port, adiabatic_angle=adiabatic_angle, shape=shape,
        min_bend_radius=min_bend_radius)

    pcell_kwargs = {"trace_template": trace_template}
    layout_kwargs = {"shape": rounded_shape.points}

    if name is not None:
        pcell_kwargs["name"] = name
    wav = i3.Waveguide(**pcell_kwargs)
    wav.Layout(**layout_kwargs)
    return wav


def bezier_ubend_fixed_bend_radius(start_port, end_port, adiabatic_angle=45.0,
                                   bend_radius=100, length=None, name=None, **kwargs):
    """Bezier U-bend between the start port and the end port with a fixed bend radius.
    Both start port and and port need to be oriented in the same direction

    Parameters
    ----------
    start_port : i3.OpticalPort
    end_port : i3.OpticalPort
    adiabatic_angle : float, optional
        Adiabatic angle of the spline in the bend, 0 is circular
    bend_radius : float, optional
        Fixed bend radius of the U-bend
    length : float, optional
        Total length of the waveguide
    name : str, optional
        Name of the waveguide connector PCell

    Return
    -------
    wav : i3.Waveguide
        Waveguide connector PCell
    """
    trace_template = get_template(start_port=start_port, end_port=end_port)
    if length is None:
        rounded_shape = shape_ubend_fixed_bend_radius(start_port=start_port,
                                                      end_port=end_port, bend_radius=bend_radius,
                                                      adiabatic_angle=adiabatic_angle)
    else:
        rounded_shape = shape_ubend_fixed_bend_radius_fixed_length(start_port=start_port,
                                                                   end_port=end_port,
                                                                   bend_radius=bend_radius,
                                                                   length=length,
                                                                   adiabatic_angle=adiabatic_angle)

    pcell_kwargs = {"trace_template": trace_template}
    layout_kwargs = {"shape": rounded_shape.points}

    if name is not None:
        pcell_kwargs["name"] = name
    wav = i3.Waveguide(**pcell_kwargs)
    wav.Layout(**layout_kwargs)
    return wav


# Regular bend
def bezier_bend(start_port, end_port, adiabatic_angle=15.0, name=None, min_bend_radius=None, **kwargs):
    """Regular bend between start_port and end_port. Maximal bend radius is used.

    Parameters
    ----------
    start_port : i3.OpticalPort
    end_port : i3.OpticalPort
    adiabatic_angle : float, optional
        Adiabatic angle of the spline in the bend, 0 is circular
    name : str, optional
        Name of the waveguide connector PCell
    min_bend_radius : float, optional
        Minimum bend radius, a warning is raised if not fulfilled

    Return
    -------
    wav : i3.Waveguide
        Waveguide connector PCell
    """
    rounded_shape = shape_bezier_bend_max_radius(
        start_port=start_port, end_port=end_port, adiabatic_angle=adiabatic_angle, min_bend_radius=min_bend_radius)
    trace_template = get_template(start_port=start_port, end_port=end_port)
    pcell_kwargs = {"trace_template": trace_template}
    layout_kwargs = {"shape": rounded_shape.points}

    if name is not None:
        pcell_kwargs["name"] = name
    wav = i3.RoundedWaveguide(**pcell_kwargs)
    wav.Layout(**layout_kwargs)
    return wav


def bezier_bend_fixed_length(start_port, end_port, total_length=None, name=None,
                             min_bend_radius=None, **kwargs):
    """Bezier bend where the length is tuned by varying the adiabatic transition in the spline

    Parameters
    ----------
    start_port : i3.OpticalPort
    end_port : i3.OpticalPort
    total_length : float, optional
        Length of the bend
    name : str, optional
        Name of the waveguide connector PCell
    min_bend_radius : float, optional
        Minimum bend radius, a warning is raised if not fulfilled

    Return
    -------
    wav : i3.Waveguide
        Waveguide connector PCell
    """
    shbezier = partial(shape_bezier_bend_max_radius, start_port=start_port, end_port=end_port, min_bend_radius=None)
    [min_length, max_length] = [shbezier(adiabatic_angle=a).length() for a in [0, 45]]
    print(min_length, total_length, max_length)
    if total_length >= min_length and total_length <= max_length:
        def tominimize(x):
            return np.abs(shbezier(adiabatic_angle=x[0]).length() - total_length)

        from scipy.optimize import minimize
        res = minimize(tominimize, x0=[0.1], bounds=[(0, 45)])
        return bezier_bend(start_port=start_port, end_port=end_port, name=name,
                           adiabatic_angle=res.x[0], min_bend_radius=min_bend_radius)
    else:
        import warnings
        warnings.warn(
            "Could not make the length {} - the length has to be between {} and {}".format(total_length, min_length,
                                                                                           max_length))
        return straight(start_port=start_port, end_port=end_port, name=name)


# Manhattan
def manhattan(start_port, end_port, name=None, bend_radius=tech_bend_radius, control_points=[],
              adiabatic_angle=0.0, start_straight=None, end_straight=None,
              min_straight=None,
              shape=None,  **kwargs):
    """Regular manhattan connector

    Parameters
    ----------
    start_port : i3.OpticalPort
    end_port : i3.OpticalPort
    name : str, optional
        Name of the waveguide connector PCell
    bend_radius : float, optional
    control_points: list of floats, optional
        List of control points through which the route has to pass
    start_straight: float, optional,
       Minimum straight length at the start_port before the first bend
    end_straight: float, optional
       Minimum straight length at the end_port before the first bend
    min_straight: float, optional
       Minimum straight length  for all straight sections in the route
    adiabatic_angle : float, optional
      Adiabatic angle of the spline in the bend
    shape: i3.Shape, optional
        Shape of the bend

    Return
    -------
    wav : i3.Waveguide
        Waveguide connector PCell
    """

    trace_template = get_template(start_port, end_port)

    if shape is None:
        shape = route_manhattan(start_port=start_port, end_port=end_port,
                                bend_radius=bend_radius, control_points=control_points,
                                start_straight=start_straight, end_straight=end_straight,
                                min_straight=min_straight, adiabatic_angle=adiabatic_angle)

    pcell_kwargs = {"trace_template": trace_template}
    layout_kwargs = {"shape": shape.points,
                     "bend_radius": bend_radius,
                     "rounding_algorithm": shape.rounding_algorithm}
    if name is not None:
        pcell_kwargs["name"] = name

    wav = i3.RoundedWaveguide(**pcell_kwargs)
    wav.Layout(**layout_kwargs)

    return wav


def manhattan_offset(start_port, end_port, name=None, offset=0.2,
                     control_points=[], bend_radius=tech_bend_radius,
                     start_straight=None, end_straight=None,
                     min_straight=None,
                     shape=None, **kwargs):
    """Manhattan connector with offset waveguides.

    Parameters
    ----------
    start_port : i3.OpticalPort
    end_port : i3.OpticalPort
    name : str, optional
        Name of the waveguide connector PCell
    offset : float, optional
        Offset between the bend and the straight part of the waveguide
    control_points: list of floats, optional
        List of control points through which the route has to pass
    bend_radius : float, optional
        Radius of the bend
    start_straight: float, optional,
       Minimum straight length at the start_port before the first bend
    end_straight: float, optional
       Minimum straight length at the end_port before the first bend
    min_straight: float, optional
       Minimum straight length for all straight sections in the route
    shape: i3.Shape, optional
        Shape of the bend

    Return
    -------
    wav : i3.Waveguide
        Waveguide connector PCell
    """

    trace_template = get_template(start_port, end_port)

    if shape is None:
        shape = route_manhattan(start_port=start_port, end_port=end_port,
                                bend_radius=bend_radius, control_points=control_points,
                                start_straight=start_straight, end_straight=end_straight,
                                min_straight=min_straight)

    from offset_bends.waveguide import RoundedWaveguideOffset

    pcell_kwargs = {"trace_template": trace_template,
                    "route": shape,
                    "bend_radius": bend_radius,
                    "offset": offset
                    }

    if name is not None:
        pcell_kwargs["name"] = name
    wav = RoundedWaveguideOffset(**pcell_kwargs)
    return wav


def manhattan_fixed_bend(start_port, end_port, taper_length=10.0, width_wide=3.0, bend_cell=None, name=None,
                         control_points=[],
                         start_straight=None, end_straight=None,
                         min_straight=None,
                         shape=None, **kwargs):
    """Manhattan connector with a fixed bend PCell.

    Parameters
    ----------
    start_port : i3.OpticalPort
    end_port : i3.OpticalPort
    taper_length : float, optional
        Length of the tapered transition between the bend and the waveguide
    width_wide : float, optional
        Width of the wide section of the waveguide
    bend_cell : i3.PCell, optional
        Bend PCell
    name : str, optional
        Name of the waveguide connector PCell
    control_points : list of floats, optional
        List of control points through which the route has to pass
    start_straight: float, optional,
       Minimum straight length at the start_port before the first bend
    end_straight: float, optional
       Minimum straight length at the end_port before the first bend
    min_straight: float, optional
       Minimum straight length for all straight sections in the route
    shape : i3.Shape, optional
        Shape of the bend

    Return
    -------
    wav : i3.Waveguide
        Waveguide connector PCell
    """

    tt = get_template(start_port=start_port, end_port=end_port)

    if bend_cell is None:
        bend_cell = i3.RoundedWaveguide(trace_template=tt, name=name + "_bend")
        bend_cell.Layout(shape=[(0.0, 0.0), (5.0, 0.0), (5.0, 5.0)], bend_radius=5.0)

    if shape is None:
        route = route_manhattan(start_port=start_port, end_port=end_port,
                                bend_radius=bend_cell.get_default_view(i3.LayoutView).bend_radius,
                                start_straight=start_straight, end_straight=end_straight,
                                min_straight=min_straight,
                                control_points=control_points)
    from fixed_bend.fixed_bend import FixedBendWaveguide

    pcell_kwargs = {"bend": bend_cell,
                    "route": route,
                    "taper_length": taper_length,
                    "width_wide": width_wide
                    }

    if name is not None:
        pcell_kwargs["name"] = name
    wav = FixedBendWaveguide(**pcell_kwargs)
    return wav


def wide_manhattan(start_port, end_port, name=None,
                   shape=None, bend_radius=tech_bend_radius, taper_length=10.0,
                   adiabatic_angle=0.0, start_straight=None, end_straight=None,
                   min_straight=None,
                   width_wide=3.0, control_points=[]):
    """Manhattan waveguide with wide straight sections.

    Parameters
    ----------
    start_port : i3.OpticalPort
    end_port : i3.OpticalPort
    name : str, optional
        Name of the waveguide connector PCell
    shape : i3.Shape, optional
        Shape to override the control points
    bend_radius : float, optional
        Fixed radius of the bend
    taper_length : float, optional
        Length of the tapered transition between the bend and the waveguide
    width_wide : float, optional
        Width of the wide section of the waveguide
    control_points: list of floats, optional
        List of control points through which the route has to pass
    start_straight: float, optional,
       minimum  straight length at the start_port before the first bend
    end_straight: float, optional
       minimum  straight length at the end_port before the first bend
    min_straight: float, optional
       minimum straight length  for all straight sections in the route
    adiabatic_angle : float, optional
       Adiabatic angle of the spline in the bend, 0 is circular

    Return
    -------
    wav : i3.Waveguide
        Waveguide connector PCell
    """
    trace_template = get_template(start_port, end_port)

    if shape is None:
        shape = route_manhattan(start_port=start_port, end_port=end_port,
                                bend_radius=bend_radius, control_points=control_points,
                                start_straight=start_straight, end_straight=end_straight,
                                min_straight=min_straight, adiabatic_angle=adiabatic_angle)

    pcell_kwargs = {"trace_template": trace_template}
    layout_kwargs = {"shape": shape,
                     "narrow_width": trace_template.core_width,
                     "expanded_width": width_wide,
                     "taper_length": taper_length,
                     "expanded_layer": trace_template.core_layer,
                     "bend_radius": bend_radius,
                     "rounding_algorithm": shape.rounding_algorithm}

    if name is not None:
        pcell_kwargs["name"] = name

    import warnings
    with warnings.catch_warnings():
        # LA issue #180.
        warnings.simplefilter('ignore', category=DeprecationWarning)

        wav = i3.ExpandedWaveguide(**pcell_kwargs)
        wav.Layout(**layout_kwargs)

        return wav


# EDA bends
def route_line(start_port, end_port):
    return i3.Shape([start_port, end_port])


eda_bends = [("BEZ_S", route_line, bezier_sbend), ("BEZ_B", route_line, bezier_bend),
             ("BEZ_U", route_u, bezier_ubend), ("SB", route_sbend, sbend)]
