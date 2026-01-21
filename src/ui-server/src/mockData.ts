import type { Build, LogEntry } from './types/mockup-types'

export const mockBuilds: Build[] = [
  {
    id: 'default',
    name: 'default',
    entry: 'main.ato:App',
    status: 'success',
    currentStage: 'complete',
    progress: 100,
    errors: 0,
    warnings: 2,
    duration: 3.4,
    startedAt: '14:32:01',
    finishedAt: '14:32:04',
    stages: [
      { name: 'parsing', status: 'success', duration: 0.2 },
      { name: 'compiling', status: 'success', duration: 1.1 },
      { name: 'linking', status: 'success', duration: 0.8 },
      { name: 'generating', status: 'warning', duration: 0.9 },
      { name: 'verifying', status: 'success', duration: 0.4 },
      { name: 'complete', status: 'success' },
    ]
  },
  {
    id: 'debug',
    name: 'debug',
    entry: 'main.ato:DebugBoard',
    status: 'error',
    currentStage: 'linking',
    progress: 65,
    errors: 3,
    warnings: 1,
    duration: 2.1,
    startedAt: '14:31:55',
    stages: [
      { name: 'parsing', status: 'success', duration: 0.3 },
      { name: 'compiling', status: 'success', duration: 1.0 },
      { name: 'linking', status: 'error', duration: 0.8 },
      { name: 'generating', status: 'pending' },
      { name: 'verifying', status: 'pending' },
      { name: 'complete', status: 'pending' },
    ]
  },
  {
    id: 'production',
    name: 'production',
    entry: 'main.ato:ProductionBoard',
    status: 'idle',
    stages: [
      { name: 'parsing', status: 'pending' },
      { name: 'compiling', status: 'pending' },
      { name: 'linking', status: 'pending' },
      { name: 'generating', status: 'pending' },
      { name: 'verifying', status: 'pending' },
      { name: 'complete', status: 'pending' },
    ]
  },
]

export const mockLogs: LogEntry[] = [
  {
    id: '1',
    level: 'info',
    message: 'Build started for target: default',
    timestamp: '14:32:01.234',
    buildTarget: 'default',
    stage: 'parsing',
  },
  {
    id: '2',
    level: 'debug',
    message: 'Parsing module ElectricPower from standard library',
    timestamp: '14:32:01.456',
    source: 'stdlib/ElectricPower.ato',
    line: 1,
    buildTarget: 'default',
    stage: 'parsing',
    details: 'Loading interface definition with voltage and current parameters',
  },
  {
    id: '3',
    level: 'info',
    message: 'Parsed 24 modules, 18 interfaces',
    timestamp: '14:32:01.678',
    buildTarget: 'default',
    stage: 'parsing',
  },
  {
    id: '4',
    level: 'warning',
    message: 'Capacitor C1 has no package constraint, defaulting to 0402',
    timestamp: '14:32:02.123',
    source: 'power_supply.ato',
    line: 45,
    column: 12,
    buildTarget: 'default',
    stage: 'compiling',
    details: `Capacitor declared without explicit package size:

    decoupling_cap = new Capacitor
    decoupling_cap.capacitance = 100nF +/- 20%
    # Missing: decoupling_cap.package = "0402"

Consider adding a package constraint to ensure correct footprint selection.`,
    raw: `[2024-01-19 14:32:02.123] WARN  atopile.compiler.constraints
  File "power_supply.ato", line 45, column 12
    decoupling_cap = new Capacitor
    ^
  ConstraintWarning: No package constraint specified for Capacitor instance 'decoupling_cap'.
  Defaulting to package size '0402' based on capacitance value.
  
  Stack trace:
    compiler/constraints.py:234 in check_passive_constraints
    compiler/visitor.py:567 in visit_NewStatement
    compiler/main.py:123 in compile_module`,
  },
  {
    id: '5',
    level: 'debug',
    message: 'Resolving interface connections for I2C bus',
    timestamp: '14:32:02.345',
    source: 'main.ato',
    line: 78,
    buildTarget: 'default',
    stage: 'linking',
  },
  {
    id: '6',
    level: 'error',
    message: 'Cannot connect ElectricPower to I2C interface',
    timestamp: '14:32:02.567',
    source: 'sensors.ato',
    line: 23,
    column: 8,
    buildTarget: 'debug',
    stage: 'linking',
    details: `Type mismatch in connection statement:

    sensor.power ~ i2c_bus  # Error: incompatible types

ElectricPower interface cannot be connected to I2C interface.
Did you mean to connect sensor.power to a power supply?

Suggestion:
    sensor.power ~ power_3v3
    sensor.i2c ~ i2c_bus`,
    raw: `[2024-01-19 14:32:02.567] ERROR atopile.linker.connections
  File "sensors.ato", line 23, column 8
    sensor.power ~ i2c_bus
           ^~~~~
  TypeError: Cannot connect interface of type 'ElectricPower' to interface of type 'I2C'.
  
  ElectricPower has members: [hv: Electrical, lv: Electrical, voltage: V]
  I2C has members: [scl: ElectricLogic, sda: ElectricLogic, frequency: Hz, address: dimensionless]
  
  These interfaces are not compatible for direct connection.
  
  Stack trace:
    linker/connections.py:156 in check_connection_types
    linker/visitor.py:234 in visit_ConnectStatement
    linker/main.py:89 in link_module`,
  },
  {
    id: '7',
    level: 'warning',
    message: 'Resistor R3 tolerance may be too tight for part picker',
    timestamp: '14:32:03.012',
    source: 'voltage_divider.ato',
    line: 12,
    buildTarget: 'default',
    stage: 'generating',
    details: `The specified tolerance of 0.1% is very tight:

    r_top.resistance = 10kohm +/- 0.1%

This may limit available parts. Consider using +/- 1% for better part availability.`,
  },
  {
    id: '8',
    level: 'error',
    message: 'Undefined reference to module "BME280_driver"',
    timestamp: '14:32:02.789',
    source: 'sensors.ato',
    line: 5,
    column: 20,
    buildTarget: 'debug',
    stage: 'linking',
    details: `Module not found in current scope:

    from "bme280.ato" import BME280_driver

The file "bme280.ato" was not found. Check that:
1. The package is installed: ato add atopile/bosch-bme280
2. The import path is correct
3. The module name matches the export`,
  },
  {
    id: '9',
    level: 'error',
    message: 'Pin "VCC" not found on component U2',
    timestamp: '14:32:02.891',
    source: 'power.ato',
    line: 67,
    column: 4,
    buildTarget: 'debug',
    stage: 'linking',
    details: `Component U2 (LDO_3V3) does not have a pin named "VCC".

Available pins: VIN, VOUT, GND, EN

Did you mean "VIN"?`,
  },
  {
    id: '10',
    level: 'info',
    message: 'Generated KiCad schematic: build/default/main.kicad_sch',
    timestamp: '14:32:03.456',
    buildTarget: 'default',
    stage: 'generating',
  },
  {
    id: '11',
    level: 'info',
    message: 'Generated KiCad PCB: build/default/main.kicad_pcb',
    timestamp: '14:32:03.678',
    buildTarget: 'default',
    stage: 'generating',
  },
  {
    id: '12',
    level: 'debug',
    message: 'Running DRC verification on generated PCB',
    timestamp: '14:32:03.789',
    buildTarget: 'default',
    stage: 'verifying',
  },
  {
    id: '13',
    level: 'info',
    message: 'Build completed successfully with 2 warnings',
    timestamp: '14:32:04.123',
    buildTarget: 'default',
    stage: 'complete',
  },
]
