import os
import sys
from pathlib import Path

from cocotb_tools.runner import get_runner


def get_sources_for_module(proj_path, module):
    """Get the source files needed for a specific module test"""
    src_path = proj_path / "src"
    test_path = proj_path / "test"

    if module == "sk6812rgbw":
        return [
            test_path / "test_sk6812rgbw.sv",
            src_path / "sk6812rgbw.sv",
        ]
    elif module == "cpu":
        return [
            test_path / "test_cpu.sv",
            src_path / "cpu.sv",
        ]
    elif module == "spi_slave":
        return [
            test_path / "test_spi_slave.sv",
            src_path / "spi_slave.sv",
            src_path / "dff_sync.sv",
        ]
    elif module == "spi_master":
        return [
            test_path / "test_spi_master.sv",
            src_path / "spi_master.sv",
        ]
    elif module == "spi_master_cpha1":
        return [
            test_path / "test_spi_master_cpha1.sv",
            src_path / "spi_master.sv",
        ]
    elif module == "spi_flash":
        return [
            test_path / "test_spi_flash.sv",
            src_path / "spi_flash.sv",
            src_path / "spi_master.sv",
        ]
    elif module == "led_controller":
        sources = [test_path / "test_led_controller.sv"]
        [sources.append(p) for p in proj_path.glob("src/*.sv")]
        return sources
    else:
        raise ValueError(f"Unknown module: {module}")


def get_toplevel_for_module(module):
    """Get the toplevel module name for a specific test"""
    if module == "sk6812rgbw":
        return "test_sk6812rgbw"
    elif module == "cpu":
        return "test_cpu"
    elif module == "spi_slave":
        return "test_spi_slave"
    elif module == "spi_master":
        return "test_spi_master"
    elif module == "spi_master_cpha1":
        return "test_spi_master_cpha1"
    elif module == "spi_flash":
        return "test_spi_flash"
    elif module == "led_controller":
        return "test_led_controller"
    else:
        raise ValueError(f"Unknown module: {module}")


def get_test_module_name(module):
    """Get the Python test module for a specific hardware module"""
    if module == "sk6812rgbw":
        return "test.test_sk6812rgbw"
    elif module == "cpu":
        return "test.test_cpu"
    elif module == "spi_slave":
        return "test.test_spi_slave"
    elif module == "spi_master":
        return "test.test_spi_master"
    elif module == "spi_master_cpha1":
        return "test.test_spi_master_cpha1"
    elif module == "spi_flash":
        return "test.test_spi_flash"
    elif module == "led_controller":
        return "test.test_led_controller"
    else:
        raise ValueError(f"Unknown module: {module}")


def run_module(module):
    """Run tests for a specific module"""
    os.environ['WAVES'] = '1'
    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent
    sources = get_sources_for_module(proj_path, module)
    toplevel = get_toplevel_for_module(module)
    test_module_name = get_test_module_name(module)

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel=toplevel,
        waves=True,
        build_dir=f"sim_build/{module}"
    )

    runner.test(hdl_toplevel=toplevel, test_module=f"{test_module_name},")


def run_all_modules():
    """Run tests for all modules"""
    modules = ["sk6812rgbw", "cpu", "spi_slave", "spi_master", "spi_flash", "led_controller"]
    for module in modules:
        print(f"\n{'='*60}")
        print(f"Running tests for: {module}")
        print('='*60)
        run_module(module)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        module = sys.argv[1]
        if module == "all":
            run_all_modules()
        else:
            run_module(module)
    else:
        # Default to running all tests
        run_all_modules()
