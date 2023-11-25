// Visual settings for the viewer
export let settings_dict = {
    common: {
        backgroundColor: 'rgba(224, 233, 227, 0.3)',
        gridSize: 15,
        parentPadding: 45,
        fontFamily: "monospace",
    },
    component : {
        strokeWidth: 2,
        fontSize: 8,
        fontWeight: "bold",
        defaultWidth: 60,
        portPitch: 15,
        defaultHeight: 50,
        labelHorizontalMargin: 15,
        labelVerticalMargin: 15,
        titleMargin: 5,
        portLabelToBorderGap: 3,
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
    },
    interface: {
        fontSize: 8,
        color: "blue",
        strokeWidth: 3,
    }
}