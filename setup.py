from setuptools import setup, find_packages
# Discover packages from Control/src and Kinematics/src
# Package names: Control.src.challenges, Control.src.esp_bridge, etc.
# package_dir maps prefix -> directory so setuptools finds the right paths
kinematics_packages = [f"Kinematics.src.{p}" for p in find_packages(where="Kinematics/src")]
all_packages = kinematics_packages

# Map package prefix to directory - use "Control.src" -> "Control/src" to avoid double "src"
package_dir = {
    "Kinematics.src": "Kinematics/src",
}

setup(
    name="ROBOX_robot_control_libraries",
    version="0.1",
    packages=all_packages,
    package_dir=package_dir,
    install_requires=[
        "numpy",
        "dynamixel-sdk",
        "scipy",
        "matplotlib",
        "keyboard",
        "PyQt5",
        "pynput",
        "PyQtWebEngine",
        "pymupdf",
        "markdown",
        "pymongo",
        "dnspython",
        "bcrypt",
        "cryptography",
        "requests",
    ],
    author="Suyash Patidar",
    author_email="suyashpatidar1997@gmail.com",
    description="A package for controlling ROBOX a custom Planar robot manipulator, integrating challenges and content.",
    python_requires=">=3.9",
)
