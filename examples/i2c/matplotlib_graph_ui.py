#!/usr/bin/env python3
"""
Matplotlib-based graph visualizer for config_traits.py

This tool creates an interactive matplotlib visualization without requiring Tkinter,
making it more compatible across different Python environments.

Usage:
    uv run python matplotlib_graph_ui.py
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Set, List, Tuple, Any, Optional
from collections import defaultdict

try:
    import networkx as nx
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.widgets import Button, CheckButtons, TextBox
except ImportError as e:
    print(f"Required packages not found: {e}")
    print("Please ensure matplotlib and networkx are installed:")
    print("uv add matplotlib networkx")
    sys.exit(1)

# Add the project root to Python path to import config_traits
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from config_traits import top, graph
    from faebryk.core.node import Node
    from faebryk.core.parameter import Parameter
    from faebryk.core.graphinterface import GraphInterface
except ImportError as e:
    print(f"Could not import faebryk modules: {e}")
    print("Make sure you're running this from the correct directory with: uv run python matplotlib_graph_ui.py")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MatplotlibGraphUI:
    """Interactive matplotlib-based graph visualizer for faebryk nodes"""
    
    def __init__(self):
        # Initialize data structures
        self.nx_graph = nx.DiGraph()
        self.node_info = {}
        self.filtered_graph = nx.DiGraph()
        self.node_positions = {}
        self.selected_node = None
        
        # UI state
        self.show_traits = True
        self.show_parameters = True
        self.show_graphinterfaces = True
        self.current_layout = "spring"
        self.search_text = ""
        
        # Colors for different node types
        self.node_colors = {
            'Top': '#3498db',        # Blue
            'Trait': '#e74c3c',      # Red
            'Version': '#2ecc71',    # Green
            'Dependency': '#f39c12', # Orange
            'Parameter': '#9b59b6',  # Purple
            'Author': '#1abc9c',     # Turquoise
            'GraphInterface': '#e67e22',  # Dark orange
            'GraphInterfaceHierarchical': '#ff9f43',  # Light orange
            'GraphInterfaceSelf': '#feca57',          # Yellow orange
            'GraphInterfaceReference': '#48dbfb',     # Light blue
            'default': '#95a5a6'     # Gray
        }
        
        logger.info("Matplotlib Graph UI initialized")
    
    def analyze_graph(self):
        """Analyze the faebryk graph and extract structure including GraphInterface nodes"""
        logger.info("Starting graph analysis...")
        
        self.nx_graph.clear()
        self.node_info.clear()
        
        # Get all GraphInterface objects
        try:
            gifs = list(graph.get_gifs())
            logger.debug(f"Found {len(gifs)} GraphInterface objects")
            
            # Extract unique nodes from GraphInterfaces
            unique_nodes = {}
            gif_to_node = {}
            node_to_gifs = {}
            
            for gif in gifs:
                try:
                    node = gif.node
                    node_id = id(node)
                    gif_to_node[gif] = node
                    
                    if node_id not in unique_nodes:
                        unique_nodes[node_id] = node
                        node_to_gifs[node_id] = []
                    node_to_gifs[node_id].append(gif)
                    
                except Exception as e:
                    logger.debug(f"Could not get node from GIF {gif}: {e}")
            
            nodes = list(unique_nodes.values())
            logger.debug(f"Extracted {len(nodes)} unique nodes")
            
        except Exception as e:
            logger.error(f"Could not get nodes from graph: {e}")
            return
        
        if not nodes:
            logger.warning("No nodes found in graph")
            return
        
        node_names = {}  # Map from node id to display name
        gif_names = {}   # Map from gif id to display name
        
        # First pass: Add all nodes (both regular nodes and GraphInterface nodes)
        node_index = 0
        
        # Add regular nodes
        for node in nodes:
            node_id = id(node)
            node_type = type(node).__name__
            
            # Create a display name
            display_name = self.create_display_name(node, node_type, node_index)
            node_names[node_id] = display_name
            
            # Get GraphInterfaces for this node
            node_gifs = node_to_gifs.get(node_id, [])
            gif_info = []
            for gif in node_gifs:
                gif_info.append({
                    'name': gif.name,
                    'type': type(gif).__name__,
                    'gif_object': gif
                })
            
            # Collect detailed node information
            info = {
                'object': node,
                'type': node_type,
                'id': node_id,
                'index': node_index,
                'display_name': display_name,
                'attributes': self.extract_node_attributes(node),
                'methods': self.extract_node_methods(node),
                'children': [],
                'traits': [],
                'graphinterfaces': gif_info,
                'module': type(node).__module__,
                'mro': [cls.__name__ for cls in type(node).__mro__],
                'is_gif': False
            }
            
            self.node_info[display_name] = info
            self.nx_graph.add_node(display_name, **{
                'type': node_type,
                'node_id': node_id,
                'info': info,
                'gif_count': len(gif_info),
                'is_gif': False
            })
            node_index += 1
        
        # Add GraphInterface nodes
        gif_index = 0
        for gif in gifs:
            gif_id = id(gif)
            gif_type = type(gif).__name__
            
            # Create a display name for the GraphInterface
            owner_node = gif_to_node.get(gif)
            owner_name = node_names.get(id(owner_node)) if owner_node else "Unknown"
            # Make each GraphInterface unique by including owner info
            gif_display_name = f"[{gif.name}] {owner_name} ({gif_type})"
            gif_names[gif_id] = gif_display_name
            
            # Collect GraphInterface information
            gif_info = {
                'object': gif,
                'type': gif_type,
                'id': gif_id,
                'index': gif_index,
                'display_name': gif_display_name,
                'gif_name': gif.name,
                'owner_node': owner_node,
                'owner_name': owner_name,
                'attributes': self.extract_gif_attributes(gif),
                'methods': self.extract_node_methods(gif),
                'children': [],
                'traits': [],
                'graphinterfaces': [],
                'module': type(gif).__module__,
                'mro': [cls.__name__ for cls in type(gif).__mro__],
                'is_gif': True
            }
            
            self.node_info[gif_display_name] = gif_info
            self.nx_graph.add_node(gif_display_name, **{
                'type': gif_type,
                'node_id': gif_id,
                'info': gif_info,
                'is_gif': True,
                'owner_node_name': owner_name
            })
            gif_index += 1
        
        # Second pass: Add node-to-GraphInterface connections
        for node in nodes:
            node_id = id(node)
            node_name = node_names.get(node_id)
            if not node_name:
                continue
                
            node_gifs = node_to_gifs.get(node_id, [])
            for gif in node_gifs:
                gif_id = id(gif)
                gif_name = gif_names.get(gif_id)
                if gif_name:
                    # Connect node to its GraphInterface
                    self.nx_graph.add_edge(node_name, gif_name, **{
                        'relationship': 'owns_gif',
                        'color': '#34495e'  # Dark gray
                    })
        
        # Third pass: Add GraphInterface-to-GraphInterface connections
        gif_edge_count = 0
        for gif in gifs:
            try:
                gif_edges = gif.get_gif_edges()
                source_gif_id = id(gif)
                source_gif_name = gif_names.get(source_gif_id)
                
                if not source_gif_name:
                    continue
                
                for connected_gif in gif_edges:
                    target_gif_id = id(connected_gif)
                    target_gif_name = gif_names.get(target_gif_id)
                    
                    if target_gif_name and source_gif_name != target_gif_name:
                        # Create edge between GraphInterfaces
                        if not self.nx_graph.has_edge(source_gif_name, target_gif_name):
                            self.nx_graph.add_edge(source_gif_name, target_gif_name, **{
                                'relationship': 'gif_connection',
                                'source_gif': gif.name,
                                'target_gif': connected_gif.name,
                                'source_gif_type': type(gif).__name__,
                                'target_gif_type': type(connected_gif).__name__,
                                'color': '#2980b9'  # Blue
                            })
                            gif_edge_count += 1
                
            except Exception as e:
                logger.debug(f"Error processing GIF connections for {gif}: {e}")
        
        # Fourth pass: Add traditional relationships (children, traits, etc.)
        for node in nodes:
            self.analyze_node_relationships(node, node_names)
        
        total_nodes = len(nodes) + len(gifs)
        logger.info(f"Graph analysis complete: {total_nodes} total nodes ({len(nodes)} regular, {len(gifs)} GraphInterface), {self.nx_graph.number_of_edges()} edges ({gif_edge_count} GIF-to-GIF connections)")
        
        # Create initial filtered graph
        self.apply_filters()
    
    def create_display_name(self, node: Any, node_type: str, index: int) -> str:
        """Create a display name for a node"""
        # Try various name attributes
        name_attrs = ['name', '_name', 'id', '_id', 'identifier']
        
        for attr in name_attrs:
            if hasattr(node, attr):
                try:
                    name_val = getattr(node, attr)
                    if name_val and str(name_val) not in ['None', '']:
                        return f"{name_val} ({node_type})"
                except:
                    continue
        
        return f"{node_type}_{index}"
    
    def extract_node_attributes(self, node: Any) -> Dict[str, str]:
        """Extract interesting attributes from a node"""
        attributes = {}
        
        for attr_name in dir(node):
            if attr_name.startswith('_'):
                continue
                
            try:
                attr_value = getattr(node, attr_name)
                if callable(attr_value):
                    continue
                    
                attr_str = str(attr_value)
                if len(attr_str) < 200:  # Only include reasonably short attributes
                    attributes[attr_name] = attr_str
                    
            except Exception:
                continue
                
        return attributes
    
    def extract_node_methods(self, node: Any) -> List[str]:
        """Extract public methods from a node"""
        methods = []
        
        for attr_name in dir(node):
            if attr_name.startswith('_'):
                continue
                
            try:
                attr_value = getattr(node, attr_name)
                if callable(attr_value):
                    methods.append(attr_name)
            except Exception:
                continue
                
        return methods
    
    def extract_gif_attributes(self, gif: Any) -> Dict[str, str]:
        """Extract interesting attributes from a GraphInterface"""
        attributes = {}
        
        # Add standard GIF attributes
        try:
            attributes['name'] = str(gif.name)
        except:
            pass
            
        try:
            attributes['node'] = str(gif.node)
        except:
            pass
            
        # Get other attributes
        for attr_name in dir(gif):
            if attr_name.startswith('_') or attr_name in ['name', 'node']:
                continue
                
            try:
                attr_value = getattr(gif, attr_name)
                if callable(attr_value):
                    continue
                    
                attr_str = str(attr_value)
                if len(attr_str) < 200:  # Only include reasonably short attributes
                    attributes[attr_name] = attr_str
                    
            except Exception:
                continue
                
        return attributes
    
    def analyze_node_relationships(self, node: Any, node_names: Dict):
        """Analyze relationships for a single node"""
        node_id = id(node)
        parent_name = node_names.get(node_id)
        
        if not parent_name:
            return
        
        parent_info = self.node_info[parent_name]
        
        # Children relationships
        if hasattr(node, 'get_children'):
            try:
                children = list(node.get_children())
                for child in children:
                    child_id = id(child)
                    child_name = node_names.get(child_id)
                    if child_name:
                        self.nx_graph.add_edge(parent_name, child_name, 
                                             relationship="contains", color="blue")
                        parent_info['children'].append(child_name)
            except Exception as e:
                logger.debug(f"Could not get children for {parent_name}: {e}")
        
        # Trait relationships
        if hasattr(node, 'get_traits'):
            try:
                traits = list(node.get_traits())
                for trait in traits:
                    trait_name = f"[TRAIT] {type(trait).__name__}"
                    if trait_name not in self.nx_graph:
                        trait_info = {
                            'object': trait,
                            'type': 'Trait',
                            'id': id(trait),
                            'display_name': trait_name,
                            'attributes': self.extract_node_attributes(trait),
                            'methods': self.extract_node_methods(trait),
                            'children': [],
                            'traits': [],
                            'module': type(trait).__module__,
                            'mro': [cls.__name__ for cls in type(trait).__mro__]
                        }
                        self.node_info[trait_name] = trait_info
                        self.nx_graph.add_node(trait_name, **{
                            'type': 'Trait',
                            'node_id': id(trait),
                            'info': trait_info
                        })
                    
                    self.nx_graph.add_edge(parent_name, trait_name, 
                                         relationship="has_trait", color="red")
                    parent_info['traits'].append(trait_name)
            except Exception as e:
                logger.debug(f"Could not get traits for {parent_name}: {e}")
    
    def apply_filters(self):
        """Apply current filters to create filtered graph"""
        self.filtered_graph.clear()
        
        for node, data in self.nx_graph.nodes(data=True):
            node_type = data.get('type', '')
            is_gif = data.get('is_gif', False)
            
            # Apply filters
            if not self.show_traits and ('Trait' in node_type or '[TRAIT]' in node):
                continue
            
            if not self.show_parameters and 'Parameter' in node_type:
                continue
                
            if not self.show_graphinterfaces and is_gif:
                continue
            
            # Apply search filter
            if self.search_text and self.search_text.lower() not in node.lower():
                continue
            
            self.filtered_graph.add_node(node, **data)
        
        # Add edges between remaining nodes
        for u, v, data in self.nx_graph.edges(data=True):
            if u in self.filtered_graph and v in self.filtered_graph:
                self.filtered_graph.add_edge(u, v, **data)
    
    def calculate_layout(self):
        """Calculate node positions with GraphInterface clustering"""
        if self.filtered_graph.number_of_nodes() == 0:
            return {}
        
        try:
            # Create a custom layout that groups GraphInterfaces around their owner nodes
            pos = self.create_clustered_layout()
            self.node_positions = pos
            return pos
        except Exception as e:
            logger.warning(f"Layout calculation failed: {e}, using fallback spring layout")
            pos = nx.spring_layout(self.filtered_graph, seed=42)
            self.node_positions = pos
            return pos
    
    def create_clustered_layout(self):
        """Create a layout where GraphInterfaces are clustered around their owner nodes"""
        import math
        
        # Separate nodes by type
        regular_nodes = []
        gif_nodes = []
        node_to_gifs = {}
        
        for node in self.filtered_graph.nodes():
            node_data = self.filtered_graph.nodes[node]
            is_gif = node_data.get('is_gif', False)
            
            if is_gif:
                gif_nodes.append(node)
                # Find the owner node for this GraphInterface
                owner_name = node_data.get('owner_node_name', 'Unknown')
                if owner_name not in node_to_gifs:
                    node_to_gifs[owner_name] = []
                node_to_gifs[owner_name].append(node)
            else:
                regular_nodes.append(node)
                if node not in node_to_gifs:
                    node_to_gifs[node] = []
        
        # First, layout regular nodes using the selected algorithm
        if len(regular_nodes) > 0:
            regular_subgraph = self.filtered_graph.subgraph(regular_nodes)
            
            if self.current_layout == "spring":
                regular_pos = nx.spring_layout(regular_subgraph, k=3, iterations=50, seed=42)
            elif self.current_layout == "circular":
                regular_pos = nx.circular_layout(regular_subgraph)
            elif self.current_layout == "kamada_kawai":
                try:
                    regular_pos = nx.kamada_kawai_layout(regular_subgraph)
                except:
                    regular_pos = nx.spring_layout(regular_subgraph, seed=42)
            elif self.current_layout == "shell":
                regular_pos = nx.shell_layout(regular_subgraph)
            elif self.current_layout == "random":
                regular_pos = nx.random_layout(regular_subgraph, seed=42)
            else:
                regular_pos = nx.spring_layout(regular_subgraph, seed=42)
        else:
            regular_pos = {}
        
        # Now position GraphInterfaces around their owner nodes
        all_pos = regular_pos.copy()
        
        for owner_node, owned_gifs in node_to_gifs.items():
            if not owned_gifs:  # No GraphInterfaces for this node
                continue
                
            # Get the position of the owner node
            if owner_node in regular_pos:
                center_x, center_y = regular_pos[owner_node]
            else:
                # If owner not in filtered regular nodes, place at origin
                center_x, center_y = 0.0, 0.0
            
            # Calculate radius based on number of GraphInterfaces
            gif_count = len(owned_gifs)
            radius = 0.3 + (gif_count * 0.05)  # Adaptive radius
            
            # Place GraphInterfaces in a circle around the owner node
            for i, gif_node in enumerate(owned_gifs):
                angle = 2 * math.pi * i / gif_count
                gif_x = center_x + radius * math.cos(angle)
                gif_y = center_y + radius * math.sin(angle)
                all_pos[gif_node] = (gif_x, gif_y)
        
        return all_pos
    
    def draw_cluster_backgrounds(self, ax, pos):
        """Draw circular backgrounds around node clusters"""
        import matplotlib.patches as patches
        
        # Group nodes by their owner
        clusters = {}
        
        for node in self.filtered_graph.nodes():
            node_data = self.filtered_graph.nodes[node]
            is_gif = node_data.get('is_gif', False)
            
            if is_gif:
                # GraphInterface node - find its cluster
                owner_name = node_data.get('owner_node_name', 'Unknown')
                if owner_name not in clusters:
                    clusters[owner_name] = {'center': None, 'gifs': [], 'node': None}
                clusters[owner_name]['gifs'].append(node)
            else:
                # Regular node - this is a cluster center
                if node not in clusters:
                    clusters[node] = {'center': None, 'gifs': [], 'node': node}
                clusters[node]['node'] = node
                clusters[node]['center'] = pos.get(node, (0, 0))
        
        # Draw background circles for clusters that have GraphInterfaces
        for cluster_name, cluster_data in clusters.items():
            if len(cluster_data['gifs']) > 0 and cluster_data['center'] is not None:
                center_x, center_y = cluster_data['center']
                
                # Calculate radius based on GraphInterface positions
                gif_positions = [pos[gif] for gif in cluster_data['gifs'] if gif in pos]
                if len(gif_positions) > 0:
                    max_distance = 0
                    for gif_x, gif_y in gif_positions:
                        distance = ((gif_x - center_x) ** 2 + (gif_y - center_y) ** 2) ** 0.5
                        max_distance = max(max_distance, distance)
                    
                    # Add some padding
                    radius = max_distance + 0.15
                    
                    # Draw background circle
                    circle = patches.Circle((center_x, center_y), radius, 
                                          facecolor='lightgray', alpha=0.1, 
                                          edgecolor='gray', linewidth=1, linestyle='--')
                    ax.add_patch(circle)
    
    def get_node_visual_properties(self) -> Tuple[List[str], List[int]]:
        """Get colors and sizes for nodes"""
        node_colors = []
        node_sizes = []
        
        for node in self.filtered_graph.nodes():
            node_data = self.filtered_graph.nodes[node]
            node_type = node_data.get('type', 'Unknown')
            is_gif = node_data.get('is_gif', False)
            
            # Get base color and size
            if is_gif:
                # GraphInterface nodes - smaller and more distinct
                color = self.node_colors.get(node_type, self.node_colors['GraphInterface'])
                size = 200  # Smaller for GraphInterface nodes
            elif '[TRAIT]' in node:
                color = self.node_colors['Trait']
                size = 1000  # Larger for trait nodes
            else:
                # Regular nodes - these are cluster centers, make them prominent
                color = self.node_colors.get(node_type, self.node_colors['default'])
                size = 1500 if node_type == 'Top' else 1000  # Larger cluster centers
            
            # Highlight search matches
            if self.search_text and self.search_text.lower() in node.lower():
                color = '#ffdc00'  # Bright yellow
                size = int(size * 1.3)
            
            # Highlight selected node
            if self.selected_node == node:
                size = int(size * 1.5)
            
            node_colors.append(color)
            node_sizes.append(size)
        
        return node_colors, node_sizes
    
    def draw_graph(self, ax):
        """Draw the graph on the given axes"""
        ax.clear()
        
        if self.filtered_graph.number_of_nodes() == 0:
            ax.text(0.5, 0.5, 'No nodes to display\n\nAdjust filters or refresh',
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=14, color='gray')
            return
        
        # Calculate layout
        pos = self.calculate_layout()
        if not pos or len(pos) == 0:
            return
        
        # Get visual properties
        node_colors, node_sizes = self.get_node_visual_properties()
        
        # Draw cluster backgrounds first
        self.draw_cluster_backgrounds(ax, pos)
        
        # Draw edges with different colors for different relationship types
        edge_colors = []
        edge_styles = []
        for edge in self.filtered_graph.edges(data=True):
            edge_data = edge[2]
            relationship = edge_data.get('relationship', 'unknown')
            
            if relationship == 'gif_connection':
                edge_colors.append('#2980b9')  # Blue for GraphInterface connections
                edge_styles.append('-')  # Solid line
            elif relationship == 'owns_gif':
                edge_colors.append('#bdc3c7')  # Light gray for node-to-GraphInterface
                edge_styles.append('-')  # Solid line
            elif relationship == 'has_trait':
                edge_colors.append('#e74c3c')  # Red for traits
                edge_styles.append('--')  # Dashed line
            elif relationship == 'contains':
                edge_colors.append('#7f8c8d')  # Gray for contains
                edge_styles.append('-')  # Solid line
            else:
                edge_colors.append('#95a5a6')  # Light gray for other
                edge_styles.append(':')
        
        if self.filtered_graph.number_of_edges() > 0:
            # Draw edges in two passes - owns_gif edges first (more subtle)
            owns_gif_edges = []
            other_edges = []
            owns_gif_colors = []
            other_colors = []
            
            for i, (u, v, data) in enumerate(self.filtered_graph.edges(data=True)):
                relationship = data.get('relationship', 'unknown')
                if relationship == 'owns_gif':
                    owns_gif_edges.append((u, v))
                    owns_gif_colors.append(edge_colors[i])
                else:
                    other_edges.append((u, v))
                    other_colors.append(edge_colors[i])
            
            # Draw owns_gif edges with lower alpha (more subtle)
            if owns_gif_edges:
                nx.draw_networkx_edges(self.filtered_graph, pos, edgelist=owns_gif_edges, ax=ax,
                                      edge_color=owns_gif_colors, alpha=0.3, 
                                      arrows=True, arrowsize=10, arrowstyle='->')
            
            # Draw other edges with normal alpha
            if other_edges:
                nx.draw_networkx_edges(self.filtered_graph, pos, edgelist=other_edges, ax=ax,
                                      edge_color=other_colors, alpha=0.7, 
                                      arrows=True, arrowsize=15, arrowstyle='->')
        
        # Draw nodes
        nx.draw_networkx_nodes(self.filtered_graph, pos, ax=ax,
                              node_color=node_colors, node_size=node_sizes,
                              alpha=0.8)
        
        # Draw labels
        labels = {}
        for node in self.filtered_graph.nodes():
            if len(node) > 25:
                labels[node] = node[:22] + "..."
            else:
                labels[node] = node
        
        nx.draw_networkx_labels(self.filtered_graph, pos, labels, ax=ax,
                               font_size=8, font_weight='bold')
        
        # Styling
        ax.set_title(f"Faebryk Graph Structure ({self.current_layout} layout)", 
                    fontsize=14, fontweight='bold', pad=20)
        ax.axis('off')
        
        # Add legend
        from matplotlib.lines import Line2D
        
        # Node legend
        node_legend_elements = [
            mpatches.Patch(color=self.node_colors['Top'], label='Top Node'),
            mpatches.Patch(color=self.node_colors['Trait'], label='Trait'),
            mpatches.Patch(color=self.node_colors['Version'], label='Version'),
            mpatches.Patch(color=self.node_colors['Parameter'], label='Parameter'),
            mpatches.Patch(color=self.node_colors['Author'], label='Author'),
            mpatches.Patch(color=self.node_colors['GraphInterfaceHierarchical'], label='GIF Hierarchical'),
            mpatches.Patch(color=self.node_colors['GraphInterfaceSelf'], label='GIF Self'),
            mpatches.Patch(color=self.node_colors['GraphInterface'], label='GIF Other'),
        ]
        
        # Edge legend
        edge_legend_elements = [
            Line2D([0], [0], color='#2980b9', linewidth=2, label='GIF-to-GIF Connection'),
            Line2D([0], [0], color='#bdc3c7', linewidth=1, alpha=0.5, label='Node owns GIF'),
            Line2D([0], [0], color='#e74c3c', linewidth=2, linestyle='--', label='Has Trait'),
            Line2D([0], [0], color='#7f8c8d', linewidth=2, label='Contains'),
        ]
        
        # Combine legends
        all_legend_elements = node_legend_elements + edge_legend_elements
        
        ax.legend(handles=all_legend_elements, loc='upper left', 
                 frameon=True, fancybox=True, shadow=True, ncol=2)
    
    def print_node_details(self, node_name: str):
        """Print detailed information about a node"""
        if node_name not in self.node_info:
            print(f"Node '{node_name}' not found")
            return
        
        node_info = self.node_info[node_name]
        
        print("\n" + "=" * 80)
        print(f"NODE DETAILS: {node_name}")
        print("=" * 80)
        print(f"Type: {node_info['type']}")
        print(f"Module: {node_info['module']}")
        print(f"Object ID: {node_info['id']}")
        
        if node_info['mro']:
            print(f"Class hierarchy: {' -> '.join(node_info['mro'])}")
        
        # Show GraphInterfaces
        if node_info.get('graphinterfaces'):
            print(f"\nGraphInterfaces ({len(node_info['graphinterfaces'])}):")
            for gif_info in node_info['graphinterfaces']:
                print(f"  • {gif_info['name']} ({gif_info['type']})")
                
                # Show connections for this GIF
                try:
                    gif_obj = gif_info['gif_object']
                    gif_edges = gif_obj.get_gif_edges()
                    if gif_edges:
                        print(f"    Connected to {len(gif_edges)} other GraphInterfaces:")
                        for connected_gif in list(gif_edges)[:3]:  # Show first 3
                            print(f"      → {connected_gif.name} ({type(connected_gif).__name__})")
                        if len(gif_edges) > 3:
                            print(f"      ... and {len(gif_edges) - 3} more")
                except Exception as e:
                    print(f"    Error getting connections: {e}")
        
        # Show graph connections to other nodes
        if self.nx_graph.has_node(node_name):
            # Outgoing edges
            out_edges = list(self.nx_graph.out_edges(node_name, data=True))
            if out_edges:
                print(f"\nConnections to other nodes ({len(out_edges)}):")
                for source, target, edge_data in out_edges:
                    relationship = edge_data.get('relationship', 'unknown')
                    if relationship == 'gif_connection':
                        gif_info_str = f"{edge_data.get('source_gif', '?')} → {edge_data.get('target_gif', '?')}"
                        print(f"  → {target} (via GraphInterface: {gif_info_str})")
                    else:
                        print(f"  → {target} (relationship: {relationship})")
                    
                    # Show additional GIF connections if present
                    if 'gif_connections' in edge_data:
                        for gif_conn in edge_data['gif_connections'][:2]:  # Show first 2
                            print(f"      + {gif_conn['source_gif']} → {gif_conn['target_gif']}")
        
        if node_info['children']:
            print(f"\nChildren ({len(node_info['children'])}):")
            for child in sorted(node_info['children']):
                print(f"  → {child}")
        
        if node_info['traits']:
            print(f"\nTraits ({len(node_info['traits'])}):")
            for trait in sorted(node_info['traits']):
                print(f"  → {trait}")
        
        if node_info['methods']:
            print(f"\nMethods ({len(node_info['methods'])}):")
            methods = sorted(node_info['methods'])
            for i, method in enumerate(methods):
                if i > 0 and i % 6 == 0:
                    print()
                print(f"{method:<15}", end=" ")
            print()
        
        if node_info['attributes']:
            print(f"\nAttributes:")
            for attr_name, attr_value in sorted(node_info['attributes'].items()):
                if len(str(attr_value)) < 100:
                    print(f"  {attr_name}: {attr_value}")
        
        print("=" * 80)
    
    def create_interactive_plot(self):
        """Create an interactive matplotlib plot"""
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(16, 12))
        plt.subplots_adjust(left=0.3, bottom=0.1, right=0.95, top=0.9)
        
        # Create control panel
        control_ax = fig.add_axes([0.02, 0.5, 0.25, 0.4])
        control_ax.set_xlim(0, 1)
        control_ax.set_ylim(0, 1)
        control_ax.axis('off')
        
        # Add title
        control_ax.text(0.5, 0.95, 'Graph Controls', ha='center', fontsize=12, fontweight='bold')
        
        # Layout buttons
        layout_y = 0.85
        control_ax.text(0.05, layout_y, 'Layout:', fontsize=10, fontweight='bold')
        
        layouts = ['spring', 'circular', 'kamada_kawai', 'shell', 'random']
        layout_buttons = {}
        
        for i, layout in enumerate(layouts):
            button_ax = fig.add_axes([0.03 + (i % 3) * 0.08, 0.75 - (i // 3) * 0.05, 0.07, 0.04])
            button = Button(button_ax, layout[:6], color='lightblue' if layout == self.current_layout else 'white')
            
            def make_layout_callback(l):
                def callback(event):
                    self.current_layout = l
                    self.apply_filters()
                    self.draw_graph(ax)
                    plt.draw()
                    # Update button colors
                    for layout_name, btn in layout_buttons.items():
                        btn.color = 'lightblue' if layout_name == l else 'white'
                        btn.hovercolor = 'lightcyan' if layout_name == l else 'lightgray'
                return callback
            
            button.on_clicked(make_layout_callback(layout))
            layout_buttons[layout] = button
        
        # Filter checkboxes
        filter_y = 0.6
        control_ax.text(0.05, filter_y, 'Filters:', fontsize=10, fontweight='bold')
        
        # Traits checkbox
        traits_ax = fig.add_axes([0.03, 0.52, 0.2, 0.06])
        traits_check = CheckButtons(traits_ax, ['Show Traits'], [self.show_traits])
        
        def traits_callback(label):
            self.show_traits = not self.show_traits
            self.apply_filters()
            self.draw_graph(ax)
            plt.draw()
        
        traits_check.on_clicked(traits_callback)
        
        # Parameters checkbox
        params_ax = fig.add_axes([0.03, 0.45, 0.2, 0.06])
        params_check = CheckButtons(params_ax, ['Show Parameters'], [self.show_parameters])
        
        def params_callback(label):
            self.show_parameters = not self.show_parameters
            self.apply_filters()
            self.draw_graph(ax)
            plt.draw()
        
        params_check.on_clicked(params_callback)
        
        # GraphInterfaces checkbox
        gifs_ax = fig.add_axes([0.03, 0.38, 0.2, 0.06])
        gifs_check = CheckButtons(gifs_ax, ['Show GraphInterfaces'], [self.show_graphinterfaces])
        
        def gifs_callback(label):
            self.show_graphinterfaces = not self.show_graphinterfaces
            self.apply_filters()
            self.draw_graph(ax)
            plt.draw()
        
        gifs_check.on_clicked(gifs_callback)
        
        # Search box
        search_y = 0.28
        control_ax.text(0.05, search_y, 'Search:', fontsize=10, fontweight='bold')
        
        search_ax = fig.add_axes([0.03, 0.18, 0.2, 0.05])
        search_box = TextBox(search_ax, '', initial=self.search_text)
        
        def search_callback(text):
            self.search_text = text
            self.apply_filters()
            self.draw_graph(ax)
            plt.draw()
        
        search_box.on_text_change(search_callback)
        
        # Refresh button
        refresh_ax = fig.add_axes([0.03, 0.08, 0.1, 0.05])
        refresh_button = Button(refresh_ax, 'Refresh', color='lightgreen')
        
        def refresh_callback(event):
            self.analyze_graph()
            self.draw_graph(ax)
            plt.draw()
        
        refresh_button.on_clicked(refresh_callback)
        
        # Info display
        info_ax = fig.add_axes([0.02, 0.02, 0.25, 0.1])
        info_ax.axis('off')
        
        def update_info():
            total_nodes = self.nx_graph.number_of_nodes()
            filtered_nodes = self.filtered_graph.number_of_nodes()
            edges = self.filtered_graph.number_of_edges()
            info_ax.clear()
            info_ax.text(0.05, 0.8, f'Total nodes: {total_nodes}', fontsize=9)
            info_ax.text(0.05, 0.6, f'Shown nodes: {filtered_nodes}', fontsize=9)
            info_ax.text(0.05, 0.4, f'Edges: {edges}', fontsize=9)
            info_ax.text(0.05, 0.2, f'Layout: {self.current_layout}', fontsize=9)
            info_ax.axis('off')
        
        # Click handler for node selection
        def on_click(event):
            if event.inaxes == ax and self.node_positions:
                click_pos = (event.xdata, event.ydata)
                if click_pos[0] is None or click_pos[1] is None:
                    return
                
                min_distance = float('inf')
                closest_node = None
                
                for node, pos in self.node_positions.items():
                    distance = ((pos[0] - click_pos[0]) ** 2 + (pos[1] - click_pos[1]) ** 2) ** 0.5
                    if distance < min_distance:
                        min_distance = distance
                        closest_node = node
                
                if min_distance < 0.1:  # Threshold for selection
                    self.selected_node = closest_node
                    self.print_node_details(closest_node)
                    self.draw_graph(ax)
                    plt.draw()
        
        fig.canvas.mpl_connect('button_press_event', on_click)
        
        # Initial draw
        self.analyze_graph()
        self.draw_graph(ax)
        update_info()
        
        # Update info periodically
        def update_display():
            update_info()
            plt.draw()
        
        plt.show()
    
    def run(self):
        """Run the interactive visualization"""
        print("🚀 Starting Matplotlib Graph Visualizer...")
        print(f"📊 Graph object: {graph}")
        print(f"🔝 Top object: {top}")
        print(f"📁 Running from: {Path.cwd()}")
        print()
        
        try:
            self.create_interactive_plot()
        except Exception as e:
            logger.error(f"Error running visualizer: {e}")
            print(f"❌ Error: {e}")
            
            # Fallback: show basic information
            print("\n📊 Basic Graph Information:")
            try:
                self.analyze_graph()
                print(f"Total nodes: {self.nx_graph.number_of_nodes()}")
                print(f"Total edges: {self.nx_graph.number_of_edges()}")
                
                # Group nodes by type
                nodes_by_type = defaultdict(list)
                for node_name, node_info in self.node_info.items():
                    nodes_by_type[node_info['type']].append(node_name)
                
                print("\nNodes by type:")
                for node_type, nodes in sorted(nodes_by_type.items()):
                    print(f"  {node_type}: {len(nodes)}")
                    for node in sorted(nodes)[:3]:  # Show first 3
                        print(f"    - {node}")
                    if len(nodes) > 3:
                        print(f"    ... and {len(nodes) - 3} more")
                        
            except Exception as analysis_error:
                print(f"Could not analyze graph: {analysis_error}")


def main():
    """Main entry point"""
    try:
        ui = MatplotlibGraphUI()
        ui.run()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
