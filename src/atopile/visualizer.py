from lxml import etree
from typing import List
import datamodel

def create_drawio_xml():
    root = etree.Element('mxGraphModel')
    root.set('dx', '1190')
    root.set('dy', '757')
    root.set('grid', '1')
    root.set('gridSize', '10')
    root.set('guides', '1')
    root.set('tooltips', '1')
    root.set('connect', '1')
    root.set('arrows', '1')
    root.set('fold', '1')
    root.set('page', '1')
    root.set('pageScale', '1')
    root.set('pageWidth', '850')
    root.set('pageHeight', '1100')
    root.set('background', '#ffffff')

    root_element = etree.Element('root')
    root.append(root_element)

    root_mxcell = etree.SubElement(root_element, 'mxCell')
    root_mxcell.set('id', '0')
    
    layer_mxcell = etree.SubElement(root_element, 'mxCell')
    layer_mxcell.set('id', '1')
    layer_mxcell.set('parent', '0')

    return root



import uuid

def create_drawio_mxfile():
    mxfile = etree.Element('mxfile')
    mxfile.set('type', 'device')
    mxfile.set('version', '14.7.6')
    return mxfile


color_names = {
    'primary_background': '#F5F5F5',  # Light Gray
    'secondary_background': '#FFFFFF',  # White
    'primary_text': '#333333',  # Dark Gray
    'secondary_text': '#666666',  # Medium Gray
    'accent_color_1': '#2E9CCA',  # Light Blue
    'accent_color_2': '#F57C00',  # Orange
    'accent_color_3': '#69AA35',  # Green
    # Add more colors as needed
}

def add_shape(root, label, x, y, width, height, fill_color_name, style='rounded=1;shape=rectangle;whiteSpace=wrap;html=1;'):
    fill_color = color_names.get(fill_color_name.lower(), fill_color_name)
    shape = etree.SubElement(root.find('root'), 'mxCell')
    shape.set('id', str(uuid.uuid4()))
    shape.set('value', label)
    shape.set('style', f"{style}fillColor={fill_color};")
    shape.set('vertex', '1')
    shape.set('parent', '1')

    geometry = etree.SubElement(shape, 'mxGeometry')
    geometry.set('x', str(x))
    geometry.set('y', str(y))
    geometry.set('width', str(width))
    geometry.set('height', str(height))
    geometry.set('as', 'geometry')

    return shape


# <mxCell id="2" value="" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#C0C0C0;" vertex="1" parent="1">
#       <mxGeometry x="10" y="10" width="100" height="50" as="geometry"/>
#     </mxCell>


def add_connector(root, source, target, label, style='edgeStyle=entityRelationEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#000000;'):
    connector = etree.SubElement(root.find('root'), 'mxCell')
    connector.set('style', style)
    connector.set('value', label)
    connector.set('edge', '1')
    connector.set('parent', '1')
    connector.set('source', source.get('id'))
    connector.set('target', target.get('id'))

    geometry = etree.SubElement(connector, 'mxGeometry')
    geometry.set('relative', '1')
    geometry.set('as', 'geometry')

    return connector

from collections import defaultdict

def visualize_circuit(components, features):
    diagram = create_drawio_xml()

    x, y = 50, 50
    component_positions = {}

    for component in components:
        component_positions[component.name] = (x, y)
        add_shape(diagram, component.name, x, y, 100, 50, 'primary_background')
        x += 150

    # Iterate over features
    for feature in features:
        for component_feature in feature.features:
            component = component_feature.component
            for pin in component_feature.pins:
                for connected_pin in pin.connected_pins:
                    connected_component = connected_pin.component
                    if connected_component != component:
                        add_connector(
                            root = diagram,
                            source = component_positions[component.name],
                            target = component_positions[connected_component.name],
                            label = f"{component.name}.{pin.name} -> {connected_component.name}.{connected_pin.name}"
                        )

    return diagram
 



# diagram = create_drawio_xml()

# esp32 = add_shape(diagram, 'ESP32', 50, 50, 100, 50, 'primary_background')
# bms_ic = add_shape(diagram, 'BMS IC', 200, 50, 100, 50, 'primary_background')
# power_supply = add_shape(diagram, 'Power Supply\n(12V to 3.3V)', 50, 150, 100, 50, 'primary_background')
# usb_interface = add_shape(diagram, 'USB Interface', 200, 150, 100, 50, 'primary_background')
# add_connector(diagram, esp32, "I2C" , bms_ic)
# add_connector(diagram, esp32, "3.3V", power_supply)
# add_connector(diagram, esp32, "USB" ,usb_interface)
# add_connector(diagram, power_supply, "3.3V", bms_ic)
# add_connector(diagram, power_supply, "5V", usb_interface)


def save_drawio_xml(diagram, filename):
    with open(filename, 'wb') as f:
        f.write(etree.tostring(diagram, pretty_print=True, encoding='utf-8'))

# save_drawio_xml(diagram, 'example_diagram.drawio')

