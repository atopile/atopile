(function eventsGraphEvents() {

    var namespace = joint.shapes;

    var graph = new joint.dia.Graph({}, { cellNamespace: namespace });

    var paper = new joint.dia.Paper({
        el: document.getElementById('paper-events-graph-events'),
        model: graph,
        width: 600,
        height: 600,
        gridSize: 1,
        background: {
            color: 'white'
        },
        interactive: true,
        cellViewNamespace: namespace
    });


    var element = new joint.shapes.standard.Rectangle();
    element.position(100, 30);
    element.resize(100, 40);
    element.attr({
        body: {
            fill: 'white',
            stoke: 'black'
        }
    });
    element.addTo(graph);

    var element2 = new joint.shapes.standard.Rectangle();
    element2.position(100, 30);
    element2.resize(140, 80);
    element2.attr({
        body: {
            fill: 'transparent',
            stoke: 'black'
        }
    });
    element.addTo(graph);

    function return_point(endView, endMagnet, anchorReference, args) {
        return new g.Point(450, 50);
    }

    //paper.options.defaultAnchor = {return_point};

    var link = new joint.shapes.standard.Link();
    link.source(element);
    link.target(model, {
        anchor: return_point});
    link.attr({
        line: {
            cursor: 'move',
            stroke: 'black'
        },
        wrapper: {
            cursor: 'move'
        }
    });
    link.labels([
        {
            markup: [{
                tagName: 'rect',
                selector: 'body'
            }, {
                tagName: 'text',
                selector: 'label'
            }],
            attrs: {
                label: {
                    pointerEvents: 'none',
                    text: '450@50',
                    textAnchor: 'middle',
                    textVerticalAnchor: 'middle',
                    fontSize: 12,
                    fill: 'black'
                },
                body: {
                    ref: 'label',
                    refX: '-10%',
                    refY: '-10%',
                    refWidth: '120%',
                    refHeight: '120%',
                    pointerEvents: 'none',
                    fill: 'white',
                    stroke: 'black',
                    strokeWidth: 2
                }
            },
            position: -45
        }
    ]);
    link.addTo(graph);

    graph.on('change:position', function(cell) {
        var center = cell.getBBox().center();
        var label = center.toString();
        cell.attr('label/text', label);
    });

    graph.on('change:target', function(cell) {
        var target = new g.Point(cell.target());
        var label = target.toString();
        cell.label(0, {
            attrs: {
                label: {
                    text: label
                }
            }
        });
    });
}());