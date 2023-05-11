const { shapes, util, dia, anchors } = joint;

class AtoElement extends dia.Element {
    defaults() {
        return {
            ...super.defaults,
            hidden: false
        };
    }

    isHidden() {
        return Boolean(this.get("hidden"));
    }

    static isAtoElement(shape) {
        return shape instanceof AtoElement;
    }
}

class AtoComponent extends AtoElement {
    defaults() {
        return {
            ...super.defaults(),
            type: "AtoComponent",
            size: { width: 200, height: 50 },
            attrs: {
                body: {
                    fill: "white",
                    stroke: "black",
                    strokeWidth: 2,
                    width: "calc(w)",
                    height: "calc(h)",
                    rx: 5,
                    ry: 5
                },
                label: {
                    text: "Component",
                    fill: "black",
                    fontSize: 12,
                    fontWeight: "bold",
                    textVerticalAnchor: "middle",
                    textAnchor: "middle",
                    fontFamily: "sans-serif",
                    x: "calc(w/2)",
                    y: "calc(h/2)"
                }
            }
        };
    }

    preinitialize() {
        this.markup = util.svg`
            <rect @selector="body" />
            <text @selector="label" />
        `;
    }

    addConnection(name, port) {
        this.addPort({ 
            group: port,
            attrs: { 
                label: { 
                    text: name,
                    fontFamily: "sans-serif",
                }
            }
        });
    }

    addNewPort(groupName, side) {
        this.prop({ports: { // This section describes what a port looks like
                    groups: {
                        [groupName]: {
                        position: {
                            name: side
                        },
                        attrs: {
                            portBody: {
                                magnet: true,
                                r: 5,
                                fill: '#FFFFFF',
                                stroke:'#023047'
                            }
                        },
                        label: {
                            position: {
                                name: side,
                                args: { y: 0 }
                            },
                            markup: [{
                                tagName: 'text',
                                selector: 'label',
                                className: 'label-text'
                            }]
                        },
                        markup: [{
                            tagName: 'circle',
                            selector: 'portBody'
                        }]
                    }
                    }
                }
            });
    }
}

const cellNamespace = {
    ...shapes,
    AtoElement,
    AtoComponent
};

function createComponent(title, x, y, module) {
    const component = new AtoComponent({
        attrs: {
            label: {
                text: title
            }
        }
    });
    component.position(x, y, { parentRelative: false });
    component.addTo(graph);
    return component;
}

const graph = new dia.Graph({}, { cellNamespace });
const paper = new joint.dia.Paper({
    el: document.getElementById('myholder'),
    model: graph,
    width: 600,
    height: 600,
    gridSize: 10,
    drawGrid: true,
    background: {
        color: 'rgba(0, 255, 0, 0.3)'
    },
    cellViewNamespace: cellNamespace
});

test = createComponent('allo', 10, 10);
test.addNewPort('port 1', 'right');
test.addConnection('pin 1', 'port 1');
test.addConnection('pin 3', 'port 1');
test.addNewPort('port 2', 'left');
test.addConnection('pin 2', 'port 2');
test.addConnection('pin 4', 'port 2');

var ports = test.getPorts();
console.log(ports)
console.log(typeof ports)
console.log(test.getGroupPorts('port 1'))
let result = test.prop('ports/groups')
console.log(typeof result)
console.log(result['port 1']['position']['name'])
    for (var listItem of result) {
        console.log('new element')
        console.log(listItem)
    }
// use this to check that the port exists and add height or width accordingly.

test.resize(100, 100);

paper.on('cell:pointerup', function(evt, x, y) {
    const requestOptions = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(graph.toJSON()) // << data going the other way
    };
    fetch('/api/graph', requestOptions);
});



