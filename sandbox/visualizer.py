from lxml import etree
from typing import List
import datamodel
import uuid
from collections import defaultdict


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

def create_drawio_mxfile():
    mxfile = etree.Element('mxfile')
    mxfile.set('type', 'device')
    mxfile.set('version', '14.7.6')
    return mxfile

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

def add_components_to_drawio_xml(drawio_xml, components):
    component_positions = {}
    row = 1
    col = 1

    for component in components:
        shape = add_shape(
            drawio_xml,
            component.name,
            col * 200,
            row * 100,
            100,
            50,
            'accent_color_1'
        )
        component_positions[component.id] = shape
        row += 1
        if row > 3:
            row = 1
            col += 1

    return component_positions

def build_connections(components):
    connections = defaultdict(set)
    for component in components:
        for feature in component.features:
            for connected_feature in feature.connections:
                connections[(component.id, feature.name)].add((connected_feature._parent.id, connected_feature.name))

    return connections

def draw_connections(drawio_xml, component_positions, connections):
    processed_connections = set()
    for (component_id, feature_name), connected_component_feature_ids_names in connections.items():
        source_shape = component_positions[component_id]

        for connected_component_id, connected_feature_name in connected_component_feature_ids_names:
            connection_tuple = (component_id, feature_name, connected_component_id, connected_feature_name)
            reverse_connection_tuple = (connected_component_id, connected_feature_name, component_id, feature_name)
            if connection_tuple not in processed_connections and reverse_connection_tuple not in processed_connections:
                target_shape = component_positions[connected_component_id]

                add_connector(
                    drawio_xml,
                    source_shape,
                    target_shape,
                    f"{feature_name} - {connected_feature_name}"
                )
                processed_connections.add(connection_tuple)
                processed_connections.add(reverse_connection_tuple)

def visualize_circuit(components):
    drawio_xml = create_drawio_xml()
    component_positions = add_components_to_drawio_xml(drawio_xml, components)
    connections = build_connections(components)
    draw_connections(drawio_xml, component_positions, connections)

    return drawio_xml

def save_drawio_xml(diagram, filename):
    with open(filename, 'wb') as f:
        f.write(etree.tostring(diagram, pretty_print=True, encoding='utf-8'))

