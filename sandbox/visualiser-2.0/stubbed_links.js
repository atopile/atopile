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

var port_group = {};
port_group['top'] = {
    position: {
        name: 'line',
        args: {
            start: { x: 0, y: 0 },
            end: { x: ('calc(w)'), y: 0 }
        },
    },
    attrs: {
        portBody: {
            magnet: true,
            r: 2,
            fill: '#FFFFFF',
            stroke:'#023047',
        },
    },
    label: {
        position: {
            args: {
                x: 0,
                y: 0,
                angle: 0,
            }, // Can't use inside/outside in combination
            //name: 'inside'
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
};

port_group['bottom'] = {
    position: {
        name: 'line',
        args: {
            start: { x: 0, y: 'calc(h)' },
            end: { x: ('calc(w)'), y: 'calc(h)' }
        },
    },
    attrs: {
        portBody: {
            magnet: true,
            r: 2,
            fill: '#FFFFFF',
            stroke:'#023047',
        },
    },
    label: {
        position: {
            args: {
                x: 0,
                y: 0,
                angle: 0,
            }, // Can't use inside/outside in combination
            //name: 'inside'
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
};

var el1 = new joint.shapes.standard.Rectangle({
    position: {
        x: 150,
        y: 150
    },
    size: {
        width: 100,
        height: 150
    },
});

el1.prop({"ports": { "groups": port_group}});
el1.addPort({
    id: 'test',
    group: 'top',
    attrs: {
        label: {
            text: 'test',
            textAnchor: 'start',
        },
    },
    //markup: '<circle id="Oval" stroke="#000000" fill="#FFFFFF" cx="0" cy="0" r="2"/>'
});

el1.addPort({
    id: 'test2',
    group: 'bottom',
    attrs: {
        label: {
            text: 'test2',
            textAnchor: 'start',
        },
    },
    //markup: '<circle id="Oval" stroke="#000000" fill="#FFFFFF" cx="0" cy="0" r="2"/>'
});

el1.addTo(graph);
//graph.resetCells([el1]);

var el2 = new joint.shapes.standard.Rectangle({
    position: {
        x: 400,
        y: 150
    },
    size: {
        width: 100,
        height: 150
    },
});

el2.prop({"ports": { "groups": port_group}});
el2.addPort({
    id: 'test',
    group: 'top',
    attrs: {
        label: {
            text: 'test',
            textAnchor: 'start',
        },
    },
    markup: '<circle id="Oval" stroke="#000000" fill="#FFFFFF" cx="0" cy="0" r="2"/>'
});

el2.addPort({
    id: 'test2',
    group: 'bottom',
    attrs: {
        label: {
            text: 'test2',
            textAnchor: 'start',
        },
    },
    markup: '<circle id="Oval" stroke="#000000" fill="#FFFFFF" cx="0" cy="0" r="2"/>'
});

el2.addTo(graph);

const link = new joint.shapes.standard.Link({
    source: {
        id: el1.id,
        port: 'test'
    },
    target: {
        id: el2.id,
        port: 'test'
    }
});
graph.addCell(link);

const link2 = new joint.shapes.standard.Link({
    source: {
        id: el1.id,
        port: 'test2',
    },
    target: {
        id: el2.id,
        port: 'test',
    }
});
graph.addCell(link2);

paper.unfreeze();