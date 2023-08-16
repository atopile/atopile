// Visual settings for the viewer
export let settings_dict = {
    common: {
        backgroundColor: 'rgba(224, 233, 227, 0.3)',
        gridSize: 5,
        parentPadding: 50,
        fontFamily: "monospace",
        fontHeightToPxRatio: 1.6,
        fontLengthToPxRatio: 0.7,
    },
    component : {
        strokeWidth: 2,
        fontSize: 8,
        fontWeight: "bold",
        defaultWidth: 60,
        portPitch: 20,
        defaultHeight: 50,
        labelHorizontalMargin: 30,
        labelVerticalMargin: 4,
        titleMargin: 10,
        pin: {
            fontSize: 8,
            fontWeight: "normal",
        },
    },
    block : {
        strokeWidth: 2,
        boxRadius: 5,
        strokeDasharray: '4,4',
        label: {
            fontSize: 8,
            fontWeight: "bold",
        }
    },
    link: {
        strokeWidth: 1,
        color: "blue"
    },
    stubs: {
        fontSize: 8,
    }
}