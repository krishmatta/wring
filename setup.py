from setuptools import setup, find_packages

setup(
    name="wring",
    version="1.0",
    author="Krish Matta",
    author_email="self@krishxmatta.dev",
    packages=find_packages(),
    install_requires=[
        "click",
        "oauthlib",
        "pyyaml",
        "ring_doorbell",
    ],
    entry_points={
        "console_scripts": [
            "wring = wring.cli:cli"
        ],
    },
)
