# Custom timing constraints for 6502 MCU
#
# This file includes base constraints plus multicycle paths for the data bus

# Source the base SDC constraints first
source $::env(SCRIPTS_DIR)/base.sdc

# Allow data bus (uio_in) paths to take 2 clock cycles
# This is appropriate because the CPU runs with a clock divider,
# so external bus data doesn't need to meet single-cycle timing

puts "\[INFO\] Applying multicycle path constraints for uio_in..."

# Setup: Allow 2 clock cycles for paths from uio_in to any register
set_multicycle_path -from [get_ports uio_in[*]] -to [all_registers] -setup 2

# Hold: Adjust hold to match (hold is always setup - 1)
set_multicycle_path -from [get_ports uio_in[*]] -to [all_registers] -hold 1

puts "\[INFO\] Multicycle path constraints applied successfully"
