var graph = new joint.dia.Graph({}, {
    cellNamespace: joint.shapes
});

const paper = new joint.dia.Paper({
    el: document.getElementById('paper'),
    width: 800,
    height: 900,
    model: graph,
    cellViewNamespace: joint.shapes,
    gridSize: 10,
    async: true,
    sorting: joint.dia.Paper.sorting.APPROX,
    snapLinks: true,
    linkPinning: false,
    magnetThreshold: 'onleave',
    defaultLink: () => new joint.shapes.standard.Link(),
    anchorNamespace: {
        ...joint.anchors,
        customAnchor
    }
});


function customAnchor(view, magnet, ref, opt, endType, linkView) {
    const elBBox = view.model.getBBox();
    const magnetCenter = view.getNodeBBox(magnet).center();
    const side = elBBox.sideNearestToPoint(magnetCenter);
    let dx = 0;
    let dy = 0;
    const length = ('length' in opt) ? opt.length : 100;
    switch (side) {
        case 'left':
        dx = -length;
        break;
    case 'right':
        dx = length;
        break;
    case 'top':
        dy = -length;
        break;
    case 'bottom':
        dy = length;
        break;

    }
    return joint.anchors.center.call(this, view, magnet, ref, {
      ...opt,
      dx,
      dy
    }, endType, linkView);
}

// Example

var el1 = new joint.shapes.standard.Rectangle({
    position: {
        x: 150,
        y: 150
    },
    size: {
        width: 100,
        height: 150
    },
    ports: {
        groups: {
            main: {
            position: 'absolute',
            attrs: {
                portRect: {
                x: -10,
                y: -10,
                width: 20,
                height: 20,
                fill: 'red',
                stroke: '#333',
                strokeWidth: 2,
                magnet: true
                }
            },
            markup: [{
                tagName: 'rect',
                selector: 'portBody',
                groupSelector: 'portRect'
            }],
            }
        },
        items: [{
            id: 'p1',
            group: 'main',
            args: {
            x: 'calc(w)',
            y: 'calc(h/2)'
            }
        }, {
            id: 'p2',
            group: 'main',
            args: {
            x: 0,
            y: 'calc(h/2)'
            }
        }, {
            id: 'p3',
            group: 'main',
            args: {
            x: 'calc(w/2)',
            y: 0
            }
        }, {
            id: 'p4',
            group: 'main',
            args: {
            x: 'calc(w/2)',
            y: 'calc(h)'
            }
        }]
    },
});

graph.resetCells([el1]);

el1.getPorts().forEach(port => {
    const link = new joint.shapes.standard.Link({
        source: {
            id: el1.id,
            port: port.id,
            anchor: {
                name: 'center'
            }
        },
            target: {
            id: el1.id,
            port: port.id,
            anchor: {
                name: 'customAnchor'
            },
            connectionPoint: {
                name: 'anchor'
            }
        }
    });
    graph.addCell(link);
});

paper.unfreeze();