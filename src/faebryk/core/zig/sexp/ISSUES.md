# NETLIST - encoding

## Fields
```
(fields
                    ((field
                            "Resistor_SMD:R_0805_2012Metric"
                            (name "Footprint")
                        )
                        (field
                            "~"
                            (name "Datasheet")
                        )
                        (field
                            ()
                            (name "Description")
                        )
                    )
                )
```

should be:
```
  (fields
        (field (name "Footprint") "Resistor_SMD:R_0603_1608Metric")
        (field (name "Datasheet") "~")
        (field (name "Description")))
```

## Sheetpath & Libsource

```
                (sheetpath
                    ((names "/")
                        (tstamps "/")
                    )
                )
                (libsource
                    ((lib "Device")
                        (part "R")
                        (description "Resistor")
                    )
                )
```

should be:

```
      (sheetpath (names "/") (tstamps "/"))
      (libsource (lib "Device") (part "LED") (description "Light emitting diode"))
```
