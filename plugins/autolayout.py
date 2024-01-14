from pcbnew import *
import math
import os
import time

class LEDLayoutPlugin(ActionPlugin):
    def defaults(self):
        self.name = "LED Griddy"
        self.category = "Set 5050 LEDs to a super tight grid."
        self.description = "Layout components on PCB in same spatial relationships as components on schematic"
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), 'griddy.png') # Optional, defaults to ""

    def Run(self):
        originx = 0
        originy = 0
        COLS = 8
        ROWS = 12
        C2C = 7 # LED Center to Center grid unit
        board = GetBoard()
        print(board.GetFileName())

        originLED = board.FindFootprintByReference('LED1')
        if not originLED.IsSelected():
            print("NO MODULE SELCTED FOR LAYOUT")
            return
        # Find/Create LED_GRID PCB Group
        group = None
        groups = board.Groups()
        for g in groups:
            if "led_grid" in g.GetName():
                group = g
        if not group:
            group = PCB_GROUP(board)
            group.SetName("led_grid")
            board.Add(group)

        # Clear out old vias and fills
        items2del = []
        for item in group.GetItems():
            if any(kw in item.GetFriendlyName() for kw in ['Zone', 'Via', 'Track']):
                items2del.append(item)
        for i in items2del: board.Remove(i)

        # Set origin to LED1
        if not originLED:
            raise Exception
            return
        else:
            originx, originy = ToMM(originLED.GetPosition())

        for footprint in board.GetFootprints():
            ref = footprint.GetReference()
            digits = ''.join(filter(str.isdigit, ref))
            letters = ''.join(filter(str.isalpha, ref))

            if 'LED' in letters:
                footprint.SetOrientationDegrees(-13)

        # Clear existing zones
        # init_zones = board.Zones()
        # z2del = []
        # for z in init_zones:
        #     if "LED_ROW" in z.GetZoneName():
        #         z2del.append(z)
        
        # for zdel in z2del:
        #     board.Remove(zdel)

        for r in range(ROWS):
            # ADD Copper pours for each new row
            # GND
            gndpoints = (
                VECTOR2I_MM(originx-3.75,originy-3.75+r*C2C),
                VECTOR2I_MM(originx+53.25,originy-3.75+r*C2C),
                VECTOR2I_MM(originx+53.25,originy-0.25+r*C2C),
                VECTOR2I_MM(originx-3.75,originy-0.25+r*C2C)
            )
            z = ZONE(board)
            z.SetLayer(F_Cu)
            z.AddPolygon( VECTOR_VECTOR2I(gndpoints) )
            z.SetIsFilled(True)
            z.SetNet(board.FindNet("gnd-1"))
            z.SetZoneName(f'LED_ROW_{r+1}_GND_ZONE')
            z.SetPadConnection(ZONE_CONNECTION_FULL)
            board.Add(z)
            group.AddItem(z)

            # VCC
            vccpoints = (
                VECTOR2I_MM(originx-3.75,originy-0.25+r*C2C),
                VECTOR2I_MM(originx+53.25,originy-0.25+r*C2C),
                VECTOR2I_MM(originx+53.25,originy+3.25+r*C2C),
                VECTOR2I_MM(originx-3.75,originy+3.25+r*C2C)
            )
            z = ZONE(board)
            z.SetLayer(F_Cu)
            z.AddPolygon( VECTOR_VECTOR2I(vccpoints) )
            z.SetIsFilled(True)
            z.SetNet(board.FindNet("vcc-7"))
            z.SetZoneName(f'LED_ROW_{r+1}_VCC_ZONE')
            z.SetPadConnection(ZONE_CONNECTION_FULL)
            board.Add(z)
            group.AddItem(z)

            # fill board
            # filler = ZONE_FILLER(board)
            # filler.Fill(board.Zones())

            # Add row DIN DOUT vias
            vdin = PCB_VIA(board)
            vdin.SetPosition(VECTOR2I_MM(originx-3, originy+r*C2C) )
            vdin.SetDrill(FromMM(0.4))
            vdin.SetWidth(FromMM(1))
            board.Add(vdin)
            group.AddItem(vdin)

            vdout = PCB_VIA(board)
            vdout.SetPosition(VECTOR2I_MM(originx+3+(COLS-1)*C2C, originy+r*C2C) )
            vdout.SetDrill(FromMM(0.4))
            vdout.SetWidth(FromMM(1))
            board.Add(vdout)
            group.AddItem(vdout)

            for c in range(COLS):
                i = (r*COLS)+c # 1 index for designator
                ledx = originx + (i%COLS)*C2C
                ledy = originy + round(C2C*math.floor(i/COLS), 6)

                led = board.FindFootprintByReference(f"LED{i+1}")
                cap = board.FindFootprintByReference(f"CLED{i+1}")
                if led:
                    group.AddItem(led)
                    led.SetOrientationDegrees(167)
                    led.SetPosition(VECTOR2I_MM(ledx, ledy))
                    led.Reference().SetTextWidth(FromMM(0.7))
                    led.Reference().SetTextWidth(FromMM(0.7))
                    led.Reference().SetTextThickness(FromMM(0.1))
                    led.Reference().SetHorizJustify(-1)
                    led.Reference().SetPosition(VECTOR2I_MM(ledx, ledy-3.5))
                if cap:
                    group.AddItem(cap)
                    cap.SetOrientationDegrees(-13)
                    cap.SetPosition(VECTOR2I_MM(ledx-1, ledy-3.75) )
                    cap.Reference().SetVisible(False)
                    cap.Value().SetVisible(False)
                # Connect data with track
                if c<COLS-1:
                    t = PCB_TRACK(board)
                    t.SetStart(VECTOR2I_MM(ledx+2.8, ledy-1))
                    t.SetEnd(VECTOR2I_MM(ledx+4.2, ledy+1))
                    t.SetWidth(FromMM(0.254))
                    t.SetLayer(F_Cu)
                    board.Add(t)
                    group.AddItem(t)


        Refresh()
        # work_dir, in_pcb_file = os.path.split(board.GetFileName())
        # os.chdir(work_dir)
        # root_schematic_file = os.path.splitext(in_pcb_file)[0] + '.sch'
        # print('work_dir = {}'.format(work_dir), file=sys.stderr)
        # print('in_pcb_file = {}'.format(in_pcb_file), file=sys.stderr)
        # print('root_schematic_file = {}'.format(root_schematic_file), file=sys.stderr)

LEDLayoutPlugin().register()