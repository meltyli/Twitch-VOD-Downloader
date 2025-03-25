from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="twitch-vod-downloader",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A tool to automatically download Twitch streams when streamers go live",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/twitch-vod-downloader",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[
        "streamlink>=5.0.0",
    ],
    entry_points={
        "console_scripts": [
            "twitch-recorder=twitch_recorder:main",
        ],
    },
)
