from typing import List, Tuple


class RangedValue:
    def __init__(self, name: str, min_value: float, max_value: float, expanding: bool, series: bool):
        self.name = name
        self.min_value = min_value
        self.max_value = max_value
        self.expanding = expanding # supply vs demand?
        self.series = series # do we sum these values or not?

"""
eg.
power_supply.power_out.voltage = 2.8V to 3.2V

"""

example_interfaces = [
    RangedValue("power_supply.power_out.voltage", 2.8, 3.2, True, False),
    RangedValue("power_supply.power_out.max_voltage", 1.8, 12, False, False),
    RangedValue("micro", 2.2, 3.4, False, False),
    RangedValue("imu", 1.8, 3.5, False, False),
]

"""
eg.
micro.sda.vol = 0V to 0.8V
micro.sda.vil = 0V to 1.2V
"""

example_interfaces = [
    RangedValue("micro-sda-vol", 0, 0.8, True, False),
    RangedValue("micro-sda-vil", 0, 1.2, False, False),
    RangedValue("imu-sda-vol", 0, 0.7, True, False),
    RangedValue("imu-sda-vil", 0, 0.9, False, False),
    RangedValue("temp-sda-vol", 0, 0.85, True, False),
    RangedValue("temp-sda-vol", 0, 1.1, False, False),
]

example_interfaces = [
    RangedValue("micro-sda-voh", 2.2, 3.3, True, False),
    RangedValue("micro-sda-vih", 2, 3.3, False, False),
    RangedValue("imu-sda-voh", 2.4, 3.3, True, False),
    RangedValue("imu-sda-vih", 1.9, 3.3, False, False),
    RangedValue("temp-sda-voh", 2.8, 3.3, True, False),
    RangedValue("temp-sda-vih", 1.8, 3.3, False, False),
]


def find_union_of_ranged_values(ranged_values: List[RangedValue]) -> RangedValue:
    #if they are series, we sum them
    if all([ranged_value.series for ranged_value in ranged_values]):
        # Calculate the sum of min and max values
        min_union = sum([ranged_value.min_value for ranged_value in ranged_values])
        max_union = sum([ranged_value.max_value for ranged_value in ranged_values])

    elif not any([ranged_value.series for ranged_value in ranged_values]):
        # Initialize min and max with the first RangedValue's min and max values
        min_union, max_union = ranged_values[0].min_value, ranged_values[0].max_value

        for ranged_value in ranged_values[1:]:
            # Update min and max values if the current RangedValue extends beyond the current union's bounds
            min_union = min(min_union, ranged_value.min_value)
            max_union = max(max_union, ranged_value.max_value)

        # Return a new RangedValue representing the union of all provided RangedValues
    return RangedValue("union", min_union, max_union, True, ranged_values[0].series)

def find_intersection_of_ranged_values(ranged_values: List[RangedValue]) -> RangedValue:
    # Initialize min and max with the first RangedValue's min and max values
    min_intersection, max_intersection = ranged_values[0].min_value, ranged_values[0].max_value

    for ranged_value in ranged_values[1:]:
        # Update min and max values to find the intersection
        min_intersection = max(min_intersection, ranged_value.min_value)
        max_intersection = min(max_intersection, ranged_value.max_value)
        # If there is no intersection
        if min_intersection > max_intersection:
            return RangedValue("no_intersection", 0.0, 0.0, False, False)  # or any indication that there's no intersection

    return RangedValue("intersection", min_intersection, max_intersection, False, False)


#1. find the union of all the expanding ranged values
#2. find the intersection of all the non-expanding ranged values

# do this for non summing ranges eg voltage:
# Expanding ranges are those that assert something will be true, eg a power supply
expanding_attributes = [ranged_value for ranged_value in example_interfaces if ranged_value.expanding]
expanding_range = find_union_of_ranged_values(expanding_attributes)

# Contracting ranges are those that assert something will not be true, eg an abs max rating on a microcontroller
contracting_attributes = [ranged_value for ranged_value in example_interfaces if not ranged_value.expanding]
contracting_range = find_intersection_of_ranged_values(contracting_attributes)

# Check if the intersection of the contracting ranges is within the union of the expanding ranges
intersection = find_intersection_of_ranged_values([expanding_range, contracting_range])
# print out the result nicely (min val, max val and a pass if the intersection is within the union)
print(f"intersection: {intersection.min_value}, {intersection.max_value}, {intersection.min_value <= expanding_range.min_value and intersection.max_value >= expanding_range.max_value}")



example_interfaces_summing = [
    RangedValue("power_supply.power_out.current", 0.02, 4, False, True),
    RangedValue("micro.power.max_current", 0.05, 0.5, True, True),
    RangedValue("imu.power.max_current", 0.15, 0.3, True, True),
    RangedValue("motor_driver.power.max_current", 0.1, 2.5, True, True),
]


# do this for summing ranges eg current:
expanding_attributes = [ranged_value for ranged_value in example_interfaces_summing if ranged_value.expanding]
expanding_range = find_union_of_ranged_values(expanding_attributes)
print(round(expanding_range.min_value, 2), round(expanding_range.max_value, 2))

contracting_attributes = [ranged_value for ranged_value in example_interfaces_summing if not ranged_value.expanding]
contracting_range = find_intersection_of_ranged_values(contracting_attributes)
print(round(contracting_range.min_value, 2), round(contracting_range.max_value, 2))

intersection = find_intersection_of_ranged_values([expanding_range, contracting_range])
print(f"intersection: {intersection.min_value}, {intersection.max_value}, {intersection.min_value <= expanding_range.min_value and intersection.max_value >= expanding_range.max_value}")

